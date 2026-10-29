import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_work import project_column_mass
from rotclimate.terrain_dry import TerrainDryModel
from rotclimate.terrain_advective import TerrainAdvectiveModel
from rotclimate.column_thermodynamics import CP


def case():
    height=np.array([[0.,1500.,3000.],[4000.,200.,1000.],[2500.,500.,2000.]]);grid=terrain_pressure_grid(surface_pressure_from_height(height,288.15),[1,.85,.5,0]);m=TerrainAdvectiveModel(grid,height,1e-4,56000.);return m


def test_rest_state_has_no_spurious_nonlinear_force():
    m=case();state=m.initial_state(m.reference_mean,np.zeros_like(m.apertures.east_kg_m2),np.zeros_like(m.apertures.south_kg_m2));new=m.advance(state,900.)
    np.testing.assert_allclose(new.temperature_k,state.temperature_k,atol=2e-12,rtol=0)
    assert abs(new.east_speed_ms).max()<1e-11 and abs(new.south_speed_ms).max()<1e-11


def test_nonlinear_transport_changes_motion_while_retaining_actual_energy():
    m=case();rng=np.random.default_rng(912);a=m.apertures;u,v,_=project_column_mass(m.grid,rng.normal(0,2,a.east_kg_m2.shape),rng.normal(0,2,a.south_kg_m2.shape),m.dx);t=m.reference_mean+rng.uniform(-.5,.5,m.shape);state=m.initial_state(t,u,v)
    baseline=TerrainDryModel(m.grid,m.h,1e-4,m.dx);control=baseline.advance(baseline.initial_state(t,u,v),60.,temperature_tolerance_k=1e-11);candidate=m.advance(state,60.,temperature_tolerance_k=1e-11)
    assert max(abs(candidate.east_speed_ms-control.east_speed_ms).max(),abs(candidate.south_speed_ms-control.south_speed_ms).max())>1e-6
    c=candidate.certificate;assert abs(c['actual_energy_residual_j_m2_sum'])<1e-3;assert abs(c['advective_kinetic_work_w_m2_sum'])<1e-10;assert c['maximum_actual_midpoint_momentum_residual_weighted_ms']<1e-8
    assert c['maximum_advective_acceleration_ms2']>1e-8


def test_repeated_coupled_nonlinear_steps_keep_actual_heat_plus_kinetic_energy():
    m=case();rng=np.random.default_rng(19);a=m.apertures;u,v,_=project_column_mass(m.grid,rng.normal(0,2,a.east_kg_m2.shape),rng.normal(0,2,a.south_kg_m2.shape),m.dx);state=m.initial_state(m.reference_mean+rng.uniform(-.5,.5,m.shape),u,v);t0=state.temperature_k.copy();x0=m._pack(u,v)
    for _ in range(8):state=m.advance(state,60.,temperature_tolerance_k=1e-11)
    x=m._pack(state.east_speed_ms,state.south_speed_ms);residual=float((CP*m.mass*(state.temperature_k-t0)).sum()+.5*((x@x)-(x0@x0)))
    assert abs(residual)<1e-3


def test_steady_manufactured_vortex_is_balanced_by_nonlinear_constraint_pressure():
    n=16;length=224000.;dx=length/n;k=np.pi/length;c=(np.arange(n)+.5)*dx;f=np.arange(1,n)*dx;grid=terrain_pressure_grid(np.full((n,n),101325.),[1,0]);m=TerrainAdvectiveModel(grid,np.zeros((n,n)),0.,dx);u=(2*np.cos(k*c)[:,None]*np.sin(k*f)[None,:])[None,None];v=(-2*np.sin(k*f)[:,None]*np.cos(k*c)[None,:])[None,None];state=m.initial_state(m.reference_mean,u,v);new=m.advance(state,60.,temperature_tolerance_k=1e-11)
    assert max(abs(new.east_speed_ms-u).max(),abs(new.south_speed_ms-v).max())<1e-4
    assert new.certificate['maximum_constraint_potential_m2_s2']>.01


def test_failed_iteration_retains_caller_state_without_mutation():
    m=case();rng=np.random.default_rng(77);a=m.apertures;u,v,_=project_column_mass(m.grid,rng.normal(0,2,a.east_kg_m2.shape),rng.normal(0,2,a.south_kg_m2.shape),m.dx);t=m.reference_mean+1.;state=m.initial_state(t,u,v)
    with pytest.raises(RuntimeError,match='coupling'):m.advance(state,60.,max_iterations=1)
    np.testing.assert_array_equal(state.temperature_k,t);np.testing.assert_array_equal(state.east_speed_ms,u);np.testing.assert_array_equal(state.south_speed_ms,v)


def test_affine_heat_centering_matches_native_equation_without_budget_feedback():
    from rotclimate.terrain_transport import TerrainTransport
    m=case();rng=np.random.default_rng(44);a=m.apertures;u,v,_=project_column_mass(m.grid,rng.normal(size=a.east_kg_m2.shape),rng.normal(size=a.south_kg_m2.shape),m.dx);transport=TerrainTransport(m.grid,u,v,m.dx,900.);t=m.reference_mean+rng.uniform(-1,1,m.shape);source=rng.uniform(-.1,.1,m.shape)
    direct,_=transport.advance(CP*t,source_per_area_s=source);centered,receipt=m._heat_transport(transport,t,source,u,v)
    np.testing.assert_allclose(centered,direct/CP,atol=5e-12,rtol=0)
    assert abs(receipt['actual_full_enthalpy_source_residual_j_m2_sum'])<1e-3


def test_explicit_transport_switch_isolates_nonlinearity_in_the_same_body():
    m=case();off=TerrainAdvectiveModel(m.grid,m.h,1e-4,m.dx,advect_momentum=False);rng=np.random.default_rng(3);a=m.apertures;u,v,_=project_column_mass(m.grid,rng.normal(0,2,a.east_kg_m2.shape),rng.normal(0,2,a.south_kg_m2.shape),m.dx);t=m.reference_mean+.5
    on=m.advance(m.initial_state(t,u,v),60.);disabled=off.advance(off.initial_state(t,u,v),60.)
    assert on.certificate['maximum_advective_acceleration_ms2']>0
    assert disabled.certificate['maximum_advective_acceleration_ms2']==0
    assert max(abs(on.east_speed_ms-disabled.east_speed_ms).max(),abs(on.south_speed_ms-disabled.south_speed_ms).max())>1e-6
