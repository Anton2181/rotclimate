import numpy as np
import pytest
from polity.core_travel import travel_distance_supported
from scripts.population_cores import travel_distance


def grid():
    shape=(9,12)
    return dict(lat=np.arange(8.,-1,-1),lon=np.arange(12.),land=np.ones(shape,bool),
        T_ann=np.full(shape,15.),P_ann=np.full(shape,900.),relief=np.arange(108).reshape(shape)*10.)


@pytest.mark.parametrize('dtype',[np.float32,np.float64])
def test_complete_support_reproduces_frozen_cost_geometry_exactly(dtype):
    z=grid();cores={'one':(7.,1.),'two':(1.,10.)}
    for key in ['T_ann','P_ann','relief']:z[key]=z[key].astype(dtype)
    old=travel_distance(z,cores,forest_cost=2,sea_cost=1,relief_cost=1)
    new=travel_distance_supported(z,cores)
    np.testing.assert_array_equal(new.distance_km,old)
    assert new.covered.all() and new.connected.all()


def test_unknown_corridor_is_not_a_cheap_water_shortcut():
    z=grid();z['land'][:,3:6]=False
    known=np.ones(z['land'].shape,bool);known[:,3:6]=False
    result=travel_distance_supported(z,{'source':(7.,1.)},covered=known)
    assert np.isfinite(result.distance_km[:,:3]).all()
    assert np.isinf(result.distance_km[:,3:]).all()
    assert not result.covered[:,3:6].any() and result.covered[:,6:].all()
    assert not result.connected[:,6:].any()
    assert np.isfinite(travel_distance(z,{'source':(7.,1.)},2,1,1)).all()


def test_unsupported_core_is_not_snapped_to_a_different_valid_location():
    z=grid();known=np.ones(z['land'].shape,bool);known[:3,:3]=False
    with pytest.raises(ValueError,match='unsupported'):travel_distance_supported(z,{'source':(7.,1.)},covered=known)
