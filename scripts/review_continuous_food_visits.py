"""Independent full workers,OWN food and strict whole-year point selection."""
import bisect
import json
from math import fsum
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_joint_visit_order import scalar_schedule
from review_delivery_timing import integrate
from review_meal_headroom import stock_end
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'
PARENT=ROOT/'output/settlement_continuous_destination_20261112'
COLLECTOR=ROOT/'output/continuous_collection_calendar_20261112'


def baseline_schedule(workers,services,origins,counts,durations,actors,targets,cost,crew):
    ok=services==0 if not workers else services/workers<=50.;each=services/workers if workers and ok else 0.
    work=[float(each)]*workers;end=work.copy();idle=[0.]*workers;available=[(float(each),w) for w in range(workers)];collection=[];missing=dict(zip(origins.tolist(),counts.tolist()))
    scheduled=np.zeros(len(actors),bool);members=np.full((len(actors),crew),-1,'i8');starts=np.zeros(len(actors));finishes=starts.copy()
    if ok:
        for j in sorted(range(len(origins)),key=lambda j:(-float(durations[j]),int(origins[j]))):
            for serial in range(int(counts[j])):
                duration=float(durations[j])
                if not available or available[0][0]+duration>50.:break
                start,w=available.pop(0);finish=start+duration;collection.append((int(origins[j]),serial,w,start,finish));missing[int(origins[j])]-=1
                work[w]+=duration;end[w]=finish;bisect.insort(available,(finish,w))
    complete=bool(ok and not any(missing.values()))
    if complete:
        for j in sorted(range(len(actors)),key=lambda j:(-float(cost[j])/crew,int(actors[j]),int(targets[j]))):
            duration=float(cost[j])/crew;eligible=sorted((end[w],w) for w in range(workers) if work[w]+duration<=50. and end[w]+duration<=7*365/12)
            if len(eligible)<crew:continue
            chosen=[w for _,w in eligible[:crew]];start=max(end[w] for w in chosen);finish=start+duration;scheduled[j]=True;members[j]=chosen;starts[j]=start;finishes[j]=finish
            for w in chosen:idle[w]+=start-end[w];work[w]+=duration;end[w]=finish
    return dict(collection=collection,missing=[missing[int(o)] for o in origins],scheduled=scheduled,qualified=scheduled&complete,members=members,starts=starts,finishes=finishes,work=work,end=end,idle=idle,
        service_ok=ok,complete=complete,service_each=each)


