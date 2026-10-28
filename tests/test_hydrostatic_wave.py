"""Independent wave dispersion and actual vertical pressure/buoyancy work."""
import numpy as np
import pytest
from rotclimate.vertical_state import build_vertical_state,stable_reference
from rotclimate.hydrostatic_wave import HydrostaticWave


def vertical(n=24,density=False):
    edges=np.linspace(0,15000,n+1)
    rho=stable_reference(.5*(edges[:-1]+edges[1:])).density_kg_m3 if density else np.ones(n)
    return build_vertical_state(edges,rho,np.full(n-1,.01**2))


@pytest.mark.parametrize('nx',[16,24])
def test_closed_standing_wave_matches_independent_cn_dispersion(nx):
    ny=3;dx=100000.;dt=600.;steps=13;col=vertical()
    c=.01*(15000/24)/(2*np.sin(np.pi/(2*24)))
    solver=HydrostaticWave(col,0,(ny,nx),dx,0.)
    phase=np.pi*(np.arange(nx)+.5)/nx;phi0=100*np.cos(phase)[None]*np.ones((ny,1))
    state=solver.initial_state(phi0)
    for _ in range(steps):state=solver.advance(state,dt)
    kd=2*np.sin(np.pi/(2*nx))/dx;angle=steps*2*np.arctan(c*kd*dt/2)
    expected_u=np.zeros((ny,nx+1));expected_u[:,1:-1]=100/c*np.sin(angle)*np.sin(np.pi*np.arange(1,nx)/nx)
    np.testing.assert_allclose(state.pressure_amplitude,phi0*np.cos(angle),rtol=1e-11,atol=1e-10)
    np.testing.assert_allclose(state.u_east,expected_u,rtol=1e-11,atol=1e-11)
    np.testing.assert_allclose(state.v_south,0.,atol=1e-11)


def test_uniform_pressure_relaxes_by_exact_cn_factor_without_spurious_wind():
    rt=1/(20*86400.);solver=HydrostaticWave(vertical(),0,(5,7),1e5,7e-5,buoyancy_drag_s=rt)
    state=solver.advance(solver.initial_state(np.full((5,7),80.)),3600.)
    expected=80*(1-1800*rt)/(1+1800*rt)
    np.testing.assert_allclose(state.pressure_amplitude,expected,rtol=1e-13,atol=1e-11)
    assert max(np.abs(state.u_east).max(),np.abs(state.v_south).max())<1e-12


def test_uniform_physical_heating_increases_pressure_state_by_actual_rate():
    solver=HydrostaticWave(vertical(),0,(5,7),1e5,7e-5)
    state=solver.advance(solver.initial_state(np.zeros((5,7))),3600.,forcing_m2_s3=.0002)
    np.testing.assert_allclose(state.pressure_amplitude,.72,rtol=1e-12,atol=1e-12)
    assert state.certificate['midpoint_heating_work_m2_s3']>0
    assert state.certificate['relative_energy_budget_error']<1e-12


def test_thermal_state_generates_wind_and_converts_available_energy_to_kinetic():
    col=vertical(density=True);ny,nx=11,13;j,i=np.mgrid[:ny,:nx]
    phi=120*np.exp(-((i-6)**2+(j-5)**2)/8)
    solver=HydrostaticWave(col,0,(ny,nx),1e5,7e-5)
    b=col.buoyancy_modes[:,0,None,None]*phi
    initial=solver.from_buoyancy(b)
    np.testing.assert_allclose(initial.pressure_amplitude,phi,rtol=1e-11,atol=1e-10)
    state=solver.advance(initial,3600.)
    assert max(np.abs(state.u_east).max(),np.abs(state.v_south).max())>.1
    assert state.certificate['modal_energy_m2_s2']==pytest.approx(initial.certificate['modal_energy_m2_s2'],rel=1e-12)
    assert np.mean(state.pressure_amplitude**2)<np.mean(phi**2)
    np.testing.assert_allclose(col.buoyancy_from_pressure(solver.pressure_levels(state)),solver.buoyancy_interfaces(state),rtol=1e-12,atol=1e-14)
    w=solver.vertical_velocity(state)
    assert w.shape==(len(col.centers_m)-1,ny,nx)


def test_variable_coriolis_preserves_energy_without_heat_or_drag():
    j,i=np.mgrid[:9,:12];solver=HydrostaticWave(vertical(density=True),0,(9,12),1e5,6e-5+2e-5*j/8)
    state=solver.initial_state(80*np.cos(np.pi*(i+.5)/12)*np.cos(np.pi*(j+.5)/9))
    initial=state.certificate['modal_energy_m2_s2']
    for _ in range(30):state=solver.advance(state,900.)
    assert state.certificate['modal_energy_m2_s2']==pytest.approx(initial,rel=1e-12)


def test_actual_vertical_buoyancy_source_work_equals_modal_work_and_reports_exclusions():
    col=vertical(density=True);ny,nx=7,9;j,i=np.mgrid[:ny,:nx]
    solver=HydrostaticWave(col,0,(ny,nx),1e5,7e-5,momentum_drag_s=1/(5*86400.),buoyancy_drag_s=1/(20*86400.))
    initial=solver.initial_state(60*np.cos(np.pi*(i+.5)/nx))
    rng=np.random.default_rng(26);source=rng.normal(size=(23,ny,nx))*1e-7
    state=solver.advance_buoyancy_heating(initial,1800.,source)
    bmid=.5*(solver.buoyancy_interfaces(initial)+solver.buoyancy_interfaces(state))
    physical=np.sum(col.interface_energy_weight[:,None,None]*bmid*source)/(col.total_mass*ny*nx)
    assert physical==pytest.approx(state.certificate['midpoint_heating_work_m2_s3'],rel=1e-11,abs=1e-18)
    assert state.certificate['excluded_buoyancy_source_energy_norm_m2_s4']>0
    assert state.certificate['relative_energy_budget_error']<1e-12


@pytest.mark.parametrize('dt',[0.,-1.,np.nan])
def test_invalid_timestep_rejected(dt):
    solver=HydrostaticWave(vertical(),0,(3,4),1e5,0.)
    with pytest.raises(ValueError):solver.advance(solver.initial_state(0.),dt)


def test_exterior_normal_wind_is_not_silently_removed():
    solver=HydrostaticWave(vertical(),0,(3,4),1e5,0.)
    with pytest.raises(ValueError):solver.initial_state(0.,u_east=1.)
