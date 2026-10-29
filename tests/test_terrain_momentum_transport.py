import numpy as np
import pytest
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_work import project_column_mass
from rotclimate.terrain_momentum_transport import momentum_transport


def vortex(n):
    length=224000.;dx=length/n;k=np.pi/length;amplitude=2.;center=(np.arange(n)+.5)*dx;face=np.arange(1,n)*dx
    grid=terrain_pressure_grid(np.full((n,n),101325.),[1,0]);u=(amplitude*np.cos(k*center)[:,None]*np.sin(k*face)[None,:])[None,None];v=(-amplitude*np.sin(k*face)[:,None]*np.cos(k*center)[None,:])[None,None]
    return grid,u,v,dx,k,amplitude,center,face


def test_manufactured_vortex_nonlinear_acceleration_converges_at_second_order():
    errors=[]
    for n in [12,24,48]:
        grid,u,v,dx,k,amplitude,center,face=vortex(n);operator=momentum_transport(grid,u,v,dx);ue,vs=operator.acceleration();ue=ue.reshape(n,n-1);vs=vs.reshape(n-1,n)
        exact_u=np.broadcast_to(-.5*amplitude**2*k*np.sin(2*k*face)[None,:],ue.shape);exact_v=np.broadcast_to(-.5*amplitude**2*k*np.sin(2*k*face)[:,None],vs.shape)
        error=np.sqrt(np.mean((ue[2:-2,2:-2]-exact_u[2:-2,2:-2])**2)+np.mean((vs[2:-2,2:-2]-exact_v[2:-2,2:-2])**2));errors.append(error)
    assert errors[0]/errors[1]>3.4 and errors[1]/errors[2]>3.4
    assert errors[-1]<2e-7


@pytest.mark.parametrize('seed',[2,51,73])
def test_irregular_terrain_momentum_transport_does_no_spurious_kinetic_work(seed):
    rng=np.random.default_rng(seed);height=rng.uniform(0,4500,(4,5));grid=terrain_pressure_grid(surface_pressure_from_height(height,288.15),[1,.9,.65,.3,0]);a=horizontal_apertures(grid);u,v,_=project_column_mass(grid,rng.normal(0,5,a.east_kg_m2.shape),rng.normal(0,5,a.south_kg_m2.shape),56000.);operator=momentum_transport(grid,u,v,56000.);x=operator.weighted_velocity
    assert (operator.weighted_operator_s+operator.weighted_operator_s.T).nnz==0
    actual_work=float(x@(operator.weighted_operator_s@x));scale=max(float(np.sum(abs(x)*abs(operator.weighted_operator_s@x))),1.)
    assert abs(actual_work)<1e-14*scale


def test_reversing_wind_keeps_advective_acceleration_and_flips_transport_operator():
    grid,u,v,dx,*_=vortex(12);forward=momentum_transport(grid,u,v,dx);reverse=momentum_transport(grid,-u,-v,dx)
    np.testing.assert_allclose(forward.weighted_operator_s.toarray(),-reverse.weighted_operator_s.toarray(),atol=1e-18)
    for a,b in zip(forward.acceleration(),reverse.acceleration()):np.testing.assert_array_equal(a,b)


def test_zero_wind_has_zero_advective_acceleration():
    grid,u,v,dx,*_=vortex(8);operator=momentum_transport(grid,0*u,0*v,dx)
    assert operator.weighted_operator_s.nnz==0
    assert not operator.acceleration()[0].any() and not operator.acceleration()[1].any()
