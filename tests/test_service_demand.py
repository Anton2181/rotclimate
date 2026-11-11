import numpy as np
import pytest
from scipy.sparse import csr_matrix

from polity.service_demand import allocate_requests,round_trip_weights


def test_overlapping_centres_share_one_request_budget_instead_of_duplicating_it():
    result=allocate_requests([[1],[1]],[100],[1,1])
    np.testing.assert_allclose(result.allocated_requests,[50,50])
    np.testing.assert_allclose(result.accessible_potential,[100,100])
    np.testing.assert_allclose(result.origin_allocated,[100])
    third=allocate_requests([[1],[1],[1]],[100],[1,1,1])
    np.testing.assert_allclose(third.allocated_requests,[100/3]*3)


def test_long_return_leg_blocks_an_apparently_nearby_destination():
    kernel=round_trip_weights([.1,.2,np.inf],[1.1,.3,.1],1.)
    assert kernel[0]==kernel[2]==0 and kernel[1]==pytest.approx(np.exp(-.5))


def test_unreachable_or_zero_mass_centres_leave_demand_unallocated():
    result=allocate_requests([[1,0]],[30,70],[0])
    np.testing.assert_allclose(result.allocated_requests,[0])
    np.testing.assert_allclose(result.origin_unallocated,[30,70])


def test_choice_is_invariant_to_common_mass_scaling_but_per_centre_units_are_not():
    one=allocate_requests([[1,.2],[.3,1]],[40,60],[1,2])
    two=allocate_requests([[1,.2],[.3,1]],[40,60],[5,10])
    np.testing.assert_allclose(one.allocated_requests,two.allocated_requests)
    np.testing.assert_allclose(one.requests_per_centre,5*two.requests_per_centre)


def test_sparse_choices_match_hand_computed_origin_shares():
    result=allocate_requests(csr_matrix([[1,.5],[.5,1]]),[20,80],[1,2])
    # First origin splits1:1; second splits1:4.
    np.testing.assert_allclose(result.allocated_requests,[10+16,10+64])
    np.testing.assert_allclose(result.choice_probabilities.toarray(),[[.5,.2],[.5,.8]])
    np.testing.assert_allclose(result.origin_unallocated,[0,0])


def test_invalid_budgets_and_inputs_fail_instead_of_becoming_extra_requests():
    with pytest.raises(ValueError):allocate_requests([[1]],[-1],[1])
    with pytest.raises(ValueError):allocate_requests([[np.nan]],[1],[1])
    with pytest.raises(ValueError):round_trip_weights([0],[0],0)
