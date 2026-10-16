"""User-run staged test of an unmixed ascending-parcel condensation bound."""
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
from experiments import v10_parcel_condensation as model
from scripts import afternoon_v10_delivery as previous
from rotclimate_v10.earth import atomic_json,sha256
run=previous.run
SOURCE=ROOT/'output/v10_afternoon_delivery'
PREFLIGHT=ROOT/'output/v10_cloud_mixing_preflight'
SEEDS=(67,103,149,211)
LIFTING=((1.,'steady'),(16.,'aligned'))


def source_id():
    h=hashlib.sha256(previous.source_id().encode())
    for path in (Path(__file__),Path(model.__file__)):h.update(path.read_bytes())
    return h.hexdigest()


def label(seed,region,amplitude,timing):
    return f's{seed}_{region}_'+run.model.variant_key(amplitude,timing)


def make_jobs(inputs):
    jobs=[]
    def add(phase,seed,region,amplitude,timing,mode,factor):
        anchor=label(seed,region,amplitude,timing)
        jobs.append({'key':f'{phase}_{anchor}_{mode}_dt{factor:g}','phase':phase,'seed':seed,'region':region,
            'amplitude':amplitude,'timing':timing,'mode':mode,'time_factor':factor,'anchor':anchor})
    for region in inputs:
        for amplitude,timing in LIFTING:add('control',41,region,amplitude,timing,'bulk',1.)
    for region in inputs:
        for amplitude,timing in LIFTING:add('screen',41,region,amplitude,timing,'parcel_lower',1.)
    for seed in SEEDS:
        for region in inputs:
            for amplitude,timing in LIFTING:
                for mode in ('parcel_lower','parcel_all'):add('repeat',seed,region,amplitude,timing,mode,1.)
    for region in inputs:
        for amplitude,timing in LIFTING:
            for mode in model.MODES:add('numerics',67,region,amplitude,timing,mode,.5)
    return jobs


def prepare():
    old,inputs,setting,initials,finals,calendars=previous.prepare()
    if json.loads((SOURCE/'manifest.json').read_text())!=old:raise ValueError('Weather parent protocol changed.')
    state=json.loads((SOURCE/'state.json').read_text());anchors={};identities={};tables={}
    for region in inputs:
        tables[(41,region)]=calendars[region]
        for amplitude,timing in LIFTING:
            key=region+'_'+run.model.variant_key(amplitude,timing);name=label(41,region,amplitude,timing)
            row=json.loads((previous.replay.SOURCE/'cases'/key/'summary.json').read_text())
            anchors[name]={'record':finals[key],'initial':initials[key],'row':row}
            identities[name]={'reference_protocol':old['reference_protocol'],'source_case':key}
    for seed in SEEDS:
        for region in inputs:
            tables[(seed,region)]=previous.read_calendar(SOURCE/'forcing'/f's{seed}_{region}',previous.cache_identity(old,inputs,seed,region))[0]
            for amplitude,timing in LIFTING:
                name=label(seed,region,amplitude,timing);row=state['cases'].get(name)
                if row is None:raise ValueError('Need completed parent case '+name)
                folder=SOURCE/'cases'/name;previous.verify_completed(folder,row)
                record=run.parent.read_checkpoint(folder,row['years'],inputs[region][0].domain.land.shape,completed=True)
                if not row['settling']['passed']:raise ValueError('Need a settled parent anchor '+name)
                anchors[name]={'record':record,'row':row}
                identities[name]={'config_sha256':row['case_config_sha256'],'summary_sha256':sha256(folder/'summary.json'),
                    'evidence_sha256':row['evidence_sha256'],'years':row['years']}
    jobs=make_jobs(inputs)
    protocol={'schema':1,'code_sha256':source_id(),'parent_code_sha256':previous.source_id(),
        'anchors':identities,'jobs':jobs,'settings':asdict(setting),'minimum_cycles':3,'maximum_cycles':6,
        'forcing':'Reuse exact parent calendars and upward dry-mass flux. No humidity, amplitude, or boundary-dose retuning.',
        'cloud_bound':'Unmixed upward donor parcels cool to the recipient pressure and undergo its linear thermal relaxation before energy-coupled liquid condensation. Condensate is removed from their carried vapor before bulk saturation; latent energy remains as sensible heat. Immediate fallout/soil convention retained. Not an entraining plume or validated cloud scheme.',
        'lower_mode':'Only first three upward interfaces; omit receiving 150hPa layer. All-interface variant is an upper-structure sensitivity.',
        'screen_gate':{'require_all_settled':True,'require_all_temperature_guards':True,'minimum_coastal_winter_gain_mm_each_strong_lift_region':5.},
        'selection':'Fixed mechanism screen followed by fixed paired sensitivity, no best weather seed or parameter choice. Synthetic seeds are reused, not untouched validation.',
        'atlas_publication':False,'downloads':False}
    return protocol,inputs,setting,anchors,tables


