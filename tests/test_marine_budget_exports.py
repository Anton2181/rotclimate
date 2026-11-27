"""Signed marine source/exports on the actual applied main model."""
from types import SimpleNamespace

import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.moisture import ocean_rate, solve_moisture
from rotclimate.solver import AdvectionSolver
from rotclimate.transport import moisture_terms, save_transport




@pytest.mark.parametrize('source_mm_day, sign', [(.1, 1), (20., -1)])
@pytest.mark.parametrize('ocean_sink', [1., .4])
def test_actual_solver_budget_requires_signed_marine_exchange(source_mm_day, sign, ocean_sink):
    shape = (5, 6)
    zero = np.zeros(shape)
    target = np.full(shape, 8.)
    rate = np.full(shape, 1 / 86400.)
    source = np.full(shape, source_mm_day / 86400.)
    solver = AdvectionSolver(*shape, dx=1.)
    solver.rtol = 1e-11
    solver.max_iter = 2000
    solver.require_convergence = True
    p = Params(moisture_diffusion=1e-6, picard_iters=512, moisture_relaxation=.25,
               moisture_residual_tol=1e-6, ocean_sink=ocean_sink)
    result = solve_moisture(solver, p, zero, zero, rate, target, source, np.full(shape, 10.),
                            np.full(shape, 2.), 1., target, np.ones(shape))
    assert result.converged
    marine = ocean_rate(p, rate, result.water, target) * (target - result.water) * 86400
    assert sign * marine[2, 2] > 0
    complete = moisture_terms(result.water, zero, zero, solver.dx, p.moisture_diffusion,
        source * 86400 + marine, result.rain, 0., result.water)
    scale = np.maximum(result.rain + np.abs(source * 86400 + marine), .1)
    assert np.max((complete['absolute_residual'] / scale)[1:-1, 1:-1]) <= p.moisture_residual_tol


@pytest.mark.parametrize('marine_mm_day', [2., -3.])
def test_saved_zone_report_keeps_signed_marine_component_visible(tmp_path, marine_mm_day):
    shape = (2, 2, 3)
    fields = {key:np.zeros(shape) for key in ['advection', 'diffusion', 'storm_exchange', 'residual', 'absolute_residual']}
    fields['marine_exchange'] = np.full(shape, marine_mm_day)
    grid = SimpleNamespace(target=np.full((2, 3), 2), land=np.ones((2, 3), bool),
        inmap=np.ones((2, 3), bool), map_slice=lambda:(slice(None), slice(None)))
    result = SimpleNamespace(params=Params(), grid=grid, days=np.array([91.25, 273.75]),
        moisture_budget=fields, E=np.zeros(shape), W=np.ones(shape), u=np.zeros(shape), v=np.zeros(shape))
    evaluation = dict(monthly=dict(Tm=np.full((12, 2, 3), 15.), Pm=np.full((12, 2, 3), 50.),
                                  summer=np.array([True] * 6 + [False] * 6)))
    path = tmp_path / 'transport.npz'
    report = save_transport(result, evaluation, path)
    value = report['zones']['cold_dry']['annual']['mean_total_mm_per_cell']['marine_exchange']
    assert value == pytest.approx(marine_mm_day * 365)
    assert 'independent reservoirs already include it in evaporation' in report['note']
    with np.load(path) as packet:
        np.testing.assert_allclose(packet['monthly_marine_exchange_mm_day'], marine_mm_day)
