"""Four user-run final-year source replays; exact physical reproduction required."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from experiments import v10_cloud_sources as model
from scripts import review_v10_cloud_mixing as review
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256
run=review.run
SOURCE=ROOT/'output/v10_cloud_mixing'
PREFLIGHT=ROOT/'output/v10_cloud_sources_preflight'
BUDGET=45*60.


def source_id():
    h=hashlib.sha256(run.source_id().encode())
    for p in (Path(__file__),Path(model.__file__),Path(review.__file__),Path(model.face_transfers.__code__.co_filename)):h.update(p.read_bytes())
    return h.hexdigest()


def prepare():
    protocol,state,inputs,setting,anchors,records,_,_,_,_=review.load_verified(SOURCE)
    jobs=[];initials={};finals={};tables={}
    for region in inputs:
        input_id=protocol['anchors'][run.label(41,region,16.,'aligned')]['reference_protocol']['inputs'][region]
        identity={'code_sha256':protocol['parent_code_sha256'],'seed':67,'region':region,'input_sha256':input_id}
        tables[region]=run.previous.read_calendar(run.SOURCE/'forcing'/f's67_{region}',identity)[0]
        for mode in ('bulk','parcel_lower'):
            key=region+'_'+mode
            source_case=run.label(67,region,16.,'aligned') if mode=='bulk' else f'repeat_s67_{region}_lift16_aligned_parcel_lower_dt1'
            folder=(run.SOURCE if mode=='bulk' else SOURCE)/'cases'/source_case
            row=anchors[source_case]['row'] if mode=='bulk' else state['cases'][source_case]
            n=row['years'];expected=anchors[source_case]['record'] if mode=='bulk' else records[source_case]
            initial=run.run.parent.read_checkpoint(folder,n-1,inputs[region][0].domain.land.shape,completed=True)
            if initial is None:raise ValueError('Need preceding-year source state.')
            initials[key]=initial[0];finals[key]=expected
            jobs.append({'key':key,'region':region,'mode':mode,'seed':67,'amplitude':16.,'timing':'aligned','source_case':source_case,'source_year':n,
                'start_npz_sha256':sha256(folder/f'year{n-1}.npz'),'final_npz_sha256':sha256(folder/f'year{n}.npz')})
    new={'schema':1,'code_sha256':source_id(),'parent_code_sha256':protocol['code_sha256'],
        'parent_manifest_sha256':sha256(SOURCE/'manifest.json'),'parent_state_sha256':sha256(SOURCE/'state.json'),
        'jobs':jobs,'budget_seconds':BUDGET,'sources':list(model.SOURCES),'winter_months_0based':review.WINTER.tolist(),
        'summer_months_0based':review.SUMMER.tolist(),'policy':'One final-year replay per fixed case, exact saved preceding-year physical state. No new warmup or changed physical trajectory.',
        'interpretation':'Last atmospheric vapor entry, not soil ancestry or causal suppression test. Initial vapor is explicitly unknown; newly evaporated land water is relabelled recycling. Parcel condensate inherits ascending-donor tags before bulk mixing.',
        'atlas_publication':False,'downloads':False}
    return new,inputs,setting,initials,finals,tables


def write_checkpoint(folder,record,collector,completed=False):
    run.run.parent.validate_record(record,collector.domain.land.shape,completed=completed)
    collector.validate_months(record[-1]['month'],record[0].water,record[1])
    stem='year1' if completed else 'year1_partial';meta=folder/(stem+'.json')
    previous=json.loads(meta.read_text()).get('arrays') if meta.exists() and not completed else None
    name='year1.npz' if completed else f'year1_m{record[-1]["month"]:02d}.npz'
    state,rain,temp,refs,info=record
    arrays=dict(water=state.water,energy=state.energy,soil=state.soil,rain=rain,temperature=temp,reference=refs)
    arrays.update({'source_'+k:v for k,v in collector.arrays.items()});atomic_npz(folder/name,**arrays)
    atomic_json(meta,{'year':1,'arrays':name,'array_sha256':sha256(folder/name),'info':info})
    if previous and previous!=name and Path(previous).name==previous:(folder/previous).unlink(missing_ok=True)


def read_checkpoint(folder,case,g,completed=False):
    record=run.run.parent.read_checkpoint(folder,1,case.domain.land.shape,completed=completed)
    if record is None:return None,None
    meta=json.loads((folder/('year1.json' if completed else 'year1_partial.json')).read_text())
    with np.load(folder/meta['arrays'],allow_pickle=False) as a:saved={k[7:]:a[k] for k in a.files if k.startswith('source_')}
    collector=model.Collector(case.domain,g,saved=saved)
    collector.validate_months(record[-1]['month'],record[0].water,record[1])
    return record,collector


def replay_case(folder,job,inputs,setting,initials,finals,tables,stop,log,progress,code_id):
    key=job['key'];case,p,g,air,c=inputs[job['region']];folder.mkdir(parents=True,exist_ok=True)
    identity={**job,'code_sha256':code_id}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text())!=identity:raise ValueError('Cloud-source replay identity changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    record,collector=read_checkpoint(folder,case,g,completed=True)
    if record is None:
        partial,collector=read_checkpoint(folder,case,g)
        if collector is None:collector=model.Collector(case.domain,g,initial_water=initials[key].water)
        driver=run.previous.weather.Driver(tables[job['region']],case,p,setting,g,air,c,16.,'aligned',67)
        started=time.monotonic();before=partial[-1].get('elapsed_seconds',0.) if partial else 0.
        def save(*record):
            if source_id()!=code_id:raise ValueError('Cloud-source sources changed during replay.')
            info=dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
            write_checkpoint(folder,(*record[:4],info),collector);progress({'case':key,'month':info['month'],'elapsed_case_seconds':info['elapsed_seconds']})
            log(f'{key}: {info["month"]}/12 months; donor/source water ledgers checked')
        record=model.year(case.domain,p,setting,initials[key],air,case.score_mask,g,driver,
            checkpoint=partial,save_month=save,should_stop=stop,condensation_mode=job['mode'],collector=collector)
        record[-1]['elapsed_seconds']=before+time.monotonic()-started
        write_checkpoint(folder,record,collector,completed=True)
    run.previous.replay.verify_physical(record,finals[key])
    target=run.run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
    masks={'domain':np.ones(case.domain.land.shape,bool),'scored_land':case.score_mask,**review.groups_for(case,target)}
    row=collector.summary(masks,review.WINTER,review.SUMMER)
    row.update(physical_reproduction_exact=True,source_case=job['source_case'],source_year=job['source_year'],elapsed_seconds=record[-1]['elapsed_seconds'],
        case_config_sha256=sha256(folder/'config.json'),evidence_sha256={name:sha256(folder/name) for name in ('year1.json','year1.npz')})
    atomic_json(folder/'summary.json',row);return row


def report(out,state):
    lines=['# Passive cloud-rain sources','',f"Status: {state['status']}; {len(state['cases'])}/4 exact final-year replays. Atlas unchanged.",'',
        '| Case: reference-arid land in summer | Total rain | Boundary | Ocean evaporation | Land recycling | Initial unknown |',
        '|---|---:|---:|---:|---:|---:|']
    for key,r in state['cases'].items():
        rain=np.array(r['regions']['reference_arid']['summer_rain_mm_by_source'])
        lines.append(f'| {key} | {rain.sum():.2f} mm | {rain[1]:.2f} mm | {rain[2]:.2f} mm | {rain[3]:.2f} mm | {rain[0]:.2f} mm |')
    lines+=['','Labels identify the last entry to atmospheric vapor. Land recycling does not identify original soil-water ancestry. Initial atmosphere remains unknown. Fractions are not the causal effect of turning a source off. Winter October–March; summer April–September. Shared reference-climate masks include neighboring land.']
    if state.get('error'):lines+=['','Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def batch(out,case_runner=replay_case,clock=time.monotonic):
    started=clock();deadline=started+BUDGET
    protocol,inputs,setting,initials,finals,tables=prepare()
    if json.loads((PREFLIGHT/'manifest.json').read_text())['protocol']!=protocol:raise ValueError('Cloud-source preflight is stale.')
    for protected in (SOURCE,run.SOURCE,PREFLIGHT,run.PREFLIGHT,run.previous.PREFLIGHT,run.previous.replay.SOURCE):
        a,b=out.resolve(),protected.resolve()
        if a==b or a in b.parents or b in a.parents:raise ValueError('Use separate cloud-source output.')
    out.mkdir(parents=True,exist_ok=True);manifest=out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=protocol:raise ValueError('Cloud-source protocol changed; preserve output and use new --out.')
    if not manifest.exists():atomic_json(manifest,protocol)
    state=json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases':{}}
    if state.get('status')=='needs_diagnosis':raise ValueError('Previous cloud-source failure needs inspection.')
    state['status']='running';interrupted=[False]
    handler=signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    def stop():return interrupted[0] or clock()>=deadline
    def log(message):
        text=run.run.parent.night.utc()+' '+message;print(text,flush=True)
        with (out/'run.log').open('a') as f:f.write(text+'\n')
    def progress(info):atomic_json(out/'progress.json',dict(info,updated_utc=run.run.parent.night.utc(),completed_jobs=len(state['cases']),planned_jobs=4,elapsed_invocation_seconds=clock()-started))
    try:
        report(out,state)
        for job in protocol['jobs']:
            if source_id()!=protocol['code_sha256']:raise ValueError('Cloud-source sources changed.')
            folder=out/'cases'/job['key']
            if job['key'] in state['cases']:
                run.previous.verify_completed(folder,state['cases'][job['key']]);continue
            if stop():raise model.base.BudgetStop()
            log('Replay '+job['key']+' from the exact preceding-year state; no warmup')
            row=case_runner(folder,job,inputs,setting,initials,finals,tables,stop,log,progress,protocol['code_sha256'])
            if source_id()!=protocol['code_sha256']:raise ValueError('Sources changed while completing source replay.')
            state['cases'][job['key']]=row;report(out,state)
        state['status']='complete'
    except model.base.BudgetStop:state['status']='interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:state['status']='needs_diagnosis';state['error']=str(error)
    finally:
        signal.signal(signal.SIGINT,handler);report(out,state);progress({'status':state['status']})
    return state


def preflight():
    protocol,inputs,setting,initials,finals,tables=prepare();checks=[]
    for job in protocol['jobs']:
        case,p,g,air,c=inputs[job['region']];before=initials[job['key']]
        driver=run.previous.weather.Driver(tables[job['region']],case,p,setting,g,air,c,16.,'aligned',67)
        f,q,_=driver.at(0.);dt=min(60.,model.base.stable_step(f,g.mass,case.domain))
        result=model.physics.advance(before,case.domain,p,setting,f,dt,0.,air,geometry=g,boundary=q,condensation_mode=job['mode'])
        copied=[v.copy() for v in (result[0].water,result[0].energy,result[0].soil,*result[1:4],result[5],result[6],result[8])]
        collector=model.Collector(case.domain,g,initial_water=before.water)
        collector.add(before,result[0],result[5],result[8],f,q,result[4],dt,0.)
        for a,b in zip(copied,(result[0].water,result[0].energy,result[0].soil,*result[1:4],result[5],result[6],result[8])):np.testing.assert_array_equal(a,b)
        checks.append({'key':job['key'],'dt_s':dt,'physical_arrays_unchanged':True,'maximum_errors':collector.arrays['maximum_errors'].tolist()})
    if source_id()!=protocol['code_sha256']:raise ValueError('Cloud-source sources changed during preflight.')
    data={'protocol':protocol,'checks':checks,'new_real_annual_replays_started':0,'atlas_updated':False}
    path=PREFLIGHT/'manifest.json'
    if path.exists():
        if json.loads(path.read_text())!=data:raise ValueError('Preserve old cloud-source preflight.')
    else:atomic_json(path,data)
    print('Cloud-source preflight passed: four independent <=60-second probes; physical arrays unchanged. No annual replay started.')
    return data


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--preflight',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'output/v10_cloud_sources');a=p.parse_args(argv)
    if a.preflight:preflight();return 0
    print('Four exact final-year source replays. Rough estimate 10–25 minutes; 45-minute invocation cap and monthly resume. No changed climate, warmup or atlas update.',flush=True)
    if not a.run:print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/replay_v10_cloud_sources.py --run');return 0
    state=batch(a.out);print('Status: '+state['status']);return 1 if state['status']=='needs_diagnosis' else 0


if __name__=='__main__':raise SystemExit(main())
