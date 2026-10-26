"""Known-answer two-stream fluxes, mass/profile identities and coupled ledgers."""
import numpy as np
import pytest
from rotclimate.layer_transport import LayerFluxSolver, return_branches
from rotclimate.solver import AdvectionSolver
from rotclimate.transport import vapor_face_fluxes, face_divergence, moisture_terms, flux_budget


def test_opposed_donor_streams_keep_their_grid_dependent_upwind_exchange():
    y,x=np.mgrid[:7,:9];water=(x*x).astype(float);zero=np.zeros_like(water)
    east=np.full_like(water,4.)
    layers=((.5,east,zero),(.5,-east,zero))
    fx,fy=vapor_face_fluxes(water,zero,zero,layers=layers)
    # Opposed first-order donors yield -a/2 * difference(W), even with net U=0.
    np.testing.assert_allclose(fx,-2*np.diff(water,axis=1))
    np.testing.assert_allclose(face_divergence(fx,fy,10),-.4)
    a,b=vapor_face_fluxes(water,zero,zero)
    np.testing.assert_array_equal(a,0);np.testing.assert_array_equal(b,0)
    # This extra upwind mixing scales with cell size; it is not an observed
    # physical eddy diffusivity and cannot bypass a finer-resolution gate.


@pytest.mark.parametrize('seed',[113,114,115])
def test_layer_operator_matches_ledger_and_boundary_telescope(seed):
    rng=np.random.default_rng(seed);shape=(7,9)
    water=rng.uniform(1,30,shape);u,v,ub,vb=rng.normal(size=(4,)+shape)*5
    layers,eu,ev=return_branches(u,v,ub,vb,.2)
    solver=LayerFluxSolver(*shape,56000);solver.set_layers(layers)
    ce,cw,cs,cn,diag=solver.coefficients(eu,ev,60000,0)
    assert all((a<=0).all() for a in [ce,cw,cs,cn]) and (diag>=0).all()
    operator=(diag[1:-1,1:-1]*water[1:-1,1:-1]+ce[1:-1,1:-1]*water[1:-1,2:]
        +cw[1:-1,1:-1]*water[1:-1,:-2]+cs[1:-1,1:-1]*water[2:,1:-1]+cn[1:-1,1:-1]*water[:-2,1:-1])
    terms=moisture_terms(water,eu,ev,56000,60000,0,0,0,water,form='flux',layers=layers)
    np.testing.assert_allclose((terms['advection']+terms['diffusion'])[1:-1,1:-1],-86400*operator,atol=1e-12)
    budget=flux_budget(water,eu,ev,56000,60000,0,np.zeros(shape),0,water,layers=layers)
    assert budget['transport_relative_cancellation']<1e-13


def test_return_flow_closes_mass_and_uses_specific_humidity_not_mass_weights():
    rng=np.random.default_rng(116);ul,vl,ub,vb=rng.normal(size=(4,6,7))
    layers,eu,ev=return_branches(ul,vl,ub,vb,.2)
    a,l_u,l_v=layers[0];b,h_u,h_v=layers[1]
    np.testing.assert_allclose(.25*l_u+.75*h_u,ub,atol=1e-15)
    np.testing.assert_allclose(.25*l_v+.75*h_v,vb,atol=1e-15)
    assert a==pytest.approx(.625) and b==pytest.approx(.375)
    assert (b/.75)/(a/.25)==pytest.approx(.2)
    np.testing.assert_allclose(eu,a*l_u+b*h_u)
    np.testing.assert_allclose(ev,a*l_v+b*h_v)


def test_dry_upper_branch_matches_the_single_lower_transport_operator():
    rng=np.random.default_rng(117);ul,vl,ub,vb=rng.normal(size=(4,6,7))
    layers,eu,ev=return_branches(ul,vl,ub,vb,0)
    solver=LayerFluxSolver(6,7,56000);solver.set_layers(layers)
    original=AdvectionSolver(6,7,56000,form='flux')
    for actual,expected in zip(solver.coefficients(eu,ev,60000,.0001),original.coefficients(ul,vl,60000,.0001)):
        np.testing.assert_array_equal(actual,expected)


def test_opposed_stream_steady_solve_matches_affine_manufactured_solution():
    _,x=np.mgrid[:7,:10];water=10+x.astype(float);zero=np.zeros_like(water);u=np.ones_like(water)*3
    solver=LayerFluxSolver(7,10,56000);solver.set_layers(((.5,u,zero),(.5,-u,zero)))
    solver.rtol=1e-11;solver.max_iter=2000;solver.require_convergence=True
    result=solver.solve(zero,zero,0,1e-5,water*1e-5,water)
    np.testing.assert_allclose(result,water,atol=1e-8)
    assert solver.converged[-1]


@pytest.mark.parametrize('updates',[dict(moisture_two_layer='yes'),dict(moisture_two_layer=True),
    dict(moisture_upper_q_ratio=-.1),dict(moisture_upper_q_ratio=1.1),dict(moisture_upper_q_ratio=np.nan)])
def test_invalid_or_incomplete_physical_profile_fails_before_grid(updates):
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):ClimateModel(Params(**updates))


def test_coupled_model_certifies_dry_air_and_actual_two_branch_water_flux(monkeypatch):
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth,layer_transport
    from rotclimate.model import ClimateModel
    case=_toy_case();p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',flux_convergence=0,
        eddy_moisture_scheme='conservative',moisture_mass_balance=True,subsidence_drying=.05),case)
    original=layer_transport.LayerFluxSolver
    monkeypatch.setattr(layer_transport,'LayerFluxSolver',lambda *a:pytest.fail('Disabled path constructed layer solver'))
    a=ClimateModel(p,grid=case.grid).run()
    assert 'two_layer_transport' not in a.numerics
    monkeypatch.setattr(layer_transport,'LayerFluxSolver',original)
    b=ClimateModel(p.replace(moisture_two_layer=True,moisture_upper_q_ratio=.2),grid=case.grid).run(diagnose_moisture=True)
    assert b.numerics['all_checks_passed']
    assert b.numerics['two_layer_transport']['max_scaled_dry_mass_divergence']<1e-12
    assert b.numerics['vapor_flux_budget']['max_relative_transport_cancellation']<1e-12
    assert b.numerics['vapor_flux_budget']['max_scaled_equation_residual']<=p.moisture_residual_tol
    assert np.max(np.abs(a.P-b.P))>1e-4
