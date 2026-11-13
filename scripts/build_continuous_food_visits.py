"""NEW funded visit jobs,two full calendars and one OWN-food-checked year."""
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
from polity.food_checked_provider_year import select_food_checked_provider_years
from polity.worker_calendar import pack_worker_calendar
from polity.joint_worker_calendar import pack_joint_worker_calendar
from settlement_locations_earth import sha,write

OUT=ROOT/'output/continuous_food_visit_calendars_20261112'
PLAN=ROOT/'calibration/continuous_food_visit_calendars_20261112/plan.json'
PARENT=ROOT/'output/settlement_continuous_destination_20261112'
COLLECTOR=ROOT/'output/continuous_collection_calendar_20261112'


def aggregate(site,time,cargo):
    order=np.lexsort((time,site));site,time,cargo=site[order],time[order],cargo[order]
    if not len(site):return dict(site=site.astype('i4'),time=time,cargo=cargo,trips=site.astype('i8'))
    starts=np.r_[0,1+np.flatnonzero((np.diff(site)!=0)|(np.diff(time)!=0))]
    return dict(site=site[starts].astype('i4'),time=time[starts],cargo=np.add.reduceat(cargo,starts),trips=np.diff(np.r_[starts,len(site)]))


def tasks_from_mask(mask,month,actor,target,site,sets):
    for a,t,s in zip(actor[mask].tolist(),target[mask].tolist(),site[mask].tolist()):
        identity=(month,int(a),int(t));assert identity not in sets[s];sets[s].add(identity)


