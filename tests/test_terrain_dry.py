import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_work import project_column_mass
from rotclimate.terrain_dry import TerrainDryModel
from rotclimate.column_thermodynamics import CP


def model():
    height=np.array([[0.,1500.,3000.],[4000.,200.,1000.],[2500.,500.,2000.]])
    grid=terrain_pressure_grid(surface_pressure_from_height(height,288.15),[1,.85,.5,0]);m=TerrainDryModel(grid,height,1e-4,56000.);return m


def test_hydrostatic_rest_does_not_create_winds_or_heat():
    m=model();a=m.apertures;state=m.initial_state(m.reference_mean,np.zeros_like(a.east_kg_m2),np.zeros_like(a.south_kg_m2));new=m.advance(state,900.)
    np.testing.assert_allclose(new.temperature_k,state.temperature_k,atol=2e-12,rtol=0)
    assert abs(new.east_speed_ms).max()<1e-11 and abs(new.south_speed_ms).max()<1e-11


def test_thermal_perturbation_generates_wind_with_no_hidden_energy_fix():
    m=model();t=m.reference_mean.copy();t[0,:,1:]+=1.;state=m.initial_state(t,np.zeros_like(m.apertures.east_kg_m2),np.zeros_like(m.apertures.south_kg_m2));new=m.advance(state,60.,temperature_tolerance_k=1e-11)
    assert abs(new.east_speed_ms).max()>1e-5
    assert abs(new.certificate['actual_energy_residual_j_m2_sum'])<1e-4
    assert new.certificate['energy_residual_heat_correction_j_m2']==0
    assert abs(new.certificate['constraint_work_w_m2_sum'])<1e-10
    assert abs(new.certificate['coriolis_work_w_m2_sum'])<1e-10


def test_repeated_native_thermal_and_pressure_updates_conserve_actual_energy():
    m=model();rng=np.random.default_rng(491);a=m.apertures;u=rng.normal(0,.1,a.east_kg_m2.shape);v=rng.normal(0,.1,a.south_kg_m2.shape);u,v,_=project_column_mass(m.grid,u,v,m.dx);state=m.initial_state(m.reference_mean+rng.uniform(-.5,.5,m.shape),u,v)
    initial_t=state.temperature_k.copy();x0=m._pack(u,v);initial_ke=.5*(x0@x0)
    for _ in range(8):state=m.advance(state,60.,temperature_tolerance_k=1e-11)
    x=m._pack(state.east_speed_ms,state.south_speed_ms);residual=float((CP*m.mass*(state.temperature_k-initial_t)).sum()+.5*(x@x)-initial_ke)
    assert abs(residual)<5e-4
    assert state.certificate['maximum_actual_midpoint_momentum_residual_weighted_ms']<1e-10


def test_zero_force_flat_uniform_state_stays_exactly_uniform():
    grid=terrain_pressure_grid(np.full((2,2),101325.),[1,.7,0]);m=TerrainDryModel(grid,np.zeros((2,2)),0.,56000.);state=m.initial_state(m.reference_mean+1,np.zeros_like(m.apertures.east_kg_m2),np.zeros_like(m.apertures.south_kg_m2));new=m.advance(state,900.)
    np.testing.assert_allclose(new.temperature_k,state.temperature_k,atol=1e-12,rtol=0)
    assert not new.east_speed_ms.any() and not new.south_speed_ms.any()


def test_bad_state_and_work_budget_inputs_are_rejected():
    m=model();a=m.apertures
    with pytest.raises(ValueError):m.initial_state(m.reference_mean,np.ones_like(a.east_kg_m2),np.ones_like(a.south_kg_m2))
    state=m.initial_state(m.reference_mean,np.zeros_like(a.east_kg_m2),np.zeros_like(a.south_kg_m2))
    with pytest.raises(ValueError):m.advance(state,-1.)


def test_removed_column_potential_does_zero_work_on_admissible_wind():
    m=model();rng=np.random.default_rng(71);a=m.apertures;u,v,_=project_column_mass(m.grid,rng.normal(size=a.east_kg_m2.shape),rng.normal(size=a.south_kg_m2.shape),m.dx)
    # A large arbitrary column potential is represented by changed ground
    # geopotential. It changes the constraint pressure, not tangent dynamics.
    shifted=TerrainDryModel(m.grid,m.h+np.arange(9).reshape(3,3)*100.,1e-4,m.dx)
    assert abs(m._pack(u,v)@shifted.reference_barotropic)<1e-10
