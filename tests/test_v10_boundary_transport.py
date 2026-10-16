"""Independent open-boundary supply/budget and frozen physics controls."""
from dataclasses import replace
from types import SimpleNamespace
import numpy as np
import pytest
from experiments import v10_boundary_transport as m,v10_regional_transport as model
from experiments import v10_cloud_column_lab as closed
from experiments import v10_boundary_lab as wave_lab
from tests.test_v10_parcel_condensation import cloudy_fixture


def strip(n=32,direction=1):
    mass=np.ones((1,1,n));ids=np.arange(n)
    d=SimpleNamespace(land=np.ones((1,n),bool),dx=1./n,dy=1.)
    g=SimpleNamespace(mass=mass,pressure=np.full_like(mass,90000.),height_m=np.zeros_like(mass))
    flow=m.base.balanced(np.full((1,1,n+1),float(direction)),np.zeros((1,2,n)),d.dx,d.dy)
    return d,g,flow,m.build_mesh(d,g,flow)


@pytest.mark.parametrize('direction',[-1,1])
def test_uniform_state_and_prescribed_inflow_exact(direction):
    d,g,f,mesh=strip(direction=direction)
    c=np.array([np.full(32,300.),np.full(32,.004),np.full(32,-12.)])
    b=c[:,mesh.boundary_cell]
    after,inside,outside,info=m.transport(c,b,mesh,.5/32)
    np.testing.assert_array_equal(after,c)
    incoming=mesh.boundary_rate<0
    expected=.5/32*mesh.boundary_rate*b
    np.testing.assert_array_equal(outside[:,incoming],expected[:,incoming])
    np.testing.assert_allclose(info['incoming_amount'],.5*c[:,0],atol=1e-12,rtol=0)
    np.testing.assert_allclose(info['outgoing_amount'],.5*c[:,0],atol=1e-12,rtol=0)


@pytest.mark.parametrize('direction',[-1,1])
def test_nonuniform_positive_open_tracers_conserve_against_independent_edge_budget(direction):
    d,g,f,mesh=strip(direction=direction);rng=np.random.default_rng(619)
    mesh=replace(mesh,mass=rng.uniform(.7,1.5,32))
    theta=rng.uniform(280.,320.,32);c=np.array([theta,.002+.00001*(theta-280.)])
    b=np.array([np.full(len(mesh.boundary_cell),310.),np.full(len(mesh.boundary_cell),.0023)])
    initial=c.copy();dt=.4*mesh.mass.min()/32
    after,inside,outside,info=m.transport(c,b,mesh,dt)
    inflow_face=0 if direction==1 else 1
    old_out=initial[:, -1 if direction==1 else 0]
    expected_input=dt*32*b[:,inflow_face];expected_output=dt*32*old_out
    np.testing.assert_allclose(np.sum(mesh.mass*(after-initial),axis=1),expected_input-expected_output,atol=1e-10,rtol=0)
    np.testing.assert_allclose(info['incoming_amount'],expected_input,atol=1e-12,rtol=0)
    np.testing.assert_allclose(info['outgoing_amount'],expected_output,atol=1e-12,rtol=0)
    np.testing.assert_allclose(after[1],.002+.00001*(after[0]-280.),atol=1e-16,rtol=0)
    assert after[1].min()>=0


def test_corner_counts_two_incoming_faces_once_each():
    # Four separate face contributions at a corner, never a ghost cell store.
    n=3;mass=np.ones((1,n,n));d=SimpleNamespace(land=np.ones((n,n),bool),dx=1.,dy=1.)
    g=SimpleNamespace(mass=mass)
    f=m.base.balanced(np.ones((1,n,n+1)),np.ones((1,n+1,n)),1.,1.)
    mesh=m.build_mesh(d,g,f);c=np.array([np.full(n*n,300.),np.zeros(n*n)])
    b=np.array([np.full(len(mesh.boundary_cell),300.),np.full(len(mesh.boundary_cell),.01)])
    after,_,outside,info=m.transport(c,b,mesh,.2)
    assert info['incoming_amount'][1]==pytest.approx(.2*6*.01,abs=1e-16)
    assert after[1,0]>0
    np.testing.assert_allclose(np.sum(mesh.mass*(after-c),axis=1)+outside.sum(1),0,atol=1e-12,rtol=0)


