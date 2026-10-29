import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures,mass_flux_divergence
from rotclimate.column_thermodynamics import G


def test_flat_limit_is_original_same_level_geometry():
    grid=terrain_pressure_grid(np.full((3,4),100000.),[1,.8,.4,0]);a=horizontal_apertures(grid)
    for k in range(3):
        np.testing.assert_array_equal(a.east_kg_m2[k,k],grid.dry_mass_kg_m2[k,:,:-1])
        np.testing.assert_array_equal(a.south_kg_m2[k,k],grid.dry_mass_kg_m2[k,:-1])
        for j in range(3):
            if j!=k:assert not np.any(a.east_kg_m2[k,j]) and not np.any(a.south_kg_m2[k,j])


def test_step_mountain_closes_underground_pressure_ranges():
    # Left intervals100–70 and70–40kPa; right60–50 and50–40.
    grid=terrain_pressure_grid(np.array([[100000.,60000.],[100000.,60000.]]),[1,.5,0],top_pressure_pa=40000.)
    a=horizontal_apertures(grid)
    expected=np.array([[0,0],[10000,10000.]])/G
    np.testing.assert_allclose(a.east_kg_m2[:,:,0,0],expected)
    assert a.east_kg_m2[:,:,0,0].sum()==pytest.approx(20000/G)
    # No horizontal opening is invented for the lowland's buried lower layer.
    assert not a.east_kg_m2[0].any()


def test_overlap_rows_never_exceed_either_neighbor_layer():
    rng=np.random.default_rng(71);grid=terrain_pressure_grid(rng.uniform(50000,105000,(5,6)),[1,.98,.9,.7,.4,0]);a=horizontal_apertures(grid)
    assert np.all(a.east_kg_m2.sum(1)<=grid.dry_mass_kg_m2[:,:,:-1]+1e-10)
    assert np.all(a.east_kg_m2.sum(0)<=grid.dry_mass_kg_m2[:,:,1:]+1e-10)
    assert np.all(a.south_kg_m2.sum(1)<=grid.dry_mass_kg_m2[:,:-1]+1e-10)
    assert np.all(a.south_kg_m2.sum(0)<=grid.dry_mass_kg_m2[:,1:]+1e-10)


def test_reversing_columns_transposes_cross_level_openings():
    p=np.array([[100000,70000,60000],[80000,90000,65000.]])
    a=horizontal_apertures(terrain_pressure_grid(p,[1,.75,.25,0]));b=horizontal_apertures(terrain_pressure_grid(p[:,::-1],[1,.75,.25,0]))
    np.testing.assert_array_equal(a.east_kg_m2,b.east_kg_m2.transpose(1,0,2,3)[:,:,:,::-1])


def test_every_arbitrary_face_flux_cancels_in_global_dry_mass_budget():
    rng=np.random.default_rng(20);a=horizontal_apertures(terrain_pressure_grid(rng.uniform(50000,100000,(7,8)),[1,.8,.5,0]))
    u=rng.normal(size=a.east_kg_m2.shape);v=rng.normal(size=a.south_kg_m2.shape)
    d=mass_flux_divergence(a,u,v,224000.)
    assert abs(d.sum())<1e-14
    np.testing.assert_array_equal(mass_flux_divergence(a,-u,-v,224000.),-d)


def test_single_cross_level_port_has_equal_opposite_layer_sources():
    a=horizontal_apertures(terrain_pressure_grid(np.array([[100000.,60000.],[100000.,60000.]]),[1,.5,0],top_pressure_pa=40000.));u=np.zeros_like(a.east_kg_m2);v=np.zeros_like(a.south_kg_m2);u[1,0,0,0]=3.
    d=mass_flux_divergence(a,u,v,1000.);expected=np.zeros_like(d);expected[1,0,0]=30/G;expected[0,0,1]=-30/G
    np.testing.assert_array_equal(d,expected)


def test_invalid_face_fields_are_rejected():
    a=horizontal_apertures(terrain_pressure_grid(np.ones((2,2))*100000,[1,0]))
    with pytest.raises(ValueError):mass_flux_divergence(a,np.zeros((2,2)),np.zeros_like(a.south_kg_m2),1.)
    with pytest.raises(ValueError):mass_flux_divergence(a,np.zeros_like(a.east_kg_m2),np.zeros_like(a.south_kg_m2),0.)
