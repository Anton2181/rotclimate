import numpy as np
import pytest

from rotclimate.config import Params
from rotclimate.model import ClimateModel, gauss
from rotclimate.moisture import solve_moisture
from rotclimate.solver import AdvectionSolver
from rotclimate.storms import RainoutExchange, exchange_budget


def test_condensate_stays_at_its_formation_site_during_later_hops():
    storm = RainoutExchange(np.ones((1, 2)), lambda a: np.full_like(a, a.mean()),
                           np.array([[2., 100.]]), steps=2)
    water = np.array([[0., 10.]])
    # First hop: vapor [2,5], rain [3,0]. Second: vapor [2,3.5],
    # additional rain [1.5,0]. Earlier rain does not travel to the second box.
    np.testing.assert_allclose(storm(water), [[2., 3.5]])
    np.testing.assert_allclose(storm.condensate(water), [[4.5, 0.]])
    assert storm.transport(water).sum() == pytest.approx(water.sum())


@pytest.mark.parametrize('height', [False, True])
def test_variable_storms_conserve_vapor_plus_rain_with_nonnegative_hops(height):
    rng = np.random.default_rng(31)
    shape = (17, 19)
    rate = rng.random(shape) / 86400.
    rate[:, :4] = 0.
    mass = np.exp(-rng.random(shape)*2) if height else None
    capacity = 3. + 7.*rng.random(shape)
    storm = RainoutExchange(rate, lambda a: gauss(a, 2., mode='reflect'), capacity, mass)
    water = 30.*rng.random(shape)
    original = water.copy()
    vapor, rain = storm.partition(water)
    assert vapor.min() >= 0. and rain.min() >= 0. and rain.sum() > 0.
    assert (vapor <= capacity).all()
    np.testing.assert_array_equal(water, original)
    assert (vapor+rain).sum() == pytest.approx(water.sum(), rel=2e-14)
    budget = exchange_budget(water, storm.frequency, storm, storm.condensate)
    assert budget['relative_closure'] < 1e-14
    assert budget['vapor_net_cell_mm_day'] == pytest.approx(-budget['condensation_cell_mm_day'], rel=2e-14)
    # In-place solver updates must invalidate the cached partition.
    water *= .5
    assert storm.transport(water).sum() == pytest.approx(water.sum(), rel=2e-14)


def test_no_condensation_reduces_to_the_broad_gaussian_at_constant_rate():
    water = np.random.default_rng(32).random((17, 19))*20.
    sigma = 6.
    storm = RainoutExchange(np.full_like(water, .3),
        lambda a: gauss(a, sigma/np.sqrt(6), mode='reflect'), np.full_like(water, 100.))
    # The finite Gaussian kernels are truncated at four standard deviations;
    # their composition approximates, rather than exactly equals, the wide one.
    np.testing.assert_allclose(storm(water), gauss(water, sigma, mode='reflect'), atol=2e-4)
    np.testing.assert_array_equal(storm.condensate(water), 0.)


def test_inactive_storms_do_not_condense_or_move_water():
    water = np.full((3, 4), 10.)
    storm = RainoutExchange(np.zeros_like(water), lambda a: a, np.zeros_like(water))
    np.testing.assert_array_equal(storm(water), water)
    np.testing.assert_array_equal(storm.condensate(water), 0.)
    assert storm.frequency == 0.


def test_mountain_condensation_reduces_vapor_reaching_the_dry_side():
    water = np.zeros((3, 41))
    water[:, :18] = 10.
    capacity = np.full_like(water, 100.)
    capacity[:, 18:21] = 1.
    gaussian = lambda a: gauss(a, 3., mode='reflect')
    rainout = RainoutExchange(np.ones_like(water), gaussian, capacity)
    no_rainout = RainoutExchange(np.ones_like(water), gaussian, np.full_like(water, 100.))
    assert rainout(water)[:, 22:30].sum() < no_rainout(water)[:, 22:30].sum()
    rain = rainout.condensate(water)
    assert rain[:, 18:21].sum() > 0.
    assert rain[:, :18].sum() == 0. and rain[:, 21:].sum() == 0.


def test_condensation_enters_the_solved_moisture_equation_exactly_once():
    shape = (5, 6)
    zero = np.zeros(shape)
    storm = RainoutExchange(np.full(shape, 1./86400.), lambda a: a, np.full(shape, 2.))
    solver = AdvectionSolver(*shape, dx=1.)
    solver.rtol, solver.max_iter, solver.require_convergence = 1e-12, 2000, True
    p = Params(moisture_diffusion=0., picard_iters=256, moisture_relaxation=.25,
               moisture_residual_tol=1e-7)
    result = solve_moisture(solver, p, u=zero, v=zero, lamE=np.full(shape, 1./86400.),
        ocean_water=np.full(shape, 8.), land_source=zero, saturation=np.full(shape, 100.),
        dynamics=zero, instability=1., boundary=np.full(shape, 8.), guess=np.ones(shape),
        exchange=storm.frequency, mix=storm, condensate=storm.condensate)
    assert result.converged and result.scaled_residual <= p.moisture_residual_tol
    # E = 8-W; event rain = W-2; steady W=5 and P=3 mm/day.
    np.testing.assert_allclose(result.water[1:-1, 1:-1], 5., atol=1e-6)
    np.testing.assert_allclose(result.rain[1:-1, 1:-1], 3., atol=1e-6)
    np.testing.assert_allclose(8.-result.water[1:-1, 1:-1], result.rain[1:-1, 1:-1], atol=1e-6)


@pytest.mark.parametrize('capacity', [-1., np.nan, np.inf])
def test_invalid_capacity_is_rejected(capacity):
    with pytest.raises(ValueError, match='capacities'):
        RainoutExchange(np.ones((3, 4)), lambda a: a, np.full((3, 4), capacity))


@pytest.mark.parametrize('strength', [0., -1., np.nan, np.inf])
def test_invalid_model_rainout_strength_is_rejected(strength):
    with pytest.raises(ValueError, match='positive eddy_rainout'):
        ClimateModel(Params(eddy_moisture_scheme='conservative-rainout', eddy_rainout=strength))


def test_coupled_mountain_rainout_passes_numerical_and_water_checks():
    from test_earth import _toy_case
    from rotclimate import earth
    case = _toy_case()
    case.grid.elev[6:18, 14:16] = 3000.
    case.grid.elev_max = case.grid.elev.copy()
    p = Params(steps_per_year=13, t_iters=24, t_relaxation=.5, t_require_convergence=True,
               eddy_moisture_scheme='conservative-rainout', eddy_rainout=1.,
               eddy_rate=.5, eddy_scale_km=300., eddy_moisture_height_km=3.,
               picard_iters=256, moisture_relaxation=.25, moisture_residual_tol=.01,
               moisture_require_convergence=True, solver_rtol=1e-7,
               solver_max_iter=2000, solver_require_convergence=True)
    result = ClimateModel(earth.earth_params(p, case), grid=case.grid).run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    budget = result.numerics['storm_exchange']
    assert budget['max_relative_closure'] < 1e-12
    assert max(b['condensation_cell_mm_day'] for b in budget['steps']) > 0.
    assert result.P.min() >= 0. and result.W.min() >= 0.
    sl = (slice(None),) + result.grid.map_slice()
    scaled = result.moisture_budget['absolute_residual']/np.maximum(result.P[sl]+np.abs(result.E[sl]), .1)
    assert scaled.max() <= p.moisture_residual_tol*1.0001
