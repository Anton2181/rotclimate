"""Known uniform-q equilibria and independent mass-aware flux identities."""
import numpy as np
import pytest
from scipy.ndimage import gaussian_filter
from rotclimate.column_mass import ColumnMassProjection
from rotclimate.layer_transport import LayerFluxSolver,return_branches
from rotclimate.storms import conservative_exchange
from rotclimate.transport import vapor_face_fluxes,face_divergence,moisture_terms,flux_budget


@pytest.mark.parametrize('layered',[False,True])
def test_uniform_specific_humidity_survives_terrain_advection_diffusion_and_storms(layered):
    terrain=np.tile(np.linspace(0,4000,11),(9,1));p=ColumnMassProjection(terrain,56000)
    u=np.full_like(terrain,6.);v=np.zeros_like(terrain);ub,vb,_=p.project(u,v)
    # Equal specific humidity in both branches makes W/M a passive tracer.
    if layered:layers,eu,ev=return_branches(u,v,ub,vb,1.)
    else:layers=((1.,ub,vb),);eu,ev=ub,vb
    W=10*p.mass
    old=face_divergence(*vapor_face_fluxes(W,eu,ev,layers=layers),56000)*86400
    assert abs(old).max()>1e-3  # old conservative column-W donors still drift
    loss,mix=conservative_exchange(np.full_like(W,1e-5),lambda a:gaussian_filter(a,1,mode='reflect'),p.mass)
    np.testing.assert_allclose(mix(W),W,atol=1e-13)
    solver=LayerFluxSolver(*W.shape,56000,column_mass=p.mass);solver.set_layers(layers)
    terms=moisture_terms(W,eu,ev,56000,60000,0,0,loss,mix(W),form='flux',layers=layers,mass=p.mass)
    assert np.nanmax(np.abs(terms['residual']))<1e-12
    solver.rtol=1e-11;solver.require_convergence=True;solver.max_iter=2000
    result=solver.solve(eu,ev,60000,1e-5,W*1e-5,W)
    np.testing.assert_allclose(result,W,atol=1e-8)


@pytest.mark.parametrize('seed',[151,152,153])
def test_mass_operator_equals_actual_local_and_boundary_fluxes(seed):
    rng=np.random.default_rng(seed);mass=rng.uniform(.3,1,(7,9));W=rng.uniform(1,30,mass.shape)
    u,v,ub,vb=rng.normal(size=(4,)+mass.shape)*5
    layers,eu,ev=return_branches(u,v,ub,vb,.2)
    solver=LayerFluxSolver(*mass.shape,56000,column_mass=mass);solver.set_layers(layers)
    ce,cw,cs,cn,d=solver.coefficients(eu,ev,60000,0)
    operator=d[1:-1,1:-1]*W[1:-1,1:-1]+ce[1:-1,1:-1]*W[1:-1,2:]+cw[1:-1,1:-1]*W[1:-1,:-2]+cs[1:-1,1:-1]*W[2:,1:-1]+cn[1:-1,1:-1]*W[:-2,1:-1]
    terms=moisture_terms(W,eu,ev,56000,60000,0,0,0,W,form='flux',layers=layers,mass=mass)
    np.testing.assert_allclose((terms['advection']+terms['diffusion'])[1:-1,1:-1],-86400*operator,atol=1e-12)
    assert all((a<=0).all() for a in [ce,cw,cs,cn]) and (d>=0).all()
    budget=flux_budget(W,eu,ev,56000,60000,0,np.zeros_like(W),0,W,layers=layers,mass=mass)
    assert budget['transport_relative_cancellation']<1e-13


@pytest.mark.parametrize('updates',[dict(moisture_mass_tracer='yes'),dict(moisture_mass_tracer=True),
    dict(moisture_mass_tracer=True,moisture_mass_balance=True,moisture_transport_form='flux',flux_convergence=0,
         eddy_moisture_height_km=2)])
def test_unsupported_or_ambiguous_mass_profile_rejected(updates):
    from rotclimate.model import ClimateModel
    from rotclimate.config import Params
    with pytest.raises(ValueError):ClimateModel(Params(**updates))


def test_coupled_two_branch_mass_tracer_keeps_actual_nonlinear_water_certificate():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case=_toy_case();p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',flux_convergence=0,
        eddy_moisture_scheme='conservative',moisture_mass_balance=True,moisture_two_layer=True,subsidence_drying=.05),case)
    a=ClimateModel(p,grid=case.grid).run()
    assert 'mass_tracer_transport' not in a.numerics
    b=ClimateModel(p.replace(moisture_mass_tracer=True),grid=case.grid).run(diagnose_moisture=True)
    assert b.numerics['all_checks_passed'] and b.numerics['mass_tracer_transport']['mass_aware_advection_diffusion_storms']
    assert b.numerics['vapor_flux_budget']['max_relative_transport_cancellation']<1e-12
    assert b.numerics['vapor_flux_budget']['max_scaled_equation_residual']<=p.moisture_residual_tol
    assert np.max(np.abs(a.P-b.P))>1e-4
