"""Full shared-cell dry dynamics: independent dispersion, work and hidden modes."""
import numpy as np
import pytest
from rotclimate.cell_thermal_column import build_cell_thermal_column
from rotclimate.cell_thermal_wave import CellThermalWave


def setup(nz=6,shape=(4,5),f=0.,**kwargs):
    col=build_cell_thermal_column(np.arange(nz+1)*1000.,np.ones(nz),np.full(nz,.0001))
    return col,CellThermalWave(col,shape,100000.,f,**kwargs)


def test_closed_box_standing_wave_matches_independent_vertical_and_horizontal_dispersion():
    nz,ny,nx=8,4,7;col,wave=setup(nz,(ny,nx));dx=wave.dx;dt=300.;steps=20
    # Lorenz c=N dz/2 cot(pi/(2nz)), horizontal C-grid kh=2sin(pi/(2nx))/dx.
    c=.01*1000/(2*np.tan(np.pi/(2*nz)));kh=2*np.sin(np.pi/(2*nx))/dx
    phase=steps*2*np.arctan(c*kh*dt/2)
    pattern=np.broadcast_to(np.cos(np.pi*(np.arange(nx)+.5)/nx),(ny,nx))
    initial=col.cell_buoyancy_modes[:,0,None,None]*pattern
    state=wave.initial_state(initial);e0=state.certificate['kinetic_plus_thermal_available_energy_m2_s2']
    for _ in range(steps):state=wave.advance(state,dt)
    np.testing.assert_allclose(state.buoyancy_cells,initial*np.cos(phase),rtol=1e-10,atol=1e-13)
    assert state.certificate['kinetic_plus_thermal_available_energy_m2_s2']==pytest.approx(e0,rel=1e-11)
    assert np.max(np.abs(state.u_east))>0


def test_varying_rotation_all_levels_preserve_energy_and_closed_column_mass():
    col,wave=setup(f=np.linspace(.5e-4,1.5e-4,20).reshape(4,5));rng=np.random.default_rng(17)
    state=wave.initial_state(rng.normal(scale=.002,size=(6,4,5)))
    e0=state.certificate['kinetic_plus_thermal_available_energy_m2_s2']
    for _ in range(30):state=wave.advance(state,300.)
    assert state.certificate['kinetic_plus_thermal_available_energy_m2_s2']==pytest.approx(e0,rel=1e-11)
    assert wave.vertical_velocity(state).shape==(5,4,5)
    mass=col.cell_mass_kg_m2[:,None,None]
    np.testing.assert_allclose(np.sum(mass*state.u_east,axis=0),0,atol=1e-10)
    np.testing.assert_allclose(np.sum(mass*state.v_south,axis=0),0,atol=1e-10)


def test_actual_forcing_work_and_damping_balance_thermal_and_kinetic_energy():
    col,wave=setup(f=1e-4,momentum_drag_s=1/40000,buoyancy_drag_s=1/90000);rng=np.random.default_rng(71)
    state=wave.initial_state(rng.normal(scale=.001,size=(6,4,5)));q=rng.normal(scale=1e-7,size=(6,4,5));dt=500.
    result=wave.advance(state,dt,buoyancy_source_s3=q)
    midb=.5*(state.buoyancy_cells+result.buoyancy_cells)
    expected_work=np.sum(col.thermal_energy_weight[:,None,None]*midb*q)/(col.total_mass*20)
    assert result.certificate['midpoint_source_work_m2_s3']==pytest.approx(expected_work,rel=1e-13)
    actual=result.certificate['kinetic_plus_thermal_available_energy_m2_s2']-state.certificate['kinetic_plus_thermal_available_energy_m2_s2']
    assert actual==pytest.approx(dt*(expected_work-result.certificate['midpoint_damping_m2_s3']),abs=1e-14)


def test_computational_thermal_mode_is_retained_stationary_and_does_not_generate_wind():
    col,wave=setup();pattern=np.arange(20).reshape(4,5)/20
    b=col.pressure_invisible_thermal_mode[:,None,None]*pattern*.1
    state=wave.initial_state(b);result=wave.advance(state,1000.)
    np.testing.assert_allclose(result.buoyancy_cells,b,atol=1e-15)
    assert np.max(np.abs(result.u_east))<1e-12
    assert np.max(np.abs(result.v_south))<1e-12
    assert result.certificate['pressure_invisible_available_energy_m2_s2']>0
    assert result.certificate['pressure_active_available_energy_m2_s2']<1e-20


def test_uniform_horizontal_heating_has_no_pressure_gradient_and_no_spurious_wind():
    col,wave=setup();q=np.linspace(1e-8,2e-8,6)[:,None,None]
    state=wave.initial_state(0.);result=wave.advance(state,600.,buoyancy_source_s3=q)
    np.testing.assert_allclose(result.buoyancy_cells,np.broadcast_to(600*q,(6,4,5)),atol=1e-16)
    assert np.max(np.abs(result.u_east))<1e-13
    assert np.max(np.abs(result.v_south))<1e-13


def test_invalid_mass_mean_flow_and_timestep_are_rejected():
    col,wave=setup();u=np.zeros((6,4,6));u[:,:,1:-1]=1
    with pytest.raises(ValueError):wave.initial_state(0.,u_east=u)
    with pytest.raises(ValueError):wave.advance(wave.initial_state(0.),0.)
