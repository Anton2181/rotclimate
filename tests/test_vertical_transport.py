"""Independent continuity, conservation and known-equilibrium operator checks."""
import numpy as np
import pytest
from rotclimate.column_mass import ColumnMassProjection

from experiments.two_reservoir_transport import VerticalTransport


def setup_case(seed=26):
    rng=np.random.default_rng(seed);shape=(8,11);dx=56000.;eta=.25
    projection=ColumnMassProjection(rng.uniform(0,3500,shape),dx)
    ul,vl=rng.normal(size=(2,)+shape)*3
    ub,vb,_=projection.project(ul,vl)
    uu,vu=(ub-eta*ul)/(1-eta),(vb-eta*vl)/(1-eta)
    return VerticalTransport(projection.mass,(ul,vl),(uu,vu),dx,mixing_rate=1/86400.)


def test_uniform_mixing_ratio_is_equilibrium_in_each_layer_over_terrain():
    op=setup_case();water=12*op.layer_mass
    terms,boundary=op.terms(water,diffusion=60000.)
    assert np.max(np.abs(terms))<1e-17
    np.testing.assert_allclose(boundary.sum(),0,atol=1e-17)
    solved,certificate=op.solve(water*1e-5,1e-5,water,diffusion=60000.)
    np.testing.assert_allclose(solved,water,atol=1e-12)
    assert certificate['max_scaled_dry_column_residual']<1e-12


@pytest.mark.parametrize('seed',[3,4,5])
def test_actual_matrix_matches_independent_donor_faces_and_vertical_ledger(seed):
    op=setup_case(seed);rng=np.random.default_rng(seed);water=rng.uniform(.1,12,(2,)+op.shape)
    reaction=rng.uniform(1e-6,2e-5,water.shape);K=60000.
    tendency=[];boundaries=[];dry=[]
    for m,(u,v),w in zip(op.layer_mass,op.winds,water):
        uf=.5*(u[:,1:]+u[:,:-1]);vf=-.5*(v[1:]+v[:-1]);q=w/m
        mf=.5*(m[:,1:]+m[:,:-1]);nf=.5*(m[1:]+m[:-1])
        east=mf*(uf*np.where(uf>=0,q[:,:-1],q[:,1:])-K*np.diff(q,axis=1)/op.dx)
        south=nf*(vf*np.where(vf>=0,q[:-1],q[1:])-K*np.diff(q,axis=0)/op.dx)
        tendency.append(-(np.diff(east,axis=1)[1:-1]+np.diff(south,axis=0)[:,1:-1])/op.dx)
        boundaries.append((east[1:-1,0].sum()-east[1:-1,-1].sum()+south[0,1:-1].sum()-south[-1,1:-1].sum())/op.dx)
        dry.append((np.diff(mf*uf,axis=1)[1:-1]+np.diff(nf*vf,axis=0)[:,1:-1])/op.dx)
    upward=-dry[0];ql,qu=(water/op.layer_mass)[:,1:-1,1:-1]
    conductance=op.mass[1:-1,1:-1]*.25*.75/86400.
    flux=np.maximum(upward,0)*ql+np.minimum(upward,0)*qu+conductance*(ql-qu)
    expected=np.stack(tendency)+np.stack([-flux,flux])
    actual=(op.matrix(reaction,K)@water.ravel()).reshape(water.shape)
    np.testing.assert_allclose(actual[:,1:-1,1:-1],reaction[:,1:-1,1:-1]*water[:,1:-1,1:-1]-expected,atol=1e-18)
    np.testing.assert_allclose(expected.sum(),sum(boundaries),atol=1e-17)
    matrix=op.matrix(reaction,K);diagonal=matrix.diagonal();off=matrix.copy();off.setdiag(0)
    assert (diagonal>0).all() and (off.data<=0).all()


def test_vertical_convergence_moistens_upper_reservoir_without_column_water_source():
    shape=(7,11);dx=1e5;eta=.25;x=np.arange(shape[1])-5
    u=np.tile(-x,(shape[0],1));v=np.zeros(shape)
    op=VerticalTransport(np.ones(shape),(u,v),(-u/3,v),dx)
    water=op.layer_mass*np.array([2.,.5])[:,None,None]
    tendency,boundary=op.terms(water)
    # All lower-layer horizontal import rises upward locally; upper water
    # increases at exactly F*(q_lower-q_upper), not an imposed dry return.
    np.testing.assert_allclose(tendency[0],0,atol=1e-19)
    np.testing.assert_allclose(tendency[1],eta/dx*(2-.5),atol=1e-19)
    np.testing.assert_allclose(tendency.sum(),boundary.sum(),atol=1e-18)


def test_surface_source_yields_positive_variable_layer_humidity_and_exact_budget():
    op=setup_case();source=np.zeros((2,)+op.shape)
    source[0]=1e-4;boundary=2*op.layer_mass;reaction=np.zeros_like(source)+2e-5
    reaction[1]*=2
    water,cert=op.solve(source,reaction,boundary,diffusion=60000.)
    terms,supply=op.terms(water,diffusion=60000.)
    np.testing.assert_allclose(source[:,1:-1,1:-1]+terms,reaction[:,1:-1,1:-1]*water[:,1:-1,1:-1],atol=1e-18)
    np.testing.assert_allclose((source-reaction*water)[:,1:-1,1:-1].sum()+supply.sum(),0,atol=1e-17)
    assert np.ptp((water[1]/op.layer_mass[1])/(water[0]/op.layer_mass[0]))>.05
    assert cert['minimum_water_mm']>0


@pytest.mark.parametrize('bad',[np.nan,-1.])
def test_invalid_mixing_rejected(bad):
    shape=(5,5);zero=np.zeros(shape)
    with pytest.raises(ValueError,match='Mixing'):
        VerticalTransport(np.ones(shape),(zero,zero),(zero,zero),1e5,mixing_rate=bad)


def test_inconsistent_dry_mass_cannot_be_hidden_in_vertical_transfer():
    shape=(5,7);u=np.tile(np.arange(7),(5,1));zero=np.zeros(shape)
    with pytest.raises(ValueError,match='dry-column'):
        VerticalTransport(np.ones(shape),(u,zero),(zero,zero),1e5)
