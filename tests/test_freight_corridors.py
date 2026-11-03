import numpy as np
import pytest

from polity.freight_corridors import FreightNetwork


def network(edges,n=4,**kwargs):
    fields=list(zip(*edges)) if edges else [[],[],[],[],[]]
    legs=tuple(np.array(a,dtype=int if i in (0,1,4) else float) for i,a in enumerate(fields))
    return FreightNetwork(n,[legs],**kwargs)


def test_cheapest_route_keeps_its_own_slow_duration_instead_of_fast_other_route():
    n=network([(0,1,2,10,1),(0,2,10,1,0),(2,1,10,1,0)])
    p=n.paths(0,[1])[1]
    assert p.cost_road_km==2 and p.travel_days==10
    np.testing.assert_array_equal(p.nodes,[0,1])


def test_parallel_leg_choice_preserves_mode_and_does_not_sum_alternatives():
    edges=[(0,1,100,1,0),(0,1,5,10,1),(1,2,2,1,0)]
    a=network(edges);b=network(edges[::-1])
    for n in [a,b]:
        p=n.paths(0,[2])[2]
        assert p.cost_road_km==7 and p.travel_days==11 and p.mode_days['sea']==10
        assert n.parallel_pair_count==n.discarded_parallel_legs==1
        assert n.maximum_sum_to_selected_cost_ratio==21


def test_equal_cost_parallel_legs_choose_shortest_duration_deterministically():
    n=network([(0,1,5,10,1),(0,1,5,2,0)])
    p=n.paths(0,[1])[1]
    assert p.cost_road_km==5 and p.travel_days==2 and p.mode_days['land']==2


def test_directionality_auxiliary_river_nodes_and_unreachable_places_are_retained():
    n=network([(0,3,1,.25,4),(3,1,2,.5,3)],n=4,n_cells=3,river_cells=[2])
    p=n.paths(0,[1,2]);assert p[2] is None
    np.testing.assert_array_equal(n.physical_cells(p[1].nodes),[0,2,1])
    assert n.paths(1,[0])[0] is None


def test_local_path_has_no_fictitious_transport_cost_or_time():
    p=network([]).paths(0,[0])[0]
    assert p.cost_road_km==p.travel_days==0 and len(p.leg_indices)==0


@pytest.mark.parametrize('edge',[(0,1,-1,2,0),(0,1,1,0,0),(0,9,1,2,0)])
def test_invalid_or_nonphysical_legs_are_rejected(edge):
    with pytest.raises(ValueError):network([edge])
