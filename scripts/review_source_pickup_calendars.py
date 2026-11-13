"""Independent actual pickup clocks/IDs and scalar export stores for all24plans."""
import json,math,sys
from pathlib import Path
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_food_events_20261113';CAL=ROOT/'output/continuous_food_visit_calendars_20261112'
NAMES=('initial_stock','final_stock','peak_stock','quota_input','requested','withdrawn','unfilled','spoiled','overflow','ledger_residual','periodic_residual')

@njit
def run_export(times,requests,lo,hi,quota_time,quota,cap,initial):
    h=-math.log(.95)/365;stock=peak=initial;clock=0.;crop=False;loss=spill=requested=withdrawn=0.;taken=np.zeros(hi-lo);missing=np.zeros(hi-lo)
    for j in range(lo,hi):
        time=times[j]
        if not crop and quota_time<=time:
            after=stock*math.exp(-h*(quota_time-clock));loss+=stock-after;stock=after+quota;spill+=max(0.,stock-cap);stock=min(cap,stock);peak=max(peak,stock);clock=quota_time;crop=True
        after=stock*math.exp(-h*(time-clock));loss+=stock-after;stock=after;amount=min(stock,requests[j]);stock-=amount;taken[j-lo]=amount;missing[j-lo]=requests[j]-amount;requested+=requests[j];withdrawn+=amount;clock=time
    if not crop:
        after=stock*math.exp(-h*(quota_time-clock));loss+=stock-after;stock=after+quota;spill+=max(0.,stock-cap);stock=min(cap,stock);peak=max(peak,stock);clock=quota_time
    after=stock*math.exp(-h*(365-clock));loss+=stock-after;stock=after
    return np.array([initial,stock,peak,quota,requested,withdrawn,missing.sum(),loss,spill,initial+quota-stock-withdrawn-loss-spill,stock-initial]),taken,missing

@njit
def all_exports(times,requests,offsets,month,energy,rural_cap,export_cap):
    n=len(month);values=np.zeros((11,n));taken=np.zeros(len(times));missing=np.zeros(len(times));h=-math.log(.95)/365
    for o in range(n):
        lo,hi=offsets[o:o+2];qt=month[o]*365/12;quota=max(0.,energy[o]-rural_cap[o])*.1;cap=export_cap[o]
        low=run_export(times,requests,lo,hi,qt,quota,cap,0.)[0][1];high=run_export(times,requests,lo,hi,qt,quota,cap,cap)[0][1];balance=quota*math.exp(-h*(365-qt))
        for j in range(lo,hi):balance-=requests[j]*math.exp(-h*(365-times[j]))
        initial=min(high,max(low,balance/(1-.95)));v,a,b=run_export(times,requests,lo,hi,qt,quota,cap,initial);values[:,o]=v;taken[lo:hi]=a;missing[lo:hi]=b
    return values,taken,missing


