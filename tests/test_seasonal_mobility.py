import numpy as np
import pytest
from harvest.seasonal_mobility import seasonal_circuit


def solve(supply,travel,**kw):
    return seasonal_circuit(np.asarray(supply,float),np.asarray(travel,float),0,daily_need=1,year_days=360,reserve_days=3,**kw)


def test_zero_supply_cannot_bootstrap_carried_food():
    route=solve(np.zeros((12,2)),[[0,1],[1,0]])
    assert route.consumed.sum()==0 and route.unmet.sum()==360
    assert np.all(route.reserves==0)


def test_stationary_matches_periodic_food_without_discrete_roundoff():
    supply=np.full((12,1),30.);supply[0]=27;supply[11]=33
    route=solve(supply,[[0]])
    assert route.unmet.sum()==0
    assert route.reserves[0]==route.reserves[-1]==3
    assert abs(route.feed_ledger_residual)<1e-9


def test_closed_route_cannot_teleport_or_borrow_transit_feed():
    supply=np.zeros((12,2));supply[:6,0]=40;supply[6:,1]=40
    mobile=solve(supply,[[0,2],[2,0]])
    fixed=solve(supply[:,0,None],[[0]])
    assert mobile.unmet.sum()<fixed.unmet.sum()
    assert mobile.locations[-1]==0
    assert np.any(mobile.locations==1)
    assert mobile.reserves[-1]==mobile.reserves[0]
    previous=np.r_[mobile.reserves[0],mobile.reserves[1:-1]]
    assert np.all(mobile.unmet+1e-9>=np.maximum(mobile.travel_days-previous,0))
    np.testing.assert_allclose(mobile.reserves[:-1]+mobile.collected-mobile.consumed,mobile.reserves[1:])
    assert np.all(mobile.collected<=supply[np.arange(12),mobile.locations]+1e-8)


def test_disconnected_patches_and_water_exclusions():
    supply=np.zeros((12,2));supply[:,1]=100
    route=solve(supply,[[0,np.inf],[np.inf,0]])
    assert np.all(route.locations==0) and route.consumed.sum()==0
    assert solve(supply,[[0,1],[1,0]],allowed=np.zeros((12,2),bool)) is None
    allowed=np.ones((12,2),bool);allowed[:,1]=False
    assert solve(supply,[[0,1],[1,0]],allowed=allowed).consumed.sum()==0


def test_global_dynamic_program_avoids_greedy_dead_end():
    # Patch 1 has a tempting bin-0 crop, but only patch 2 can cross into the
    # long resource season at 3. Only one edge can be taken in each snapshot.
    supply=np.zeros((12,4));supply[0,1]=100;supply[0,2]=20;supply[1:10,3]=40;supply[10:,0]=40
    tr=np.full((4,4),np.inf);np.fill_diagonal(tr,0)
    for a,b in [(0,1),(0,2),(2,3),(3,0)]:tr[a,b]=1
    route=solve(supply,tr)
    assert route.locations[0]==2
    assert route.locations[1]==3
    assert abs(route.feed_ledger_residual)<1e-8


def test_refined_reserve_states_do_not_worsen_best_feeding():
    supply=np.array([[15,45],[45,15]]*6,float)
    coarse=solve(supply,[[0,.5],[.5,0]])
    fine=solve(supply,[[0,.5],[.5,0]],reserve_quantum_days=.5)
    assert fine.unmet.sum()<=coarse.unmet.sum()+1e-9


def test_dynamic_program_matches_exhaustive_all_closed_zero_pack_routes():
    from itertools import product
    rng=np.random.default_rng(58);supply=rng.uniform(0,55,(12,2));travel=np.array([[0,1.5],[2,0]])
    result=seasonal_circuit(supply,travel,0,daily_need=1,reserve_days=0,year_days=360)
    best=np.inf
    for prefix in product(range(2),repeat=11):
        locations=prefix+(0,);previous=0;missing=0
        for t,destination in enumerate(locations):
            trip=travel[previous,destination]
            missing+=30-min(supply[t,destination],30-trip)
            previous=destination
        best=min(best,missing)
    assert result.objective_unmet==pytest.approx(best,abs=1e-8)
