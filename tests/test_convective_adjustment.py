"""Conservative convective mixing, actual stability and split feedback."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import G,CP,RD
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.pressure_moist import gas_energy,PressureMoistModel
from rotclimate.convective_adjustment import adjust_convection,advance_with_convection,_saturated_lift
from rotclimate.parcel_stability import parcel_profile


def column(exponent=.18,n=10):
    edges=np.geomspace(101325.,38000.,n+1);p=np.sqrt(edges[:-1]*edges[1:]);m=-np.diff(edges)/G
    return p,m,300*(p/p[0])**exponent


def test_dry_unstable_column_neutralizes_without_water_or_unbooked_energy():
    p,m,t=column(.4);w=np.zeros_like(t);result=adjust_convection(t,w,m,p)
    assert result.certificate['converged'];assert result.certificate['adjusted_pairs']>0
    assert result.ground_rain_kg_m2==0
    np.testing.assert_allclose(gas_energy(result.temperature_k,result.vapor_kg_m2,m).sum(),gas_energy(t,w,m).sum(),rtol=1e-13)
    potential=result.temperature_k*(100000/p)**(RD/CP)
    assert np.min(np.diff(potential))>-.02


def test_stable_unsaturated_column_is_unchanged():
    p,m,t=column(.08);w=.9*saturation_vapor_mass(t,m,p);result=adjust_convection(t,w,m,p)
    assert result.certificate['adjusted_pairs']==0
    np.testing.assert_allclose(result.temperature_k,t,atol=1e-11)
    np.testing.assert_allclose(result.vapor_kg_m2,w,atol=1e-12)


def test_saturated_conditional_adjustment_preserves_actual_enthalpy_water_and_rain():
    p,m,t=column();w=saturation_vapor_mass(t,m,p);result=adjust_convection(t,w,m,p)
    assert result.certificate['converged'];assert result.certificate['adjusted_pairs']>0
    before=gas_energy(t,w,m).sum();after=gas_energy(result.temperature_k,result.vapor_kg_m2,m).sum()+result.ground_rain_enthalpy_j_m2
    assert after==pytest.approx(before,abs=2e-5)
    assert result.vapor_kg_m2.sum()+result.ground_rain_kg_m2==pytest.approx(w.sum(),abs=1e-10)
    assert result.ground_rain_kg_m2>0
    sat=saturation_vapor_mass(result.temperature_k,m,p)
    for k in range(len(p)-1):
        if result.vapor_kg_m2[k]>=sat[k]*(1-1e-8):
            source=float(saturation_vapor_mass(result.temperature_k[k],1.,p[k]))
            lifted=parcel_profile(p[k:k+2],result.temperature_k[k],source,max_log_pressure_step=.002)
            assert lifted.temperature_k[-1]<=result.temperature_k[k+1]+.011


def test_unsaturated_dry_stable_conditional_energy_does_not_trigger_unforced_adjustment():
    p,m,t=column();w=.5*saturation_vapor_mass(t,m,p);result=adjust_convection(t,w,m,p)
    assert result.certificate['adjusted_pairs']==0
    np.testing.assert_allclose(result.temperature_k,t,atol=1e-11)


def test_saturated_target_agrees_with_independent_finer_parcel_integration():
    p=np.array([100000.,90000.]);q=float(saturation_vapor_mass(300.,1.,p[0]))
    expected=parcel_profile(p,300.,q,max_log_pressure_step=.002).temperature_k[-1]
    assert float(_saturated_lift(300.,p[0],p[1]))==pytest.approx(expected,abs=2e-6)


def test_split_coupled_convection_retains_actual_energy_water_and_feedback():
    edges=np.geomspace(101325.,38000.,7);model=PressureMoistModel(edges,(4,5),100000.,1e-4)
    p=model.column.centers_pa;t=np.broadcast_to((300*(p/p[0])**.18)[:,None,None],model.mass.shape).copy()
    y,x=np.mgrid[:4,:5];rh=.85+.25*np.exp(-((x-2)**2+(y-1.5)**2)/2);w=saturation_vapor_mass(t,model.mass,model.pressure)*rh[None]
    state=model.initial_state(t,w);initial=gas_energy(t,w,model.mass).sum();rain=np.zeros((4,5));rain_h=np.zeros((4,5));pairs=0
    for _ in range(3):
        state=advance_with_convection(model,state,300.);rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2
        pairs+=state.certificate['convective_adjustment']['adjusted_pairs']
    mass=model.mass[:,0,0,None,None];kinetic=.5*(np.sum(mass*state.u_east[:,:,1:-1]**2)+np.sum(mass*state.v_south[:,1:-1]**2))
    assert gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+kinetic+rain_h.sum()==pytest.approx(initial,abs=1e-4)
    assert state.vapor_kg_m2.sum()+rain.sum()==pytest.approx(w.sum(),abs=1e-9)
    assert pairs>0
    assert np.max(abs(state.u_east))>0


def test_unconverged_short_sweep_budget_is_explicit():
    p,m,t=column(.4,n=16);result=adjust_convection(t,np.zeros_like(t),m,p,max_sweeps=1)
    assert not result.certificate['converged']
    assert result.certificate['remaining_active_interfaces']>0


def test_invalid_mass_and_controls_rejected():
    p,m,t=column()
    with pytest.raises(ValueError):adjust_convection(t,np.zeros_like(t),-m,p)
    with pytest.raises(ValueError):adjust_convection(t,np.zeros_like(t),m,p,neutral_tolerance_k=0.)


def test_finite_relaxation_conserves_actual_energy_water_and_exported_rain():
    edges=np.geomspace(101325.,38000.,7);model=PressureMoistModel(edges,(2,2),100000.,1e-4)
    p=model.column.centers_pa;t=np.broadcast_to((300*(p/p[0])**.18)[:,None,None],model.mass.shape).copy()
    w=saturation_vapor_mass(t,model.mass,model.pressure);state=model.initial_state(t,w)
    result=advance_with_convection(model,state,300.,relaxation_s=3600.)
    m=model.mass[:,0,0,None,None];ke=.5*(np.sum(m*result.u_east[:,:,1:-1]**2)+np.sum(m*result.v_south[:,1:-1]**2))
    assert gas_energy(result.temperature_k,result.vapor_kg_m2,model.mass).sum()+ke+result.ground_rain_enthalpy_j_m2.sum()==pytest.approx(gas_energy(t,w,model.mass).sum(),abs=1e-4)
    assert result.vapor_kg_m2.sum()+result.ground_rain_kg_m2.sum()==pytest.approx(w.sum(),abs=1e-10)
    assert result.certificate['adjusted_fraction']==pytest.approx(1-np.exp(-300/3600))


def test_infinite_time_limit_recovers_no_adjustment_dynamics():
    edges=np.geomspace(101325.,38000.,7);model=PressureMoistModel(edges,(2,2),100000.,1e-4)
    p=model.column.centers_pa;t=np.broadcast_to((300*(p/p[0])**.18)[:,None,None],model.mass.shape).copy()
    w=saturation_vapor_mass(t,model.mass,model.pressure);state=model.initial_state(t,w)
    expected=model.advance(state,300.);actual=advance_with_convection(model,state,300.,relaxation_s=1e40)
    np.testing.assert_allclose(actual.temperature_k,expected.temperature_k,atol=1e-10)
    np.testing.assert_allclose(actual.vapor_kg_m2,expected.vapor_kg_m2,atol=1e-10)
    np.testing.assert_allclose(actual.ground_rain_kg_m2,expected.ground_rain_kg_m2,atol=1e-10)


def test_negative_relaxation_time_rejected():
    edges=np.geomspace(101325.,38000.,7);model=PressureMoistModel(edges,(2,2),100000.,1e-4);state=model.initial_state(280.)
    with pytest.raises(ValueError):advance_with_convection(model,state,300.,relaxation_s=-1.)
