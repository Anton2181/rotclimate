import numpy as np
import pytest
from rotclimate.pressure_moist import PressureMoistModel
from rotclimate.pressure_boundary import BoundaryPressureMoistModel,baroclinic_lower_wind_seed
from rotclimate.momentum_initialization import least_acceleration_wind,initial_transport_tendency


def setup(boundary=False):
    p=[101325,85000,65000,40000];shape=(4,5);f=np.linspace(5e-5,1e-4,20).reshape(shape)
    base=PressureMoistModel(p,shape,200000.,f,momentum_drag_s=1/(5*86400))
    t=np.broadcast_to(np.array([290.,270.,245.])[:,None,None],base.mass.shape).copy()
    t+=np.arange(20).reshape(shape)[None]*.2
    u,v=baroclinic_lower_wind_seed(np.ones(shape)*2,np.ones(shape),base.column.cell_mass_kg_m2)
    ub=np.zeros_like(u);vb=np.zeros_like(v)
    if boundary:ub[:,:,[0,-1]]=u[:,:,[0,-1]];vb[:,[0,-1]]=v[:,[0,-1]]
    else:u[:,:,[0,-1]]=0;v[:,[0,-1]]=0
    model=BoundaryPressureMoistModel(p,shape,200000.,f,u_boundary=ub,v_boundary=vb,momentum_drag_s=base.r) if boundary else base
    return model,t,u,v


@pytest.mark.parametrize('boundary',[False,True])
def test_actual_quadratic_optimum_and_mass_constraint(boundary):
    model,t,u,v=setup(boundary);ref=model._velocity(u,v);tau=21600.
    result=least_acceleration_wind(model,t,u,v,correction_time_s=tau)
    x=model._velocity(result.u_east,result.v_south);a=model.momentum.toarray()
    b=model._pressure_force(t)+getattr(model,'boundary_rotation_force',0.)
    # Independent dense linear algebra checks the unique minimum, including
    # prescribed-boundary rotation. No test assumes residual vanishes.
    expected=np.linalg.solve(np.eye(len(ref))+tau*tau*a.T@a,ref-tau*tau*a.T@b)
    np.testing.assert_allclose(x,expected,rtol=1e-11,atol=1e-10)
    assert result.certificate['new_objective']<=result.certificate['old_objective']
    for flow in [result.u_east,result.v_south]:
        np.testing.assert_allclose(np.sum(model.column.cell_mass_kg_m2[:,None,None]*flow,axis=0),0,atol=1e-8)


def test_tradeoff_curve_and_small_correction_limit():
    model,t,u,v=setup();results=[least_acceleration_wind(model,t,u,v,correction_time_s=tau) for tau in [.001,3600,21600,86400]]
    residual=[r.certificate['final_mass_weighted_acceleration_norm'] for r in results]
    correction=[r.certificate['velocity_correction_mass_weighted_norm'] for r in results]
    assert np.all(np.diff(residual)<=0);assert np.all(np.diff(correction)>=0)
    np.testing.assert_allclose(results[0].u_east,u,atol=1e-9)
    np.testing.assert_allclose(results[0].v_south,v,atol=1e-9)


def test_uniform_rest_is_unchanged_and_inputs_preserved():
    model,t,u,v=setup();t=np.broadcast_to(t[:,:1,:1],t.shape).copy();u*=0;v*=0
    before=t.copy();r=least_acceleration_wind(model,t,u,v,correction_time_s=86400)
    np.testing.assert_array_equal(r.u_east,u);np.testing.assert_array_equal(r.v_south,v);np.testing.assert_array_equal(t,before)
    assert r.certificate['kinetic_energy_change_j_m2']==0


@pytest.mark.parametrize('tau',[0,-1,float('inf'),float('nan')])
def test_bad_timescale_rejected(tau):
    model,t,u,v=setup()
    with pytest.raises(ValueError):least_acceleration_wind(model,t,u,v,correction_time_s=tau)


def test_initial_transport_uniform_donor_limit():
    p=[101325,85000,65000,40000];shape=(4,5)
    masses=-np.diff(p)/9.80665;u,v=baroclinic_lower_wind_seed(np.ones(shape)*2,np.ones(shape),masses)
    ub=np.zeros_like(u);vb=np.zeros_like(v);ub[:,:,[0,-1]]=u[:,:,[0,-1]];vb[:,[0,-1]]=v[:,[0,-1]]
    model=BoundaryPressureMoistModel(p,shape,200000,1e-4,u_boundary=ub,v_boundary=vb,external_temperature_k=280,external_mixing_ratio=.005)
    r=initial_transport_tendency(model,np.full(model.mass.shape,280.),model.mass*.005,u,v)
    np.testing.assert_allclose(r['temperature_k_s'],0,atol=1e-15)
    np.testing.assert_allclose(r['vapor_kg_m2_s'],0,atol=1e-15)


def test_initial_transport_actual_regional_energy_and_water_tendency():
    model,t,u,v=setup(True);w=model.mass*.005
    result=initial_transport_tendency(model,t,w,u,v)
    x=model._velocity(u,v);force=model._pressure_force(t)+model.boundary_rotation_force
    dk=float(-np.dot(x,model.momentum@x+force))
    outward_phi=model._geopotential_boundary_flux(t)
    rotation=float(-np.dot(x,model.boundary_rotation_force))
    np.testing.assert_allclose(result['gas_enthalpy_w_m2'].sum()+dk,
        -result['outward_gas_enthalpy_w_m2']*model.n-outward_phi+rotation,rtol=1e-12,atol=1e-8)
    np.testing.assert_allclose(result['vapor_kg_m2_s'].sum(),-result['outward_vapor_kg_m2_s']*model.n,atol=1e-13)
    dh=(1004*model.mass+1850*w)*result['temperature_k_s']+(2.5e6+1850*(t-273.15))*result['vapor_kg_m2_s']
    np.testing.assert_allclose(dh,result['gas_enthalpy_w_m2'],rtol=1e-12,atol=1e-8)