def summary(record,case,check,years,anchor):
    row=run.parent.night.summarize(record,case,check,years)
    response=run.parent.review.run.review.run.rain_vector(case,record[1])
    baseline=anchor['row']['response']
    target=run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
    classes=run.koppen_maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)
    parcel=np.array(record[-1]['parcel_rain_scored_land_mm']).sum(0)
    row.update(response=response,baseline_response=baseline,coastal_winter_gain_mm=response['coast_winter_mm']-baseline['coast_winter_mm'],
        monthly_mae_change_mm=response['monthly_mae_mm']-baseline['monthly_mae_mm'],
        koppen_fixed_surface_temperature=run.koppen_maps.comparison(target,classes,case.score_mask),
        annual_subgrid_rain_scored_land_by_layer_mm=parcel.tolist(),
        uppermost_subgrid_rain_fraction=float(parcel[-1]/parcel.sum()) if parcel.sum()>0 else 0.,
        note='Unmixed parcel limit, not a validated cloud/rain scheme. Instant liquid fallout; no independent temperature or fantasy transfer.')
    return row


def case_run(folder,job,inputs,setting,anchors,tables,stop,log,progress,code_id):
    case,p,g,air,c=inputs[job['region']];anchor=anchors[job['anchor']]
    folder.mkdir(parents=True,exist_ok=True)
    identity={**job,'code_sha256':code_id,'settings':asdict(setting)}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text())!=identity:raise ValueError('Cloud mixing case identity changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    driver=previous.weather.Driver(tables[(job['seed'],job['region'])],case,p,setting,g,air,c,job['amplitude'],job['timing'],job['seed'])
    state=anchor['initial'] if job['phase']=='control' else anchor['record'][0]
    last=None;check={'passed':False};maximum=1 if job['phase']=='control' else 6
    for year in range(1,maximum+1):
        if source_id()!=code_id:raise ValueError('Cloud mixing sources changed.')
        record=run.parent.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
        if record is None:
            partial=run.parent.read_checkpoint(folder,year,case.domain.land.shape)
            if partial is not None:run.validate_control_record(partial,driver.monthly_targets)
            started=time.monotonic();before=partial[-1].get('elapsed_seconds',0.) if partial else 0.
            def save(*record):
                if source_id()!=code_id:raise ValueError('Cloud mixing sources changed during integration.')
                info=dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
                run.parent.write_checkpoint(folder,year,(*record[:4],info))
                progress({'year':year,'month':info['month'],'elapsed_year_seconds':info['elapsed_seconds']})
                log(f'{job["key"]}: cycle {year}/{maximum}, month {info["month"]}/12; water and heat checked')
            record=model.year(case.domain,p,setting,state,air,case.score_mask,g,driver,
                checkpoint=partial,save_month=save,should_stop=stop,condensation_mode=job['mode'],time_factor=job['time_factor'])
            record[-1]['elapsed_seconds']=before+time.monotonic()-started
            run.parent.write_checkpoint(folder,year,record,completed=True)
        run.validate_control_record(record,driver.monthly_targets)
        if job['phase']=='control':
            previous.replay.verify_physical(record,anchor['record'])
            if np.any(record[-1]['parcel_rain_scored_land_mm']):raise ValueError('Bulk control contains parcel rain.')
            check=anchor['row']['settling'];break
        if last is not None:check=run.parent.settling(last,record,case,g)
        state=record[0]
        if year>=3 and check['passed']:break
        last=record
    row=summary(record,case,check,year,anchor)
    row.update(physical_control_exact=job['phase']=='control',case_config_sha256=sha256(folder/'config.json'),
        elapsed_seconds=sum(json.loads((folder/f'year{n}.json').read_text())['info']['elapsed_seconds'] for n in range(1,year+1)),
        evidence_sha256={f'year{n}.{ext}':sha256(folder/f'year{n}.{ext}') for n in range(1,year+1) for ext in ('json','npz')})
    atomic_json(folder/'summary.json',row);return row


def screen_gate(protocol,state):
    jobs=[j for j in protocol['jobs'] if j['phase']=='screen']
    if not all(j['key'] in state['cases'] for j in jobs):return {'ready':False,'passed':False}
    rows=[state['cases'][j['key']] for j in jobs]
    physical=all(r['settling']['passed'] and r['guards']['lower_temperature'] and r['guards']['upper_temperature'] for r in rows)
    strong=[state['cases'][j['key']]['coastal_winter_gain_mm'] for j in jobs if j['amplitude']==16.]
    threshold=protocol['screen_gate']['minimum_coastal_winter_gain_mm_each_strong_lift_region']
    return {'ready':True,'passed':physical and all(v>=threshold for v in strong),
        'settled_and_temperature_checks_pass':physical,'strong_lift_coastal_winter_gains_mm':strong,'threshold_mm':threshold}


def report(out,state,protocol):
    gate=screen_gate(protocol,state);state['screen_gate']=gate
    lines=['# Unmixed ascending-parcel cloud bound','',f"Status: {state['status']}; {len(state['cases'])}/{len(protocol['jobs'])} jobs. Atlas unchanged.",'',
        'This is a deliberately unmixed, immediate-liquid-fallout limit. It tests sensitivity to unresolved cloud formation; it is not a validated replacement cloud scheme.', '',
        '| Case | Coastal winter rain | Change from bulk | Monthly MAE change | Uppermost fraction of parcel rain | Settled |',
        '|---|---:|---:|---:|---:|---|']
    for job in protocol['jobs']:
        if job['key'] not in state['cases']:continue
        r=state['cases'][job['key']]
        lines.append(f'| {job["key"]} | {r["response"]["coast_winter_mm"]:.2f} mm | {r["coastal_winter_gain_mm"]:+.2f} mm | {r["monthly_mae_change_mm"]:+.3f} mm | {r["uppermost_subgrid_rain_fraction"]:.1%} | {r["settling"]["passed"]} |')
    lines+=['','Screen gate: '+json.dumps(gate), '', 'Water input and circulation match the parent within each catalogue/region. The amplification and timing pair is not a pure lifting-only contrast. Do not equate synthetic-catalogue variability with observed uncertainty. Opportunity sums from old replays are not alternative-climate rain.']
    if state.get('error'):lines+=['','Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def batch(out,hours=7.,stage='overnight',case_runner=None,clock=time.monotonic):
    if not np.isfinite(hours) or not 0<hours<=10:raise ValueError('Use a positive budget up to ten hours.')
    if stage not in ('smoke','overnight'):raise ValueError('Unknown stage.')
    started=clock();deadline=started+hours*3600
    protocol,inputs,setting,anchors,tables=prepare()
    if json.loads((PREFLIGHT/'manifest.json').read_text())['protocol']!=protocol:raise ValueError('Cloud mixing preflight is stale.')
    for protected in (SOURCE,PREFLIGHT,previous.PREFLIGHT,previous.replay.SOURCE,previous.replay.PREFLIGHT,run.PREFLIGHT,ROOT/'output/v10_split_column'):
        a,b=out.resolve(),protected.resolve()
        if a==b or a in b.parents or b in a.parents:raise ValueError('Use a separate cloud mixing output folder.')
    out.mkdir(parents=True,exist_ok=True)
    manifest=out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=protocol:raise ValueError('Cloud mixing protocol changed; preserve output and use new --out.')
    if not manifest.exists():atomic_json(manifest,protocol)
    state=json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases':{},'invocations':[]}
    if state.get('status')=='needs_diagnosis':raise ValueError('Previous failure needs inspection.')
    invocation={'started_utc':run.parent.night.utc(),'hours':hours,'stage':stage};state['invocations'].append(invocation)
    state['status']='running';interrupted=[False];job={}
    handler=signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    def stop():return interrupted[0] or clock()>=deadline
    def log(message):
        text=run.parent.night.utc()+' '+message;print(text,flush=True)
        with (out/'run.log').open('a') as f:f.write(text+'\n')
    def progress(info):
        if source_id()!=protocol['code_sha256']:raise ValueError('Cloud mixing sources changed.')
        atomic_json(out/'progress.json',dict(info,case=job.get('key'),phase=job.get('phase'),
            updated_utc=run.parent.night.utc(),completed_jobs=len(state['cases']),planned_jobs=8 if stage=='smoke' else len(protocol['jobs']),elapsed_invocation_seconds=clock()-started,budget_hours=hours))
    try:
        report(out,state,protocol)
        for job in protocol['jobs']:
            if source_id()!=protocol['code_sha256']:raise ValueError('Cloud mixing sources changed.')
            if stage=='smoke' and job['phase'] not in ('control','screen'):break
            folder=out/'cases'/job['key']
            if job['key'] in state['cases']:
                previous.verify_completed(folder,state['cases'][job['key']]);continue
            if job['phase'] not in ('control','screen'):
                gate=screen_gate(protocol,state)
                if not gate['passed']:
                    state['status']='screen_complete_no_expansion';break
            if stop():raise model.base.BudgetStop()
            log(f'[{len(state["cases"])+1}/{8 if stage=="smoke" else len(protocol["jobs"])}] {job["key"]}; {(deadline-clock())/3600:.2f} hours left')
            row=(case_runner or case_run)(folder,job,inputs,setting,anchors,tables,stop,log,progress,protocol['code_sha256'])
            if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed while completing cloud case.')
            state['cases'][job['key']]=row;report(out,state,protocol);progress({'status':'running'})
        if state['status']=='running':state['status']='smoke_complete' if stage=='smoke' else 'complete'
    except model.base.BudgetStop:state['status']='interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:state['status']='needs_diagnosis';state['error']=str(error)
    finally:
        signal.signal(signal.SIGINT,handler)
        invocation.update(finished_utc=run.parent.night.utc(),elapsed_seconds=clock()-started,status=state['status'])
        report(out,state,protocol);progress({'status':state['status']})
    return state


def preflight():
    protocol,inputs,setting,anchors,tables=prepare();checks=[]
    for seed in (41,67):
        for region,(case,p,g,air,c) in inputs.items():
            for amplitude,timing in LIFTING:
                state=anchors[label(seed,region,amplitude,timing)]['record'][0]
                driver=previous.weather.Driver(tables[(seed,region)],case,p,setting,g,air,c,amplitude,timing,seed)
                f,q,_=driver.at(0.);dt=min(60.,model.base.stable_step(f,g.mass,case.domain))
                old=run.model.advance(state,case.domain,p,setting,f,dt,0.,air,geometry=g,boundary=q)
                for mode in model.MODES:
                    result=model.advance(state,case.domain,p,setting,f,dt,0.,air,geometry=g,boundary=q,condensation_mode=mode)
                    if mode=='bulk':
                        for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(result[0],name),getattr(old[0],name))
                        for i in (1,2,3,5,6):np.testing.assert_array_equal(result[i],old[i])
                        if result[4]!=old[4] or result[7]!=old[7]:raise ValueError('New bulk physical operator changed.')
                    checks.append({'seed':seed,'region':region,'amplitude':amplitude,'timing':timing,'mode':mode,'dt_s':dt,
                        'rain_coast_mm_per_probe':float(result[1][case.score_mask&(case.coast_distance_km<150.)].mean()),
                        'parcel_rain_coast_mm_per_probe':float(result[8][:,case.score_mask&(case.coast_distance_km<150.)].sum(0).mean()),
                        'water_error_mm':result[4]['water_error_mm'],'energy_error_j_m2':result[4]['energy_error_j_m2'],'temperature_ledger_error_c':result[7]})
    if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed during cloud mixing preflight.')
    data={'protocol':protocol,'checks':checks,'new_annual_integrations_started':0,'atlas_updated':False,
        'probe_caution':'Independent Jan-1 steps from the saved final-year states. Amounts are per probe, not annual rainfall; unmixed liquid closure is a mechanism bound.'}
    path=PREFLIGHT/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=data:raise ValueError('Preserve old cloud mixing preflight.')
    else:atomic_json(path,data)
    print('Cloud mixing preflight passed: 24 independent <=60-second steps; eight exact bulk controls. No annual climate launched.',flush=True)
    return data


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--preflight',action='store_true')
    p.add_argument('--stage',choices=('smoke','overnight'),default='overnight');p.add_argument('--hours',type=float,default=7.)
    p.add_argument('--out',type=Path,default=ROOT/'output/v10_cloud_mixing');a=p.parse_args(argv)
    if a.preflight:preflight();return 0
    print('Four exact saved-year controls, then four regional cloud-bound screens; smoke estimate 20–40 minutes.',flush=True)
    print('Overnight expands only if the declared screen passes: 32 fixed paired climates and 12 half-step numerical checks. Rough estimate 5–8 hours, budgeted/resumable. No atlas update.',flush=True)
    if not a.run:
        print('Read-only plan. Launch with --run --stage smoke --hours 0.75, or --run --stage overnight --hours 7.');return 0
    state=batch(a.out,a.hours,a.stage);print('Status: '+state['status'],flush=True)
    return 1 if state['status']=='needs_diagnosis' else 0


if __name__=='__main__':raise SystemExit(main())
