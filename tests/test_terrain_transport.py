import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_work import project_column_mass,compression_power
from rotclimate.terrain_transport import TerrainTransport


def case():
    rng=np.random.default_rng(919);height=rng.uniform(0,4500,(4,5));grid=terrain_pressure_grid(surface_pressure_from_height(height,288.15),[1,.9,.65,.3,0]);a=horizontal_apertures(grid);u=rng.normal(0,5,a.east_kg_m2.shape);v=rng.normal(0,5,a.south_kg_m2.shape);u,v,_=project_column_mass(grid,u,v,56000.)
    return rng,grid,u,v


def test_constant_mixing_ratio_survives_variable_mass_and_cross_level_flow():
    _,grid,u,v=case();transport=TerrainTransport(grid,u,v,56000.,86400.);old=np.full_like(grid.dry_mass_kg_m2,.007);new,receipt=transport.advance(old)
    # Long steps amplify the measured floating-point continuity residual.
    # Bound that effect explicitly instead of renormalizing the tracer.
    bound=10*np.finfo(float).eps*.007+86400*.007*receipt['maximum_native_dry_mass_residual_kg_m2_s']/grid.dry_mass_kg_m2.min()
    assert np.max(abs(new-old))<=1.05*bound
    assert bound<1e-12*.007
    assert receipt['maximum_native_dry_mass_residual_kg_m2_s']<1e-12


def test_sharp_positive_tracer_is_conserved_without_clipping_at_large_timestep():
    _,grid,u,v=case();transport=TerrainTransport(grid,u,v,56000.,864000.);old=np.zeros_like(grid.dry_mass_kg_m2);old[0,1,2]=.02;new,receipt=transport.advance(old)
    assert new.min()>=0 and new.max()<=old.max()
    assert np.sum(grid.dry_mass_kg_m2*new)==pytest.approx(np.sum(grid.dry_mass_kg_m2*old),rel=5e-14)
    assert abs(receipt['actual_tracer_source_residual_per_area_sum'])<1e-12


def test_heat_and_water_share_geometry_but_conserve_their_own_sources():
    rng,grid,u,v=case();transport=TerrainTransport(grid,u,v,56000.,900.)
    for old,source in [(rng.uniform(200000,300000,grid.dry_mass_kg_m2.shape),np.full(grid.dry_mass_kg_m2.shape,.2)),(rng.uniform(0,.02,grid.dry_mass_kg_m2.shape),np.full(grid.dry_mass_kg_m2.shape,1e-7))]:
        new,receipt=transport.advance(old,source_per_area_s=source)
        np.testing.assert_allclose(np.sum(grid.dry_mass_kg_m2*new),np.sum(grid.dry_mass_kg_m2*old)+900*source.sum(),rtol=1e-14)
        assert receipt['maximum_rowwise_backward_error']<1e-14


def test_continuity_omega_matches_independent_pressure_subinterval_reconstruction():
    _,grid,u,v=case();transport=TerrainTransport(grid,u,v,56000.,900.);compression=compression_power(grid,u,v,56000.,np.zeros_like(grid.dry_mass_kg_m2))
    np.testing.assert_allclose(transport.interface_omega_pa_s,compression.interface_omega_pa_s,atol=5e-15,rtol=1e-12)


def test_zero_velocity_keeps_arbitrary_tracers_and_exact_source_increment():
    rng,grid,u,v=case();transport=TerrainTransport(grid,0*u,0*v,56000.,900.);old=rng.uniform(.001,.02,grid.dry_mass_kg_m2.shape);source=np.full_like(old,1e-6);new,_=transport.advance(old,source_per_area_s=source)
    np.testing.assert_allclose(new,old+900*source/grid.dry_mass_kg_m2,rtol=3e-16)


def test_unphysical_flux_and_excess_removal_rejected():
    _,grid,u,v=case()
    with pytest.raises(ValueError):TerrainTransport(grid,u+1,v,56000.,900.)
    transport=TerrainTransport(grid,u,v,56000.,900.)
    with pytest.raises(ValueError):transport.advance(np.zeros_like(grid.dry_mass_kg_m2),source_per_area_s=-1)
