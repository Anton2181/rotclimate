import numpy as np
import pytest
from rotclimate.pressure_boundary import BoundaryPressureMoistModel,advance_boundary_with_convection,baroclinic_lower_wind_seed
from rotclimate.pressure_moist import gas_energy
from rotclimate.rigid_lid_moist import RigidLidMoistModel,stagger_two_reservoir_wind


def model(**kwargs):
    return RigidLidMoistModel([101325,85000,65000,40000],(4,5),200000,1e-4,**kwargs)


def circulation(m):
    ny,nx=m.shape;psi=np.zeros((ny+1,nx+1));psi[1:-1,1:-1]=np.arange((ny-1)*(nx-1)).reshape(ny-1,nx-1)*1e5
    return np.broadcast_to(np.diff(psi,axis=0)[None]/m.dx,(m.nz,ny,nx+1)).copy(),np.broadcast_to(-np.diff(psi,axis=1)[None]/m.dx,(m.nz,ny+1,nx)).copy()


def test_mean_circulation_retained_with_exact_column_mass():
    m=model();u,v=circulation(m);x=m._velocity(u,v)
    assert np.linalg.norm(x)>0
    np.testing.assert_allclose(m.column_divergence@x,0,atol=1e-15)
    assert np.max(abs(np.sum(m.mass[:,:,:1]*u,axis=0)))>1
    old=BoundaryPressureMoistModel([101325,85000,65000,40000],m.shape,m.dx,1e-4)
    with pytest.raises(ValueError,match='depth-mean'):old._velocity(u,v)


def test_mass_projection_is_orthogonal_idempotent_and_only_changes_mean():
    m=model();rng=np.random.default_rng(412);u=rng.normal(size=(m.nz,4,6));v=rng.normal(size=(m.nz,5,5));u[:,:,[0,-1]]=0;v[:,[0,-1]]=0
    raw=m._pack_unchecked(u,v);pu,pv,c=m.project_initial_wind(u,v);x=m._velocity(pu,pv)
    np.testing.assert_allclose(np.dot(x,raw-x),0,atol=1e-9)
    np.testing.assert_allclose(.5*np.dot(raw-x,raw-x)/m.n,c['removed_kinetic_energy_j_m2'],rtol=1e-12)
    np.testing.assert_allclose(pu-u,np.broadcast_to((pu-u)[:1],u.shape),atol=1e-12)
    np.testing.assert_allclose(pv-v,np.broadcast_to((pv-v)[:1],v.shape),atol=1e-12)
    ppu,ppv,_=m.project_initial_wind(pu,pv)
    np.testing.assert_allclose(ppu,pu,atol=1e-12);np.testing.assert_allclose(ppv,pv,atol=1e-12)