def check_policy(row,policy,F,f,x,paths):
    key=row['key'];n=len(f['total']);crew=row['crew'];folder=OUT/key/policy;a=dict(np.load(folder/'fields.npz'));workers=f['staff'].astype('i8');offsets=np.r_[0,np.cumsum(workers)]
    by_site=[np.flatnonzero(x['owner']==s) for s in range(n)];tasks=[set() for _ in range(n)];events={};bins=np.zeros((12,n));missing_bins=bins.copy();trip_count=visit_count=worker_count=0
    scheduled_mask=np.zeros_like(F[key+'__served'])
    for month in range(12):
        p=dict(np.load(folder/f'calendar_{month:02d}.npz'));np.testing.assert_array_equal(p['worker_offsets'],offsets);np.testing.assert_array_equal(p['worker_counts'],workers)
        aa,tt=np.where(F[key+'__served'][month]);owners=F[key+'__provider_for_target'][month,aa,tt]
        assert list(zip(p['visit_site'].tolist(),p['visit_actor'].tolist(),p['visit_target'].tolist()))==sorted(zip(owners.tolist(),aa.tolist(),tt.tolist()))
        np.testing.assert_array_equal(p['visit_required_hours'],F[key+'__chosen_cost_hours'][month,p['visit_actor'],p['visit_target']])
        counts=f['origin_trips'][month].astype('i8');np.testing.assert_array_equal(p['required_trip_counts'],counts);services=f['work_secondary_hours'][1:,month].sum(axis=0);np.testing.assert_array_equal(p['home_service_hours'],services)
        co=np.r_[0,np.cumsum(np.bincount(p['collection_site'],minlength=n))];vo=np.r_[0,np.cumsum(np.bincount(p['visit_site'],minlength=n))];unfilled=np.zeros(len(counts),'i8')
        provider_work=np.zeros(n);provider_visit=np.zeros(n);provider_collection=np.zeros(n);max_work=np.zeros(n);max_end=np.zeros(n);physical=np.zeros(n,'i8');complete=np.zeros(n,bool)
        for site in range(n):
            origins=by_site[site];origins=origins[counts[origins]>0];duration=7*(paths['outward_days'][month,origins]+paths['inward_days'][month,origins])+.25
            assert paths['access'][month,origins].all();cl,ch=co[site:site+2];vl,vh=vo[site:site+2]
            replay=baseline_schedule if policy=='baseline' else scalar_schedule
            e=replay(int(workers[site]),float(services[site]),origins,counts[origins],duration,p['visit_actor'][vl:vh],p['visit_target'][vl:vh],p['visit_required_hours'][vl:vh],crew)
            for column,name in enumerate(('origin','serial','worker','start','end')):np.testing.assert_array_equal(p['collection_'+name][cl:ch],[v[column] for v in e['collection']])
            for name,expected in [('visit_scheduled','scheduled'),('visit_bin_qualified','qualified'),('visit_crew','members'),('visit_start','starts'),('visit_end','finishes')]:np.testing.assert_array_equal(p[name][vl:vh],e[expected])
            ws=slice(offsets[site],offsets[site+1])
            for name,expected in [('worker_work_hours','work'),('worker_calendar_end','end'),('worker_idle_hours','idle')]:np.testing.assert_array_equal(p[name][ws],e[expected])
            assert bool(p['collection_complete'][site])==e['complete'] and bool(p['service_packed'][site])==e['service_ok']
            spans=[[(0.,e['service_each'])] for _ in range(int(workers[site]))]
            for _,_,w,start,finish in e['collection']:spans[w].append((start,finish))
            for j in range(int(vl),int(vh)):
                if not p['visit_scheduled'][j]:continue
                members=p['visit_crew'][j].tolist();assert len(set(members))==crew and all(0<=w<workers[site] for w in members)
                assert p['visit_actor'][j]==x['actor'][site];np.testing.assert_allclose(p['visit_end'][j]-p['visit_start'][j],p['visit_required_hours'][j]/crew,atol=1e-12)
                identity=(month,int(p['visit_actor'][j]),int(p['visit_target'][j]));assert identity not in tasks[site];tasks[site].add(identity)
                scheduled_mask[month,identity[1],identity[2]]=True
                for w in members:spans[w].append((float(p['visit_start'][j]),float(p['visit_end'][j])))
            for w,intervals in enumerate(spans):
                last=0.;charged=0.
                for start,finish in sorted(intervals):assert start>=last and finish>=start and finish<=7*365/12;last=finish;charged+=finish-start
                assert e['work'][w]<=50.;np.testing.assert_allclose(charged,e['work'][w],rtol=1e-11,atol=1e-9)
            np.testing.assert_allclose(e['end'],np.asarray(e['work'])+e['idle'],atol=1e-9)
            unfilled[origins]=e['missing'];provider_work[site]=sum(e['work']);provider_visit[site]=p['visit_required_hours'][vl:vh][e['scheduled']].sum()
            provider_collection[site]=sum(v[4]-v[3] for v in e['collection']);max_work[site]=max(e['work'],default=0.);max_end[site]=max(e['end'],default=0.);physical[site]=int(e['scheduled'].sum());complete[site]=e['complete']
            assert provider_visit[site]<=F[key+'__reserved_hours'][month,site]+1e-7 and provider_work[site]<=f['work_gross_hours'][month,site]+1e-7
            trip_count+=len(e['collection']);visit_count+=int(vh-vl);worker_count+=int(workers[site])
        np.testing.assert_array_equal(unfilled,p['unpacked_trip_counts']);np.testing.assert_array_equal(a['bin_complete'][month],complete)
        for field,value in [('work_hours',provider_work),('visit_hours',provider_visit),('collection_hours',provider_collection),('max_worker_hours',max_work),('max_calendar_end',max_end),('physical_visits',physical)]:np.testing.assert_allclose(a[field][month],value,rtol=1e-12,atol=1e-7)
        if policy=='baseline':
            old=dict(np.load(COLLECTOR/row['parent_key']/f'calendar_{month:02d}.npz'))
            for field in old:
                if not field.startswith('worker_') or field in ('worker_counts','worker_offsets'):np.testing.assert_array_equal(p[field],old[field])
        # Full raw cargo partition,including all missing original serials.
        planned={(o,s) for o in np.flatnonzero(counts) for s in range(int(counts[o]))};seen=set()
        for j,(origin,serial,site,end) in enumerate(zip(p['collection_origin'].tolist(),p['collection_serial'].tolist(),p['collection_site'].tolist(),p['collection_end'].tolist())):
            identity=(origin,serial);assert identity in planned and identity not in seen;seen.add(identity);assert x['owner'][origin]==site
            cargo=min(120000.,f['origin_departures'][month,origin]-120000.*serial);assert cargo>0 and cargo==p['packed_cargo'][j]
            time=((month+1)*365/12+end/7)%365;assert int(time*12/365)==(month+1)%12;bins[(month+1)%12,site]+=cargo*.95;events.setdefault((site,time),[]).append(cargo*.95)
        for j,(origin,serial) in enumerate(zip(p['missing_origin'].tolist(),p['missing_serial'].tolist())):
            identity=(origin,serial);assert identity in planned and identity not in seen;seen.add(identity);cargo=min(120000.,f['origin_departures'][month,origin]-120000.*serial)
            assert cargo>0 and cargo==p['missing_cargo'][j];missing_bins[(month+1)%12,x['owner'][origin]]+=cargo*.95
        assert seen==planned
    np.testing.assert_array_equal(scheduled_mask,a['scheduled']);np.testing.assert_allclose(bins,a['packed_arrivals'],rtol=1e-12,atol=1e-6);np.testing.assert_allclose(missing_bins,a['missing_arrivals'],rtol=1e-12,atol=1e-6);np.testing.assert_allclose(bins+missing_bins,f['arrivals'],rtol=1e-12,atol=1e-6)
    ev=dict(np.load(folder/'events.npz'));assert len(events)==len(ev['site'])
    for site,time,cargo,count in zip(ev['site'],ev['time'],ev['cargo'],ev['trips']):
        q=events.pop((int(site),float(time)));assert len(q)==count;np.testing.assert_allclose(fsum(q),cargo,rtol=1e-12,atol=1e-7)
    assert not events;eo=np.searchsorted(ev['site'],np.arange(n+1));active=f['active'];food_checked=0
    for account in 'ABC':
        for site in np.flatnonzero(active):
            if account=='C':sl=slice(eo[site],eo[site+1]);times=ev['time'][sl];cargo=ev['cargo'][sl]
            else:times=np.arange(12)*365/12;cargo=(f['arrivals'] if account=='A' else bins)[:,site]
            rate=f['total'][site]*2500;cap=rate*90
            def drift(stock):return stock_end(times,cargo,rate,cap,stock)-stock
            initial=0. if drift(0.)<=0 else brentq(drift,0.,cap,xtol=1e-7,rtol=1e-14)
            scale=max(1.,rate*365);assert abs(initial-a[account+'__initial_stock'][site])<=1e-9*scale
            values=integrate(times,cargo,rate,cap,float(a[account+'__initial_stock'][site]))
            for name,value in values.items():np.testing.assert_allclose(value,a[account+'__'+name][site],rtol=1e-10,atol=1e-4)
            assert abs(values['periodic_residual'])<=1e-9*scale and abs(values['ledger_residual'])<=1e-9*scale
            assert bool(a[account+'__no_shortage'][site])==(a[account+'__unmet'][site]<=1e-8*max(1.,a[account+'__needed'][site]));food_checked+=1
    np.testing.assert_array_equal(a['mandatory_complete'],active&a['bin_complete'].all(axis=0));np.testing.assert_array_equal(a['qualified'],a['mandatory_complete']&a['C__no_shortage'])
    return a,tasks,dict(trips=trip_count,visits=visit_count,worker_bins=worker_count,food=food_checked)


