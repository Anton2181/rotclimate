from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from polity.directed_trade import gravity_routes, inbound_catchments, map_fields
from polity.trade import catchments, flows


def network(edges, n=3, cells=None):
    row, col, value = zip(*edges) if edges else ([], [], [])
    return SimpleNamespace(base=csr_matrix((value,(row,col)),shape=(n,n)),
                           n_cells=n if cells is None else cells, n=n)


def routed(net, towns, mass, **kwargs):
    a,b,v = gravity_routes([net],towns,mass,**kwargs)
    return {(int(i),int(j)):float(x) for i,j,x in zip(a,b,v)}


def test_hinterland_uses_the_cost_of_bringing_goods_into_town():
    net = network([(0,1,1.),(1,0,10.),(2,1,9.),(1,2,2.)])
    mass, owner = inbound_catchments(net,[0,2],[10.,100.,20.])
    # Town 0 can deliver to the village cheaply, but the village reaches 2.
    np.testing.assert_array_equal(owner,[0,1,1])
    np.testing.assert_allclose(mass,[10.,120.])
    old_mass, _ = catchments(net,[0,2],[10.,100.,20.])
    np.testing.assert_allclose(old_mass,[110.,20.])


def test_unreachable_population_is_not_assigned_and_river_nodes_add_no_people():
    net = network([(0,3,1.),(3,1,1.),(1,3,1.),(3,0,1.)],n=4,cells=3)
    mass, owner = inbound_catchments(net,[0],[10.,20.,30.])
    np.testing.assert_array_equal(owner,[0,0,-1])
    np.testing.assert_allclose(mass,[30.])
    np.testing.assert_array_equal(inbound_catchments(net,[],[10.,20.,30.])[1],-1)


def test_gravity_counts_both_asymmetric_directions_once():
    net = network([(0,1,1.),(1,0,10.)],n=2)
    actual = routed(net,[0,1],[10.,20.],scale=100.)
    assert actual == pytest.approx({(0,1):200*np.exp(-.01),(1,0):200*np.exp(-.1)})


def test_directed_trade_is_invariant_to_town_record_order():
    net = network([(0,1,1.),(1,0,10.)],n=2)
    actual = routed(net,[0,1],[10.,20.],scale=100.)
    assert routed(net,[1,0],[20.,10.],scale=100.) == pytest.approx(actual)
    # The historical algorithm selected a top-town pair's direction by its
    # record index. Preserve it for old evidence and expose the regression.
    first = flows([net],[0,1],[10.,20.],scale=100.)
    second = flows([net],[1,0],[20.,10.],scale=100.)
    assert first[2].sum() != pytest.approx(second[2].sum())


def test_top_source_approximation_retains_return_shipments_without_double_counting():
    net = network([(0,1,1.),(1,0,2.),(1,2,3.),(2,1,4.)])
    # Town 0 is largest. Omit 1<->2 pairs, but retain 0<->1 and 0<->2.
    actual = routed(net,[0,1,2],[30.,20.,10.],scale=100.,sources=1)
    assert actual[(0,1)] == pytest.approx(600*np.exp(-.01)+300*np.exp(-.04))
    assert actual[(1,0)] == pytest.approx(600*np.exp(-.02)+300*np.exp(-.06))
    assert actual[(1,2)] == pytest.approx(300*np.exp(-.04))
    assert actual[(2,1)] == pytest.approx(300*np.exp(-.06))


def test_empty_and_disconnected_economies_have_zero_shipments():
    net = network([],n=2)
    assert routed(net,[0,1],[10.,20.]) == {}
    assert routed(net,[],[]) == {}
    assert routed(net,[0,1],[0.,0.]) == {}


def test_seasonal_routes_are_averaged_and_cost_cutoff_is_explicit():
    a = network([(0,1,1.)],n=2)
    b = network([(1,0,2.)],n=2)
    i,j,v = gravity_routes([a,b],[0,1],[10.,20.],scale=100.)
    actual = dict(zip(zip(i,j),v))
    assert actual == pytest.approx({(0,1):100*np.exp(-.01),(1,0):100*np.exp(-.02)})
    assert routed(b,[0,1],[10.,20.],scale=.1,limit_scale=6.) == {}


@pytest.mark.parametrize('people',[[1.,-1.,2.],[1.,np.nan,2.],[1.,2.]])
def test_invalid_population_rejected(people):
    with pytest.raises(ValueError,match='population'):
        inbound_catchments(network([],n=3),[0],people)


def test_auxiliary_river_nodes_cannot_be_aggregated_under_changed_identities():
    a=network([(0,2,1.),(2,1,1.)],n=3,cells=2)
    b=network([(0,2,1.),(2,1,1.)],n=3,cells=2)
    a.river_cells=np.array([0]);b.river_cells=np.array([1])
    with pytest.raises(ValueError,match='river-node identities'):
        gravity_routes([a,b],[0,1],[10.,20.])


def test_map_fields_use_inbound_population_without_predicting_town_sizes(monkeypatch):
    from polity import trade as T
    net=network([(0,1,1.),(1,0,10.),(2,1,9.),(1,2,2.)])
    monkeypatch.setattr(T,'cost_network',lambda *args:net)
    r=dict(land=np.ones((1,3),bool),claim=np.zeros((1,3),int),density=np.array([[10.,100.,20.]]),
           cell_km=1.,towns=[dict(row=0,col=0),dict(row=0,col=2)],world={},statics={},climate={},ports=[],river_places=[])
    fresh=map_fields(r,sources=2)
    np.testing.assert_allclose(fresh['mass'],[10.,120.])
    assert fresh['area_ha'] is None and fresh['eligible_people']==130. and fresh['unassigned_people']==0.
    assert fresh['market_access_direction']=='outbound'
    cached=map_fields(r,sources=2,outward_access=np.stack([fresh['ma_local'],fresh['ma']]))
    np.testing.assert_allclose(cached['mass'],fresh['mass'])
    for a,b in zip(cached['edges'],fresh['edges']):np.testing.assert_allclose(a,b)
