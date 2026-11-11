import numpy as np
import pytest
from scipy.sparse import eye
from polity.service_demand import allocate_requests
from polity.service_opportunity import normalize_opportunities,local_controls


def test_mass_budget_and_eligibility_are_separate_from_relative_weights():
    weights=np.array([1.,2.,100.]);before=weights.copy()
    mass=normalize_opportunities(weights,[True,True,False],12.)
    np.testing.assert_allclose(mass,[4,8,0]);np.testing.assert_array_equal(weights,before)
    assert normalize_opportunities(np.ones(3),[True,True,False],12).sum()==12


def test_zero_travel_control_is_the_actual_identity_kernel_allocation():
    d=np.array([10.,30.,90.]);m=np.array([2.,3.,0.])
    control=local_controls(d,m);allocation=allocate_requests(eye(3),d,m)
    np.testing.assert_allclose(control['zero_travel_per_centre'],allocation.requests_per_centre)
    np.testing.assert_allclose(control['local_demand'],allocation.allocated_requests)
    np.testing.assert_allclose(allocation.origin_unallocated,[0,0,90])


def test_common_mass_scaling_does_not_get_fitted_into_control_ranks():
    a=local_controls([10,20],[1,2]);b=local_controls([10,20],[3,6])
    np.testing.assert_allclose(a['inverse_mass'],3*b['inverse_mass'])
    np.testing.assert_allclose(a['zero_travel_per_centre'],3*b['zero_travel_per_centre'])


def test_invalid_support_and_tiny_mass_fail_without_silent_rank_floor():
    with pytest.raises(ValueError):normalize_opportunities([0],[True],1)
    with pytest.raises(ValueError):normalize_opportunities([-1],[True],1)
    with pytest.raises(ValueError):local_controls([1e6],[1e-320])
