import numpy as np
import pytest

from rotclimate.solver import AdvectionSolver
from rotclimate.transport import vapor_face_fluxes,face_divergence,boundary_supply,flux_budget,moisture_terms


def test_variable_flow_solver_preserves_constant_through_flux_not_constant_concentration():
    shape=(5,15)
    u=np.broadcast_to(np.linspace(1,3,shape[1]),shape).copy()
    zero=np.zeros(shape)
    exact=np.empty(shape)
    exact[:,:-1]=10/(.5*(u[:,1:]+u[:,:-1]))
    exact[:,-1]=exact[:,-2]
    solver=AdvectionSolver(*shape,dx=10000,form='flux')
    solver.rtol=1e-11
    solver.max_iter=2000
    solver.require_convergence=True
    result=solver.solve(u,zero,0,zero,zero,exact)
    np.testing.assert_allclose(result,exact,atol=1e-9)
    assert solver.converged[-1]
    east,_=vapor_face_fluxes(result,u,zero)
    np.testing.assert_allclose(east[1:-1],10,atol=1e-9)


@pytest.mark.parametrize('seed',[17,18,19])
def test_local_flux_operator_matches_solver_and_telescopes_to_boundary(seed):
    rng=np.random.default_rng(seed)
    W=rng.uniform(1,25,(7,9));u=rng.normal(size=W.shape)*4;v=rng.normal(size=W.shape)*4
    solver=AdvectionSolver(*W.shape,dx=28000,form='flux')
    ce,cw,cs,cn,diag=solver.coefficients(u,v,60000,0)
    operator=(diag[1:-1,1:-1]*W[1:-1,1:-1]+ce[1:-1,1:-1]*W[1:-1,2:]+
              cw[1:-1,1:-1]*W[1:-1,:-2]+cs[1:-1,1:-1]*W[2:,1:-1]+cn[1:-1,1:-1]*W[:-2,1:-1])
    terms=moisture_terms(W,u,v,solver.dx,60000,0,np.zeros_like(W),0,W,form='flux')
    np.testing.assert_allclose((terms['advection']+terms['diffusion'])[1:-1,1:-1],-86400*operator,atol=1e-13)
    faces=vapor_face_fluxes(W,u,v)
    np.testing.assert_allclose(-86400*face_divergence(*faces,solver.dx).sum(),boundary_supply(*faces,solver.dx),atol=1e-12)
    budget=flux_budget(W,u,v,solver.dx,60000,0,np.zeros_like(W),0,W)
    assert budget['transport_relative_cancellation']<1e-14


def test_converging_flux_collects_water_without_negative_neighbor_coefficients():
    y,x=np.mgrid[:7,:9]
    u=(4-x).astype(float);v=(y-3).astype(float)
    solver=AdvectionSolver(7,9,10000,form='flux')
    ce,cw,cs,cn,diag=solver.coefficients(u,v,10000,1e-5)
    assert all((a<=0).all() for a in [ce,cw,cs,cn]) and (diag>0).all()
    solver.rtol=1e-10;solver.require_convergence=True;solver.max_iter=2000
    result=solver.solve(u,v,10000,np.full((7,9),1e-5),np.full((7,9),1e-4),np.full((7,9),10.))
    assert result.min()>=0 and result[3,4]>10


@pytest.mark.parametrize('changes',[dict(moisture_transport_form='other'),
    dict(moisture_transport_form='flux',flux_convergence=.1),
    dict(moisture_transport_form='flux',transport_scheme='exponential')])
def test_ambiguous_moisture_import_is_rejected_before_model_grid(changes):
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):ClimateModel(Params(**changes))


def test_conservative_mean_and_storm_transport_have_a_coupled_vapor_ledger():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case=_toy_case()
    p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',
         flux_convergence=0,eddy_moisture_scheme='conservative',subsidence_drying=.05),case)
    result=ClimateModel(p,grid=case.grid).run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    budget=result.numerics['vapor_flux_budget']
    assert budget['horizontal_transport_conservative']
    assert budget['max_relative_transport_cancellation']<1e-12
    assert budget['max_scaled_equation_residual']<=p.moisture_residual_tol
    assert result.numerics['linear_solves']>budget['moisture_linear_solves']>0
    assert result.P.min()>=0 and result.W.min()>=0