def main():
    r=json.loads((OUT/'results.json').read_text());funded=json.loads((OUT/'funded_results.json').read_text());counts=dict(trips=0,visits=0,worker_bins=0,food=0)
    for name,digest in {**r['sources'],**r['producers'],**r['unchanged_map_sha256']}.items():assert sha(ROOT/name)==digest,name
    assert len(r['visit_rows'])==32 and len(r['food_rows'])==48 and r['selected_fields_sha256']==sha(OUT/'selected_fields.npz')
    for row in funded['rows']:
        key=row['key'];mode=row['climate'];f=dict(np.load(PARENT/row['parent_key']/'fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));paths=dict(np.load(ROOT/f'output/settlement_monthly_work_20261112/{mode}_paths.npz'))
        with np.load(OUT/'funded_fields.npz') as z:F={name:z[name] for name in z.files if name.startswith(key+'__') or name==mode+'__demand'}
        case=next(v for v in r['cases'] if v['key']==key)
        for name,digest in case['files_sha256'].items():assert sha(OUT/name)==digest,name
        replay={}
        for policy in ('baseline','joint'):
            a,jobs,c=check_policy(row,policy,F,f,x,paths);replay[policy]=(a,jobs)
            for name in counts:counts[name]+=c[name]
            pr=next(v for v in r['visit_rows'] if v['key']==key and v['stage']=='policy' and v['policy']==policy)
            owner=F[key+'__provider_for_target'];valid=F[key+'__served'];qpoints=a['scheduled'] & np.where(valid,a['qualified'][np.maximum(owner,0)],False)
            assert pr['funded_visits']==int(valid.sum()) and pr['physically_scheduled_visits']==int(a['scheduled'].sum()) and pr['qualified_visits']==int(qpoints.sum())
            for actor in pr['actors']:
                i=actor['actor_index'];assert actor['funded_visits']==int(valid[:,i].sum()) and actor['physically_scheduled_visits']==int(a['scheduled'][:,i].sum()) and actor['qualified_visits']==int(qpoints[:,i].sum())
            for account in 'ABC':
                fr=next(v for v in r['food_rows'] if v['key']==key and v['policy']==policy and v['accounting']==account)
                for actor in [None,*range(18)]:
                    mask=f['active'] if actor is None else f['active']&(x['actor']==actor);s=fr if actor is None else fr['actors'][actor]
                    assert s['scored_providers']==int(mask.sum()) and s['food_no_shortage']==int((mask&a[account+'__no_shortage']).sum())
                    for field in a:
                        if field.startswith(account+'__') and field!=account+'__no_shortage':np.testing.assert_allclose(s[field.removeprefix(account+'__')],a[field][mask].sum(),rtol=1e-12,atol=1e-6)
        b,bjobs=replay['baseline'];j,jjobs=replay['joint'];s=dict(np.load(OUT/key/'selected_fields.npz'));n=len(f['total']);chosen=np.zeros(n,'i1');qualified=np.zeros(n,bool);served=np.zeros_like(F[key+'__served']);baseline=served.copy();baseline_count=np.zeros(n,'i8');selected_count=baseline_count.copy()
        for site in range(n):
            base_ok=bool(f['active'][site] and b['bin_complete'][:,site].all() and b['C__no_shortage'][site]);joint_ok=bool(f['active'][site] and j['bin_complete'][:,site].all() and j['C__no_shortage'][site])
            if base_ok:
                baseline_count[site]=len(bjobs[site])
                for month,actor,target in bjobs[site]:baseline[month,actor,target]=True
            if joint_ok and (not base_ok or bjobs[site]<jjobs[site]):chosen[site]=1
            qualified[site]=joint_ok if chosen[site] else base_ok;physical=j if chosen[site] else b;tasks=jjobs[site] if chosen[site] else bjobs[site]
            assert s['selected_mandatory_complete'][site]==bool(f['active'][site] and physical['bin_complete'][:,site].all())
            assert s['selected_food_no_shortage'][site]==bool(f['active'][site] and physical['C__no_shortage'][site])
            for field in ('bin_complete','work_hours','max_worker_hours','max_calendar_end','collection_hours','visit_hours','physical_visits','missing_trips'):np.testing.assert_array_equal(s['provider_'+field][:,site],physical[field][:,site])
            for field in physical:
                if field.startswith('C__'):assert s['food_'+field.removeprefix('C__')][site]==physical[field][site]
            if qualified[site]:
                for month,actor,target in tasks:
                    assert F[key+'__served'][month,actor,target] and F[key+'__provider_for_target'][month,actor,target]==site
                    served[month,actor,target]=True;selected_count[site]+=1
        for name,value in [('policy',chosen),('qualified',qualified),('served',served),('baseline_served',baseline),('baseline_task_counts',baseline_count),('selected_task_counts',selected_count),('added_task_counts',selected_count-baseline_count)]:np.testing.assert_array_equal(s[name],value)
        assert np.all(~baseline|served) and np.all(~served|F[key+'__served'])
        np.testing.assert_array_equal(s['schedule_unqualified'],F[key+'__served']&~served)
        partition=served.astype('u1')+s['schedule_unqualified']
        for field in ('route_unreachable','provider_work_unavailable','capacity_unmet'):np.testing.assert_array_equal(s[field],F[key+'__'+field]);partition+=s[field]
        np.testing.assert_array_equal(partition,np.broadcast_to(F[mode+'__demand'],served.shape).astype('u1'))
        np.testing.assert_array_equal(s['provider_reserved_patrol_hours'],F[key+'__reserved_hours']);np.testing.assert_array_equal(s['provider_unused_patrol_hours'],F[key+'__reserved_hours']-s['provider_visit_hours']);np.testing.assert_array_equal(s['provider_unused_staff_hours'],f['work_gross_hours']-s['provider_work_hours'])
        sr=next(v for v in r['visit_rows'] if v['key']==key and v['stage']=='selected');assert sr['qualified_visits']==int(served.sum()) and sr['baseline_qualified_visits']==int(baseline.sum()) and sr['added_visits']==int(served.sum()-baseline.sum()) and sr['qualified_providers']==int(qualified.sum())
        for actor in sr['actors']:
            i=actor['actor_index'];assert actor['qualified_visits']==int(served[:,i].sum()) and actor['baseline_qualified_visits']==int(baseline[:,i].sum()) and actor['qualified_providers']==int((qualified&(x['actor']==i)).sum())
        with np.load(OUT/'selected_fields.npz') as global_fields:
            for field,value in s.items():np.testing.assert_array_equal(global_fields[key+'__'+field],value)
        print('Independent full calendars,OWN food and selected year',key,flush=True)
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),selected_fields_sha256=sha(OUT/'selected_fields.npz'),reviewer_sha256=sha(Path(__file__)),
        independent_joint_reviewer_sha256=sha(ROOT/'scripts/review_joint_visit_order.py'),scalar_inventory_reviewer_sha256=sha(ROOT/'scripts/review_delivery_timing.py'),scalar_stock_end_reviewer_sha256=sha(ROOT/'scripts/review_meal_headroom.py'),
        counters=counts,visit_rows_checked=32,policy_food_rows_checked=48,one_whole_policy_per_provider_year=True,own_food_and_physical_work_separate=True,baseline_both_task_identities_preserved=True,
        every_final_task_in_new_funded_plan=True,all_active_policy_food_inventories_retained=True,all_actor_request_partitions=True,original_maps_unchanged=True,
        scope='Necessary destination cereal and supplied full calendars only;not source intrabin/rations/location/complete diets/observed roles/held blocks or authority.'))


if __name__=='__main__':main()
