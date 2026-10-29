"""Frozen synthetic pressure-phase equivalence and paired timing benchmark."""
from pathlib import Path
import argparse,json,subprocess,sys,time,platform
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from rotclimate.fast_liquid_phase import enthalpy_phase_fast
from rotclimate.pressure_moist import enthalpy_phase,gas_energy
from rotclimate.phase_adjustment import _saturation


def run(path,out):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed phase benchmark source: '+n)
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal timing declaration first')
    if out.exists() and any(out.iterdir()):raise ValueError('Keep prior timing/equivalence attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);results={};raw={}
    edges=np.array(plan['pressure_edges_pa']);p0=np.sqrt(edges[:-1]*edges[1:]);m0=-np.diff(edges)/9.80665;shape=(len(m0),*plan['horizontal_shape'])
    horizontal=np.arange(np.prod(shape[1:])).reshape(shape[1:]);t=np.broadcast_to(300*(p0/edges[0])[:,None,None]**(287.05*.006/9.80665),shape).copy()+.5*np.sin(horizontal)[None]
    p=np.broadcast_to(p0[:,None,None],shape);m=np.broadcast_to(m0[:,None,None],shape);sat=m*_saturation(t,p)
    for case,factors in [('clear',np.full(shape,.5)),('condensing',np.full(shape,1.2)),('mixed',np.broadcast_to(.7+.5*np.sin(horizontal)[None],shape))]:
        w=sat*factors;durations=dict(reference=[],candidate=[])
        for _ in range(plan['warmups']):enthalpy_phase(t,w,m,p);enthalpy_phase_fast(t,w,m,p)
        values={}
        for repeat in range(plan['repetitions']):
            order=['reference','candidate'] if repeat%2==0 else ['candidate','reference']
            for name in order:
                function=enthalpy_phase if name=='reference' else enthalpy_phase_fast
                start=time.perf_counter();values[name]=function(t,w,m,p);durations[name].append(time.perf_counter()-start)
        old,new=values['reference'],values['candidate'];diffs=[]
        for a,b in zip(old,new):np.testing.assert_allclose(a,b,rtol=1e-9,atol=1e-6);diffs.append(float(abs(a-b).max()))
        errors={}
        for name,(nt,nw,rain,rain_h) in values.items():
            h0=gas_energy(t,w,m).sum(0);ee=float(np.max(abs(gas_energy(nt,nw,m).sum(0)+rain_h-h0))/max(float(abs(h0).max()),1.))
            we=float(np.max(abs(nw.sum(0)+rain-w.sum(0)))/max(float(w.sum(0).max()),1.))
            if max(ee,we)>1e-11:raise ValueError('Actual synthetic phase budget failed')
            errors[name]=dict(actual_energy_relative_error=ee,actual_water_relative_error=we)
            for key,a in zip(['temperature','vapor','rain','rain_enthalpy'],values[name]):raw[case+'_'+name+'_'+key]=a
        raw.update({case+'_input_temperature':t,case+'_input_vapor':w,case+'_input_mass':m,case+'_input_pressure':p})
        old_median=float(np.median(durations['reference']));new_median=float(np.median(durations['candidate']))
        results[case]=dict(timing_seconds=durations,reference_median_s=old_median,candidate_median_s=new_median,median_speedup=old_median/new_median,
            maximum_absolute_differences=dict(zip(['temperature_k','vapor_kg_m2','rain_kg_m2','rain_enthalpy_j_m2'],diffs)),outputs_byte_exact=all(a.tobytes()==b.tobytes() for a,b in zip(old,new)),actual_budgets=errors)
    np.savez_compressed(out/'fields.npz',**raw)
    result=dict(status='synthetic_phase_equivalence_and_timing_complete',new_earth_integrations=0,physics_adoption=False,dynamics_backend_adoption=False,
        results=results,python=platform.python_version(),numpy=np.__version__,plan_sha256=file_hash(path),fields_sha256=file_hash(out/'fields.npz'),
        scope='Synthetic six-level pressure phase only, paired alternating timings, unchanged physical equations. Does not measure end-to-end speed or Earth rainfall accuracy.')
    write_json(out/'verification.json',result)
    print(json.dumps({k:dict(speedup=v['median_speedup'],maximum_absolute_differences=v['maximum_absolute_differences'],byte_exact=v['outputs_byte_exact']) for k,v in results.items()},indent=2))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();run(a.plan,a.out)