def main():
    r=json.loads((OUT/'results.json').read_text());assert len(r['rows'])==24;requests_checked=origins_checked=actors_checked=0;largest=0.
    for n,d in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/n)==d,n
    for n,d in r['files_sha256'].items():assert sha(OUT/n)==d,n
    source_review=ROOT/'output/source_continuous_meals_20261113/review.json';sr=json.loads(source_review.read_text());assert sr['status']=='passed' and sr['results_sha256']==sha(source_review.parent/'results.json')
    for row in r['rows']:
        key=row['key'];mode=row['climate'];policy=row['policy'];f=dict(np.load(OUT/(row['case']+'_fields.npz')));parent=dict(np.load(ROOT/f'output/settlement_continuous_destination_20261112/{mode}_h{row["hours_worker_year"]}_load120000_all_open/fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));paths=dict(np.load(ROOT/f'output/settlement_monthly_work_20261112/{mode}_paths.npz'));S=np.load(CAL/'selected_fields.npz')[key+'__policy']
        expected=[]
        for month in range(12):
            for pol in (('baseline','joint') if policy=='selected' else (policy,)):
                c=dict(np.load(CAL/key/pol/f'calendar_{month:02d}.npz'));keep=S[c['collection_site']]==int(pol=='joint') if policy=='selected' else np.ones(len(c['collection_origin']),bool)
                origin=c['collection_origin'][keep];serial=c['collection_serial'][keep];provider=c['collection_site'][keep];time=month*365/12+(c['collection_start'][keep]+7*paths['outward_days'][month,origin]+.25)/7
                assert np.all(time<=month*365/12+c['collection_end'][keep]/7+1e-10);np.testing.assert_array_equal(provider,x['owner'][origin]);cargo=np.minimum(120000.,parent['origin_departures'][month,origin]-120000.*serial);np.testing.assert_array_equal(cargo,c['packed_cargo'][keep]);ids=month*(1<<48)+origin*(1<<24)+serial
                expected.append(dict(origin=origin,serial=serial,provider=provider,time=time,id=ids,requested=cargo,month=np.full(len(origin),month,'i1')))
        e={n:np.concatenate([v[n] for v in expected]) for n in expected[0]};order=np.lexsort((e['id'],e['time'],e['origin']))
        for n,v in e.items():np.testing.assert_array_equal(f['pickup__'+n],v[order])
        assert len(np.unique(f['pickup__id']))==len(order);offset=np.r_[0,np.cumsum(np.bincount(f['pickup__origin'],minlength=row['origins']))];np.testing.assert_array_equal(offset,f['request_offsets'])
        source=dict(np.load(source_review.parent/f'{mode}_h{row["hours_worker_year"]}_fields.npz'))
        for name,v in f.items():
            if name.startswith('rural__'):
                prior=source['local__B__'+name[7:]];scale=np.maximum(1.,source['local__capacity']);error=float(np.max(abs(v-prior)/scale));largest=max(largest,error);assert error<=1e-9,(row['case'],name,error)
        for name,expected_value in [('origin_grid_node',x['local_index']),('owner',x['owner']),('actor',x['actor'][x['owner']]),('people',parent['rural']),('produced',parent['produced_kcal']),('rural_capacity',parent['rural']*2500*365),('export_capacity',parent['export_harvested']),('harvest_bin',source['local__harvest_bin'])]:np.testing.assert_array_equal(f[name],expected_value)
        values,taken,missing=all_exports(f['pickup__time'],f['pickup__requested'],offset,f['harvest_bin'],f['produced'],f['rural_capacity'],f['export_capacity']);scale=np.maximum(1.,np.maximum(f['export_capacity'],f['export__requested']))
        for i,name in enumerate(NAMES):
            error=float(np.max(abs(values[i]-f['export__'+name])/scale));largest=max(largest,error);assert error<=1e-9,(row['case'],name,error)
        np.testing.assert_allclose(taken,f['pickup__withdrawn'],rtol=1e-8,atol=1e-4);np.testing.assert_allclose(missing,f['pickup__unfilled'],rtol=1e-8,atol=1e-4)
        np.testing.assert_allclose(f['pickup__withdrawn']+f['pickup__unfilled'],f['pickup__requested'],rtol=1e-12,atol=1e-6);np.testing.assert_allclose(f['uncollected'],f['rural__overflow']*.9+f['export__overflow'],rtol=1e-12,atol=1e-6)
        assert np.all(abs(f['total_ledger_residual'])<=1e-9*np.maximum(1.,f['produced']))
        for name,flag in [('rural_food_pass',f['rural__unmet']<=1e-8*np.maximum(1.,f['rural__needed'])),('export_request_pass',f['export__unfilled']<=1e-8*np.maximum(1.,f['export__requested']))]:np.testing.assert_array_equal(f[name],flag)
        np.testing.assert_array_equal(f['both_pass'],f['rural_food_pass']&f['export_request_pass']);assert not f['rural_food_pass'][f['people']>0].any()
        for name in ['rural__needed','rural__unmet','export__requested','export__withdrawn','export__unfilled','uncollected']:np.testing.assert_allclose(f['provider__'+name],np.bincount(x['owner'],weights=f[name],minlength=len(parent['total'])),rtol=1e-12,atol=1e-5)
        for name,column in [('rural_food_pass','rural_food_pass_providers'),('export_request_pass','export_request_pass_providers'),('both_pass','both_providers')]:
            np.testing.assert_array_equal(f['provider__'+name],parent['active']&~(np.bincount(x['owner'],weights=~f[name],minlength=len(parent['total']))>0));assert row[column]==int(f['provider__'+name].sum())
        for column,expected_value in [('origins',len(f['people'])),('positive_people_origins',int((f['people']>0).sum())),('rural_food_pass_origins',int(f['rural_food_pass'].sum())),('export_request_pass_origins',int(f['export_request_pass'].sum())),('both_origins',int(f['both_pass'].sum())),('pickup_requests',len(order)),('active_providers',int(parent['active'].sum()))]:assert row[column]==expected_value
        for name,array in [('raw_requested',f['pickup__requested']),('raw_withdrawn',taken),('raw_unfilled',missing),('rural_needed',f['rural__needed']),('rural_unmet',f['rural__unmet'])]:assert abs(row[name]-float(array.sum()))<=1e-9*max(1.,float(abs(array).sum()))
        for actor in row['actors']:
            i=actor['actor'];local=f['actor']==i;owned=x['actor']==i;tasks=x['actor'][f['pickup__provider']]==i
            assert actor['origins']==int(local.sum()) and actor['active_providers']==int((owned&parent['active']).sum())
            for name,field in [('rural_food_pass_providers','rural_food_pass'),('export_request_pass_providers','export_request_pass'),('both_providers','both_pass')]:assert actor[name]==int((owned&f['provider__'+field]).sum())
            for name,array,mask in [('raw_requested',f['pickup__requested'],tasks),('raw_withdrawn',taken,tasks),('raw_unfilled',missing,tasks),('rural_unmet',f['rural__unmet'],local)]:assert abs(actor[name]-float(array[mask].sum()))<=1e-9*max(1.,float(abs(array[mask]).sum()))
            actors_checked+=1
        requests_checked+=len(order);origins_checked+=row['origins'];print('Independent source pickup IDs,clocks,raw cargo and stores passed',row['case'],flush=True)
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),source_meal_review_sha256=sha(source_review),cases=24,pickup_requests_checked=requests_checked,origin_two_store_years_checked=origins_checked,actor_rows_checked=actors_checked,largest_account_error_per_energy_scale=largest,all_partial_and_rural_failed_sources_retained=True,raw_source_retention_not_applied=True,prior_maps_and_destination_food_unchanged=True))
if __name__=='__main__':main()
