"""User-run local boundary-humidity test with fixed circulation and dose control."""
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
from experiments import v10_spatial_humidity as boundary
from scripts import replay_v10_cloud_sources as replay,review_v10_cloud_sources as review
from rotclimate_v10.earth import atomic_json,sha256
run=replay.run
physics=replay.model.physics
SOURCE=ROOT/'output/v10_cloud_sources'
PREFLIGHT=ROOT/'output/v10_spatial_humidity_preflight'
BUDGET=90*60.


def source_id():
    h=hashlib.sha256(replay.source_id().encode())
    for path in (Path(__file__),Path(boundary.__file__),Path(review.__file__),Path(boundary.atmosphere.__file__)):h.update(path.read_bytes())
    return h.hexdigest()


def make_jobs(regions):
    jobs=[]
    for region in regions:
        for mode in ('bulk','parcel_lower'):jobs.append({'key':f'control_{region}_{mode}_uniform','phase':'control','region':region,'mode':mode,'variant':'uniform'})
    for region in regions:
        for mode in ('bulk','parcel_lower'):
            for variant in ('local','local_matched'):jobs.append({'key':f'test_{region}_{mode}_{variant}','phase':'test','region':region,'mode':mode,'variant':variant})
    return jobs


def prepare():
    prepared=replay.prepare()
    parent,state,inputs,source_records,collectors,_,_=review.load_verified(SOURCE,prepared)
    _,_,setting,initials,finals,originals=prepared
    texts,downloads=boundary.atmosphere.acquire(ROOT/'data/v10_atmosphere',fetch=False)
    fields=boundary.atmosphere.fields_from_cache(texts)
    profiles={region:boundary.local_profile(case,g,fields) for region,(case,p,g,air,c) in inputs.items()}
    protocol={'schema':1,'code_sha256':source_id(),'source_code_sha256':parent['code_sha256'],
        'source_manifest_sha256':sha256(SOURCE/'manifest.json'),'source_state_sha256':sha256(SOURCE/'state.json'),
        'reference_downloads':downloads,'profile_array_sha256':{region:run.run.parent.geometry_rules.array_id({'local_monthly':a}) for region,a in profiles.items()},
        'source_jobs':parent['jobs'],'jobs':make_jobs(inputs),'settings':asdict(setting),'seed':67,'amplitude':16.,'timing':'aligned',
        'budget_seconds':BUDGET,'minimum_cycles':3,'maximum_cycles':6,
        'controls':'Four exact final-year uniform-profile replays. Candidate climates start from the settled paired baseline final state.',
        'forcing':'Native cached monthly local mixing ratio at each boundary cell/actual pressure, same nominal event pulse and safe local saturation cap. Dry 150hPa lid retained. No horizontal/vertical dry-flow changes.',
        'dose':'local uses its own native-pattern gross input; local_matched normalizes to the original actual monthly gross incoming vapor. Actual humidity means/variance and cap clipping need not match.',
        'selection':'Fixed regional input sensitivity with bulk and lower-interface cloud rules; no parameter fit or best-seed selection. Reused synthetic weather and different climatology periods are not independent climate validation.',
        'atlas_publication':False,'downloads':False}
    return protocol,inputs,setting,initials,finals,originals,profiles


def forcing_identity(protocol,region):
    return {'code_sha256':protocol['code_sha256'],'region':region,'profile_array_sha256':protocol['profile_array_sha256'][region]}


