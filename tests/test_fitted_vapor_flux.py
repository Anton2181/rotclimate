"""Independent analytic and conservation checks for fitted shared-face fluxes."""
import numpy as np
import pytest

from rotclimate.solver import AdvectionSolver
from rotclimate.transport import (vapor_face_fluxes, diffusion_face_fluxes,
                                 boundary_supply, moisture_terms, flux_budget)


@pytest.mark.parametrize('speed', [-2., 2.])
@pytest.mark.parametrize('dx', [1., 2.])
def test_fitted_flux_solves_analytic_constant_flux_profile(speed, dx):
    # F=u*W-K*dW/dx=u for W=1+c*exp(u*x/K), independent of x.
    shape=(7,21); k=4.; x=np.arange(shape[1])*dx
    exponential=speed*x/k; exponential-=exponential.max()
    exact=np.broadcast_to(1+.5*np.exp(exponential),shape).copy()
    u=np.full(shape,speed); v=np.zeros(shape)
    solver=AdvectionSolver(*shape,dx,form='flux',scheme='exponential')
    solver.rtol=1e-12; solver.max_iter=3000; solver.require_convergence=True
    actual=solver.solve(u,v,k,.01,.01*exact,exact)
    np.testing.assert_allclose(actual,exact,atol=1e-10)
    adv=vapor_face_fluxes(actual,u,v)[0]
    diff=diffusion_face_fluxes(actual,k,dx,scheme='exponential',u=u,v=v)[0]
    np.testing.assert_allclose(adv+diff,speed,atol=1e-10)


@pytest.mark.parametrize('seed', [31,32])
def test_variable_flow_stencil_matches_local_and_boundary_ledgers(seed):
    rng=np.random.default_rng(seed); shape=(9,11); dx=28000.; k=60000.
    water=rng.uniform(.1,30,shape); u=rng.normal(0,4,shape); v=rng.normal(0,4,shape)
    solver=AdvectionSolver(*shape,dx,form='flux',scheme='exponential')
    ce,cw,cs,cn,diag=solver.coefficients(u,v,k,0.)
    assert all(np.all(c<=0) for c in [ce,cw,cs,cn]) and np.all(diag>=0)
    op=(diag[1:-1,1:-1]*water[1:-1,1:-1]+ce[1:-1,1:-1]*water[1:-1,2:]
        +cw[1:-1,1:-1]*water[1:-1,:-2]+cs[1:-1,1:-1]*water[2:,1:-1]
        +cn[1:-1,1:-1]*water[:-2,1:-1])
    terms=moisture_terms(water,u,v,dx,k,0,0,0,water,form='flux',scheme='exponential')
    np.testing.assert_allclose(terms['residual'][1:-1,1:-1],-86400*op,atol=3e-13)
    adv=vapor_face_fluxes(water,u,v)
    diff=diffusion_face_fluxes(water,k,dx,scheme='exponential',u=u,v=v)
    expected=boundary_supply(*(a+b for a,b in zip(adv,diff)),dx)
    np.testing.assert_allclose(terms['residual'][1:-1,1:-1].sum(),expected,atol=3e-12)
    ledger=flux_budget(water,u,v,dx,k,0,np.zeros(shape),0,water,scheme='exponential')
    assert ledger['transport_relative_cancellation']<1e-14


def test_fitted_flux_has_exact_zero_wind_and_zero_diffusion_limits():
    rng=np.random.default_rng(44); shape=(7,9); dx=56000.
    u=rng.normal(size=shape); v=rng.normal(size=shape)
    fitted=AdvectionSolver(*shape,dx,form='flux',scheme='exponential')
    upwind=AdvectionSolver(*shape,dx,form='flux')
    for winds,k in [((u,v),0.), ((np.zeros(shape),np.zeros(shape)),60000.)]:
        for a,b in zip(fitted.coefficients(*winds,k,1e-5),upwind.coefficients(*winds,k,1e-5)):
            np.testing.assert_allclose(a,b,rtol=1e-15,atol=0)


@pytest.mark.parametrize('changes', [dict(moisture_flux_scheme='other'),
    dict(moisture_flux_scheme='exponential'),
    dict(moisture_flux_scheme='exponential',moisture_transport_form='flux',flux_convergence=0,
         moisture_two_layer=True)])
def test_unsupported_fitted_flux_combinations_fail_before_grid(changes):
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError): ClimateModel(Params(**changes))


def test_fitted_flux_model_checks_the_equation_it_actually_solves():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case=_toy_case()
    p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',
        moisture_flux_scheme='exponential',flux_convergence=0,
        eddy_moisture_scheme='conservative',subsidence_drying=.05),case)
    result=ClimateModel(p,grid=case.grid).run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    ledger=result.numerics['vapor_flux_budget']
    assert ledger['horizontal_transport_conservative']
    assert ledger['max_relative_transport_cancellation']<1e-12
    assert ledger['max_scaled_equation_residual']<=p.moisture_residual_tol
    assert result.W.min()>=0 and result.P.min()>=0
