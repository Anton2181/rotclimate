from types import SimpleNamespace

import numpy as np

from rotclimate.config import Params
from rotclimate.transport import moisture_terms, save_transport
from rotclimate.solver import AdvectionSolver


def test_observed_transport_matches_the_actual_solver_operator():
    rng=np.random.default_rng(3)
    W=rng.uniform(1,20,(6,7)); u=rng.normal(size=W.shape); v=rng.normal(size=W.shape)
    solver=AdvectionSolver(*W.shape,dx=15000.)
    ce,cw,cs,cn,diag=solver.coefficients(u,v,60000.,np.zeros_like(W))
    operator=(diag[1:-1,1:-1]*W[1:-1,1:-1]+ce[1:-1,1:-1]*W[1:-1,2:]
              +cw[1:-1,1:-1]*W[1:-1,:-2]+cs[1:-1,1:-1]*W[2:,1:-1]
              +cn[1:-1,1:-1]*W[:-2,1:-1])
    terms=moisture_terms(W,u,v,solver.dx,60000.,np.zeros_like(W),np.zeros_like(W),0.,W)
    np.testing.assert_allclose((terms['advection']+terms['diffusion'])[1:-1,1:-1],
                               -86400.*operator,atol=1e-12)


def test_upwind_advection_sources_include_northward_row_sign():
    y, x = np.mgrid[:5, :6]
    W = 20. - x + y
    # u*dW/dx + v*dW/dnorth = -2 -3: 5 units/day supplied.
    rain = np.full_like(W, 5.)
    t = moisture_terms(W, np.full_like(W, 2.), np.full_like(W, 3.),
                       86400., 0., np.zeros_like(W), rain, 0., W)
    np.testing.assert_allclose(t['advection'][1:-1, 1:-1], 5.)
    np.testing.assert_allclose(t['residual'][1:-1, 1:-1], 0., atol=1e-12)
    assert np.isnan(t['residual'][0]).all()


def test_diffusion_and_exchange_are_water_sources_with_correct_daily_units():
    y, x = np.mgrid[:5, :6]
    W = (x*x + y*y).astype(float)
    t = moisture_terms(W, np.zeros_like(W), np.zeros_like(W),
                       1., 1/86400., np.zeros_like(W), np.full_like(W, 6.),
                       1/86400., W+2.)
    np.testing.assert_allclose(t['diffusion'][1:-1, 1:-1], 4.)
    np.testing.assert_allclose(t['storm_exchange'][1:-1, 1:-1], 2.)
    np.testing.assert_allclose(t['residual'][1:-1, 1:-1], 0., atol=1e-12)


def test_seasonal_averaging_cannot_hide_opposing_instantaneous_residuals(tmp_path):
    shape = (2, 2, 3)
    residual = np.stack([np.full((2,3), 2.), np.full((2,3), -2.)])
    budget = {key: np.zeros(shape) for key in ('advection', 'diffusion', 'storm_exchange')}
    budget.update(residual=residual, absolute_residual=np.abs(residual))
    grid = SimpleNamespace(target=np.full((2,3), 2), land=np.ones((2,3), bool),
                           inmap=np.ones((2,3), bool), map_slice=lambda: (slice(None),slice(None)))
    result = SimpleNamespace(params=Params(), grid=grid, days=np.array([91.25,273.75]),
                             moisture_budget=budget, E=np.zeros(shape), W=np.ones(shape),
                             u=np.zeros(shape), v=np.zeros(shape))
    evaluation = dict(monthly=dict(Tm=np.full((12,2,3), 15.), Pm=np.full((12,2,3), 50.),
                                   summer=np.array([True]*6+[False]*6)))
    path = tmp_path / 'transport.npz'
    report = save_transport(result, evaluation, path)
    annual = report['zones']['cold_dry']['annual']
    assert abs(annual['mean_total_mm_per_cell']['residual']) < 1e-10
    assert annual['mean_absolute_equation_residual_mm_day'] == 2.
    with np.load(path, allow_pickle=False) as archive:
        assert archive['monthly_water_mm'].shape == (12,2,3)
        assert 'params_json' in archive


def test_diagnostic_sources_close_the_active_equation_without_changing_climate():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case = _toy_case()
    p = earth.earth_params(strict_params().replace(subsidence_drying=.1,
                            flux_convergence=.3), case)
    observed = ClimateModel(p, grid=case.grid).run(diagnose_moisture=True)
    ordinary = ClimateModel(p, grid=case.grid).run()
    assert observed.numerics['all_checks_passed'] and ordinary.numerics['all_checks_passed']
    for name in ['T', 'Tsl', 'P', 'W', 'u', 'v', 'E']:
        np.testing.assert_array_equal(getattr(observed, name), getattr(ordinary, name))
    terms = observed.moisture_budget
    assert terms['column_drying'].min() < 0 and terms['column_drying'].max() <= 0
    assert terms['convergence_import'].max() > 0 and terms['convergence_import'].min() >= 0
    evaporation = observed.E[(slice(None),) + case.grid.map_slice()]
    np.testing.assert_array_equal(terms['evaporation'], evaporation)
    closure = evaporation + sum(terms[name] for name in ['column_drying', 'convergence_import',
                               'advection', 'diffusion', 'storm_exchange'])
    rain = observed.P[(slice(None),) + case.grid.map_slice()]
    np.testing.assert_allclose(closure - rain, terms['residual'], atol=2e-6)
