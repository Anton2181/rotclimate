import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from scripts.audit_moisture_structure import face_transport,periodic_exchange,symmetric_exchange,two_box_example


def test_variable_local_mixing_creates_water_even_in_a_closed_two_box_system():
    d = two_box_example()
    assert d['original_source_mm_day'] == [10.,0.]
    assert d['original_net_mm_day'] == 10.
    assert d['symmetric_source_mm_day'] == [5.,-5.]
    assert d['symmetric_net_mm_day'] == 0.


def test_periodic_pairwise_exchange_conserves_water_with_variable_rates():
    rng = np.random.default_rng(71)
    w,r = rng.random((19,23))*40,rng.random((19,23))*2
    result = periodic_exchange(w,r,2.3)
    assert abs(result.sum()) < 1e-10
    assert result[np.unravel_index(w.argmin(),w.shape)] >= 0
    assert result[np.unravel_index(w.argmax(),w.shape)] <= 0


def test_pairwise_exchange_preserves_uniform_water_and_constant_rate_limit():
    rng = np.random.default_rng(1)
    w,r = rng.random((13,17))*30,rng.random((13,17))
    np.testing.assert_allclose(periodic_exchange(np.full_like(w,12.),r,1.7),0,atol=1e-13)
    np.testing.assert_allclose(periodic_exchange(w,np.full_like(w,.9),1.7),
                               .9*(gaussian_filter(w,1.7,mode='wrap')-w),atol=1e-13)


@pytest.mark.parametrize('closed',[True,False])
def test_finite_volume_transport_cancels_internal_faces_and_accounts_for_boundary(closed):
    rng = np.random.default_rng(9)
    w,u,v = rng.random((3,9,12))*20,rng.normal(size=(3,9,12)),rng.normal(size=(3,9,12))
    source,outward = face_transport(w,u,v,14000,closed=closed)
    np.testing.assert_allclose(source.sum(axis=(-1,-2)),-outward,atol=1e-11)
    if closed:
        np.testing.assert_array_equal(outward,0)


def test_eastward_flow_is_upwind_and_v_is_positive_map_up():
    w = np.array([[1.,2.,3.],[1.,2.,3.],[1.,2.,3.]])
    u,v = np.ones_like(w),np.zeros_like(w)
    source,_ = face_transport(w,u,v,86400,closed=True)
    np.testing.assert_array_equal(source[1],[-1.,-1.,2.])
    up,_ = face_transport(w.T,np.zeros_like(w),np.ones_like(w),86400,closed=True)
    np.testing.assert_array_equal(up[:,1],[2.,1.,-3.])


def test_uniform_water_can_have_nonzero_flux_divergence_under_divergent_wind():
    w = np.full((5,7),10.)
    u = np.broadcast_to(np.arange(7),(5,7))
    source,_ = face_transport(w,u,np.zeros_like(w),86400)
    np.testing.assert_array_equal(source[1:-1,1:-1],-10.)
    # Advective concentration form is zero for uniform water, hence not the
    # column-conserving flux form when the prescribed wind diverges.


def test_invalid_operator_inputs_are_rejected():
    w = np.ones((3,4))
    with pytest.raises(ValueError):face_transport(w,w,w,0)
    with pytest.raises(ValueError):periodic_exchange(w,w,-1)
    with pytest.raises(ValueError):symmetric_exchange(w,-w,lambda a:a)
