"""Independent sorted-list workers,cargo partitions and scalar food inventories."""
import bisect
import json
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import brentq

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_delivery_timing import integrate
from review_meal_headroom import stock_end
from settlement_locations_earth import sha,write

OUT=ROOT/'output/continuous_collection_calendar_20261112'
PARENT=ROOT/'output/settlement_continuous_destination_20261112'


def main():
    r=json.loads((OUT/'results.json').read_text());trip_records=worker_bins=food_records=missing_records=0
    for name,digest in {**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for case in r['cases']:
        key=case['key'];mode=case['rows'][0]['climate'];f=dict(np.load(PARENT/key/'fields.npz'));a=dict(np.load(OUT/key/'fields.npz'))
        x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));paths=dict(np.load(ROOT/f'output/settlement_monthly_work_20261112/{mode}_paths.npz'))
        for name,digest in case['sources'].items():assert sha(ROOT/name)==digest,name
        for name,digest in case['files_sha256'].items():assert sha(OUT/name)==digest,name
        n=len(f['total']);workers=f['staff'].astype('i8');offsets=np.r_[0,np.cumsum(workers)];active=f['active'];by_site=[np.flatnonzero(x['owner']==site) for site in range(n)]
        np.testing.assert_array_equal(a['active'],active);np.testing.assert_array_equal(a['residents'],f['total']);np.testing.assert_array_equal(a['staff'],f['staff']);np.testing.assert_array_equal(a['capacity'],f['total']*2500*90)
        bins=np.zeros((12,n));missing_bins=bins.copy();events={};missing_count=0;packed_count=0;total_work=0.;flags=[]
        for month in range(12):
            c=dict(np.load(OUT/key/f'calendar_{month:02d}.npz'));counts=f['origin_trips'][month].astype('i8');services=f['work_secondary_hours'][1:,month].sum(axis=0)
            np.testing.assert_array_equal(c['worker_counts'],workers);np.testing.assert_array_equal(c['worker_offsets'],offsets);np.testing.assert_array_equal(c['home_service_hours'],services);np.testing.assert_array_equal(c['required_trip_counts'],counts)
            boundaries=np.r_[0,np.cumsum(np.bincount(c['collection_site'],minlength=n))];missing=np.zeros(len(counts),'i8');service_flags=[];collection_flags=[]
            for site in range(n):
                w=int(workers[site]);service_ok=services[site]==0 if w==0 else services[site]/w<=50.;each=services[site]/w if w and service_ok else 0.
                duty=[float(each)]*w;ends=duty.copy();available=[(float(each),j) for j in range(w)];expected=[];origins=by_site[site];origins=origins[counts[origins]>0]
                durations={int(o):float(7*(paths['outward_days'][month,o]+paths['inward_days'][month,o])+.25) for o in origins}
                for origin in sorted(origins.tolist(),key=lambda o:(-durations[o],o)):
                    assert paths['access'][month,origin];packed=0
                    if service_ok:
                        for serial in range(int(counts[origin])):
                            if not available or available[0][0]+durations[origin]>50.:break
                            start,worker=available.pop(0);end=start+durations[origin];expected.append((origin,serial,worker,start,end));duty[worker]+=durations[origin];ends[worker]=end
                            bisect.insort(available,(end,worker));packed+=1
                    missing[origin]=counts[origin]-packed
                start,end=boundaries[site:site+2]
                for column,name in enumerate(('origin','serial','worker','start','end')):np.testing.assert_array_equal(c['collection_'+name][start:end],[v[column] for v in expected])
                np.testing.assert_array_equal(c['collection_site'][start:end],np.full(len(expected),site))
                ws=slice(offsets[site],offsets[site+1]);np.testing.assert_array_equal(c['worker_work_hours'][ws],duty);np.testing.assert_array_equal(c['worker_calendar_end'][ws],ends);assert not c['worker_idle_hours'][ws].any()
                intervals=[float(each)]*w
                for _,_,worker,left,right in expected:
                    assert left>=intervals[worker] and right>=left and right<=7*365/12;intervals[worker]=right
                assert all(v<=50 for v in duty);complete=bool(service_ok and not missing[origins].any())
                assert bool(c['service_packed'][site])==service_ok and bool(c['collection_complete'][site])==complete
                service_flags.append(service_ok);collection_flags.append(complete);worker_bins+=w;total_work+=sum(duty)
            np.testing.assert_array_equal(c['unpacked_trip_counts'],missing)
            np.testing.assert_array_equal(a['collection_complete'][month],collection_flags);np.testing.assert_array_equal(a['service_packed'][month],service_flags)
            expected_work=np.bincount(np.repeat(np.arange(n),workers),weights=c['worker_work_hours'],minlength=n);np.testing.assert_array_equal(a['worker_work_hours'][month],expected_work)
            # One complete original identity set includes BOTH delivered and missing.
            planned={(o,s) for o in np.flatnonzero(counts) for s in range(int(counts[o]))};seen=set()
            for j,(origin,serial,site,end) in enumerate(zip(c['collection_origin'].tolist(),c['collection_serial'].tolist(),c['collection_site'].tolist(),c['collection_end'].tolist())):
                identity=(origin,serial);assert identity in planned and identity not in seen;seen.add(identity);assert x['owner'][origin]==site
                cargo=min(120000.,f['origin_departures'][month,origin]-120000.*serial);assert cargo>0 and c['packed_cargo'][j]==cargo
                time=((month+1)*365/12+end/7)%365;assert int(time*12/365)==(month+1)%12
                bins[(month+1)%12,site]+=cargo*.95;events.setdefault((site,time),[]).append(cargo*.95)
            for j,(origin,serial) in enumerate(zip(c['missing_origin'].tolist(),c['missing_serial'].tolist())):
                identity=(origin,serial);assert identity in planned and identity not in seen;seen.add(identity)
                cargo=min(120000.,f['origin_departures'][month,origin]-120000.*serial);assert cargo>0 and c['missing_cargo'][j]==cargo
                missing_bins[(month+1)%12,x['owner'][origin]]+=cargo*.95
            assert seen==planned
            packed_count+=len(c['collection_origin']);missing_count+=len(c['missing_origin']);flags.append(np.asarray(collection_flags)&service_flags)
        np.testing.assert_allclose(bins,a['packed_arrivals'],rtol=1e-12,atol=1e-6);np.testing.assert_allclose(missing_bins,a['missing_arrivals'],rtol=1e-12,atol=1e-6);np.testing.assert_allclose(bins+missing_bins,f['arrivals'],rtol=1e-12,atol=1e-6)
        np.testing.assert_array_equal(a['mandatory_complete'],active & np.stack(flags).all(axis=0));np.testing.assert_array_equal(a['planned_arrivals'],f['arrivals'])
        e=dict(np.load(OUT/key/'events.npz'));assert len(events)==len(e['site'])
        from math import fsum
        for site,time,cargo,count in zip(e['site'],e['time'],e['cargo'],e['trips']):
            q=events.pop((int(site),float(time)));assert len(q)==count;np.testing.assert_allclose(fsum(q),cargo,rtol=1e-12,atol=1e-7)
        assert not events and int(e['trips'].sum())==packed_count and case['packed_trips']==packed_count and case['missing_trips']==missing_count
        np.testing.assert_allclose(total_work,case['actual_worker_hours'],rtol=1e-12,atol=1e-6)
        trip_records+=packed_count;missing_records+=missing_count;eo=np.searchsorted(e['site'],np.arange(n+1))
        for account in 'ABC':
            for site in np.flatnonzero(active):
                if account=='C':sl=slice(eo[site],eo[site+1]);times=e['time'][sl];cargo=e['cargo'][sl]
                else:times=np.arange(12)*365/12;cargo=(f['arrivals'] if account=='A' else bins)[:,site]
                rate=f['total'][site]*2500;cap=a['capacity'][site]
                def drift(initial):return stock_end(times,cargo,rate,cap,initial)-initial
                initial=0. if drift(0.)<=0 else brentq(drift,0.,cap,xtol=1e-7,rtol=1e-14)
                scale=max(1.,rate*365);assert abs(initial-a[account+'__initial_stock'][site])<=1e-9*scale
                values=integrate(times,cargo,rate,cap,float(a[account+'__initial_stock'][site]))
                for name,value in values.items():np.testing.assert_allclose(value,a[account+'__'+name][site],rtol=1e-10,atol=1e-4)
                assert abs(values['periodic_residual'])<=1e-9*scale and abs(values['ledger_residual'])<=1e-9*scale
                assert abs(values['needed']-values['consumed']-values['unmet'])<=1e-9*scale
                assert bool(a[account+'__no_shortage'][site])==(a[account+'__unmet'][site]<=1e-8*max(1.,a[account+'__needed'][site]))
                food_records+=1
            row=next(v for v in r['rows'] if v['key']==key and v['accounting']==account)
            for actor in [None,*range(18)]:
                mask=active if actor is None else active & (x['actor']==actor);s=row if actor is None else row['actors'][actor]
                assert s['scored_providers']==int(mask.sum()) and s['food_no_shortage']==int((mask & a[account+'__no_shortage']).sum())
                assert s['mandatory_complete']==int((mask & a['mandatory_complete']).sum()) and s['mandatory_and_food']==int((mask & a['mandatory_complete'] & a[account+'__no_shortage']).sum())
                for name in values:np.testing.assert_allclose(s[name],a[account+'__'+name][mask].sum(),rtol=1e-12,atol=1e-6)
            assert not a[account+'__no_shortage'][~active].any()
        np.testing.assert_allclose(a['B__harvested'],a['C__harvested'],rtol=1e-12,atol=1e-6)
        print('Independent NEW calendars/cargo/all-provider food',key,flush=True)
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        scalar_inventory_reviewer_sha256=sha(ROOT/'scripts/review_delivery_timing.py'),scalar_stock_end_reviewer_sha256=sha(ROOT/'scripts/review_meal_headroom.py'),
        packed_trip_identities_checked=trip_records,missing_trip_identities_checked=missing_records,worker_bins_checked=worker_bins,active_provider_food_inventories_checked=food_records,
        all_twelve_rows_and_actor_summaries_checked=True,all_partial_delivery_providers_retained=True,original_lag_and_retention_once=True,
        omissions_separate_from_phase=True,original_atlas_unchanged=True,scope='Collector-only necessary work/destination cereal;not visit calendars,source intrabin food,rations/location,complete diets or authority.'))


if __name__=='__main__':main()
