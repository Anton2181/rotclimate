"""Audit all24fixed collection plans against two physical source event stores."""
import argparse,json,subprocess,sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.source_food_events import periodic_source_food_year
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_food_events_20261113';CAL=ROOT/'output/continuous_food_visit_calendars_20261112';PARENT=ROOT/'output/settlement_continuous_destination_20261112';PLAN=ROOT/'calibration/source_food_events_20261113/plan.json'


def run_case(task):
    row,policy,out=task;key=row['key'];mode=row['climate'];pk=row['parent_key'];ident=key+'_'+policy;out=Path(out);source=PARENT/pk;f=dict(np.load(source/'fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));paths=dict(np.load(ROOT/f'output/settlement_monthly_work_20261112/{mode}_paths.npz'))
    with np.load(CAL/'selected_fields.npz') as z:selection=z[key+'__policy']
    pieces=[];sources={}
    for path in [source/'fields.npz',source/'results.json',ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz',ROOT/f'output/settlement_monthly_work_20261112/{mode}_paths.npz',CAL/'selected_fields.npz']:
        sources[str(path.relative_to(ROOT))]=sha(path)
    for month in range(12):
        for p in (('baseline','joint') if policy=='selected' else (policy,)):
            path=CAL/key/p/f'calendar_{month:02d}.npz';sources[str(path.relative_to(ROOT))]=sha(path)
            with np.load(path) as c:
                keep=selection[c['collection_site']]==int(p=='joint') if policy=='selected' else np.ones(len(c['collection_site']),bool)
                origin=c['collection_origin'][keep];serial=c['collection_serial'][keep];site=c['collection_site'][keep];start=c['collection_start'][keep];end=c['collection_end'][keep];cargo=c['packed_cargo'][keep]
                pickup_hours=start+7*paths['outward_days'][month,origin]+.25;assert np.all(pickup_hours<=end+1e-10);assert np.all((pickup_hours>=0)&(pickup_hours<7*365/12));assert np.all(serial<(1<<24)) and np.all(origin<(1<<24))
                time=month*365/12+pickup_hours/7;ids=(np.int64(month)<<48)|(origin.astype('i8')<<24)|serial.astype('i8')
                np.testing.assert_array_equal(site,x['owner'][origin]);np.testing.assert_allclose(cargo,np.minimum(120000.,f['origin_departures'][month,origin]-120000.*serial),rtol=1e-12,atol=1e-6)
                pieces.append(dict(origin=origin,serial=serial,provider=site,month=np.full(len(origin),month,'i1'),id=ids,time=time,requested=cargo))
    request={n:np.concatenate([p[n] for p in pieces]) for n in pieces[0]};order=np.lexsort((request['id'],request['time'],request['origin']));request={n:v[order] for n,v in request.items()};assert len(np.unique(request['id']))==len(request['id'])
    count=len(x['local_index']);offset=np.r_[0,np.cumsum(np.bincount(request['origin'],minlength=count))];fields={};actual=np.zeros(len(order));missing=actual.copy();bits=x['boundaries'][x['local_index']];harvest_month=np.array([next((m for m in range(12) if int(bit)&(1<<m)),0) for bit in bits]);capacity=f['rural']*2500*365
    for origin in range(count):
        lo,hi=offset[origin:origin+2];sl=slice(lo,hi);y=periodic_source_food_year([harvest_month[origin]*365/12],[f['produced_kcal'][origin]],request['time'][sl],request['requested'][sl],request['id'][sl],demand_rate=f['rural'][origin]*2500,rural_capacity=capacity[origin],export_capacity=f['export_harvested'][origin])
        for account in ('rural','export'):
            for name,value in asdict(getattr(y,account)).items():
                field=account+'__'+name
                if field not in fields:fields[field]=np.zeros(count)
                fields[field][origin]=value
        for name,value in [('uncollected',y.uncollected),('total_ledger_residual',y.total_ledger_residual)]:
            if name not in fields:fields[name]=np.zeros(count)
            fields[name][origin]=value
        actual[sl]=y.pickup_withdrawn;missing[sl]=y.pickup_unfilled
    request.update(withdrawn=actual,unfilled=missing);fields.update(origin_grid_node=x['local_index'],owner=x['owner'],actor=x['actor'][x['owner']],people=f['rural'],produced=f['produced_kcal'],harvest_bin=harvest_month,rural_capacity=capacity,export_capacity=f['export_harvested'],request_offsets=offset)
    fields['rural_food_pass']=fields['rural__unmet']<=1e-8*np.maximum(1.,fields['rural__needed']);fields['export_request_pass']=fields['export__unfilled']<=1e-8*np.maximum(1.,fields['export__requested']);fields['both_pass']=fields['rural_food_pass']&fields['export_request_pass']
    provider={};n=len(f['total'])
    for name in ['rural__needed','rural__unmet','export__requested','export__withdrawn','export__unfilled','uncollected']:
        provider[name]=np.bincount(x['owner'],weights=fields[name],minlength=n)
    for name in ['rural_food_pass','export_request_pass','both_pass']:
        bad=np.bincount(x['owner'],weights=~fields[name],minlength=n)>0;provider[name]=f['active']&~bad
    for name,v in provider.items():fields['provider__'+name]=v
    fields.update(provider_active=f['active'],provider_actor=x['actor'],**{'pickup__'+n:v for n,v in request.items()})
    path=out/(ident+'_fields.npz');np.savez_compressed(path,**fields)
    summary=dict(case=ident,key=key,policy=policy,climate=mode,hours_worker_year=row['hours_worker_year'],crew=row['crew'],origins=count,positive_people_origins=int((f['rural']>0).sum()),rural_food_pass_origins=int(fields['rural_food_pass'].sum()),export_request_pass_origins=int(fields['export_request_pass'].sum()),both_origins=int(fields['both_pass'].sum()),pickup_requests=len(order),raw_requested=float(request['requested'].sum()),raw_withdrawn=float(actual.sum()),raw_unfilled=float(missing.sum()),rural_needed=float(fields['rural__needed'].sum()),rural_unmet=float(fields['rural__unmet'].sum()),active_providers=int(f['active'].sum()),rural_food_pass_providers=int(provider['rural_food_pass'].sum()),export_request_pass_providers=int(provider['export_request_pass'].sum()),both_providers=int(provider['both_pass'].sum()),actors=[])
    for actor in range(18):
        owned=x['actor']==actor;local=fields['actor']==actor;tasks=x['actor'][request['provider']]==actor
        summary['actors'].append(dict(actor=actor,origins=int(local.sum()),active_providers=int((owned&f['active']).sum()),rural_food_pass_providers=int((owned&provider['rural_food_pass']).sum()),export_request_pass_providers=int((owned&provider['export_request_pass']).sum()),both_providers=int((owned&provider['both_pass']).sum()),raw_requested=float(request['requested'][tasks].sum()),raw_withdrawn=float(actual[tasks].sum()),raw_unfilled=float(missing[tasks].sum()),rural_unmet=float(fields['rural__unmet'][local].sum())))
    print('Source pickup audit built',ident,'requests',len(order),'raw unfilled',summary['raw_unfilled'],flush=True)
    return dict(row=summary,sources=sources,file=path.name,sha256=sha(path))


def main(out=OUT,jobs=2):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes();out.mkdir(parents=True,exist_ok=True)
    prototype=json.loads((OUT/'prototype_review.json').read_text());assert prototype['status']=='passed_synthetic_controls_only'
    for n,d in prototype['producers'].items():assert sha(ROOT/n)==d,n
    producer_paths=[Path(__file__),ROOT/'harvest/source_food_events.py',ROOT/'harvest/event_food_stocks.py',PLAN];producers={str(p.relative_to(ROOT)):sha(p) for p in producer_paths}
    checks=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_source_food_events.py','tests/test_event_food_stocks.py','tests/test_source_meal_chronology.py'],cwd=ROOT,capture_output=True,text=True,check=True);write(out/'controls.json',dict(status='passed_before_cohort_outputs',output=checks.stdout,producers=producers,prototype_review_sha256=sha(OUT/'prototype_review.json')))
    calendars=json.loads((CAL/'results.json').read_text());review=json.loads((CAL/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(CAL/'results.json');funded=json.loads((CAL/'funded_results.json').read_text());tasks=[(row,policy,str(out)) for row in funded['rows'] for policy in ('baseline','joint','selected')]
    protected={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'atlases/earth_fit').rglob('*')) if p.is_file()}
    with ProcessPoolExecutor(max_workers=jobs) as pool:cases=list(pool.map(run_case,tasks))
    sources={str((CAL/'results.json').relative_to(ROOT)):sha(CAL/'results.json'),str((CAL/'review.json').relative_to(ROOT)):sha(CAL/'review.json')}
    for c in cases:sources.update(c['sources'])
    write(out/'results.json',dict(status='fixed_source_pickup_event_diagnostic',rows=[c['row'] for c in cases],sources=sources,producers=producers,files_sha256={c['file']:c['sha256'] for c in cases},unchanged_atlas_sha256=protected,scope='All24fixed calendar/source plans retain rural failures and explicit raw pickup deficits. No capacity,date,resident,work or destination replacement;not complete provisioning qualification.'))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--jobs',type=int,default=2);a=p.parse_args();main(a.out,a.jobs)