def test_nonzero_mean_flow_dry_constraint_does_no_work():
    m=model(phase_enabled=False);u,v=circulation(m);t=np.broadcast_to(np.array([290.,270.,245.])[:,None,None],m.mass.shape).copy()
    s=m.initial_state(t,0,u,v);initial=gas_energy(t,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(m._velocity(u,v),m._velocity(u,v))
    for _ in range(4):s=m.advance(s,300)
    x=m._velocity(s.u_east,s.v_south);final=gas_energy(s.temperature_k,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)
    np.testing.assert_allclose(final,initial,rtol=1e-12)
    np.testing.assert_allclose(s.temperature_k,t,atol=1e-9)
    assert np.linalg.norm(x)>.9*np.linalg.norm(m._velocity(u,v))
    assert abs(s.certificate['rigid_lid_constraint_pressure_work_w_m2'])<1e-10


@pytest.mark.parametrize('ports',[False,True])
def test_zero_mean_limit_recovers_frozen_boundary_dynamics(ports):
    shape=(4,5);p=[101325,85000,65000,40000];mass=-np.diff(p)/9.80665
    u,v=baroclinic_lower_wind_seed(np.ones(shape)*2,np.ones(shape),mass)
    ub=np.zeros_like(u);vb=np.zeros_like(v)
    if ports:ub[:,:,[0,-1]]=u[:,:,[0,-1]];vb[:,[0,-1]]=v[:,[0,-1]]
    u[:,:,[0,-1]]=ub[:,:,[0,-1]];v[:,[0,-1]]=vb[:,[0,-1]]
    kwargs=dict(u_boundary=ub,v_boundary=vb,momentum_drag_s=1/(5*86400))
    old=BoundaryPressureMoistModel(p,shape,200000,1e-4,**kwargs);new=RigidLidMoistModel(p,shape,200000,1e-4,**kwargs)
    t=np.broadcast_to(np.array([290.,270.,245.])[:,None,None],old.mass.shape).copy()+np.arange(20).reshape(shape)[None]*.05
    a=old.advance(old.initial_state(t,old.mass*.002,u,v),120);b=new.advance(new.initial_state(t,old.mass*.002,u,v),120)
    for key in ['temperature_k','vapor_kg_m2','u_east','v_south','ground_rain_kg_m2']:
        np.testing.assert_allclose(getattr(a,key),getattr(b,key),rtol=1e-10,atol=1e-9)


def test_nonzero_mean_flow_with_moist_convection_and_drag_conserves():
    m=model(momentum_drag_s=1/86400);u,v=circulation(m);t=np.broadcast_to(np.array([298.,265.,232.])[:,None,None],m.mass.shape).copy();w=m.mass*np.array([.015,.004,.0003])[:,None,None]
    s=m.initial_state(t,w,u,v);x=m._velocity(u,v);initial=gas_energy(t,w,m.mass).sum()+.5*np.dot(x,x)
    s=advance_boundary_with_convection(m,s,60,relaxation_s=3600)
    x=m._velocity(s.u_east,s.v_south);final=gas_energy(s.temperature_k,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)+s.ground_rain_enthalpy_j_m2.sum()
    np.testing.assert_allclose(final,initial,rtol=1e-12)
    np.testing.assert_allclose(s.vapor_kg_m2.sum()+s.ground_rain_kg_m2.sum(),w.sum(),rtol=1e-12)


def test_divergent_initial_mean_and_changed_ports_rejected():
    m=model();u,v=circulation(m);u[0,1,1]+=1
    with pytest.raises(ValueError,match='column dry mass'):m._velocity(u,v)
    u,v=circulation(m);u[0,0,0]=1
    with pytest.raises(ValueError,match='Exterior'):m.project_initial_wind(u,v)


def test_variable_rotation_mean_flow_and_actual_regional_port_budget():
    p=[101325,85000,65000,40000];shape=(4,5);mass=-np.diff(p)/9.80665
    bu,bv=baroclinic_lower_wind_seed(np.full(shape,2.),np.full(shape,-1.),mass)
    ub=np.zeros_like(bu);vb=np.zeros_like(bv);ub[:,:,[0,-1]]=bu[:,:,[0,-1]];vb[:,[0,-1]]=bv[:,[0,-1]]
    f=np.linspace(5e-5,1.2e-4,20).reshape(shape)
    m=RigidLidMoistModel(p,shape,200000,f,u_boundary=ub,v_boundary=vb,external_temperature_k=290,external_mixing_ratio=.007,momentum_drag_s=1/86400)
    cu,cv=circulation(m);u,v=bu+cu,bv+cv
    t=np.broadcast_to(np.array([290.,270.,245.])[:,None,None],m.mass.shape).copy();w=m.mass*.002
    s=m.initial_state(t,w,u,v);x=m._velocity(u,v);initial=gas_energy(t,w,m.mass).sum()+.5*np.dot(x,x)
    s=advance_boundary_with_convection(m,s,120,relaxation_s=3600);c=s.certificate
    x=m._velocity(s.u_east,s.v_south);final=gas_energy(s.temperature_k,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)+s.ground_rain_enthalpy_j_m2.sum()
    power=c['external_power_w_m2']+c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
    np.testing.assert_allclose(final-initial,120*power*m.n,atol=1e-4,rtol=1e-10)
    np.testing.assert_allclose(s.vapor_kg_m2.sum()+s.ground_rain_kg_m2.sum()-w.sum(),-120*c['outward_boundary_vapor_kg_m2_s']*m.n,atol=1e-10)
    assert abs(c['dynamics_before_adjustment']['rigid_lid_constraint_pressure_work_w_m2'])<1e-9


def test_constrained_rotation_second_order_against_matrix_exponential():
    from scipy.linalg import expm
    p=[101325,85000,65000,40000];shape=(4,5);f=np.linspace(2e-5,1.2e-4,20).reshape(shape)
    m=RigidLidMoistModel(p,shape,200000,f,phase_enabled=False);u,v=circulation(m);x0=m._velocity(u,v)
    d=m.constraint.toarray();projection=np.eye(len(x0))-d.T@np.linalg.solve(d@d.T,d)
    exact=expm(-3600*projection@m.momentum.toarray()@projection)@x0
    errors=[]
    for dt in [900,450,225]:
        s=m.initial_state(280.,0,u,v)
        for _ in range(3600//dt):s=m.advance(s,dt)
        x=m._velocity(s.u_east,s.v_south);errors.append(np.linalg.norm(x-exact))
        np.testing.assert_allclose(np.dot(x,x),np.dot(x0,x0),rtol=1e-11)
    assert 3.8<errors[0]/errors[1]<4.2
    assert 3.8<errors[1]/errors[2]<4.2


def test_both_archived_reservoir_winds_retained_with_grid_sign():
    lower=np.arange(20).reshape(4,5);upper=lower+10
    u,v=stagger_two_reservoir_wind(lower,lower+1,upper,upper+2,3)
    np.testing.assert_array_equal(u[0,:,0],lower[:,0]);np.testing.assert_array_equal(u[1:,:,0],np.broadcast_to(upper[:,0],(2,4)))
    np.testing.assert_array_equal(u[0,:,1:-1],.5*(lower[:,:-1]+lower[:,1:]))
    np.testing.assert_array_equal(v[0,0],-lower[0]-1);np.testing.assert_array_equal(v[1:,0],np.broadcast_to(-upper[0]-2,(2,5)))
