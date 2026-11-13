"""Independent scalar controls for the new two-store source event primitive.

These are seeded synthetic controls, not scores on any historical cohort.
"""
import json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.source_food_events import periodic_source_food_year
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_food_events_20261113'


def replay(harvest_t,harvest_q,pickup_t,pickup_q,ids,rate,rcap,ecap,fraction,loss,rinitial,einitial):
    h=-math.log1p(-loss)/365;clock=0.;r=rinitial;e=einitial;rpeak=r;epeak=e
    eaten=gap=rloss=eloss=rover=eover=short=0.;taken=[0.]*len(ids)
    events=sorted([(float(t),0,i,float(q)) for i,(t,q) in enumerate(zip(harvest_t,harvest_q))]+[(float(t),1,i,float(q)) for i,(t,q) in enumerate(zip(pickup_t,pickup_q))],key=lambda v:(v[0],v[1],int(ids[v[2]]) if v[1] else v[2]))
    events.append((365.,2,0,0.))
    for time,kind,i,q in events:
        dt=time-clock
        if rate:
            empty=math.log1p(r*h/rate)/h if h else r/rate;fed=min(dt,empty);meal=rate*fed
            after=max(0.,(r+rate/h)*math.exp(-h*fed)-rate/h) if h else max(0.,r-meal)
            if empty<=dt:after=0.
            eaten+=meal;gap+=rate*(dt-fed);short+=dt-fed;rloss+=max(0.,r-after-meal);r=after
        else:
            after=r*math.exp(-h*dt);rloss+=r-after;r=after
        after=e*math.exp(-h*dt);eloss+=e-after;e=after
        if kind==0:
            available=r+q;overflow=max(0.,available-rcap);rover+=overflow;r=min(rcap,available);rpeak=max(rpeak,r)
            available=e+fraction*overflow;eover+=max(0.,available-ecap);e=min(ecap,available);epeak=max(epeak,e)
        elif kind==1:taken[i]=min(e,q);e-=taken[i]
        clock=time
    supplied=math.fsum(harvest_q);requested=math.fsum(pickup_q);withdrawn=math.fsum(taken);quota=rover*fraction;uncollected=rover-quota+eover
    rural=dict(initial_stock=rinitial,final_stock=r,peak_stock=rpeak,harvested=supplied,needed=rate*365,consumed=eaten,unmet=gap,spoiled=rloss,overflow=rover,shortfall_days=short,ledger_residual=rinitial+supplied-r-eaten-rloss-rover,periodic_residual=r-rinitial)
    export=dict(initial_stock=einitial,final_stock=e,peak_stock=epeak,quota_input=quota,requested=requested,withdrawn=withdrawn,unfilled=requested-withdrawn,spoiled=eloss,overflow=eover,ledger_residual=einitial+quota-e-withdrawn-eloss-eover,periodic_residual=e-einitial)
    return rural,export,taken,uncollected


def minimum_fixed_point(function,capacity):
    if capacity==0 or function(0.)<=0:return 0.
    lo,hi=0.,capacity
    for _ in range(100):
        mid=(lo+hi)/2
        if function(mid)>mid:lo=mid
        else:hi=mid
    return hi


def main():
    rng=np.random.default_rng(20261113);largest=0.;pickups=0;cases=200
    for case in range(cases):
        ht=rng.uniform(0,365,size=int(rng.integers(0,8)));hq=rng.uniform(0,10000,size=len(ht));pt=rng.uniform(0,365,size=int(rng.integers(0,16)));pq=rng.uniform(0,1000,size=len(pt));ids=rng.permutation(len(pt)).astype('i8')
        if len(ht)>1 and case%3==0:ht[:2]=0.
        if len(pt)>1 and case%4==0:pt[:2]=0.
        rate=float(rng.uniform(0,20));rcap=float(rng.uniform(0,10000));ecap=float(rng.uniform(0,3000));fraction=float(rng.uniform(0,1));loss=float(rng.uniform(0,.3))
        if case%5==0:loss=0.
        if case%7==0:rate=0.
        if case%11==0:rcap=0.
        if case%13==0:ecap=0.
        def run(r,e):return replay(ht,hq,pt,pq,ids,rate,rcap,ecap,fraction,loss,r,e)
        ri=minimum_fixed_point(lambda s:run(s,0.)[0]['final_stock'],rcap)
        ei=minimum_fixed_point(lambda s:run(ri,s)[1]['final_stock'],ecap)
        rural,export,taken,uncollected=run(ri,ei)
        actual=periodic_source_food_year(ht,hq,pt,pq,ids,demand_rate=rate,rural_capacity=rcap,export_capacity=ecap,quota_fraction=fraction,loss_fraction_year=loss)
        scale=max(1.,sum(hq),rate*365,sum(pq),rcap,ecap)
        for account,expected in [(actual.rural,rural),(actual.export,export)]:
            for name,value in expected.items():
                error=abs(getattr(account,name)-value)/scale;largest=max(largest,error);assert error<1e-9,(case,name,value,getattr(account,name))
        assert abs(actual.uncollected-uncollected)<1e-9*scale;np.testing.assert_allclose(actual.pickup_withdrawn,taken,rtol=1e-9,atol=1e-7)
        np.testing.assert_allclose(np.asarray(actual.pickup_withdrawn)+actual.pickup_unfilled,pq,rtol=1e-12,atol=1e-8);assert actual.pickup_ids==tuple(ids.tolist());assert abs(actual.total_ledger_residual)<1e-9*scale;pickups+=len(pt)
    OUT.mkdir(parents=True,exist_ok=True);write(OUT/'prototype_review.json',dict(status='passed_synthetic_controls_only',seed=20261113,cases=cases,pickup_requests_checked=pickups,largest_account_error_per_energy_scale=largest,independent_bisection_and_scalar_stores=True,no_historical_or_calendar_cohort_scored=True,producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'harvest/source_food_events.py',ROOT/'harvest/event_food_stocks.py',ROOT/'calibration/source_food_events_20261113/plan.json']}));print('Independent source prototype passed',cases,'synthetic cases,',pickups,'pickup requests;largest normalized error',largest)
if __name__=='__main__':main()
