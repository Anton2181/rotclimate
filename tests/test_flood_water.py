import numpy as np
import pytest
from harvest.flood_water import route_water_budget


def months(values):return np.broadcast_to(np.asarray(values,dtype=float),(12,len(values))).copy()


def assert_conserved(source,result):
    np.testing.assert_allclose(source.sum(axis=1),sum(result[k].sum(axis=1) for k in ('delivered_m3','delivery_loss_m3','outlet_m3')),rtol=2e-14,atol=1e-12)
    for a in result.values():assert np.isfinite(a).all() and np.all(a>=0)


def test_upstream_withdrawal_is_not_available_again_downstream():
    source=months([0,3,2]);demand=months([5,5,0])
    r=route_water_budget(source,demand,[0,1,2],[-1,0,0])
    np.testing.assert_array_equal(r['delivered_m3'],months([2,3,0]))
    np.testing.assert_array_equal(r['unmet_m3'],months([3,2,0]))
    assert not r['outlet_m3'].any();assert_conserved(source,r)


def test_losses_are_paid_from_the_same_budget():
    source=months([10]);r=route_water_budget(source,months([3]),[0],[-1],efficiency=.5)
    np.testing.assert_array_equal(r['delivered_m3'],months([3]))
    np.testing.assert_array_equal(r['delivery_loss_m3'],months([3]))
    np.testing.assert_array_equal(r['outlet_m3'],months([4]));assert_conserved(source,r)


def test_months_and_independent_outlets_do_not_share_water():
    source=months([0,0]);source[0]=[8,4];demand=months([10,10])
    r=route_water_budget(source,demand,[0,1],[-1,-1])
    assert r['delivered_m3'][0].tolist()==[8,4] and not r['delivered_m3'][1:].any()
    assert_conserved(source,r)


def test_merging_sources_and_multiple_depths():
    source=months([1,2,3,4]);r=route_water_budget(source,months([0,0,0,0]),[0,1,2,3],[-1,0,1,1])
    np.testing.assert_array_equal(r['available_m3'],months([10,9,3,4]))
    np.testing.assert_array_equal(r['outlet_m3'],months([10,0,0,0]));assert_conserved(source,r)


def test_random_forests_conserve_with_spatial_efficiencies_and_month_rotation():
    rng=np.random.default_rng(71734)
    for n in range(1,51):
        receiver=np.array([-1]+[int(rng.integers(-1,c)) for c in range(1,n)])
        source=rng.uniform(0,200,(12,n));demand=rng.uniform(0,150,(12,n));eff=rng.uniform(.1,1,n)
        r=route_water_budget(source,demand,np.arange(n),receiver,efficiency=eff);assert_conserved(source,r)
        assert np.all(r['delivered_m3']<=demand+1e-12)
        assert np.all(r['downstream_m3']<=r['available_m3']+1e-12)
        shifted=route_water_budget(np.roll(source,5,axis=0),np.roll(demand,5,axis=0),np.arange(n),receiver,efficiency=eff)
        scaled=route_water_budget(source*1e6,demand*1e6,np.arange(n),receiver,efficiency=eff)
        for name in r:
            np.testing.assert_allclose(shifted[name],np.roll(r[name],5,axis=0),atol=1e-12)
            np.testing.assert_allclose(scaled[name]/1e6,r[name],atol=1e-12)


def test_inactive_zero_cells_are_allowed():
    r=route_water_budget(months([0,0]),months([0,0]),np.array([],dtype=int),[-1,-1])
    assert not any(v.any() for v in r.values())


@pytest.mark.parametrize('order,receiver',[
    ([0,0],[-1,0]),([1,0],[-1,0]),([0,1],[1,0]),([0,1],[-1,1]),
    ([0],[-1,0]),([0,2],[-1,0]),([0,1],[-1,2]),([0.,1.],[-1,0]),
])
def test_invalid_or_partial_graph_refused(order,receiver):
    with pytest.raises(ValueError):route_water_budget(months([1,1]),months([1,1]),order,receiver)


@pytest.mark.parametrize('source,demand,eff',[
    (months([-1]),months([1]),1), (months([np.nan]),months([1]),1),
    (months([1]),months([np.inf]),1), (months([1]),months([-1]),1),
    (np.ones((11,1)),np.ones((11,1)),1), (months([1]),months([1]),0),
    (months([1]),months([1]),1.01), (months([1]),months([1]),np.nan),
])
def test_invalid_volumes_and_efficiency_refused(source,demand,eff):
    with pytest.raises(ValueError):route_water_budget(source,demand,[0],[-1],efficiency=eff)
