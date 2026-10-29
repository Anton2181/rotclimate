"""Repeated actual pressure/enthalpy/vapor/phase coupling and dry/moist limits."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import CP,LV
from rotclimate.moist_enthalpy import CP_VAPOR,REFERENCE_K,liquid_enthalpy
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.pressure_moist import PressureMoistModel,gas_energy,enthalpy_phase


def setup(phase=True,drag=0.):
    model=PressureMoistModel(np.geomspace(101325.,38000.,7),(4,5),100000.,1e-4,momentum_drag_s=drag,phase_enabled=phase)
    p=model.column.centers_pa;t=(300*(p/p[0])**.18)[:,None,None]*np.ones(model.mass.shape)
    return model,t


def actual_total(model,state):
    m=model.mass[:,0,0,None,None]
    kinetic=.5*(np.sum(m*state.u_east[:,:,1:-1]**2)+np.sum(m*state.v_south[:,1:-1]**2))
    h=(CP*model.mass+CP_VAPOR*state.vapor_kg_m2)*(state.temperature_k-REFERENCE_K)+LV*state.vapor_kg_m2
    return h.sum()+kinetic


def test_dry_uniform_horizontal_atmosphere_stays_motionless_without_reference_reset():
    model,t=setup();state=model.initial_state(t)
    for _ in range(3):state=model.advance(state,300.)
    np.testing.assert_allclose(state.temperature_k,t,atol=1e-12)
    assert np.max(abs(state.u_east))<1e-11
    assert np.max(abs(state.v_south))<1e-11
    assert np.max(state.ground_rain_kg_m2)==0


def test_actual_dry_thermal_state_generates_wind_and_preserves_enthalpy_plus_kinetic_energy():
    model,t=setup(phase=False);y,x=np.mgrid[:4,:5];t=t+.15*np.sin(np.arange(6)*np.pi/5)[:,None,None]*np.exp(-((x-2)**2+(y-1.5)**2)/2)
    state=model.initial_state(t);initial=actual_total(model,state)
    for _ in range(8):state=model.advance(state,300.)
    assert np.max(abs(state.u_east))>1e-3
    assert actual_total(model,state)==pytest.approx(initial,abs=2e-4)
    assert state.certificate['maximum_temperature_fixed_point_residual_k']<=1e-8
    assert abs(state.certificate['actual_pressure_compression_cancellation_error_w_m2'])<1e-9


def test_repeated_moist_phase_transport_and_wind_feedback_has_actual_water_rain_energy_budget():
    model,t=setup(drag=1/86400);y,x=np.mgrid[:4,:5];rh=.85+.25*np.exp(-((x-2)**2+(y-1.5)**2)/2)
    w=saturation_vapor_mass(t,model.mass,model.pressure)*rh[None]
    state=model.initial_state(t,w);initial=actual_total(model,state);rain=np.zeros(model.shape);rain_h=np.zeros(model.shape)
    for _ in range(6):
        state=model.advance(state,300.);rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2
    assert np.max(abs(state.u_east))>1e-4
    assert rain.max()>0
    np.testing.assert_allclose(state.vapor_kg_m2.sum()+rain.sum(),w.sum(),atol=1e-9)
    assert actual_total(model,state)+rain_h.sum()==pytest.approx(initial,abs=3e-4)
    assert state.certificate['drag_heat_w_m2']>0


def test_vapor_and_external_heat_are_booked_with_actual_source_enthalpy():
    model,t=setup();w=.5*saturation_vapor_mass(t,model.mass,model.pressure);state=model.initial_state(t,w)
    heat=np.full(model.mass.shape,.01);evap=np.zeros_like(heat);evap[0]=1e-6;dt=300.;source_t=290.
    result=model.advance(state,dt,heating_w_m2=heat,evaporation_kg_m2_s=evap,vapor_source_temperature_k=source_t)
    source=heat+evap*(LV+CP_VAPOR*(source_t-REFERENCE_K))
    actual=actual_total(model,result)+result.ground_rain_enthalpy_j_m2.sum()-actual_total(model,state)
    assert actual==pytest.approx(dt*source.sum(),abs=1e-4)
    np.testing.assert_allclose(result.vapor_kg_m2.sum()+result.ground_rain_kg_m2.sum()-w.sum(),dt*evap.sum(),atol=1e-10)


def test_enthalpy_only_falling_rain_is_not_given_fixed_height_fall_heat():
    model,t=setup();w=saturation_vapor_mass(t,model.mass,model.pressure)*1.04
    nt,nw,rain,rain_h=enthalpy_phase(t,w,model.mass,model.pressure)
    np.testing.assert_allclose(gas_energy(nt,nw,model.mass).sum(0)+rain_h,gas_energy(t,w,model.mass).sum(0),rtol=1e-13,atol=1e-6)
    np.testing.assert_allclose(nw.sum(0)+rain,w.sum(0),atol=1e-11)
    np.testing.assert_allclose(rain_h,liquid_enthalpy(nt[0],rain),atol=1e-10)


def test_coupled_iteration_does_not_reapply_phase_or_evaporation_per_iteration():
    model,t=setup();w=saturation_vapor_mass(t,model.mass,model.pressure)*1.02;state=model.initial_state(t,w)
    first=model.advance(state,120.,temperature_tolerance_k=1e-7)
    strict=model.advance(state,120.,temperature_tolerance_k=1e-10)
    np.testing.assert_allclose(first.vapor_kg_m2,strict.vapor_kg_m2,atol=1e-8)
    np.testing.assert_allclose(first.ground_rain_kg_m2,strict.ground_rain_kg_m2,atol=1e-8)


def test_failed_coupling_budget_or_timestep_is_not_silently_accepted():
    model,t=setup();t=t.copy();t[2,1,2]+=.1;state=model.initial_state(t)
    with pytest.raises(RuntimeError):model.advance(state,300.,max_iterations=1,temperature_tolerance_k=1e-14)
    with pytest.raises(ValueError):model.advance(state,0.)
