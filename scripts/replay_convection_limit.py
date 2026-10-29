"""One frozen rejected-step replay, then static convection work-cap controls."""
from pathlib import Path
import argparse,json,subprocess,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import surface_forcing_pilot as legacy
import lower_cell_resolution_pilot as grid
from local_benchmark_protocol import file_hash,write_json
from rotclimate.phase_backend import bind_dependencies
from rotclimate.convection_observer import observe_convection
from rotclimate.surface_coupling import SurfaceState


def run(path,out):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal replay and static controls before outcomes')
    if out.exists() and any(out.iterdir()):raise ValueError('Retain every previous replay')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_protocol.json',plan);captured=[]
    def observer(record):
        if record['certificate']['converged']:return
        index=len(captured);fields={k:v for k,v in record.items() if isinstance(v,np.ndarray)};target=out/f'closure_input_{index}.npz';np.savez_compressed(target,**fields)
        meta={k:v for k,v in record.items() if k not in fields};meta['fields_sha256']=file_hash(target);write_json(out/f'closure_input_{index}.json',meta);captured.append((fields,meta))
    watched=observe_convection(grid.SELECTED,observer)
    def prepare(case,region):
        values=list(grid.prepare(case,region));base=dict(values[0]);base['regions']={k:dict(v) for k,v in base['regions'].items()};base['regions'][region]['model_day']+=plan['completed_steps_before_rejection']*plan['timestep_s']/86400;values[0]=base
        with np.load(ROOT/plan['source_partial']) as f:a={k:f[k] for k in f.files}
        model=values[2];values[3]=model.initial_state(a['temperature'],a['vapor'],a['u'],a['v']);model._velocity(values[3].u_east,values[3].v_south)
        values[4]=SurfaceState(a['surface_temperature'],a['surface_liquid'],a['substrate_capacity'])
        values[1]=dict(values[1],initial_conversion_rain=np.zeros(model.shape),initial_conversion_rain_enthalpy=np.zeros(model.shape))
        return tuple(values)
    runner=bind_dependencies(legacy.run,prepare=prepare,advance_surface_coupled=watched.surface_coupled,advance_boundary_with_convection=watched.advance_with_convection)
    runner(ROOT/plan['replay_case_plan'],out/'replay');r=json.loads((out/'replay/verification.json').read_text());row=r['results'][0]
    assert r['actual_earth_initialized_integrations_started']==1
    replay_matches=bool(row['status']=='failed' and row['completed_steps']==0 and row['error']==plan['expected_error'] and len(captured)==1)
    weather_exact=None
    if row['status']=='failed':
        with np.load(ROOT/plan['source_partial']) as source,np.load(out/'replay'/plan['region']/'forced/900_partial.npz') as replay:
            weather_exact={k:source[k].tobytes()==replay[k].tobytes() for k in ['temperature','vapor','u','v','surface_temperature','surface_liquid','substrate_capacity']}
        replay_matches=replay_matches and all(weather_exact.values())
    controls=[]
    for index,(a,meta) in enumerate(captured):
        before=(1004*a['cell_mass']+1850*a['input_vapor'])*a['input_temperature']+(2.5e6-1850*273.15)*a['input_vapor'];water0=a['input_vapor'].sum(0)
        for cap in plan['static_maximum_sweeps']:
            start=time.perf_counter();kwargs=dict(meta['controls'],max_sweeps=cap);result=grid.SELECTED.adjustment(a['input_temperature'],a['input_vapor'],a['cell_mass'],a['pressure'],**kwargs);seconds=time.perf_counter()-start
            after=(1004*a['cell_mass']+1850*result.vapor_kg_m2)*result.temperature_k+(2.5e6-1850*273.15)*result.vapor_kg_m2
            er=float(np.max(abs(after.sum(0)+result.ground_rain_enthalpy_j_m2-before.sum(0))/np.maximum(abs(before).sum(0),1.)));wr=float(np.max(abs(result.vapor_kg_m2.sum(0)+result.ground_rain_kg_m2-water0)/np.maximum(water0,1.)))
            target=out/f'closure_{index}_cap{cap}.npz';np.savez_compressed(target,temperature=result.temperature_k,vapor=result.vapor_kg_m2,rain=result.ground_rain_kg_m2,rain_enthalpy=result.ground_rain_enthalpy_j_m2)
            exact=all(getattr(result,k).tobytes()==a[n].tobytes() for k,n in [('temperature_k','output_temperature'),('vapor_kg_m2','output_vapor'),('ground_rain_kg_m2','rain'),('ground_rain_enthalpy_j_m2','rain_enthalpy')])
            c=dict(input_index=index,maximum_sweeps=cap,seconds=seconds,certificate=result.certificate,actual_energy_relative_error=er,actual_water_relative_error=wr,byte_exact_to_captured_target=exact,fields_sha256=file_hash(target));controls.append(c);write_json(target.with_suffix('.json'),c);print(json.dumps(c),flush=True)
    result=dict(status='rejected_step_replay_and_static_caps_finished',actual_earth_initialized_integrations_started=r['actual_earth_initialized_integrations_started'],integrations_completed=r['integrations_completed'],replay_status=row['status'],expected_rejection_reproduced=replay_matches,rejected_weather_state_byte_exact=weather_exact,static_closure_cases=len(controls),static_controls=controls,captured_nonconverged_targets=len(captured),literal_plan_sha256=file_hash(path),replay_receipt_sha256=file_hash(out/'replay/verification.json'),physics_adoption=False,recalibration=False,monthly_skill=False,scope='One actual Earth-input next-step replay counts as a new integration attempt. Its expected rejection remains a numerical failure. Subsequent work-cap solves operate only on the captured static convection input and add no dynamics integrations. Neutral tolerance, phase law, relaxation and planetary parameters unchanged. No failure replaced.')
    write_json(out/'verification.json',result)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan,a.out)