def policy_run(row,F,f,x,paths,policy,out):
    key=row['key'];crew=row['crew'];n=len(f['total']);workers=f['staff'].astype('i8');offsets=np.r_[0,np.cumsum(workers)];worker_site=np.repeat(np.arange(n),workers)
    by_site=[np.flatnonzero(x['owner']==s) for s in range(n)];jobs=[set() for _ in range(n)];all_scheduled=np.zeros_like(F[key+'__served']);arrays={};months=[];pieces=[];files={}
    folder=out/key/policy;folder.mkdir(parents=True,exist_ok=True)
    for month in range(12):
        aa,tt=np.where(F[key+'__served'][month]);site=F[key+'__provider_for_target'][month,aa,tt];cost=F[key+'__chosen_cost_hours'][month,aa,tt]
        order=np.argsort(site,kind='stable');bounds=np.r_[0,np.cumsum(np.bincount(site,minlength=n))];counts=f['origin_trips'][month].astype('i8');duration=np.zeros(len(counts));positive=counts>0
        assert paths['access'][month,positive].all();duration[positive]=7*(paths['outward_days'][month,positive]+paths['inward_days'][month,positive])+.25
        services=f['work_secondary_hours'][1:,month].sum(axis=0);parts={};unfilled=np.zeros(len(counts),'i8');complete=np.zeros(n,bool);service_ok=np.zeros(n,bool)
        for s in range(n):
            origins=by_site[s];origins=origins[counts[origins]>0];ids=order[bounds[s]:bounds[s+1]];actors,targets=aa[ids],tt[ids];job_cost=cost[ids]
            assert (actors==x['actor'][s]).all()
            packer=pack_worker_calendar if policy=='baseline' else pack_joint_worker_calendar
            r=packer(workers=int(workers[s]),duty_cap_hours=50.,calendar_hours=7*365/12,home_service_hours=float(services[s]),
                collection_origin=origins,collection_count=counts[origins],collection_duration=duration[origins],visit_actor=actors,visit_target=targets,visit_duration=job_cost/crew,crew=crew)
            scheduled=r.visit_packed if policy=='baseline' else r.visit_scheduled;bin_qualified=scheduled & r.collection_complete
            if policy=='joint':np.testing.assert_array_equal(bin_qualified,r.visit_bin_qualified)
            packet={**{name:getattr(r,name) for name in ['collection_origin','collection_serial','collection_worker','collection_start','collection_end','worker_work_hours','worker_calendar_end','worker_idle_hours']},
                'collection_site':np.full(len(r.collection_origin),s,'i8'),'visit_site':np.full(len(ids),s,'i8'),'visit_actor':actors,'visit_target':targets,
                'visit_required_hours':job_cost,'visit_scheduled':scheduled,'visit_bin_qualified':bin_qualified,'visit_crew':r.visit_crew,'visit_start':r.visit_start,'visit_end':r.visit_end}
            for name,value in packet.items():parts.setdefault(name,[]).append(value)
            unfilled[origins]=r.collection_unpacked_counts;complete[s]=r.collection_complete;service_ok[s]=r.service_packed
            np.testing.assert_allclose(r.worker_work_hours.sum(),r.service_packed_hours+np.sum(duration[origins]*(counts[origins]-r.collection_unpacked_counts))+job_cost[scheduled].sum(),rtol=1e-11,atol=1e-7)
        packet={name:np.concatenate(values) for name,values in parts.items()};partition=partition_trip_cargo(f['origin_departures'][month],counts,x['owner'],packet['collection_origin'],packet['collection_serial'],packet['collection_site'],provider_count=n)
        np.testing.assert_array_equal(np.bincount(partition.missing_origin,minlength=len(counts)),unfilled)
        packet.update(worker_offsets=offsets,worker_counts=workers,home_service_hours=services,collection_complete=complete,service_packed=service_ok,required_trip_counts=counts,unpacked_trip_counts=unfilled,
            packed_cargo=partition.packed_cargo,missing_origin=partition.missing_origin,missing_serial=partition.missing_serial,missing_cargo=partition.missing_cargo)
        if policy=='baseline':
            previous=dict(np.load(COLLECTOR/row['parent_key']/f'calendar_{month:02d}.npz'))
            for name in previous:
                if not name.startswith('worker_') or name in ('worker_offsets','worker_counts'):np.testing.assert_array_equal(packet[name],previous[name])
        path=folder/f'calendar_{month:02d}.npz';np.savez_compressed(path,**packet);files[str(path.relative_to(out))]=sha(path)
        scheduled=packet['visit_scheduled'];all_scheduled[month,packet['visit_actor'][scheduled],packet['visit_target'][scheduled]]=True
        tasks_from_mask(scheduled,month,packet['visit_actor'],packet['visit_target'],packet['visit_site'],jobs)
        physical=np.bincount(packet['visit_site'],weights=scheduled,minlength=n).astype('i8');visit_hours=np.bincount(packet['visit_site'],weights=packet['visit_required_hours']*scheduled,minlength=n)
        collection_hours=np.bincount(packet['collection_site'],weights=packet['collection_end']-packet['collection_start'],minlength=n);work=np.bincount(worker_site,weights=packet['worker_work_hours'],minlength=n)
        max_work=np.zeros(n);max_end=np.zeros(n);np.maximum.at(max_work,worker_site,packet['worker_work_hours']);np.maximum.at(max_end,worker_site,packet['worker_calendar_end'])
        np.testing.assert_allclose(work,collection_hours+visit_hours+services*service_ok,rtol=1e-11,atol=1e-7)
        assert (visit_hours<=F[key+'__reserved_hours'][month]+1e-7).all() and (work<=f['work_gross_hours'][month]+1e-7).all()
        times=lagged_return_times(packet['collection_end'],month);pieces.append((packet['collection_site'],times,partition.packed_cargo*.95))
        packed=np.bincount(packet['collection_site'],weights=partition.packed_cargo*.95,minlength=n)
        missing=np.bincount(x['owner'][partition.missing_origin],weights=partition.missing_cargo*.95,minlength=n)
        np.testing.assert_allclose(packed+missing,f['arrivals'][(month+1)%12],rtol=1e-12,atol=1e-6)
        months.append(dict(bin_complete=complete&service_ok,service_packed=service_ok,work_hours=work,max_worker_hours=max_work,max_calendar_end=max_end,collection_hours=collection_hours,visit_hours=visit_hours,
            physical_visits=physical,missing_trips=np.bincount(x['owner'],weights=unfilled,minlength=n).astype('i8'),packed_arrivals=packed,missing_arrivals=missing))
    for name in months[0]:arrays[name]=np.stack([m[name] for m in months])
    for name in ('packed_arrivals','missing_arrivals'):arrays[name]=np.roll(arrays[name],1,axis=0)
    events=aggregate(*(np.concatenate([p[i] for p in pieces]) for i in range(3)));path=folder/'events.npz';np.savez_compressed(path,**events);files[str(path.relative_to(out))]=sha(path)
    eo=np.searchsorted(events['site'],np.arange(n+1));active=f['active'];food_rows=[]
    for account in 'ABC':
        values={}
        for s in np.flatnonzero(active):
            if account=='C':sl=slice(eo[s],eo[s+1]);times=events['time'][sl];cargo=events['cargo'][sl]
            else:times=np.arange(12)*365/12;cargo=(f['arrivals'] if account=='A' else arrays['packed_arrivals'])[:,s]
            inventory=periodic_event_food_year(times,cargo,demand_rate=f['total'][s]*2500,capacity=f['total'][s]*2500*90)
            for name,value in asdict(inventory).items():
                if name not in values:values[name]=np.zeros(n)
                values[name][s]=value
        for name,value in values.items():arrays[account+'__'+name]=value
        food_ok=active & (values['unmet']<=1e-8*np.maximum(1.,values['needed']));arrays[account+'__no_shortage']=food_ok
        def summary(mask):return dict(scored_providers=int(mask.sum()),food_no_shortage=int((mask&food_ok).sum()),**{name:float(value[mask].sum()) for name,value in values.items()})
        food_rows.append(dict(key=key,policy=policy,climate=row['climate'],hours_worker_year=row['hours_worker_year'],crew=crew,accounting=account,**summary(active),
            actors=[dict(actor_index=a,**summary(active&(x['actor']==a))) for a in range(18)]))
        if policy=='baseline':
            previous=dict(np.load(COLLECTOR/row['parent_key']/'fields.npz'))
            for name in values:np.testing.assert_array_equal(arrays[account+'__'+name],previous[account+'__'+name])
            np.testing.assert_array_equal(food_ok,previous[account+'__no_shortage'])
    arrays['scheduled']=all_scheduled;arrays['mandatory_complete']=active & arrays['bin_complete'].all(axis=0);arrays['qualified']=arrays['mandatory_complete'] & arrays['C__no_shortage']
    path=folder/'fields.npz';np.savez_compressed(path,**arrays);files[str(path.relative_to(out))]=sha(path)
    provider_of_job=F[key+'__provider_for_target'];valid=F[key+'__served'];qualified_points=all_scheduled & np.where(valid,arrays['qualified'][np.maximum(provider_of_job,0)],False)
    policy_row=dict(key=key,stage='policy',policy=policy,climate=row['climate'],hours_worker_year=row['hours_worker_year'],crew=crew,funded_visits=int(valid.sum()),physically_scheduled_visits=int(all_scheduled.sum()),
        qualified_visits=int(qualified_points.sum()),mandatory_complete_providers=int(arrays['mandatory_complete'].sum()),food_no_shortage_providers=int(arrays['C__no_shortage'].sum()),qualified_providers=int(arrays['qualified'].sum()),
        missing_collector_trips=int(arrays['missing_trips'].sum()),actual_visit_hours=float(arrays['visit_hours'].sum()),actors=[])
    for actor in range(18):policy_row['actors'].append(dict(actor_index=actor,funded_visits=int(valid[:,actor].sum()),physically_scheduled_visits=int(all_scheduled[:,actor].sum()),qualified_visits=int(qualified_points[:,actor].sum())))
    print(key,policy,'qualified',policy_row['qualified_visits'],'providers',policy_row['qualified_providers'],flush=True)
    return arrays,jobs,policy_row,food_rows,files


