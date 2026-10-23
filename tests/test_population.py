import numpy as np
import pytest
from population.models import allocate,market_access,walking_speed


def test_known_census_allocation_saturates_attractive_land_without_losing_people():
    people,unmet=allocate([2,6],[3,1],6)
    np.testing.assert_allclose(people,[2,4],atol=1e-10)
    assert unmet<1e-10


def test_population_budget_accounts_for_all_excess_and_zero_attraction():
    people,unmet=allocate([2,6,10],[3,1,0],12)
    np.testing.assert_array_equal(people,[2,6,0]);assert unmet==4
    assert allocate([2,6],[1,1],0)[0].sum()==0


def test_uniform_weights_reproduce_same_budget_uniform_occupation():
    c=np.array([0,2,8,10.]);p,u=allocate(c,np.ones(4),7)
    np.testing.assert_allclose(p,c*7/c.sum(),atol=1e-10)
    assert u<1e-10


@pytest.mark.parametrize('c,w,n',[([-1],[1],2),([1],[np.nan],2),([1],[1],-2)])
def test_invalid_population_inputs_are_rejected(c,w,n):
    with pytest.raises(ValueError):allocate(c,w,n)


def test_walking_direction_is_resident_to_market_not_reverse():
    z=np.array([[0.,100.]]);land=np.ones(z.shape,bool)
    hours,_=market_access(z,land,1,[(0,0)])
    assert hours[0,1]==pytest.approx(1/walking_speed(-.1))
    uphill,_=market_access(z,land,1,[(0,1)])
    assert uphill[0,0]==pytest.approx(1/walking_speed(.1))
    assert uphill[0,0]>hours[0,1]


def test_markets_cannot_cross_water_or_blocked_diagonal_corners():
    land=np.eye(2,dtype=bool)
    hours,markets=market_access(np.zeros((2,2)),land,1,[(0,0)])
    assert hours[0,0]==0 and markets[0,0]==1
    assert hours[1,1]==-1 and markets[1,1]==0


def test_flat_access_and_duplicate_sources_have_deterministic_market_ids():
    hours,markets=market_access(np.zeros((1,3)),np.ones((1,3),bool),2,[(0,0),(0,0)])
    np.testing.assert_allclose(hours,[[0,2/walking_speed(0),4/walking_speed(0)]])
    np.testing.assert_array_equal(markets,[[1,1,1]])
