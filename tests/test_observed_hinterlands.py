import numpy as np
import pytest

from polity.observed_hinterlands import hinterland_people,grid_points


@pytest.mark.parametrize('cell',[3.,9.])
def test_native_projection_round_trip_not_affine_degrees(cell):
    from polity.earth import grid
    g=grid(31.8,45.6,600,500,cell)
    points=grid_points(g['lat'].ravel(),g['lon'].ravel(),g)
    yy,xx=np.indices(g['x'].shape)
    np.testing.assert_allclose(points,np.column_stack([yy.ravel(),xx.ravel()]),atol=1e-8,rtol=0)


def test_native_equatorial_distance_has_independent_spherical_solution():
    import math
    g=dict(x=np.array([[-1.,0.],[-1.,0.]]),y=np.array([[1.,1.],[0.,0.]]),cell_km=1.,lat0=0.,lon0=0.)
    np.testing.assert_allclose(grid_points([0.],[1.],g),[[1.,1.+6371*math.pi/180]],atol=1e-10)


def test_fractional_geometry_and_cutoff_with_hand_counted_people():
    # Three 1km² cells contain2,4,8people. Each is owned once, with a finite radius.
    d=np.array([[2.,4.,8.]])
    np.testing.assert_array_equal(hinterland_people(d,np.ones_like(d,bool),[[0,.2],[0,1.9]],1),[6,8])
    np.testing.assert_array_equal(hinterland_people(d,np.ones_like(d,bool),[[0,.2]],1,.3),[2])


def test_coincident_records_share_people_without_deleting_a_record():
    np.testing.assert_array_equal(hinterland_people([[10]],[[True]],[[0,0],[0,0]],2),[20,20])


def test_equidistant_centres_split_cell_and_ignore_nonland():
    np.testing.assert_array_equal(hinterland_people([[6,100]],[[True,False]],[[0,-1],[0,1]],1),[3,3])


def test_no_centres_and_out_of_range_do_not_create_people():
    assert hinterland_people([[1]],[[True]],[],1).shape==(0,)
    np.testing.assert_array_equal(hinterland_people([[1]],[[True]],[[20,20]],1,1),[0])


def test_chunked_mass_conservation_including_fractional_centres():
    density=np.arange(1,10001).reshape(100,100)/100
    h=hinterland_people(density,np.ones_like(density,bool),[[3.2,4.4],[60,60],[90.9,89.8]],1,1000)
    assert h.sum()==pytest.approx(density.sum(),abs=1e-8)


@pytest.mark.parametrize('density,land,points,cell,radius',[
    ([[1]],[[True]],[[float('nan'),0]],1,60),
    ([[-1]],[[True]],[[0,0]],1,60),
    ([[1]],[[True]],[[0,0]],0,60),
    ([[1]],[[True]],[[0,0]],1,-1),
    ([[1]],[[True]],[[0,0]],1,float('inf')),
    ([[1,2]],[[True]],[[0,0]],1,60),
])
def test_invalid_accounting_inputs_rejected(density,land,points,cell,radius):
    with pytest.raises(ValueError):hinterland_people(density,land,points,cell,radius)
