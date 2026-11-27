"""Fixed14-run finite native-parent pressure-context pilot."""
from dataclasses import asdict
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from experiments.nested_pressure_context import nested_pressure
from circulation_components import pressure_velocity
PLAN=ROOT/'calibration/nested_pressure_context_20261127/plan.json'
OUT=ROOT/'output/nested_pressure_context_20261127'
MODEL=OUT/'model'


def check(plan):
    for section in ['model_sources_sha256','execution_sources_sha256','inputs_sha256']:
        for name,digest in plan[section].items():
            assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():
        p=MODEL/name
        assert not p.is_symlink() and p.stat().st_nlink==1 and file_hash(p)==digest,name
    for name,version in plan['libraries'].items():
        assert importlib.metadata.version(name)==version
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
        assert os.environ.get(name)=='1'
    assert os.getpriority(os.PRIO_PROCESS,0)>=10


def exact_control(folder,spec):
    with np.load(folder/'cells'/(spec['region']+'.npz')) as new,np.load(ROOT/spec['control_cells']) as old:
        assert set(new)==set(old)
        for k in old:
            assert new[k].shape==old[k].shape and new[k].dtype==old[k].dtype and new[k].tobytes()==old[k].tobytes(),(spec['region'],k)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    plan=json.loads(PLAN.read_text())
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert len(plan['cases'])==6 and plan['maximum_integrations']==14
    lock=(OUT/'.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (OUT/'failure.json').exists(),'Preserve failure; no automatic retry'
    check(plan)
    assert not any(n=='rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0]=[str(MODEL/'scripts'),str(MODEL)]
    import benchmark_local as benchmark
    from rotclimate import earth,model as physical
    from rotclimate.config import Params
    from rotclimate.koppen import monthly_stats
    assert Path(physical.__file__).resolve().is_relative_to(MODEL.resolve())
    assert Path(benchmark.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    specs=json.loads((ROOT/plan['region_specs']).read_text())
    earth.REGIONS.update(specs)
    params=Params.from_json(ROOT/plan['params'])
    assert params.wind_source==params.sst_source=='model'
    assert params.t_require_convergence and params.moisture_require_convergence and params.solver_require_convergence
    assert params.moisture_residual_tol==.01
    for part in plan['parts']:
        assert json.loads((ROOT/part['control_protocol']).read_text())['params']==json.loads(json.dumps(asdict(params)))
    if not args.run:
        assert not (OUT/'preparation.json').exists()
        actual={}
        for s in plan['cases']:
            actual[s['region']]={}
            for arm,pad,key in [('child',1100.,'case_identity'),('parent',4012.,'parent_case_identity')]:
                actual[s['region']][arm]=case_hash(earth.region_case(s['region'],56.,pad))
                assert actual[s['region']][arm]==s[key]
        freeze(OUT/'preparation.json',dict(plan_sha256=file_hash(PLAN),actual_case_identities=actual,integrations=0))
        print('Prepared six matched parent/child cases; zero integrations',flush=True)
        return
    assert not (OUT/'results.json').exists(),'Preserve completed experiment'
    assert json.loads((OUT/'preparation.json').read_text())['plan_sha256']==file_hash(PLAN)
    freeze(OUT/'protocol.json',dict(plan_sha256=file_hash(PLAN),preparation_sha256=file_hash(OUT/'preparation.json'),
        execution_sources_sha256=plan['execution_sources_sha256'],intervention=plan['intervention']))
    jobs=[('default_off',next(s for s in plan['cases'] if s['region']==n)) for n in plan['default_off_controls']]
    jobs += [('parent',s) for s in plan['cases']]
    jobs += [('nested',s) for s in plan['cases']]
    rows,protocols=[],{}
    for index,(arm,spec) in enumerate(jobs):
        check(plan)
        name,part=spec['region'],spec['part']
        pad=4012. if arm=='parent' else 1100.
        expected=spec['parent_case_identity'] if arm=='parent' else spec['case_identity']
        folder=OUT/(arm+'_'+part)
        for sub in ['cases','cells','attempts']:
            (folder/sub).mkdir(parents=True,exist_ok=True)
        if arm=='nested':
            parents={}
            for p in plan['cases']:
                stem=OUT/('parent_'+p['part'])
                r=json.loads((stem/'cases'/(p['region']+'.json')).read_text())
                assert r['status']=='passed' and r['numerics']['all_checks_passed']
                capture=stem/'cells'/(p['region']+'_context.npz')
                assert file_hash(capture)==r['context_capture_sha256']
                parents[p['region']]=dict(capture=str(capture.relative_to(ROOT)),capture_sha256=file_hash(capture),case_identity=r['case_identity'])
            freeze(OUT/'parents_frozen.json',dict(parents=parents,selection='all six native parents; none selected by accuracy'))
        if (arm,part) not in protocols:
            names=[s['region'] for s in plan['cases'] if s['part']==part and (arm!='default_off' or s['region'] in plan['default_off_controls'])]
            protocols[arm,part]=freeze(folder/'protocol.json',dict(params=asdict(params),regions=names,
                region_specs={n:specs[n] for n in names},cell_km=56.,pad_km=pad,sources=plan['benchmark_protocol_sources_sha256'],
                physical_operator_override=dict(arm=arm,intervention=plan['intervention'] if arm=='nested' else None,
                    parent_manifest_sha256=file_hash(OUT/'parents_frozen.json') if arm=='nested' else None),
                note='Native finite parents; only pressure exterior uses parent anomalies in nested children. Local inputs and moisture boundaries fixed.'))
        identity=protocols[arm,part]
        record=folder/'cases'/(name+'.json')
        attempt=folder/'attempts'/(name+'.json')
        capture=folder/'cells'/(name+'_context.npz')
        if record.exists():
            row=json.loads(record.read_text())
            assert row['status']=='passed' and row['numerics']['all_checks_passed']
            assert row['identity']==identity and row['case_identity']==expected
            assert file_hash(folder/'cells'/(name+'.npz'))==row['cells_sha256']
            assert file_hash(capture)==row['context_capture_sha256']
            if arm=='default_off':
                exact_control(folder,spec)
            rows.append(dict(arm=arm,part=part,**row))
            continue
        assert not attempt.exists(),'Preserve interrupted integration; record recovery separately'
        freeze(attempt,dict(arm=arm,spec=spec,protocol_sha256=file_hash(folder/'protocol.json'),campaign_protocol_sha256=file_hash(OUT/'protocol.json')))
        write_json(OUT/'status.json',dict(stage='integrating',completed=index,total=14,arm=arm,region=name))
        original_run,original_pressure=physical.ClimateModel.run,physical.ClimateModel.pressure_wind
        case=earth.region_case(name,56.,pad)
        assert case_hash(case)==expected
        with np.load(ROOT/spec['control_cells']) as z:
            ii,jj=z['i'].copy(),z['j'].copy()
        if arm=='parent':
            ii,jj=ii+52,jj+52
        parent_anomalies={}
        if arm=='nested':
            f=ROOT/parents[name]['capture']
            assert file_hash(f)==parents[name]['capture_sha256']
            with np.load(f) as z:
                parent_anomalies={float(d):a.copy() for d,a in zip(z['days'],z['anomaly'],strict=True)}
        latest,day,calls={},[None],[0]
        def recorded_pressure(self,anomaly):
            assert day[0] is not None
            if arm=='nested':
                p,g=self.p,self.g
                pres=nested_pressure(parent_anomalies[day[0]],anomaly,52,p.slp_scale_km/g.cell_km,
                    p.slp_local_km/g.cell_km,p.slp_large,p.slp_local,physical.gauss)
                self.last_pres=pres
                velocity=pressure_velocity(pres,self.lat,self.bl_drag,g.dx_m,
                    physical.OMEGA*(-1. if p.retrograde else 1.),physical.RHO_AIR)
            else:
                velocity=original_pressure(self,anomaly)
            latest[day[0]]=(anomaly.copy(),self.last_pres.copy())
            calls[0]+=1
            return velocity
        def recorded_run(self,*a,**kw):
            assert self.tap is None
            def tap(stage,d,values):
                if stage=='zonal':
                    day[0]=float(d)
            self.tap=tap
            try:
                result=original_run(self,*a,**kw)
            finally:
                self.tap=None
            if result.numerics['all_checks_passed']:
                assert set(latest)==set(map(float,result.days))
                fields=dict(days=result.days,anomaly=np.stack([latest[float(d)][0] for d in result.days]),
                    pressure=np.stack([latest[float(d)][1] for d in result.days]),pressure_calls=np.asarray(calls[0]),
                    full_lat=self.lat.copy(),full_lon=case.lon.copy(),wind_i=ii,wind_j=jj,
                    wind_lat=self.lat[ii,jj],wind_lon=case.lon[ii,jj])
                for k in ['u','v']:
                    fields[k]=monthly_stats(getattr(result,k),getattr(result,k),result.days,result.params.year_days)['Tm'][:,ii,jj]
                np.savez_compressed(capture,**fields)
            return result
        physical.ClimateModel.run,physical.ClimateModel.pressure_wind=recorded_run,recorded_pressure
        try:
            row=benchmark.one((name,asdict(params),56.,str(folder),specs,identity,pad))
        except BaseException as error:
            write_json(OUT/'failure.json',dict(arm=arm,region=name,exception=repr(error),automatic_retry=False))
            raise
        finally:
            physical.ClimateModel.run,physical.ClimateModel.pressure_wind=original_run,original_pressure
        if row['status']!='passed' or row['numerics']['all_checks_passed'] is not True:
            write_json(OUT/'failure.json',dict(arm=arm,region=name,record=row,automatic_retry=False))
            raise RuntimeError('Original numerical criteria failed; stop')
        assert row['case_identity']==expected
        if arm=='default_off':
            exact_control(folder,spec)
        row['context_capture_sha256']=file_hash(capture)
        write_json(record,row)
        rows.append(dict(arm=arm,part=part,**row))
        print(f"Native-parent context {index+1}/14: {arm} {name}",flush=True)
    for (arm,part),identity in protocols.items():
        folder=OUT/(arm+'_'+part)
        records={r['region']:{k:v for k,v in r.items() if k not in ['arm','part']} for r in rows if r['arm']==arm and r['part']==part}
        write_json(folder/'summary.json',dict(complete=True,identity=identity,regions=records,params=asdict(params),
            cell_km=56.,pad_km=4012. if arm=='parent' else 1100.,all=benchmark.group_means(records,list(records))))
    check(plan)
    write_json(OUT/'results.json',dict(status='completed_fixed14_native_parent_pilot',rows=rows,integrations=14,
        protocol_sha256=file_hash(OUT/'protocol.json'),atlas_changed=False))
    subprocess.run([str(ROOT/'.venv/bin/python'),'-I',str(ROOT/'scripts/review_nested_pressure_context.py')],cwd=ROOT,check=True)
    write_json(OUT/'status.json',dict(stage='ready_for_agent_review',completed=14))


if __name__=='__main__':
    main()
