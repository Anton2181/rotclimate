import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_work import project_column_mass,compression_power
from rotclimate.terrain_work_cache import TerrainWorkCache,cached_work_model
from rotclimate.terrain_advective import TerrainAdvectiveModel


def case():
    rng=np.random.default_rng(321);height=rng.uniform(0,4500,(4,5));grid=terrain_pressure_grid(surface_pressure_from_height(height,288.15),[1,.9,.65,.3,0]);a=horizontal_apertures(grid);u,v,_=project_column_mass(grid,rng.normal(0,3,a.east_kg_m2.shape),rng.normal(0,3,a.south_kg_m2.shape),56000.);return rng,height,grid,u,v


def test_cached_quadrature_matches_independent_physical_integration():
    rng,_,grid,u,v=case();cache=TerrainWorkCache(grid,56000.)
    for _ in range(5):
        delta=rng.uniform(-3,3,grid.dry_mass_kg_m2.shape);old=compression_power(grid,u,v,56000.,delta);new=cache.evaluate(grid,u,v,56000.,delta)
        np.testing.assert_allclose(new.layer_power_w_m2,old.layer_power_w_m2,atol=2e-11,rtol=2e-12)
        np.testing.assert_allclose(new.interface_omega_pa_s,old.interface_omega_pa_s,atol=5e-15,rtol=1e-12)


def test_same_advance_body_and_trajectory_without_global_patching():
    rng,height,grid,u,v=case();original=TerrainAdvectiveModel.advance.__globals__['compression_power'];slow=TerrainAdvectiveModel(grid,height,1e-4,56000.);fast=cached_work_model(TerrainAdvectiveModel)(grid,height,1e-4,56000.);temperature=slow.reference_mean+rng.uniform(-.5,.5,grid.dry_mass_kg_m2.shape);a=slow.initial_state(temperature,u,v);b=fast.initial_state(temperature,u,v)
    assert fast.advance.__func__.__code__ is TerrainAdvectiveModel.advance.__code__
    for _ in range(4):a=slow.advance(a,60.);b=fast.advance(b,60.)
    np.testing.assert_allclose(b.temperature_k,a.temperature_k,atol=1e-10,rtol=0);np.testing.assert_allclose(b.east_speed_ms,a.east_speed_ms,atol=1e-10,rtol=0);np.testing.assert_allclose(b.south_speed_ms,a.south_speed_ms,atol=1e-10,rtol=0)
    assert TerrainAdvectiveModel.advance.__globals__['compression_power'] is original


def test_geometry_mutation_and_reference_changes_rejected():
    _,_,grid,u,v=case();cache=TerrainWorkCache(grid,56000.);delta=np.zeros_like(grid.dry_mass_kg_m2)
    with pytest.raises(ValueError):cache.evaluate(grid,u,v,56001.,delta)
    with pytest.raises(ValueError):cache.evaluate(grid,u,v,56000.,delta,reference_temperature_k=290.)
    grid.edges_pa[0,0,0]-=1
    with pytest.raises(ValueError):cache.evaluate(grid,u,v,56000.,delta)


def test_zero_flow_stays_exactly_zero():
    _,_,grid,u,v=case();cache=TerrainWorkCache(grid,56000.);result=cache.evaluate(grid,0*u,0*v,56000.,np.zeros_like(grid.dry_mass_kg_m2))
    assert not result.layer_power_w_m2.any() and not result.interface_omega_pa_s.any()
