"""Frozen paired24h trajectories with exact scoped transport factor reuse."""
from pathlib import Path
import argparse,json,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import surface_forcing_pilot as legacy
import open_mean_pilot
from local_benchmark_protocol import file_hash,write_json
from rotclimate.phase_backend import make_phase_backend,bind_dependencies
from rotclimate.pressure_moist import enthalpy_phase
from rotclimate.fast_liquid_phase import enthalpy_phase_fast
from rotclimate.shared_transport_backend import make_shared_transport_backend


def backend(name):
    if name not in ['reference','candidate']:raise ValueError('Unknown transport backend')
    return make_shared_transport_backend(reuse=name=='candidate',phase=enthalpy_phase_fast,name=name)

def preparation(selected):
    wind=bind_dependencies(open_mean_pilot.prepare,OpenMeanRigidLidModel=selected.model_type)
    return bind_dependencies(legacy.prepare,prepare_wind=wind)


def run(path,out,preflight=False):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed backend comparison source: '+n)
    if preflight:
        rows=[]
        for region,case_path in plan['case_plans'].items():
            case=json.loads((ROOT/case_path).read_text())
            for name in plan['backend_order'][region]:
                selected=backend(name);prepared=preparation(selected)(case,region)
                assert prepared[2].phase_backend_name==name
                rows.append(dict(region=region,backend=name,shape=list(prepared[3].temperature_k.shape),frozen_code_bodies_unchanged=all(v['same_code_object'] for v in selected.body_sources.values())))
        print(json.dumps(dict(status='transport_backends_prepared_no_integrations',actual_earth_initialized_integrations_started=0,cases=rows,literal_plan_sha256=file_hash(path)),indent=2));return
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal backend protocol before integrating')
    if out.exists() and any(out.iterdir()):raise ValueError('Retain prior backend comparison attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_protocol.json',plan);rows=[]
    for region,case_path in plan['case_plans'].items():
        for name in plan['backend_order'][region]:
            selected=backend(name);timings=[];case_out=out/(region+'_'+name)
            def timed(*args,**kwargs):
                start=time.perf_counter();completed=False
                try:
                    result=selected.surface_coupled(*args,**kwargs);completed=True;return result
                finally:
                    seconds=time.perf_counter()-start
                    record=dict(seconds=seconds,completed=completed)
                    if completed:record['transport']=result.certificate['dynamics_before_surface_return']['dynamics_before_adjustment']['transport_factor_reuse']
                    timings.append(record)
            runner=bind_dependencies(legacy.run,prepare=preparation(selected),advance_surface_coupled=timed,advance_boundary_with_convection=selected.advance_with_convection)
            start=time.perf_counter()
            try:
                runner(ROOT/case_path,case_out)
                receipt=json.loads((case_out/'verification.json').read_text())
                if receipt['actual_earth_initialized_integrations_started']!=1:raise ValueError('Wrong declared backend case count')
                row=dict(region=region,backend=name,status=receipt['results'][0]['status'],earth_integrations_started=1,
                    completed=receipt['integrations_completed'],source_receipt_sha256=file_hash(case_out/'verification.json'))
            except Exception as error:
                case_out.mkdir(parents=True,exist_ok=True);failure=dict(error=repr(error),traceback=traceback.format_exc());write_json(case_out/'driver_failure.json',failure)
                started=0
                if (case_out/'verification.json').exists():started=json.loads((case_out/'verification.json').read_text())['actual_earth_initialized_integrations_started']
                row=dict(region=region,backend=name,status='driver_failed',earth_integrations_started=started,completed=0,error=repr(error))
            row.update(driver_wall_seconds=time.perf_counter()-start,step_timings=timings,body_bindings=selected.body_sources)
            successful=[t['seconds'] for t in timings if t['completed']]
            row['successful_step_median_s']=float(np.median(successful)) if successful else None
            row['successful_steps_total_s']=float(sum(successful))
            row['transport_totals']={key:sum(t['transport'][key] for t in timings if t['completed']) for key in ['solves','factorizations','exact_matrix_reuses']}
            write_json(case_out/'backend_timing.json',row);rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ['step_timings','body_bindings']}),flush=True)
    result=dict(status='paired_shared_transport_earth_input_comparison_complete',actual_earth_initialized_integrations_started=sum(r['earth_integrations_started'] for r in rows),
        integrations_completed=sum(r['completed'] for r in rows),legacy_benchmark_attempts_added=0,monthly_skill=False,physics_adoption=False,numerical_backend_adoption=False,
        literal_plan_sha256=file_hash(path),results=rows,scope='Same fast phase root and frozen24h physics/initial fields. Reference factorizes each tracer solve; candidate reuses only an exactly matching CSC factor within one advance call. Physics and transport code bodies reused. State-equivalence and actual budget checks precede acceptance; no timing speed gate or parameter fitting.')
    write_json(out/'verification.json',result)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--preflight',action='store_true');a=ap.parse_args();run(a.plan,a.out,a.preflight)