def case_run(folder,job,inputs,setting,initials,finals,originals,tables,stop,log,progress,code_id):
    region=job['region'];case,p,g,air,c=inputs[region];anchor=finals[region+'_'+job['mode']]
    folder.mkdir(parents=True,exist_ok=True);identity={**job,'code_sha256':code_id,'settings':asdict(setting)}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text())!=identity:raise ValueError('Spatial humidity case changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    driver=boundary.Driver(originals[region],tables[region],job['variant'],case,p,setting,g,air,c)
    state=initials[region+'_'+job['mode']] if job['phase']=='control' else anchor[0]
    previous=None;check={'passed':False};maximum=1 if job['phase']=='control' else 6
    for year in range(1,maximum+1):
        if source_id()!=code_id:raise ValueError('Spatial humidity sources changed.')
        record=run.run.parent.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
        if record is None:
            partial=run.run.parent.read_checkpoint(folder,year,case.domain.land.shape)
            if partial is not None:run.run.validate_control_record(partial,driver.monthly_targets)
            started=time.monotonic();before=partial[-1].get('elapsed_seconds',0.) if partial else 0.
            def save(*record):
                if source_id()!=code_id:raise ValueError('Spatial humidity sources changed during integration.')
                info=dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
                run.run.parent.write_checkpoint(folder,year,(*record[:4],info));progress({'case':job['key'],'year':year,'month':info['month'],'elapsed_year_seconds':info['elapsed_seconds']})
                log(f'{job["key"]}: cycle {year}/{maximum}, month {info["month"]}/12; actual vapor input checked')
            record=physics.year(case.domain,p,setting,state,air,case.score_mask,g,driver,
                checkpoint=partial,save_month=save,should_stop=stop,condensation_mode=job['mode'])
            record[-1]['elapsed_seconds']=before+time.monotonic()-started
            run.run.parent.write_checkpoint(folder,year,record,completed=True)
        run.run.validate_control_record(record,driver.monthly_targets)
        if job['phase']=='control':
            run.previous.replay.verify_physical(record,anchor);check={'passed':True};break
        if previous is not None:check=run.run.parent.settling(previous,record,case,g)
        state=record[0]
        if year>=3 and check['passed']:break
        previous=record
    base={'row':{'response':run.run.parent.review.run.review.run.rain_vector(case,anchor[1])}}
    row=run.summary(record,case,check,year,base)
    row.update(note='Local boundary-humidity sensitivity; prescribed circulation and reference-informed temperature. Cloud mode is an unmixed liquid bound, not a validated scheme.',
        physical_control_exact=job['phase']=='control',monthly_import_target_mm=driver.monthly_targets.tolist(),
        boundary_import_change_fraction=float(driver.monthly_targets.sum()/originals[region]['monthly_import_target_mm'].sum()-1),
        case_config_sha256=sha256(folder/'config.json'),elapsed_seconds=sum(json.loads((folder/f'year{n}.json').read_text())['info']['elapsed_seconds'] for n in range(1,year+1)),
        evidence_sha256={f'year{n}.{ext}':sha256(folder/f'year{n}.{ext}') for n in range(1,year+1) for ext in ('json','npz')})
    atomic_json(folder/'summary.json',row);return row


def report(out,state,diagnostics):
    lines=['# Local boundary-humidity comparison','',f"Status: {state['status']}; {len(state['cases'])}/12 cases. Atlas unchanged.",'',
        '| Case | Coastal winter rain | Change from uniform | Monthly MAE change | Med still arid | Gross incoming water change | Settled |',
        '|---|---:|---:|---:|---:|---:|---|']
    for key,r in state['cases'].items():
        lines.append(f'| {key} | {r["response"]["coast_winter_mm"]:.2f} mm | {r["coastal_winter_gain_mm"]:+.2f} mm | {r["monthly_mae_change_mm"]:+.3f} mm | {r["koppen_fixed_surface_temperature"]["target_mediterranean_to_arid"]:.1%} | {r["boundary_import_change_fraction"]:+.1%} | {r["settling"]["passed"]} |')
    lines+=['','Uniform controls must reproduce exactly. local_matched is the distribution contrast at fixed monthly gross input; local changes both pattern and amount. The dry flow and original nominal storm pulse remain unchanged. No hourly observed weather, parameter selection or fantasy publication.']
    if state.get('error'):lines+=['','Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def batch(out,case_runner=case_run,clock=time.monotonic):
    started=clock();deadline=started+BUDGET
    protocol,inputs,setting,initials,finals,originals,profiles=prepare()
    ready=json.loads((PREFLIGHT/'manifest.json').read_text())
    if ready['protocol']!=protocol:raise ValueError('Spatial humidity preflight is stale.')
    for protected in (SOURCE,PREFLIGHT,replay.SOURCE,replay.PREFLIGHT,run.SOURCE,run.PREFLIGHT):
        a,b=out.resolve(),protected.resolve()
        if a==b or a in b.parents or b in a.parents:raise ValueError('Use a separate spatial humidity output folder.')
    tables={};diagnostics={}
    for region in inputs:tables[region],diagnostics[region]=run.previous.read_calendar(PREFLIGHT/'forcing'/region,forcing_identity(protocol,region))
    out.mkdir(parents=True,exist_ok=True);manifest=out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=protocol:raise ValueError('Spatial humidity protocol changed; preserve output and use new --out.')
    if not manifest.exists():atomic_json(manifest,protocol)
    state=json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases':{}}
    if state.get('status')=='needs_diagnosis':raise ValueError('Previous spatial humidity failure needs inspection.')
    state['status']='running';interrupted=[False]
    handler=signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    def stop():return interrupted[0] or clock()>=deadline
    def log(message):
        text=run.run.parent.night.utc()+' '+message;print(text,flush=True)
        with (out/'run.log').open('a') as f:f.write(text+'\n')
    def progress(info):atomic_json(out/'progress.json',dict(info,updated_utc=run.run.parent.night.utc(),completed_jobs=len(state['cases']),planned_jobs=12,elapsed_invocation_seconds=clock()-started))
    try:
        report(out,state,diagnostics)
        for job in protocol['jobs']:
            if source_id()!=protocol['code_sha256']:raise ValueError('Spatial humidity sources changed.')
            folder=out/'cases'/job['key']
            if job['key'] in state['cases']:
                run.previous.verify_completed(folder,state['cases'][job['key']]);continue
            if stop():raise physics.base.BudgetStop()
            log(f'Start {job["key"]}')
            row=case_runner(folder,job,inputs,setting,initials,finals,originals,tables,stop,log,progress,protocol['code_sha256'])
            if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed while completing humidity case.')
            state['cases'][job['key']]=row;report(out,state,diagnostics)
        state['status']='complete'
    except physics.base.BudgetStop:state['status']='interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:state['status']='needs_diagnosis';state['error']=str(error)
    finally:
        signal.signal(signal.SIGINT,handler);report(out,state,diagnostics);progress({'status':state['status']})
    return state


def preflight():
    protocol,inputs,setting,initials,finals,originals,profiles=prepare();checks=[];tables={};diagnostics={}
    for region,(case,p,g,air,c) in inputs.items():
        print(region+': preparing cached local boundary forcing; no annual climate integration',flush=True)
        tables[region],diagnostics[region]=boundary.prepare_tables(case,p,setting,g,air,c,originals[region],profiles[region],lambda s:print(s,flush=True))
        old=run.previous.weather.Driver(originals[region],case,p,setting,g,air,c,16.,'aligned',67)
        old_f,old_q,_=old.at(0.)
        for variant in boundary.VARIANTS:
            driver=boundary.Driver(originals[region],tables[region],variant,case,p,setting,g,air,c);f,q,_=driver.at(0.)
            for name in ('x','y','vertical'):np.testing.assert_array_equal(getattr(f,name),getattr(old_f,name))
            for mode in ('bulk','parcel_lower'):
                before=initials[region+'_'+mode];dt=min(60.,physics.base.stable_step(f,g.mass,case.domain))
                result=physics.advance(before,case.domain,p,setting,f,dt,0.,air,geometry=g,boundary=q,condensation_mode=mode)
                if variant=='uniform':
                    expected=physics.advance(before,case.domain,p,setting,old_f,dt,0.,air,geometry=g,boundary=old_q,condensation_mode=mode)
                    for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(result[0],name),getattr(expected[0],name))
                    for i in (1,2,3,5,6,8):np.testing.assert_array_equal(result[i],expected[i])
                    if result[4]!=expected[4] or result[7]!=expected[7]:raise ValueError('Uniform step control changed.')
                checks.append({'region':region,'variant':variant,'mode':mode,'dt_s':dt,'dry_flow_identical':True,
                    'water_error_mm':result[4]['water_error_mm'],'energy_error_j_m2':result[4]['energy_error_j_m2'],'temperature_ledger_error_c':result[7]})
    if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed during spatial humidity preflight.')
    data={'protocol':protocol,'checks':checks,'forcing_diagnostics':diagnostics,'new_annual_integrations_started':0,'new_downloads':0,'atlas_updated':False}
    path=PREFLIGHT/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=data:raise ValueError('Preserve existing spatial humidity preflight.')
        for region in inputs:run.previous.read_calendar(PREFLIGHT/'forcing'/region,forcing_identity(protocol,region))
    else:
        for region in inputs:run.previous.write_calendar(PREFLIGHT/'forcing'/region,forcing_identity(protocol,region),tables[region],diagnostics[region])
        atomic_json(path,data)
    print('Spatial humidity preflight passed: two forcing calendars, identical uniform boundaries/flow, matched monthly input and twelve independent <=60-second probes.')
    return data


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--preflight',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'output/v10_spatial_humidity');a=p.parse_args(argv)
    if a.preflight:preflight();return 0
    print('Four exact controls, then eight fixed local-humidity comparisons. Estimated 45–75 minutes; 90-minute cap and monthly resume. Cached inputs; no fit or atlas update.',flush=True)
    if not a.run:print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_spatial_humidity.py --run');return 0
    state=batch(a.out);print('Status: '+state['status']);return 1 if state['status']=='needs_diagnosis' else 0


if __name__=='__main__':raise SystemExit(main())
