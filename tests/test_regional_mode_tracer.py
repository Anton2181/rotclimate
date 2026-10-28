"""Known donor-transport limits without centering staggered circulation winds."""
import numpy as np
import pytest
from rotclimate.regional_baroclinic import RegionalMode, mass_divergence, solve_regional_mode
from rotclimate.regional_mode_tracer import solve_mode_tracer

SCALES=dict(wave_speed_ms=50.,momentum_drag_s=1/(5*86400.),thermal_drag_s=1/(20*86400.))


def mode_from_faces(u,v,mass,dx):
    return RegionalMode(u,v,np.zeros_like(mass),mass_divergence(u,v,mass,dx),{})


def test_stagnant_independent_boxes_have_source_over_loss_solution():
    mass=np.full((4,6),10000.)
    mode=mode_from_faces(np.zeros((4,7)),np.zeros((5,6)),mass,100000.)
    source=np.stack([np.full(mass.shape,.0002),np.full(mass.shape,.0001)])
    loss=[1/(2*86400.),1/(8*86400.)]
    out=solve_mode_tracer(mode,mass,100000.,source,loss,[.01,.005])
    np.testing.assert_allclose(out.water,source/np.array(loss)[:,None,None],rtol=1e-13)
    np.testing.assert_array_equal(out.upward_water_flux,0.)


def test_opposing_uniform_flow_matches_two_independent_upwind_recurrences():
    ny,nx=4,9;dx=100000.;mass=np.full((ny,nx),10000.)
    mode=mode_from_faces(np.ones((ny,nx+1)),np.zeros((ny+1,nx)),mass,dx)
    rate=1/(3*86400.);external=np.array([.012,.003])
    out=solve_mode_tracer(mode,mass,dx,0.,rate,external)
    lower=.25*10000*external[0]*(.75/(.75+rate*dx))**np.arange(nx,0,-1)
    upper=.75*10000*external[1]*(.25/(.25+rate*dx))**np.arange(1,nx+1)
    np.testing.assert_allclose(out.water[0],np.broadcast_to(lower,(ny,nx)),rtol=1e-12)
    np.testing.assert_allclose(out.water[1],np.broadcast_to(upper,(ny,nx)),rtol=1e-12)
    np.testing.assert_array_equal(out.upward_water_flux,0.)


def test_variable_mass_and_boundaries_preserve_uniform_mixing_ratio():
    j,i=np.mgrid[:9,:13];dx=100000.;mass=10000*(1-.5*np.exp(-((i-7)**2+(j-4)**2)/5))
    heating=.0008*np.exp(-((i-6)**2+(j-5)**2)/8)
    mode=solve_regional_mode(heating,dx,7e-5,column_mass=mass,
        boundaries=dict(east='impedance',west='impedance'),**SCALES)
    q=.008;water=np.stack([.25*mass*q,.75*mass*q]);loss=1/(5*86400.)
    out=solve_mode_tracer(mode,mass,dx,loss*water,loss,q)
    np.testing.assert_allclose(out.water,water,rtol=1e-12,atol=1e-10)
    assert out.upward_water_flux[5,6]>0
    assert out.certificate['maximum_dry_column_face_flux_residual']==0


def test_manufactured_nonuniform_water_uses_lower_and_upper_donors_and_boundary_faces():
    # One internal face transports east aloft, west below, causing ascent in
    # left cells and descent in right cells. No exterior flow in this case.
    dx=100000.;mass=np.array([[8000.,6000.],[10000.,7000.]])
    u=np.zeros((2,3));u[:,1]=2.;v=np.zeros((3,2))
    mode=mode_from_faces(u,v,mass,dx)
    water=np.array([[[20.,30.],[40.,50.]],[[5.,8.],[13.,21.]]])
    ml=np.stack([.25*mass,.75*mass]);q=water/ml
    mf=.5*(mass[:,0]+mass[:,1]);fl=-.25*.75*mf*2.;fu=-fl
    # Horizontal lower donor on right; upper donor on left.
    wx=np.zeros((2,2,3));wx[0,:,1]=fl*q[0,:,1];wx[1,:,1]=fu*q[1,:,0]
    up=.25*.75*mass*mode.divergence_per_s
    donor=np.where(up>=0,q[0],q[1]);vertical=up*donor
    rate=1e-4
    source=rate*water+np.diff(wx,axis=2)/dx+np.stack([vertical,-vertical])
    assert np.all(source>0)
    out=solve_mode_tracer(mode,mass,dx,source,rate,.01)
    np.testing.assert_allclose(out.water,water,rtol=1e-12,atol=1e-11)
    np.testing.assert_allclose(out.east_water_flux,wx,rtol=1e-12,atol=1e-11)
    np.testing.assert_allclose(out.upward_water_flux,vertical,rtol=1e-12,atol=1e-14)
    assert np.all(out.upward_water_flux[:,0]>0)
    assert np.all(out.upward_water_flux[:,1]<0)


def test_actual_boundary_and_layer_budgets_close_for_different_humidities():
    j,i=np.mgrid[:10,:14];mass=10000*(.5+.5*i/13);dx=80000.
    mode=solve_regional_mode(.001*np.exp(-((i-7)**2+(j-5)**2)/10),dx,7e-5,
        column_mass=mass,boundaries=dict(west='impedance',east='impedance',north='impedance',south='impedance'),**SCALES)
    source=np.zeros((2,)+mass.shape);source[0]=.00002
    out=solve_mode_tracer(mode,mass,dx,source,1/(7*86400.),[.01,.002])
    wx,wy=out.east_water_flux,out.south_water_flux
    outward=(wx[:,:,-1].sum(1)-wx[:,:,0].sum(1)+wy[:,-1].sum(1)-wy[:,0].sum(1))/dx
    balance=source.sum((1,2))-out.removal.sum((1,2))-outward
    np.testing.assert_allclose(balance,[out.upward_water_flux.sum(),-out.upward_water_flux.sum()],atol=1e-14)
    assert abs(balance.sum())<1e-14
    assert np.min(out.water)>=0
    # Lower and upper tracer humidity are solved independently.
    mixing=out.water/np.stack([.25*mass,.75*mass])
    assert np.ptp(mixing[1]/mixing[0])>.01


@pytest.mark.parametrize('changes',[dict(removal_rate=0),dict(source=-1),dict(external_mixing_ratio=-.1)])
def test_invalid_tracer_problem_rejected(changes):
    mass=np.ones((3,4));mode=mode_from_faces(np.zeros((3,5)),np.zeros((4,4)),mass,1e5)
    args=dict(source=0.,removal_rate=1e-5,external_mixing_ratio=.01);args.update(changes)
    with pytest.raises(ValueError):solve_mode_tracer(mode,mass,1e5,**args)


def test_stale_mass_divergence_is_rejected_before_transport():
    mass=np.ones((3,4));u=np.zeros((3,5));u[:,1:4]=1.
    mode=mode_from_faces(u,np.zeros((4,4)),mass,1e5)
    with pytest.raises(ValueError,match='inconsistent'):
        solve_mode_tracer(mode,mass,2e5,0.,1e-5,.01)
