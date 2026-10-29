"""Regional boundary ports: closed limits and independent actual energy/water."""
import numpy as np
import pytest
from rotclimate.pressure_moist import PressureMoistModel,gas_energy
from rotclimate.pressure_boundary import BoundaryPressureMoistModel,advance_boundary_with_convection,baroclinic_lower_wind_seed
from rotclimate.convective_adjustment import advance_with_convection
from rotclimate.phase_adjustment import saturation_vapor_mass


def geometry():
    edges=np.geomspace(101325.,38000.,7);closed=PressureMoistModel(edges,(4,5),100000.,0.)
    m=closed.column.cell_mass_kg_m2;profile=np.linspace(3.,-3.,6);profile-=np.dot(m,profile)/m.sum()
    fullu=np.broadcast_to(profile[:,None,None],(6,4,6)).copy();ub=np.zeros_like(fullu);ub[:,:,[0,-1]]=fullu[:,:,[0,-1]]
    t=np.broadcast_to((300*(closed.column.centers_pa/closed.column.centers_pa[0])**.12)[:,None,None],closed.mass.shape).copy()
    return edges,closed,ub,fullu,t


def actual_energy(model,state):
    m=model.mass[:,0,0,None,None]
    return gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+.5*(np.sum(m*state.u_east[:,:,1:-1]**2)+np.sum(m*state.v_south[:,1:-1]**2))


def test_zero_boundary_variant_recovers_frozen_closed_dynamics():
    edges,_,ub,fullu,t=geometry();a=PressureMoistModel(edges,(4,5),100000.,1e-4);b=BoundaryPressureMoistModel(edges,(4,5),100000.,1e-4)
    t=t.copy();t[2,1,2]+=.1;initial_a=a.initial_state(t);initial_b=b.initial_state(t)
    for _ in range(3):initial_a=a.advance(initial_a,300.);initial_b=b.advance(initial_b,300.)
    for field in ['temperature_k','vapor_kg_m2','u_east','v_south','ground_rain_kg_m2']:
        np.testing.assert_allclose(getattr(initial_a,field),getattr(initial_b,field),atol=1e-11)


def test_uniform_baroclinic_throughflow_retains_uniform_layer_states():
    edges,_,ub,fullu,t=geometry();model=BoundaryPressureMoistModel(edges,(4,5),100000.,0.,u_boundary=ub,external_temperature_k=t,external_mixing_ratio=.001,phase_enabled=False)
    state=model.initial_state(t,.001*model.mass,u_east=fullu)
    result=model.advance(state,600.)
    np.testing.assert_allclose(result.temperature_k,t,atol=1e-11)
    np.testing.assert_allclose(result.vapor_kg_m2,state.vapor_kg_m2,atol=1e-11)
    np.testing.assert_allclose(result.u_east,fullu,atol=1e-12)


def test_actual_boundary_vapor_and_enthalpy_supply_balance_interior_changes():
    edges,_,ub,fullu,t=geometry();model=BoundaryPressureMoistModel(edges,(4,5),100000.,0.,u_boundary=ub,external_temperature_k=t,external_mixing_ratio=.002)
    old=model.initial_state(t,.001*model.mass,u_east=fullu);dt=600.;new=model.advance(old,dt);c=new.certificate
    incoming_energy=c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
    delta=(actual_energy(model,new)+new.ground_rain_enthalpy_j_m2.sum()-actual_energy(model,old))/model.n
    assert delta==pytest.approx(dt*incoming_energy,abs=2e-5)
    water=(new.vapor_kg_m2.sum()+new.ground_rain_kg_m2.sum()-old.vapor_kg_m2.sum())/model.n
    assert water>0
    assert water==pytest.approx(-dt*c['outward_boundary_vapor_kg_m2_s'],abs=1e-11)


def test_prescribed_coriolis_boundary_exchange_and_geopotential_work_are_booked():
    edges,_,ub,fullu,t=geometry();model=BoundaryPressureMoistModel(edges,(4,5),100000.,1e-4,u_boundary=ub,external_temperature_k=t)
    old=model.initial_state(t);new=model.advance(old,300.);c=new.certificate
    assert abs(c['prescribed_boundary_rotation_work_w_m2'])>0
    assert abs(c['actual_pressure_compression_cancellation_error_w_m2'])<1e-9
    expected=300*(c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2'])
    assert (actual_energy(model,new)+new.ground_rain_enthalpy_j_m2.sum()-actual_energy(model,old))/model.n==pytest.approx(expected,abs=2e-5)


def test_boundary_mass_source_and_ignored_interior_velocity_are_rejected():
    edges,_,ub,fullu,t=geometry();bad=ub.copy();bad[0,:,0]+=1.
    with pytest.raises(ValueError):BoundaryPressureMoistModel(edges,(4,5),100000.,0.,u_boundary=bad)
    with pytest.raises(ValueError):BoundaryPressureMoistModel(edges,(4,5),100000.,0.,u_boundary=fullu)


def test_zero_ports_recover_closed_convective_wrapper():
    edges,_,ub,fullu,t=geometry();a=PressureMoistModel(edges,(4,5),100000.,1e-4);b=BoundaryPressureMoistModel(edges,(4,5),100000.,1e-4)
    w=1.02*saturation_vapor_mass(t,a.mass,a.pressure)
    ca=advance_with_convection(a,a.initial_state(t,w),300.,relaxation_s=3600.)
    cb=advance_boundary_with_convection(b,b.initial_state(t,w),300.,relaxation_s=3600.)
    for field in ['temperature_k','vapor_kg_m2','u_east','v_south','ground_rain_kg_m2']:
        np.testing.assert_allclose(getattr(ca,field),getattr(cb,field),atol=1e-10)


def test_prescribed_ports_and_convection_retain_combined_actual_budgets():
    edges,old,ub,fullu,t=geometry();sat=saturation_vapor_mass(t,old.mass,old.pressure)
    model=BoundaryPressureMoistModel(edges,(4,5),100000.,1e-4,u_boundary=ub,external_temperature_k=t,external_mixing_ratio=.95*sat/old.mass)
    state=model.initial_state(t,1.02*sat);result=advance_boundary_with_convection(model,state,300.,relaxation_s=3600.);c=result.certificate
    supply=c['external_power_w_m2']+c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
    change=(actual_energy(model,result)+result.ground_rain_enthalpy_j_m2.sum()-actual_energy(model,state))/model.n
    assert change==pytest.approx(300*supply,abs=2e-5)
    water=(result.vapor_kg_m2.sum()+result.ground_rain_kg_m2.sum()-state.vapor_kg_m2.sum())/model.n
    assert water==pytest.approx(-300*c['outward_boundary_vapor_kg_m2_s'],abs=1e-11)


def test_archived_lower_wind_seed_retains_face_values_sign_and_zero_depth_mean():
    right=np.arange(12.).reshape(3,4);up=np.full_like(right,2.);mass=np.array([1000.,1500.,2500.])
    u,v=baroclinic_lower_wind_seed(right,up,mass)
    np.testing.assert_allclose(u[0,:,0],right[:,0],atol=0)
    np.testing.assert_allclose(u[0,:,1:-1],.5*(right[:,:-1]+right[:,1:]),atol=0)
    np.testing.assert_allclose(v[0],-2.,atol=0)
    np.testing.assert_allclose(np.sum(mass[:,None,None]*u,axis=0),0,atol=1e-12)
    np.testing.assert_allclose(np.sum(mass[:,None,None]*v,axis=0),0,atol=1e-12)