def run(row,out):
    key=row['key'];mode=row['climate'];f=dict(np.load(PARENT/row['parent_key']/'fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));paths=dict(np.load(ROOT/f'output/settlement_monthly_work_20261112/{mode}_paths.npz'))
    with np.load(OUT/'funded_fields.npz') as z:F={name:z[name] for name in z.files if name.startswith(key+'__') or name==mode+'__demand'}
    n=len(f['total']);funded=[set() for _ in range(n)]
    for month in range(12):
        a,t=np.where(F[key+'__served'][month]);s=F[key+'__provider_for_target'][month,a,t];tasks_from_mask(np.ones(len(a),bool),month,a,t,s,funded)
    results={policy:policy_run(row,F,f,x,paths,policy,out) for policy in ('baseline','joint')};b,bjobs,br,bfood,bfiles=results['baseline'];j,jjobs,jr,jfood,jfiles=results['joint']
    chosen=select_food_checked_provider_years(active=f['active'],baseline_complete=b['bin_complete'],joint_complete=j['bin_complete'],baseline_food=b['C__no_shortage'],joint_food=j['C__no_shortage'],
        baseline_tasks=bjobs,joint_tasks=jjobs,funded_tasks=funded)
    selected={name:getattr(chosen,name) for name in chosen.__dataclass_fields__ if name!='qualified_tasks'};served=np.zeros_like(F[key+'__served']);baseline=np.zeros_like(served);completed=np.zeros((12,n),'i8')
    for site in range(n):
        if b['qualified'][site]:
            for month,a,t in bjobs[site]:baseline[month,a,t]=True
        for month,a,t in chosen.qualified_tasks[site]:
            assert F[key+'__served'][month,a,t] and F[key+'__provider_for_target'][month,a,t]==site
            served[month,a,t]=True;completed[month,site]+=1
    assert np.all(~baseline|served) and np.all(~served|F[key+'__served'])
    selected.update(served=served,baseline_served=baseline,original_funded=F[key+'__served'],schedule_unqualified=F[key+'__served']&~served,provider_completed_visits=completed)
    for name in ('route_unreachable','provider_work_unavailable','capacity_unmet'):selected[name]=F[key+'__'+name]
    partition=served.astype('u1')+selected['schedule_unqualified']
    for name in ('route_unreachable','provider_work_unavailable','capacity_unmet'):partition+=selected[name]
    np.testing.assert_array_equal(partition,np.broadcast_to(F[mode+'__demand'],served.shape).astype('u1'))
    use_joint=chosen.policy==1
    for name in ('bin_complete','work_hours','max_worker_hours','max_calendar_end','collection_hours','visit_hours','physical_visits','missing_trips'):
        selected['provider_'+name]=np.where(use_joint[None,:],j[name],b[name])
    for name in b:
        if name.startswith('C__'):selected['food_'+name.removeprefix('C__')]=np.where(use_joint,j[name],b[name])
    selected['provider_reserved_patrol_hours']=F[key+'__reserved_hours'];selected['provider_unused_patrol_hours']=F[key+'__reserved_hours']-selected['provider_visit_hours'];selected['provider_unused_staff_hours']=f['work_gross_hours']-selected['provider_work_hours']
    selected_row=dict(key=key,stage='selected',policy='one_provider_year',climate=mode,hours_worker_year=row['hours_worker_year'],crew=row['crew'],funded_visits=int(F[key+'__served'].sum()),
        physically_scheduled_visits=int(selected['provider_physical_visits'].sum()),qualified_visits=int(served.sum()),baseline_qualified_visits=int(baseline.sum()),added_visits=int(served.sum()-baseline.sum()),
        qualified_providers=int(chosen.qualified.sum()),mandatory_complete_providers=int(chosen.selected_mandatory_complete.sum()),food_no_shortage_providers=int(chosen.selected_food_no_shortage.sum()),
        joint_policy_providers=int(use_joint.sum()),baseline_tasks_lost=0,actors=[])
    for actor in range(18):selected_row['actors'].append(dict(actor_index=actor,funded_visits=int(F[key+'__served'][:,actor].sum()),baseline_qualified_visits=int(baseline[:,actor].sum()),qualified_visits=int(served[:,actor].sum()),qualified_providers=int((chosen.qualified&(x['actor']==actor)).sum())))
    folder=out/key;path=folder/'selected_fields.npz';np.savez_compressed(path,**selected);files={**bfiles,**jfiles,str(path.relative_to(out)):sha(path)}
    funded_row=dict(row,stage='funded',policy='hour_plan',funded_visits=row['completed_visits'],qualified_visits=None,physically_scheduled_visits=None)
    write(folder/'case.json',dict(key=key,visit_rows=[funded_row,br,jr,selected_row],food_rows=[*bfood,*jfood],files_sha256=files))
    print(key,'selected',selected_row['qualified_visits'],'baselineBoth',selected_row['baseline_qualified_visits'],flush=True)
    return dict(key=key,visit_rows=[funded_row,br,jr,selected_row],food_rows=[*bfood,*jfood],files_sha256=files)


def task(args):return run(*args)


def main(out=OUT,jobs=4):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes(),'Commit visit/food declaration first'
    funded=json.loads((OUT/'funded_results.json').read_text());review=json.loads((OUT/'funded_review.json').read_text());reference=json.loads((COLLECTOR/'results.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'funded_results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_point_jobs.py')
    controls=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_network_visits.py','tests/test_food_checked_provider_year.py','tests/test_joint_worker_calendar.py','tests/test_provider_year_schedule.py','tests/test_worker_calendar.py','tests/test_delivery_partition.py','tests/test_event_food_stocks.py'],cwd=ROOT,capture_output=True,text=True)
    assert controls.returncode==0,controls.stdout+controls.stderr
    sources={**funded['sources'],**funded['producers']}
    for p in [OUT/'funded_results.json',OUT/'funded_fields.npz',OUT/'funded_review.json',COLLECTOR/'results.json',COLLECTOR/'review.json']:sources[str(p.relative_to(ROOT))]=sha(p)
    for case in reference['cases']:
        for name,digest in case['files_sha256'].items():sources[str((COLLECTOR/name).relative_to(ROOT))]=digest
    for name,digest in {**sources,**funded['unchanged_map_sha256']}.items():assert sha(ROOT/name)==digest,name
    out.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=jobs) as workers:cases=list(workers.map(task,[(row,out) for row in funded['rows']]))
    arrays={}
    for case in cases:
        with np.load(out/case['key']/'selected_fields.npz') as z:
            for name in z.files:arrays[case['key']+'__'+name]=z[name]
    with np.load(OUT/'funded_fields.npz') as z:
        for mode in ('raw','corrected'):arrays[mode+'__demand']=z[mode+'__demand']
    np.savez_compressed(out/'selected_fields.npz',**arrays)
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,ROOT/'polity/food_checked_provider_year.py',ROOT/'polity/provider_year_schedule.py',ROOT/'polity/worker_calendar.py',ROOT/'polity/joint_worker_calendar.py',ROOT/'polity/delivery_partition.py',ROOT/'harvest/event_food_stocks.py']}
    for name,digest in {**sources,**funded['unchanged_map_sha256']}.items():assert sha(ROOT/name)==digest,name
    write(out/'calendar_controls.json',dict(status='passed_before_full_calendars',output=controls.stdout,producers=producers))
    write(out/'results.json',dict(status='continuous_cereal_and_whole_provider_year_point_visits',adopt=False,visit_rows=[v for c in cases for v in c['visit_rows']],food_rows=[v for c in cases for v in c['food_rows']],cases=cases,
        sources=sources,producers=producers,selected_fields_sha256=sha(out/'selected_fields.npz'),unchanged_map_sha256=funded['unchanged_map_sha256'],
        scope='One WHOLE provider-year,OWN cereal food plus12mandatory bins,strict baseline Both-task preservation. Necessary under supplied source/availability/ration assumptions,not complete provisioning,observed roles,held blocks or authority.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--jobs',type=int,default=4);args=p.parse_args();main(args.out,args.jobs)
