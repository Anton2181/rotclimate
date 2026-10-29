import numpy as np
import pytest
from rotclimate.open_mean_boundary import OpenMeanRigidLidModel,balance_normal_ports
from rotclimate.rigid_lid_refined import RefinedRigidLidMoistModel
from rotclimate.pressure_boundary import advance_boundary_with_convection
from rotclimate.pressure_moist import gas_energy


P=[101325,85000,65000,40000];SHAPE=(4,5)


def throughflow(f=0.,**kwargs):
    u=np.zeros((3,4,6));v=np.zeros((3,5,5));u[:,:,[0,-1]]=2.
    return OpenMeanRigidLidModel(P,SHAPE,200000,f,u_boundary=u,v_boundary=v,external_temperature_k=280.,external_mixing_ratio=.003,**kwargs)


def test_uniform_barotropic_throughflow_preserves_temperature_water_and_wind():
    m=throughflow(phase_enabled=False);u=np.full((3,4,6),2.);v=np.zeros((3,5,5))
    s=m.initial_state(280,m.mass*.003,u,v)
    for _ in range(3):s=m.advance(s,300)
    np.testing.assert_allclose(s.temperature_k,280,atol=1e-10);np.testing.assert_allclose(s.vapor_kg_m2,m.mass*.003,atol=1e-11)
    np.testing.assert_allclose(s.u_east,u,atol=1e-12);np.testing.assert_allclose(s.v_south,v,atol=1e-12)
    assert abs(s.certificate['actual_gas_plus_kinetic_plus_rain_energy_residual_j_m2'])<1e-5


def test_affine_projection_can_add_energy_and_is_nearest_admissible_wind():
    m=throughflow();u=m.u_boundary.copy();v=m.v_boundary.copy();pu,pv,c=m.project_initial_wind(u,v)
    np.testing.assert_allclose(pu,2,atol=1e-11);np.testing.assert_allclose(pv,0,atol=1e-11)
    assert c['kinetic_energy_change_j_m2']>0
    x=m._velocity(pu,pv);raw=m._pack_unchecked(u,v);d=m.constraint.toarray()
    expected=raw-d.T@np.linalg.solve(d@d.T,d@raw+m.boundary_mass_divergence[:-1])
    np.testing.assert_allclose(x,expected,atol=1e-9)
    ppu,ppv,_=m.project_initial_wind(pu,pv);np.testing.assert_allclose(ppu,pu,atol=1e-12);np.testing.assert_allclose(ppv,pv,atol=1e-12)


def test_actual_constraint_boundary_pressure_work_and_moist_convection_budget():
    m=throughflow(np.linspace(5e-5,1.2e-4,20).reshape(SHAPE),momentum_drag_s=1/86400)
    u,v,_=m.project_initial_wind(m.u_boundary,m.v_boundary)
    t=np.broadcast_to(np.array([295.,265.,235.])[:,None,None],m.mass.shape).copy()+np.arange(20).reshape(SHAPE)[None]*.1
    w=m.mass*np.array([.010,.003,.0002])[:,None,None];s=m.initial_state(t,w,u,v);x=m._velocity(u,v)
    initial=gas_energy(t,w,m.mass).sum()+.5*np.dot(x,x)
    s=advance_boundary_with_convection(m,s,120,relaxation_s=3600);c=s.certificate;dynamic=c['dynamics_before_adjustment']
    x=m._velocity(s.u_east,s.v_south);final=gas_energy(s.temperature_k,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)+s.ground_rain_enthalpy_j_m2.sum()
    power=c['external_power_w_m2']+c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
    np.testing.assert_allclose(final-initial,120*power*m.n,atol=1e-4,rtol=1e-10)
    np.testing.assert_allclose(s.vapor_kg_m2.sum()+s.ground_rain_kg_m2.sum()-w.sum(),-120*c['outward_boundary_vapor_kg_m2_s']*m.n,atol=1e-10)
    assert abs(dynamic['outward_boundary_constraint_geopotential_work_w_m2'])>1e-5
    np.testing.assert_allclose(dynamic['rigid_lid_constraint_pressure_work_w_m2'],-dynamic['outward_boundary_constraint_geopotential_work_w_m2'],atol=1e-10)
    np.testing.assert_allclose(c['outward_boundary_geopotential_work_w_m2'],dynamic['outward_boundary_thermal_geopotential_work_w_m2']+dynamic['outward_boundary_constraint_geopotential_work_w_m2'],atol=1e-12)


def test_explicit_port_preparation_balances_global_mass_preserves_shear_and_inputs():
    rng=np.random.default_rng(81);u=np.zeros((3,4,6));v=np.zeros((3,5,5));u[:,:,[0,-1]]=rng.normal(size=(3,4,2));v[:,[0,-1]]=rng.normal(size=(3,2,5));old_u=u.copy();old_v=v.copy()
    mass=-np.diff(P)/9.80665;bu,bv,c=balance_normal_ports(u,v,mass,200000)
    np.testing.assert_array_equal(u,old_u);np.testing.assert_array_equal(v,old_v)
    np.testing.assert_allclose(np.diff(bu,axis=0),np.diff(u,axis=0),atol=1e-14);np.testing.assert_allclose(np.diff(bv,axis=0),np.diff(v,axis=0),atol=1e-14)
    assert abs(c['original_net_outward_dry_mass_kg_s'])>1e5
    assert abs(c['corrected_net_outward_dry_mass_kg_s'])<1e-5
    m=OpenMeanRigidLidModel(P,SHAPE,200000,1e-4,u_boundary=bu,v_boundary=bv)
    pu,pv,_=m.project_initial_wind(bu,bv);m._velocity(pu,pv)


def test_unbalanced_mass_and_interior_port_entries_rejected():
    u=np.zeros((3,4,6));u[:,:,0]=2
    with pytest.raises(ValueError,match='globally zero'):OpenMeanRigidLidModel(P,SHAPE,200000,1e-4,u_boundary=u)
    u*=0;u[0,1,2]=1
    with pytest.raises(ValueError,match='zero interior'):OpenMeanRigidLidModel(P,SHAPE,200000,1e-4,u_boundary=u)


def test_closed_mean_limit_recovers_refined_frozen_core():
    a=RefinedRigidLidMoistModel(P,SHAPE,200000,1e-4);b=OpenMeanRigidLidModel(P,SHAPE,200000,1e-4)
    t=np.broadcast_to(np.array([290.,270.,245.])[:,None,None],a.mass.shape).copy()+np.arange(20).reshape(SHAPE)[None]*.1
    sa=a.advance(a.initial_state(t,a.mass*.002),120);sb=b.advance(b.initial_state(t,b.mass*.002),120)
    for key in ['temperature_k','vapor_kg_m2','u_east','v_south','ground_rain_kg_m2']:
        np.testing.assert_allclose(getattr(sa,key),getattr(sb,key),rtol=1e-11,atol=1e-10)