def test_external_flux_recovers_frozen_upwind_without_changing_supply():
    d,g,f,mesh=strip();c=np.array([np.linspace(290.,310.,32),np.linspace(.001,.008,32)])
    b=c[:,mesh.boundary_cell].copy();b[:,0]=[320.,.009]
    # Analytic donor-cell outgoing/incoming amounts, independent of FCT budget.
    dt=.5/32;after,inside,outside,info=m.transport(c,b,mesh,dt)
    expected=dt*mesh.boundary_rate*np.where(mesh.boundary_rate<0,b,c[:,mesh.boundary_cell])
    np.testing.assert_array_equal(outside,expected)
    assert info['maximum_courant']==pytest.approx(.5)


@pytest.mark.parametrize('layers',[4,32,128])
def test_closed_thermal_kernel_matches_saved_candidate(layers):
    d,g,state,f=closed.fixture(layers)
    t=m.base.temperature(state.energy,g.mass,state.water,g.height_m)
    dt=min(60.,m.base.stable_step(f,g.mass,d))
    old=m.parent.thermal_transport(state,f,dt,d,g,t,np.zeros_like(g.mass))
    new=m.thermal_transport(state,f,dt,d,g,t,np.zeros_like(g.mass))
    for i in range(6):
        # Work subtracts O(1e7) energy stores; a few ULPs are not a new source.
        tolerance=4*np.spacing(abs(state.energy).max()) if i==4 else 1e-9
        np.testing.assert_allclose(old[i],new[i],atol=tolerance,rtol=1e-13)
    assert abs(new[6])<1e-7


@pytest.mark.parametrize('mode',['bulk','parcel_lower','parcel_all'])
@pytest.mark.parametrize('physics',[False,True])
def test_upwind_regional_adapter_delegates_exactly_and_fct_closes_ledgers(mode,physics):
    case,p,s,g,air,state,f,q=cloudy_fixture();dt=60.
    old=model.original.advance(state,case.domain,p,s,f,dt,0.,air,physics=physics,geometry=g,boundary=q,condensation_mode=mode)
    control=model.advance(state,case.domain,p,s,f,dt,0.,air,physics=physics,geometry=g,boundary=q,condensation_mode=mode,transport_scheme='upwind')
    for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(old[0],name),getattr(control[0],name))
    for i in (1,2,3,5,6,8):np.testing.assert_array_equal(old[i],control[i])
    assert old[4]==control[4] and old[7]==control[7]
    candidate=model.advance(state,case.domain,p,s,f,dt,0.,air,physics=physics,geometry=g,boundary=q,condensation_mode=mode)
    assert candidate[0].water.min()>=0 and candidate[0].soil.min()>=0
    assert abs(candidate[4]['water_error_mm'])<1e-9 and abs(candidate[4]['energy_error_j_m2'])<1e-5
    assert candidate[7]<1e-9


def test_invalid_open_continuity_and_negative_boundary_rejected():
    d,g,f,mesh=strip();bad=mesh.boundary_rate.copy();bad[0]*=2
    with pytest.raises(ValueError,match='continuity'):replace(mesh,boundary_rate=bad).validate()
    c=np.ones((2,32));b=np.ones((2,len(mesh.boundary_cell)));b[1,0]=-1
    with pytest.raises(ValueError,match='nonnegative'):m.transport(c,b,mesh,.5/32)


@pytest.mark.parametrize('direction',[-1,1])
@pytest.mark.parametrize('cells',[16,32,64])
def test_exact_open_wave_supply_and_independent_heat_budget(cells,direction):
    old=wave_lab.wave(cells,'upwind',direction);new=wave_lab.wave(cells,'coupled_fct',direction)
    assert new['gross_incoming_vapor']==old['gross_incoming_vapor']
    assert new['gross_incoming_vapor']==pytest.approx(.004,abs=1e-15)
    assert new['theta_mae_k']<old['theta_mae_k']
    assert abs(new['water_error'])<1e-11 and abs(new['energy_error'])<1e-6
