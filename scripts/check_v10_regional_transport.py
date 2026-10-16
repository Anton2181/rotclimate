"""User-run fixed transport comparison; default prints a plan only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from experiments import v10_regional_transport as model,v10_boundary_lab as laboratory
from scripts import check_v10_spatial_humidity as source,review_v10_spatial_humidity as review
from scripts import check_v10_split_column as checkpoints,replay_v10_delivery as replay
from scripts import audit_v10_flux_transport as closed_audit
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256

SOURCE=ROOT/'output/v10_spatial_humidity'
PREFLIGHT=ROOT/'output/v10_regional_transport_preflight'
DEFAULT_OUT=ROOT/'output/v10_regional_transport'
verify_completed=source.run.previous.verify_completed


def source_id():
    h=hashlib.sha256(source.source_id().encode()+closed_audit.source_id().encode())
    for path in (Path(__file__),Path(model.__file__),Path(model.transport.__file__),Path(laboratory.__file__)):
        h.update(path.read_bytes())
    return h.hexdigest()


def make_jobs(regions):
    return [{'key':f'{phase}_{region}_{mode}','phase':phase,'region':region,'mode':mode,
             'scheme':'upwind' if phase=='control' else 'coupled_fct',
             'source_case':f'test_{region}_{mode}_local_matched'}
            for phase in ('control','candidate') for mode in ('bulk','parcel_lower') for region in regions]


def prepare():
    parent_saved=json.loads((ROOT/'output/v10_flux_transport_lab/audit.json').read_text())
    if parent_saved['code_sha256']!=closed_audit.source_id() or not parent_saved['all_development_gates_pass']:
        raise ValueError('Need unchanged, passing closed transport laboratory evidence.')
    prepared=source.prepare()
    parent,state,inputs,_,records,_,_,_,_=review.load_verified(SOURCE,prepared)
    setting=prepared[2];originals=prepared[5];anchors={};identities={};tables={}
    for region in inputs:
        tables[region]=source.run.previous.read_calendar(source.PREFLIGHT/'forcing'/region,source.forcing_identity(parent,region))[0]
        for mode in ('bulk','parcel_lower'):
            key=f'test_{region}_{mode}_local_matched';folder=SOURCE/'cases'/key;row=state['cases'][key];n=row['years']
            before=checkpoints.read_checkpoint(folder,n-1,inputs[region][0].domain.land.shape,completed=True)
            if before is None:raise ValueError('Need the state preceding the settled source year.')
            anchors[key]={'initial':before[0],'record':records[key],'row':row}
            identities[key]={'source_year':n,'source_start_sha256':sha256(folder/f'year{n-1}.npz'),
                'source_final_sha256':sha256(folder/f'year{n}.npz'),'source_summary_sha256':sha256(folder/'summary.json')}
    protocol={'schema':1,'code_sha256':source_id(),'source_code_sha256':parent['code_sha256'],
        'source_manifest_sha256':sha256(SOURCE/'manifest.json'),'source_state_sha256':sha256(SOURCE/'state.json'),
        'closed_lab_evidence_sha256':{name:sha256(ROOT/'output/v10_flux_transport_lab'/name) for name in ('audit.json','paths.npz')},
        'anchors':identities,'jobs':make_jobs(inputs),'settings':asdict(setting),'minimum_cycles':3,'maximum_cycles':6,
        'seed':67,'forcing_variant':'local_matched','maximum_invocation_hours':4.,
        'forcing':'Exact cached seed67 lift16 aligned dry flow, local humidity pattern and fixed actual monthly gross incoming vapor. No new forcing table or downloads.',
        'transport':'Only internal theta/vapor transfers use shared bounded flux correction. External incoming/outgoing faces retain frozen donor-cell fluxes. Original cloud, soil, relaxation and energy/work conventions remain fixed.',
        'controls':'Four exact final-year upwind replays from their saved preceding-year states. Four FCT candidates start from their paired settled final states and repeat 3–6 cycles.',
        'selection':'Fixed numerical/physical mechanism comparison, no fit, best-seed selection or atlas promotion. Compare coast winter and reference-arid summer errors separately. Reused regions/weather are not untouched validation.',
        'atlas_publication':False,'downloads':False}
    return protocol,inputs,setting,anchors,tables,originals


def driver_for(region,inputs,setting,tables,originals):
    case,p,g,air,c=inputs[region]
    return source.boundary.Driver(originals[region],tables[region],'local_matched',case,p,setting,g,air,c)


def protected_paths():
    from scripts import replay_v10_cloud_geometry as geometry
    return (SOURCE,PREFLIGHT,ROOT/'output/v10_cloud_geometry',ROOT/'output/v10_cloud_lab',ROOT/'output/v10_flux_transport_lab',*geometry.protected_paths())


def check_output_path(out):
    for protected in protected_paths():
        a,b=out.resolve(),protected.resolve()
        if a==b or a in b.parents or b in a.parents:raise ValueError('Preserve completed climates, laboratory evidence and prepared inputs.')


def preflight():
    protocol,inputs,setting,anchors,tables,originals=prepare()
    path=PREFLIGHT/'manifest.json'
    if path.exists():
        saved=json.loads(path.read_text())
        if saved['protocol']!=protocol:raise ValueError('Prepared transport comparison is stale; preserve it for diagnosis.')
        print('Reusing unchanged prepared transport checks; no simulation advanced.',flush=True);return saved
    checks=[];waves={};arrays={};estimates={}
    for n in (16,32,64,128):
        for scheme in ('upwind','coupled_fct'):
            key=f'n{n}_{scheme}';r=laboratory.wave(n,scheme)
            waves[key]={k:v for k,v in r.items() if not isinstance(v,np.ndarray)}
            for k,v in r.items():
                if isinstance(v,np.ndarray):arrays[key+'_'+k]=v
    if not all(waves[f'n{n}_coupled_fct']['theta_mae_k']<waves[f'n{n}_upwind']['theta_mae_k'] for n in (16,32,64,128)):
        raise ValueError('Open manufactured accuracy comparison failed.')
    for region,(case,p,g,air,c) in inputs.items():
        for mode in ('bulk','parcel_lower'):
            key=f'test_{region}_{mode}_local_matched';before=anchors[key]['record'][0]
            driver=driver_for(region,inputs,setting,tables,originals);timings=[];ratios=[]
            for day in (0.,90.,180.,270.):
                flow,q,_=driver.at(day*86400.);dt=min(60.,model.base.stable_step(flow,g.mass,case.domain))
                tick=time.monotonic()
                expected=model.original.advance(before,case.domain,p,setting,flow,dt,day*86400.,air,geometry=g,boundary=q,condensation_mode=mode)
                old_seconds=time.monotonic()-tick
                control=model.advance(before,case.domain,p,setting,flow,dt,day*86400.,air,geometry=g,boundary=q,condensation_mode=mode,transport_scheme='upwind')
                for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(expected[0],name),getattr(control[0],name))
                for i in (1,2,3,5,6,8):np.testing.assert_array_equal(expected[i],control[i])
                if expected[4]!=control[4] or expected[7]!=control[7]:raise ValueError('Upwind step regression failed.')
                tick=time.monotonic()
                result=model.advance(before,case.domain,p,setting,flow,dt,day*86400.,air,geometry=g,boundary=q,condensation_mode=mode)
                elapsed=time.monotonic()-tick;timings.append(elapsed);ratios.append(elapsed/max(old_seconds,1e-9))
                # Independently reconstruct true external vapor and MSE transfer.
                mesh=model.transport.build_mesh(case.domain,g,flow);bq=q.ravel()[mesh.boundary_cell]
                oldq=(before.water/g.mass).ravel()[mesh.boundary_cell]
                target=model.coordinates.targets(case.domain,p,setting,day*86400.,air)[0]
                bh=(model.base.CP*(target+273.15)+model.base.G*g.height_m+model.base.LV*q).ravel()[mesh.boundary_cell]
                oldh=(before.energy/g.mass).ravel()[mesh.boundary_cell]
                area=np.prod(case.domain.land.shape);incoming=mesh.boundary_rate<0
                vapor_outside=dt*mesh.boundary_rate*np.where(incoming,bq,oldq)
                energy_outside=dt*mesh.boundary_rate*np.where(incoming,bh,oldh)
                actual_import=-vapor_outside[incoming].sum()/area
                if abs(actual_import-result[4]['boundary_import_gross_mm'])>1e-10 or abs(vapor_outside.sum()/area-result[4]['boundary_export_mm'])>1e-10 or abs(energy_outside.sum()/area-result[4]['energy_boundary_export_j_m2'])>1e-5:
                    raise ValueError('Independent external flux reconstruction failed.')
                if result[4]['boundary_import_gross_mm']!=control[4]['boundary_import_gross_mm']:
                    raise ValueError('Corrected transport changed prescribed incoming vapor.')
                checks.append({'region':region,'mode':mode,'day':day,'dt_s':dt,'independent_probe':True,
                    'upwind_arrays_exact':True,'incoming_vapor_identical':True,'external_vapor_heat_verified':True,
                    'water_error_mm':result[4]['water_error_mm'],'energy_error_j_m2':result[4]['energy_error_j_m2'],
                    'temperature_ledger_error_c':result[7],'original_step_seconds':old_seconds,'candidate_step_seconds':elapsed})
            steps=anchors[key]['record'][-1]['steps']
            estimates[f'{region}_{mode}']={'saved_steps_per_cycle':steps,'median_candidate_step_seconds':float(np.median(timings)),
                'median_step_cost_ratio':float(np.median(ratios)),'rough_candidate_cycle_minutes':float(np.median(timings)*steps/60)}
    if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed during transport preparation.')
    low=sum(r['rough_candidate_cycle_minutes'] for r in estimates.values())*3
    high=sum(r['rough_candidate_cycle_minutes'] for r in estimates.values())*6
    data={'protocol':protocol,'checks':checks,'manufactured_waves':waves,'cost_estimates':estimates,
        'rough_candidate_batch_minutes_3_to_6_cycles':[low,high],
        'real_annual_integrations_started':0,'new_downloads':0,'atlas_updated':False,
        'probe_note':'Sixteen independent <=60-second FCT probes and exact upwind comparisons on saved states. Seasonal forcing dates reuse a fixed saved state; they are interface checks, not evolved seasonal climates. Timing extrapolates saved step counts and excludes source verification/checkpoint overhead.'}
    atomic_npz(PREFLIGHT/'manufactured_waves.npz',**arrays)
    data['manufactured_arrays_sha256']=sha256(PREFLIGHT/'manufactured_waves.npz')
    atomic_json(path,data)
    print('Prepared: exact upwind probes, identical incoming supply, independent external heat/water checks and fixed eight-case protocol.',flush=True)
    print(f'Rough candidate-only batch estimate {low:.0f}–{high:.0f} minutes, plus four controls and overhead; not a guaranteed ETA.',flush=True)
    return data


def summarize(record,case,check,years,anchor,job):
    row=source.run.summary(record,case,check,years,anchor)
    target=source.run.run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
    groups=review.cloud.groups_for(case,target)
    seasonal=review.seasonal_errors(anchor['record'][1],record[1],case.observed_rain_mm,groups)
    thermal=row['guards']['lower_temperature'] and row['guards']['upper_temperature']
    row.update(transport_scheme=job['scheme'],forcing_variant='local_matched',source_case=job['source_case'],
        physical_control_exact=job['phase']=='control',seasonal_errors=seasonal,
        mechanism_screen=review.process_screen('local_matched',row['coastal_winter_gain_mm'],seasonal,check['passed'],thermal),
        note='Fixed internal transport sensitivity under identical prescribed inflow and cloud/soil/thermal rules. No calibration or atlas selection.')
    return row


def case_run(folder,job,inputs,setting,anchors,tables,originals,stop,log,progress,code_id):
    case,p,g,air,c=inputs[job['region']];anchor=anchors[job['source_case']]
    identity={**job,'code_sha256':code_id,'settings':asdict(setting)};folder.mkdir(parents=True,exist_ok=True)
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text())!=identity:raise ValueError('Transport case identity changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    driver=driver_for(job['region'],inputs,setting,tables,originals)
    state=anchor['initial'] if job['phase']=='control' else anchor['record'][0]
    last=None;check={'passed':False};maximum=1 if job['phase']=='control' else 6
    for year in range(1,maximum+1):
        if source_id()!=code_id:raise ValueError('Transport sources changed.')
        initial=state
        record=checkpoints.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
        if record is None:
            partial=checkpoints.read_checkpoint(folder,year,case.domain.land.shape)
            if partial is not None:source.run.run.validate_control_record(partial,driver.monthly_targets)
            started=time.monotonic();before=partial[-1].get('elapsed_seconds',0.) if partial else 0.
            def save(*record):
                if source_id()!=code_id:raise ValueError('Transport sources changed during integration.')
                info=dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
                checkpoints.write_checkpoint(folder,year,(*record[:4],info))
                progress({'case':job['key'],'year':year,'month':info['month'],'elapsed_year_seconds':info['elapsed_seconds']})
                log(f'{job["key"]}: cycle {year}/{maximum}, month {info["month"]}/12; physical ledgers and incoming supply checked')
            record=model.year(case.domain,p,setting,state,air,case.score_mask,g,driver,
                checkpoint=partial,save_month=save,should_stop=stop,condensation_mode=job['mode'],transport_scheme=job['scheme'])
            record[-1]['elapsed_seconds']=before+time.monotonic()-started
            checkpoints.write_checkpoint(folder,year,record,completed=True)
        source.run.run.validate_control_record(record,driver.monthly_targets)
        review.verify_fields(record,initial,case,g,job['mode'])
        if job['phase']=='control':
            replay.verify_physical(record,anchor['record']);check={'passed':True};break
        if last is not None:check=checkpoints.settling(last,record,case,g)
        state=record[0]
        if year>=3 and check['passed']:break
        last=record
    row=summarize(record,case,check,year,anchor,job)
    row.update(case_config_sha256=sha256(folder/'config.json'),
        elapsed_seconds=sum(json.loads((folder/f'year{n}.json').read_text())['info']['elapsed_seconds'] for n in range(1,year+1)),
        evidence_sha256={f'year{n}.{ext}':sha256(folder/f'year{n}.{ext}') for n in range(1,year+1) for ext in ('json','npz')})
    atomic_json(folder/'summary.json',row);return row


def report(out,state):
    lines=['# Fixed regional transport comparison','',f"Status: {state['status']}; {len(state['cases'])}/8 cases. Atlas unchanged.",'',
        '| Case | Coast winter rain | Change | Monthly MAE change | Med still arid | Settled | Mechanism screen |',
        '|---|---:|---:|---:|---:|---|---|']
    for key,r in state['cases'].items():
        lines.append(f"| {key} | {r['response']['coast_winter_mm']:.2f}mm | {r['coastal_winter_gain_mm']:+.2f}mm | {r['monthly_mae_change_mm']:+.3f}mm | {r['koppen_fixed_surface_temperature']['target_mediterranean_to_arid']:.1%} | {r['settling']['passed']} | {r['mechanism_screen']['passes']} |")
    lines+=['','Four exact upwind controls, four fixed FCT climates. Prescribed incoming water, flow and clouds stay paired. The screen requires reduced reference-arid summer MAE, coastal winter loss <=2mm, settled cycles and existing temperature guards; it is not an atlas publication rule. Seasonal spatial errors are saved in each summary.']
    if state.get('error'):lines+=['','Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def batch(out,hours=1.5,case_runner=case_run,clock=time.monotonic):
    if not np.isfinite(hours) or not 0<hours<=4:raise ValueError('Use an invocation budget above zero and at most four hours.')
    check_output_path(out)
    started=clock();deadline=started+hours*3600
    protocol,inputs,setting,anchors,tables,originals=prepare()
    ready=json.loads((PREFLIGHT/'manifest.json').read_text())
    if ready['protocol']!=protocol or sha256(PREFLIGHT/'manufactured_waves.npz')!=ready['manufactured_arrays_sha256']:
        raise ValueError('Prepared transport checks are stale or changed.')
    if (out/'manifest.json').exists() and json.loads((out/'manifest.json').read_text())!=protocol:
        raise ValueError('Transport protocol changed; preserve output and choose a new folder.')
    state=json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases':{},'invocations':[]}
    if state.get('status')=='needs_diagnosis':raise ValueError('Previous transport failure needs inspection before resume.')
    if state.get('status')=='complete':
        for job in protocol['jobs']:verify_completed(out/'cases'/job['key'],state['cases'][job['key']])
        return state  # Completed evidence is read-only, including state/manifest hashes.
    out.mkdir(parents=True,exist_ok=True)
    if not (out/'manifest.json').exists():atomic_json(out/'manifest.json',protocol)
    state['status']='running';interrupted=[False]
    handler=signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    def stop():return interrupted[0] or clock()>=deadline
    def log(message):
        print(message,flush=True)
        with (out/'run.log').open('a') as f:f.write(message+'\n')
    def progress(info):atomic_json(out/'progress.json',dict(info,completed_jobs=len(state['cases']),planned_jobs=8,elapsed_invocation_seconds=clock()-started))
    try:
        report(out,state)
        for job in protocol['jobs']:
            if source_id()!=protocol['code_sha256']:raise ValueError('Transport sources changed.')
            folder=out/'cases'/job['key']
            if job['key'] in state['cases']:verify_completed(folder,state['cases'][job['key']]);continue
            if stop():raise model.base.BudgetStop()
            log('Start '+job['key'])
            row=case_runner(folder,job,inputs,setting,anchors,tables,originals,stop,log,progress,protocol['code_sha256'])
            if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed while completing transport case.')
            verify_completed(folder,row)
            state['cases'][job['key']]=row;report(out,state)
        state['status']='complete'
    except model.base.BudgetStop:state['status']='interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:state['status']='needs_diagnosis';state['error']=str(error)
    finally:
        signal.signal(signal.SIGINT,handler)
        state['invocations'].append({'elapsed_seconds':clock()-started,'budget_hours':hours,'status':state['status']})
        report(out,state);progress({'status':state['status']})
    return state


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true');p.add_argument('--preflight',action='store_true')
    p.add_argument('--hours',type=float,default=1.5);p.add_argument('--out',type=Path,default=DEFAULT_OUT);a=p.parse_args(argv)
    if a.preflight:preflight();return 0
    print('Four exact upwind controls, then four fixed FCT climates with 3–6 settling cycles. No search, download or atlas update.',flush=True)
    if not a.run:
        print('Read-only plan. User launch: caffeinate -i .venv/bin/python -u scripts/check_v10_regional_transport.py --run --hours 1.5',flush=True);return 0
    state=batch(a.out,a.hours);print('Status: '+state['status'],flush=True)
    return 1 if state['status']=='needs_diagnosis' else 0


if __name__=='__main__':raise SystemExit(main())
