"""Independent N-level donor fluxes, continuity and old two-layer limits."""
import numpy as np
import pytest
from rotclimate.multilevel_transport import solve_multilevel
from rotclimate.regional_baroclinic import RegionalMode,mass_divergence,embed_two_layers
from rotclimate.regional_mode_tracer import solve_mode_tracer
from rotclimate.vertical_state import build_vertical_state,stable_reference


def test_two_level_limit_matches_prior_native_face_tracer():
    ny,nx=5,7;j,i=np.mgrid[:ny,:nx];mass=9000*(1-.3*np.exp(-((i-3)**2+(j-2)**2)/3));dx=1e5
    u=np.zeros((ny,nx+1));u[:,1:-1]=np.sin(np.pi*np.arange(1,nx)/nx)
    v=np.zeros((ny+1,nx));mode=RegionalMode(u,v,np.zeros_like(mass),mass_divergence(u,v,mass,dx),{})
    old=solve_mode_tracer(mode,mass,dx,[1e-5,2e-6],1/(8*86400.),[.009,.0025])
    layers=embed_two_layers(mode);m=np.stack([.25*mass,.75*mass])
    new=solve_multilevel(m,np.stack([layers['lower_u_east'],layers['upper_u_east']]),
        np.stack([layers['lower_v_south'],layers['upper_v_south']]),dx,[1e-5,2e-6],1/(8*86400.),[.009,.0025])
    np.testing.assert_allclose(new.amount,old.water,rtol=1e-12,atol=1e-10)
    np.testing.assert_allclose(new.upward_tracer_flux[0],old.upward_water_flux,rtol=1e-12,atol=1e-14)


@pytest.mark.parametrize('nz',[4,16])
def test_constant_mixing_ratio_is_preserved_with_stratified_mass_and_overturning(nz):
    edges=np.linspace(0,15000,nz+1);ref=stable_reference(.5*(edges[:-1]+edges[1:]))
    col=build_vertical_state(edges,ref.density_kg_m3,np.full(nz-1,.0001))
    ny,nx=5,7;mass=np.broadcast_to(col.cell_mass_kg_m2[:,None,None],(nz,ny,nx)).copy();dx=1e5
    u=np.zeros((nz,ny,nx+1));u[:,:,1:-1]=col.pressure_modes[:,0,None,None]*np.sin(np.pi*np.arange(1,nx)/nx)[None,None,:]
    v=np.zeros((nz,ny+1,nx));q=.007;rate=1/(5*86400.)
    out=solve_multilevel(mass,u,v,dx,rate*q*mass,rate,q)
    np.testing.assert_allclose(out.amount,q*mass,rtol=1e-12,atol=1e-10)
    assert out.certificate['maximum_relative_dry_column_mass_residual']<1e-12


def test_nonuniform_manufactured_donors_switch_at_each_interface_and_close_budgets():
    nz,ny,nx=3,2,2;dx=1e5
    mass=np.broadcast_to(np.array([1000.,3000.,5000.])[:,None,None],(nz,ny,nx)).copy()
    speeds=np.array([-3.,2.,-.6]);u=np.zeros((nz,ny,nx+1));u[:,:,1]=speeds[:,None];v=np.zeros((nz,ny+1,nx))
    water=np.array([[[3.,8.],[7.,2.]],[[20.,5.],[15.,9.]],[[5.,30.],[10.,4.]]]);q=water/mass
    fx=np.zeros_like(u)
    for k in range(nz):fx[k,:,1]=mass[k,:,0]*speeds[k]*q[k,:,0 if speeds[k]>=0 else 1]
    dry=np.diff(mass[:,:,:1]*u,axis=2)/dx
    up=-np.cumsum(dry,axis=0)[:-1]
    vertical=up*np.where(up>=0,q[:-1],q[1:])
    vf=np.concatenate([np.zeros_like(water[:1]),vertical,np.zeros_like(water[:1])])
    rate=1e-3;source=rate*water+np.diff(fx,axis=2)/dx+np.diff(vf,axis=0)
    assert np.all(source>0)
    out=solve_multilevel(mass,u,v,dx,source,rate,.01)
    np.testing.assert_allclose(out.amount,water,rtol=1e-12,atol=1e-11)
    np.testing.assert_allclose(out.east_tracer_flux,fx,rtol=1e-12,atol=1e-11)
    np.testing.assert_allclose(out.upward_tracer_flux,vertical,rtol=1e-12,atol=1e-14)
    assert np.any(up>0) and np.any(up<0)
    assert abs(out.certificate['actual_column_budget_error_cell_s'])<1e-14


def test_four_uniform_flows_match_independent_layer_upwind_recurrences():
    nz,ny,nx=4,3,8;dx=1e5;mass=np.full((nz,ny,nx),2000.)
    speed=np.array([-3.,-1.,1.,3.]);u=np.broadcast_to(speed[:,None,None],(nz,ny,nx+1)).copy();v=np.zeros((nz,ny+1,nx))
    outside=np.array([.009,.007,.004,.002]);rate=1/(3*86400.)
    out=solve_multilevel(mass,u,v,dx,0.,rate,outside)
    for k,s in enumerate(speed):
        steps=np.arange(nx,0,-1) if s<0 else np.arange(1,nx+1)
        expected=2000*outside[k]*(abs(s)/(abs(s)+rate*dx))**steps
        np.testing.assert_allclose(out.amount[k],np.broadcast_to(expected,(ny,nx)),rtol=1e-12)
    np.testing.assert_array_equal(out.upward_dry_mass_flux,0.)


@pytest.mark.parametrize('changes',[dict(source=-1),dict(reaction_rate=0),dict(external_mixing_ratio=-1)])
def test_invalid_scalar_equation_rejected(changes):
    args=dict(layer_mass=np.ones((3,2,2)),u_east=0.,v_south=0.,cell_m=1e5,source=0.,reaction_rate=1e-5,external_mixing_ratio=.01)
    args.update(changes)
    with pytest.raises(ValueError):solve_multilevel(**args)


def test_unbalanced_dry_column_is_not_fixed_by_fake_vertical_air_source():
    mass=np.ones((3,2,2));u=np.zeros((3,2,3));u[:,:,1]=1.
    with pytest.raises(ValueError,match='dry-column'):
        solve_multilevel(mass,u,0.,1e5,0.,1e-5,.01)
