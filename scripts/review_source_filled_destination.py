"""Independent full source/return-event joins and scalar destination inventories."""
import json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import brentq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_delivery_timing import integrate
from review_meal_headroom import stock_end
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_filled_destination_20261113';SRC=ROOT/'output/source_food_events_20261113';CAL=ROOT/'output/continuous_food_visit_calendars_20261112'

def main():
    r=json.loads((OUT/'results.json').read_text());sr=json.loads((SRC/'results.json').read_text());requests=events=food=actors=0
    assert len(r['rows'])==48
    for n,d in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/n)==d,n
    for n,d in r['files_sha256'].items():assert sha(OUT/n)==d,n
    for source in sr['rows']:
        case,key,mode,policy=[source[n] for n in ('case','key','climate','policy')];ev=dict(np.load(OUT/(case+'_events.npz')));fields=dict(np.load(OUT/(case+'_fields.npz')));s=dict(np.load(SRC/(case+'_fields.npz')));f=dict(np.load(ROOT/f'output/settlement_continuous_destination_20261112/{mode}_h{source["hours_worker_year"]}_load120000_all_open/fields.npz'));S=np.load(CAL/'selected_fields.npz')[key+'__policy'];n=len(f['total']);pieces=[]
        for month in range(12):
            for pol in (('baseline','joint') if policy=='selected' else (policy,)):
                c=dict(np.load(CAL/key/pol/f'calendar_{month:02d}.npz'));keep=S[c['collection_site']]==int(pol=='joint') if policy=='selected' else np.ones(len(c['collection_site']),bool);origin=c['collection_origin'][keep];serial=c['collection_serial'][keep];site=c['collection_site'][keep];ids=month*(1<<48)+origin*(1<<24)+serial;time=((month+1)*365/12+c['collection_end'][keep]/7)%365;raw=c['packed_cargo'][keep];assert np.all((time>=0)&(time<365)) and np.all((time*12/365).astype(int)==(month+1)%12);pieces.append(dict(id=ids,time=time,site=site,raw=raw))
        p={n:np.concatenate([v[n] for v in pieces]) for n in pieces[0]};assert len(p['id'])==len(s['pickup__id']);src_order=np.argsort(s['pickup__id']);idx=np.searchsorted(s['pickup__id'][src_order],p['id']);np.testing.assert_array_equal(s['pickup__id'][src_order[idx]],p['id']);np.testing.assert_array_equal(s['pickup__requested'][src_order[idx]],p['raw']);taken=s['pickup__withdrawn'][src_order[idx]];missing=s['pickup__unfilled'][src_order[idx]];assert np.all((taken>=0)&(taken<=p['raw']));np.testing.assert_allclose(taken+missing,p['raw'],rtol=1e-12,atol=1e-6)
        order=np.lexsort((p['time'],p['site']));site=p['site'][order];time=p['time'][order];starts=np.r_[0,1+np.flatnonzero((np.diff(site)!=0)|(np.diff(time)!=0))];np.testing.assert_array_equal(ev['site'],site[starts]);np.testing.assert_array_equal(ev['time'],time[starts]);np.testing.assert_array_equal(ev['trips'],np.diff(np.r_[starts,len(site)]))
        for column,q in [('A_cargo',p['raw']*.95),('B_cargo',taken*.95),('unfilled_retained_potential',missing*.95)]:
            # Separate accumulation from the production reduceat path.
            group=np.repeat(np.arange(len(starts)),np.diff(np.r_[starts,len(order)]));expected=np.bincount(group,weights=q[order],minlength=len(starts));np.testing.assert_allclose(ev[column],expected,rtol=1e-12,atol=1e-5)
        np.testing.assert_allclose(ev['B_cargo']+ev['unfilled_retained_potential'],ev['A_cargo'],rtol=1e-12,atol=1e-5);assert abs(float(ev['unfilled_retained_potential'].sum())-source['raw_unfilled']*.95)<=1e-10*max(1.,source['raw_unfilled'])
        x=np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz');np.testing.assert_array_equal(fields['actor'],x['actor']);np.testing.assert_array_equal(s['provider_actor'],x['actor']);np.testing.assert_array_equal(s['provider_active'],f['active'])
        for name,column in [('active','active'),('people','total'),('staff','staff')]:np.testing.assert_array_equal(fields[name],f[column])
        np.testing.assert_array_equal(fields['capacity'],f['total']*2500*90)
        for name,original in [('source_rural_food_pass','provider__rural_food_pass'),('source_export_request_pass','provider__export_request_pass'),('source_both_pass','provider__both_pass')]:np.testing.assert_array_equal(fields[name],s[original])
        if policy=='selected':
            previous={name.removeprefix(key+'__food_'):v for name,v in dict(np.load(CAL/'selected_fields.npz')).items() if name.startswith(key+'__food_')};mandatory=np.load(CAL/'selected_fields.npz')[key+'__selected_mandatory_complete']
        else:z=dict(np.load(CAL/key/policy/'fields.npz'));previous={name.removeprefix('C__'):v for name,v in z.items() if name.startswith('C__')};mandatory=z['mandatory_complete']
        np.testing.assert_array_equal(fields['mandatory_complete'],mandatory)
        for name,v in previous.items():np.testing.assert_array_equal(fields['A__food_pass' if name=='no_shortage' else 'A__'+name],v.astype(bool)&f['active'] if name=='no_shortage' else v)
        offsets=np.searchsorted(ev['site'],np.arange(n+1))
        for account in ('A','B'):
            row=next(v for v in r['rows'] if v['case']==case and v['accounting']==account)
            for j in np.flatnonzero(f['active']):
                sl=slice(offsets[j],offsets[j+1]);times=ev['time'][sl];cargo=ev[account+'_cargo'][sl];rate=f['total'][j]*2500;cap=rate*90
                def drift(stock):return stock_end(times,cargo,rate,cap,stock)-stock
                initial=0. if drift(0.)<=0 else brentq(drift,0.,cap,xtol=1e-7,rtol=1e-14);scale=max(1.,rate*365);assert abs(initial-fields[account+'__initial_stock'][j])<=1e-9*scale
                values=integrate(times,cargo,rate,cap,float(fields[account+'__initial_stock'][j]))
                for name,value in values.items():assert abs(value-fields[account+'__'+name][j])<=1e-9*scale,(case,account,j,name)
                assert abs(values['ledger_residual'])<=1e-9*scale and abs(values['periodic_residual'])<=1e-9*scale;food+=1
            passed=f['active']&(fields[account+'__unmet']<=1e-8*np.maximum(1.,fields[account+'__needed']));all_pass=passed&mandatory&fields['source_both_pass'];np.testing.assert_array_equal(fields[account+'__food_pass'],passed);np.testing.assert_array_equal(fields[account+'__all_gates_pass'],all_pass);assert not all_pass.any()
            for col,value in [('scored_providers',int(f['active'].sum())),('destination_food_pass',int(passed.sum())),('mandatory_complete',int(mandatory.sum())),('source_export_pass',int(fields['source_export_request_pass'].sum())),('source_rural_pass',int(fields['source_rural_food_pass'].sum())),('all_gates_pass',int(all_pass.sum()))]:assert row[col]==value
            assert row['raw_source_unfilled']==source['raw_unfilled'] and row['counterfactual_retained_missing']==source['raw_unfilled']*.95
            names=[name.removeprefix(account+'__') for name in fields if name.startswith(account+'__') and not name.endswith(('food_pass','all_gates_pass'))]
            for name in names:assert row[name]==float(fields[account+'__'+name].sum())
            for a in row['actors']:
                mask=fields['actor']==a['actor'];assert a['scored_providers']==int((mask&f['active']).sum()) and a['destination_food_pass']==int((mask&passed).sum()) and a['all_gates_pass']==int((mask&all_pass).sum())
                for name in names:assert a[name]==float(fields[account+'__'+name][mask].sum())
                actors+=1
        assert not (fields['B__food_pass']&~fields['A__food_pass']).any();assert np.all(fields['B__unmet']+1e-8*np.maximum(1.,fields['A__needed'])>=fields['A__unmet']);requests+=len(p['id']);events+=len(ev['site']);print('Independent source-filled return events,scalar food and all gates passed',case,flush=True)
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),scalar_inventory_reviewer_sha256=sha(ROOT/'scripts/review_delivery_timing.py'),scalar_stock_end_sha256=sha(ROOT/'scripts/review_meal_headroom.py'),request_ID_joins_checked=requests,grouped_return_events_checked=events,active_provider_food_inventories_checked=food,actor_rows_checked=actors,all48outcomes=True,A_exact_prior_C=True,B_food_pass_subset_A=True,all_source_rural_failures_retained=True,no_extra_retention_or_delay=True,original_maps_and_residents_unchanged=True))
if __name__=='__main__':main()
