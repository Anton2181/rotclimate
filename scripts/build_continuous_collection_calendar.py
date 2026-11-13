"""Pack NEW collection jobs and separate missing cargo from arrival phases."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.event_food_stocks import periodic_event_food_year
from polity.delivery_partition import partition_trip_cargo,lagged_return_times
from polity.worker_calendar import pack_worker_calendar
from settlement_locations_earth import sha,write

OUT=ROOT/'output/continuous_collection_calendar_20261112'
PARENT=ROOT/'output/settlement_continuous_destination_20261112'
PLAN=ROOT/'calibration/continuous_collection_calendar_20261112/plan.json'


def aggregate_events(site,time,cargo):
    order=np.lexsort((time,site));site,time,cargo=site[order],time[order],cargo[order]
    if not len(site):return dict(site=site.astype('i4'),time=time,cargo=cargo,trips=site.astype('i8'))
    starts=np.r_[0,1+np.flatnonzero((np.diff(site)!=0)|(np.diff(time)!=0))]
    return dict(site=site[starts].astype('i4'),time=time[starts],cargo=np.add.reduceat(cargo,starts),trips=np.diff(np.r_[starts,len(site)]))


def run(case,out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes(),'Commit new collection calendar declaration first'
    key=case['key'];folder=PARENT/key;review=json.loads((folder/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(folder/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_destination.py')
    for name,digest in {**case['sources'],**case['producers']}.items():assert sha(ROOT/name)==digest,name
    f=dict(np.load(folder/'fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{case["climate"]}_inputs.npz'));paths=dict(np.load(ROOT/f'output/settlement_monthly_work_20261112/{case["climate"]}_paths.npz'))
    for name in ('owner','local_index','nodes'):np.testing.assert_array_equal(paths[name],x[name])
    n=len(f['total']);owner=x['owner'];workers=np.floor(f['staff']).astype('i8');offsets=np.r_[0,np.cumsum(workers)];active=f['active']
    assert np.array_equal(workers,f['staff']) and np.array_equal(active,f['total']>0)
    origins_by_site=[np.flatnonzero(owner==site) for site in range(n)];empty=np.array([],dtype='i8');complete=[];services_complete=[];work=[];packed_bins=[];missing_bins=[];pieces=[];files={}
    packed_trip_count=missing_trip_count=0;work_hours=0.;max_duty=0.;case_out=out/key;case_out.mkdir(parents=True,exist_ok=True)
    for month in range(12):
        duration=7*(paths['outward_days'][month]+paths['inward_days'][month])+.25;counts=f['origin_trips'][month].astype('i8');services=f['work_secondary_hours'][1:,month].sum(axis=0)
        collected={name:[] for name in ('origin','serial','worker','start','end','site')};worker_rows={name:[] for name in ('work_hours','calendar_end','idle_hours')};unpacked=np.zeros(len(owner),'i8');service_ok=np.zeros(n,bool);collection_ok=np.zeros(n,bool)
        for site in range(n):
            origins=origins_by_site[site];origins=origins[counts[origins]>0]
            assert paths['access'][month,origins].all()
            r=pack_worker_calendar(workers=int(workers[site]),duty_cap_hours=50.,calendar_hours=7*365/12,home_service_hours=float(services[site]),
                collection_origin=origins,collection_count=counts[origins],collection_duration=duration[origins],visit_actor=empty,visit_target=empty,visit_duration=np.array([]),crew=1)
            for name in ('origin','serial','worker','start','end'):collected[name].append(getattr(r,'collection_'+name))
            collected['site'].append(np.full(len(r.collection_origin),site,'i8'))
            for name in worker_rows:worker_rows[name].append(getattr(r,'worker_'+name))
            unpacked[origins]=r.collection_unpacked_counts;service_ok[site]=r.service_packed;collection_ok[site]=r.collection_complete
            np.testing.assert_allclose(r.worker_work_hours.sum(),r.service_packed_hours+np.sum(duration[origins]*(counts[origins]-r.collection_unpacked_counts)),rtol=1e-11,atol=1e-7)
        c={name:np.concatenate(values) for name,values in collected.items()};w={name:np.concatenate(values) for name,values in worker_rows.items()}
        partition=partition_trip_cargo(f['origin_departures'][month],counts,owner,c['origin'],c['serial'],c['site'],provider_count=n)
        np.testing.assert_array_equal(np.bincount(partition.missing_origin,minlength=len(owner)),unpacked)
        time=lagged_return_times(c['end'],month);assert (np.floor(time*12/365).astype(int)==(month+1)%12).all()
        packed=np.bincount(c['site'],weights=partition.packed_cargo*.95,minlength=n);missing=np.bincount(owner[partition.missing_origin],weights=partition.missing_cargo*.95,minlength=n)
        np.testing.assert_allclose(packed+missing,f['arrivals'][(month+1)%12],rtol=1e-12,atol=1e-6)
        packet=dict(**{'collection_'+name:value for name,value in c.items()},**{'worker_'+name:value for name,value in w.items()},worker_offsets=offsets,worker_counts=workers,
            home_service_hours=services,service_packed=service_ok,collection_complete=collection_ok,required_trip_counts=counts,unpacked_trip_counts=unpacked,
            packed_cargo=partition.packed_cargo,missing_origin=partition.missing_origin,missing_serial=partition.missing_serial,missing_cargo=partition.missing_cargo)
        path=case_out/f'calendar_{month:02d}.npz';np.savez_compressed(path,**packet);files[str(path.relative_to(out))]=sha(path)
        complete.append(collection_ok);services_complete.append(service_ok);work.append(np.bincount(np.repeat(np.arange(n),workers),weights=w['work_hours'],minlength=n))
        packed_bins.append(packed);missing_bins.append(missing);pieces.append((c['site'],time,partition.packed_cargo*.95))
        packed_trip_count+=len(c['origin']);missing_trip_count+=len(partition.missing_origin);work_hours+=w['work_hours'].sum();max_duty=max(max_duty,float(w['work_hours'].max(initial=0)))
    events=aggregate_events(*(np.concatenate([p[i] for p in pieces]) for i in range(3)));path=case_out/'events.npz';np.savez_compressed(path,**events);files[str(path.relative_to(out))]=sha(path)
    event_offsets=np.searchsorted(events['site'],np.arange(n+1));packed_arrivals=np.roll(np.stack(packed_bins),1,axis=0);missing_arrivals=np.roll(np.stack(missing_bins),1,axis=0)
    mandatory=active & np.stack(complete).all(axis=0) & np.stack(services_complete).all(axis=0)
    arrays=dict(active=active,actor=x['actor'],residents=f['total'],staff=f['staff'],capacity=f['total']*2500*90,mandatory_complete=mandatory,collection_complete=np.stack(complete),service_packed=np.stack(services_complete),
        worker_work_hours=np.stack(work),planned_arrivals=f['arrivals'],packed_arrivals=packed_arrivals,missing_arrivals=missing_arrivals)
    rows=[]
    for account in 'ABC':
        values={}
        for site in np.flatnonzero(active):
            if account=='C':sl=slice(event_offsets[site],event_offsets[site+1]);times=events['time'][sl];cargo=events['cargo'][sl]
            else:times=np.arange(12)*365/12;cargo=(f['arrivals'] if account=='A' else packed_arrivals)[:,site]
            inventory=periodic_event_food_year(times,cargo,demand_rate=f['total'][site]*2500,capacity=arrays['capacity'][site])
            for name,value in asdict(inventory).items():
                if name not in values:values[name]=np.zeros(n)
                values[name][site]=value
        for name,value in values.items():arrays[account+'__'+name]=value
        food_ok=active & (values['unmet']<=1e-8*np.maximum(1.,values['needed']));arrays[account+'__no_shortage']=food_ok
        if account=='A':
            assert food_ok[active].all()
            for name in values:
                if 'town_'+name in f:np.testing.assert_allclose(values[name][active],f['town_'+name][active],rtol=1e-8,atol=1e-3)
        def summary(mask):
            return dict(scored_providers=int(mask.sum()),food_no_shortage=int((mask & food_ok).sum()),mandatory_complete=int((mask & mandatory).sum()),
                mandatory_and_food=int((mask & mandatory & food_ok).sum()),**{name:float(value[mask].sum()) for name,value in values.items()})
        rows.append(dict(key=key,climate=case['climate'],hours_worker_year=case['hours_worker_year'],accounting=account,**summary(active),unscored_providers=int((~active).sum()),
            actors=[dict(actor_index=a,**summary(active & (x['actor']==a))) for a in range(18)]))
        print(key,account,'food',rows[-1]['food_no_shortage'],'of',int(active.sum()),'mandatory+food',rows[-1]['mandatory_and_food'],flush=True)
    path=case_out/'fields.npz';np.savez_compressed(path,**arrays);files[str(path.relative_to(out))]=sha(path)
    sources={**case['sources'],**case['producers']}
    for p in [folder/'results.json',folder/'review.json',folder/'fields.npz']:sources[str(p.relative_to(ROOT))]=sha(p)
    return dict(key=key,rows=rows,sources=sources,files_sha256=files,packed_trips=packed_trip_count,missing_trips=missing_trip_count,actual_worker_hours=float(work_hours),max_worker_duty=max_duty)


def task(args):return run(*args)


def main(out=OUT,jobs=4):
    controls=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_delivery_partition.py','tests/test_event_food_stocks.py','tests/test_worker_calendar.py'],cwd=ROOT,capture_output=True,text=True)
    assert controls.returncode==0,controls.stdout+controls.stderr
    parent=json.loads((PARENT/'summary.json').read_text());out.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=jobs) as workers:cases=list(workers.map(task,[(case,out) for case in parent['rows']]))
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,ROOT/'polity/delivery_partition.py',ROOT/'polity/worker_calendar.py',ROOT/'harvest/event_food_stocks.py',ROOT/'tests/test_delivery_partition.py']}
    for name,digest in parent['unchanged_atlas_sha256'].items():assert sha(ROOT/name)==digest,name
    write(out/'controls.json',dict(status='passed_before_production',output=controls.stdout,producers=producers))
    write(out/'results.json',dict(status='new_collection_calendar_and_destination_food_audit',adopt=False,rows=[row for c in cases for row in c['rows']],cases=cases,producers=producers,
        unchanged_atlas_sha256=parent['unchanged_atlas_sha256'],scope='Collector-only necessary work/destination cereal audit. A-to-B omissions;B-to-C phases. All active providers retained. No visit-map,source intrabin,ration/location,complete diet or authority qualification.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--jobs',type=int,default=4);args=p.parse_args();main(args.out,args.jobs)
