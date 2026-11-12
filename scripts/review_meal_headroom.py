"""Independent scalar inventories and bracket search for conditional meal bounds."""
import csv
import gzip
import io
import json
from math import exp,expm1,log1p
from pathlib import Path
import sys

import numpy as np
from scipy.optimize import brentq

try:
    from numba import njit
except ImportError:
    def njit(**options):
        return lambda function:function

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_delivery_timing import integrate
from settlement_locations_earth import sha,write

OUT=ROOT/'output/network_visit_meal_headroom_20261112'
TIMING=ROOT/'output/network_visit_delivery_timing_20261112'


@njit(cache=True)
def stock_end(times,cargo,rate,capacity,initial):
    """Independent end map; no ledger arrays needed during stock root search."""
    hazard=-log1p(-.05)/365;stock=initial;previous=0.
    for i in range(len(times)):
        dt=times[i]-previous
        stock=max(0.,stock*exp(-hazard*dt)+rate*expm1(-hazard*dt)/hazard)
        stock=min(capacity,stock+cargo[i]);previous=times[i]
    dt=365-previous
    return max(0.,stock*exp(-hazard*dt)+rate*expm1(-hazard*dt)/hazard)


def main():
    r=json.loads((OUT/'results.json').read_text());a=dict(np.load(OUT/'fields.npz'));t=dict(np.load(TIMING/'fields.npz'))
    for name,digest in {**r['sources'],**r['producers'],**r['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['bracket_iterations']==48 and r['fixed_staff_and_original_physical_capacity']
    csv_rows=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'providers.csv.gz').read_bytes()).decode())))
    csv_index={(v['case'],v['accounting'],int(v['provider'])):v for v in csv_rows};assert len(csv_index)==len(csv_rows)
    checked=0;inventories=0;largest_bound_error=0.;largest_scalar_error=0.;near_threshold=0
    for key in dict.fromkeys(v['key'] for v in r['rows']):
        e=dict(np.load(TIMING/f'{key}_events.npz'));scored=a[key+'__scored'];staff=a[key+'__fixed_staff'];civilian=a[key+'__parent_civilian'];cap=a[key+'__physical_capacity'];n=len(scored)
        np.testing.assert_array_equal(scored,t[key+'__scored']);np.testing.assert_array_equal(cap,t[key+'__capacity'])
        np.testing.assert_array_equal(staff+civilian,t[key+'__residents']);np.testing.assert_allclose(staff[scored],100.,rtol=0,atol=1e-12)
        assert (civilian>=0).all();offsets=np.searchsorted(e['site'],np.arange(n+1))
        for account in 'BC':
            p=f'{key}__{account}__'
            for site in np.flatnonzero(scored):
                if account=='B':times=np.arange(12)*365/12;cargo=t[key+'__arrivals'][:,site]
                else:sl=slice(offsets[site],offsets[site+1]);times=e['time'][sl];cargo=e['cargo'][sl]
                def independent(alpha):
                    rate=2500*(staff[site]+alpha*civilian[site]);capacity=cap[site]
                    def drift(stock):return stock_end(times,cargo,rate,capacity,stock)-stock
                    end_zero=stock_end(times,cargo,rate,capacity,0.)
                    initial=0. if end_zero<=0 else brentq(drift,0.,capacity,xtol=1e-7,rtol=1e-14)
                    return integrate(times,cargo,rate,capacity,initial)
                def margin(alpha):
                    v=independent(alpha);return v['unmet']-1e-8*max(1.,v['needed'])
                staff_score,full_score=margin(0.),margin(1.);staff_ok=staff_score<=0;full_ok=full_score<=0
                assert bool(a[p+'staff_feasible'][site])==staff_ok and bool(a[p+'full_demand_passes'][site])==full_ok
                lo,hi=a[p+'passing_alpha'][site],a[p+'failing_alpha'][site]
                if not staff_ok:assert np.isnan(lo) and hi==0
                elif full_ok:assert lo==1 and np.isnan(hi)
                else:
                    assert 0<=lo<hi<=1 and hi-lo<=2**-48
                    # Separate 24-step scalar search checks the narrow reported
                    # bracket to a wider independently resolved numeric interval.
                    left,right=0.,1.
                    for _ in range(24):
                        middle=.5*(left+right)
                        if margin(middle)<=0:left=middle
                        else:right=middle
                    assert left-1e-9<=lo<=hi<=right+1e-9
                    largest_bound_error=max(largest_bound_error,right-left)
                for label,alpha in [('staff',0.),('full',1.),('passing',lo),('failing',hi)]:
                    valid=np.isfinite(alpha)
                    if label in ('passing','failing'):assert bool(a[p+label+'_valid'][site])==valid
                    if not valid:continue
                    rate=2500*(staff[site]+alpha*civilian[site]);initial=a[p+label+'__initial_stock'][site]
                    actual=integrate(times,cargo,rate,cap[site],float(initial));scale=max(1.,rate*365)
                    for name,value in actual.items():
                        recorded=a[p+label+'__'+name][site];delta=abs(value-recorded);largest_scalar_error=max(largest_scalar_error,delta)
                        assert delta<=2e-12*scale,(key,account,site,label,name,value,recorded)
                    assert 0<=initial<=cap[site] and actual['peak_stock']<=cap[site]
                    assert abs(actual['periodic_residual'])<=2e-9*scale and abs(actual['ledger_residual'])<=2e-9*scale
                    if label in ('passing','failing'):
                        recorded_score=a[p+label+'__unmet'][site]-1e-8*max(1.,a[p+label+'__needed'][site])
                        assert (recorded_score<=0)==(label=='passing')
                        independent_score=actual['unmet']-1e-8*max(1.,actual['needed'])
                        # The final 2^-48 interval is finer than accumulated
                        # floating-point grain precision. Report near-threshold
                        # checks rather than claiming independent bit agreement.
                        if abs(independent_score)<=2e-12*scale:near_threshold+=1
                        elif label=='passing':assert independent_score<=0
                        else:assert independent_score>0
                    inventories+=1
                row=csv_index.pop((key,account,int(site)))
                for name,value in [('fixed_staff',staff[site]),('parent_civilian',civilian[site]),('physical_capacity',cap[site])]:assert float(row[name])==value
                assert int(row['actor'])==a[key+'__actor'][site]
                for name,value in [('passing_alpha',lo),('failing_alpha',hi)]:assert (float(row[name])==value) if np.isfinite(value) else row[name]==''
                for name in ('staff_feasible','full_demand_passes'):assert row[name]==str(bool(a[p+name][site]))
                for name in actual:
                    if np.isfinite(lo):assert float(row[name])==a[p+'passing__'+name][site]
                    else:assert row[name]==''
                assert float(row['staff_unmet'])==a[p+'staff__unmet'][site] and float(row['full_demand_unmet'])==a[p+'full__unmet'][site]
                checked+=1
            row=next(v for v in r['rows'] if v['key']==key and v['accounting']==account)
            for actor in [None,*range(18)]:
                mask=scored if actor is None else scored & (a[key+'__actor']==actor);summary=row if actor is None else row['actors'][actor]
                feasible=mask & a[p+'staff_feasible'];alpha=a[p+'passing_alpha'][feasible]
                assert summary['scored_providers']==int(mask.sum()) and summary['staff_infeasible']==int((mask & ~a[p+'staff_feasible']).sum())
                assert summary['full_demand_passes']==int((mask & a[p+'full_demand_passes']).sum())
                for name,value in [('fixed_staff',staff[mask].sum()),('parent_civilian',civilian[mask].sum()),('conditional_civilian_meal_equivalent',(civilian[feasible]*alpha).sum()),('civilian_meal_equivalent_reduction',(civilian[feasible]*(1-alpha)).sum())]:
                    assert abs(value-summary[name])<=1e-10*max(1.,value)
            print('Independent meal brackets',key,account,flush=True)
    assert not csv_index and len(r['rows'])==16
    write(OUT/'review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),scalar_reviewer_sha256=sha(ROOT/'scripts/review_delivery_timing.py'),
        provider_accounting_bounds_checked=checked,endpoint_inventories_checked=inventories,independent_bracket_steps=24,max_independent_alpha_interval=largest_bound_error,
        max_scalar_field_difference=largest_scalar_error,near_threshold_scalar_checks=near_threshold,
        near_threshold_note='Reported 48-step bounds are finer than floating-point grain precision. Independent 24-step brackets and scalar ledger tolerances are stated explicitly;no bitwise independent bound claim.',
        fixed_staff_original_capacity_and_cargo=True,every_provider_csv_and_actor_summary_checked=True,original_atlas_unchanged=True,scope='Conditional destination civilian meal bounds;not resident replanning,source/ration/location validation or empirical population.'))


if __name__=='__main__':main()
