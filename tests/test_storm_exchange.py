import numpy as np
import pytest
from scipy.ndimage import gaussian_filter

from rotclimate.config import Params
from rotclimate.model import ClimateModel, gauss
from rotclimate.storms import conservative_exchange, exchange_budget


@pytest.mark.parametrize('sigma', [0., 1.2, 6., 17.])
def test_reflected_fft_gaussian_matches_scipy_and_is_symmetric(sigma):
    rng = np.random.default_rng(21)
    a, b = rng.random((13, 17)), rng.random((13, 17))
    np.testing.assert_allclose(gauss(a, sigma, mode='reflect'),
                             gaussian_filter(a, sigma, mode='reflect'), atol=2e-12)
    assert np.sum(a * gauss(b, sigma, mode='reflect')) == pytest.approx(
        np.sum(b * gauss(a, sigma, mode='reflect')), abs=2e-11)


@pytest.mark.parametrize('height', [False, True])
def test_variable_rates_conserve_water_and_reduce_humidity_variance(height):
    rng = np.random.default_rng(22)
    rate = rng.random((17, 19)) / 86400.
    mass = np.exp(-rng.random(rate.shape) * 2) if height else np.ones_like(rate)
    water = rng.random(rate.shape) * 30
    loss, target = conservative_exchange(rate, lambda a: gauss(a, 6., mode='reflect'), mass)
    flux = loss * (target(water) - water)
    assert loss.min() >= 0 and target(water).min() >= 0
    assert abs(flux.sum()) < 1e-13
    # Pairwise diffusion dissipates specific-humidity contrast.
    assert np.sum(water / mass * flux) < 0
    np.testing.assert_allclose(target(12 * mass), 12 * mass, atol=1e-12)
    budget = exchange_budget(water, loss, target)
    assert budget['relative_closure'] < 1e-13
    assert budget['boundary_supply_cell_mm_day'] == pytest.approx(86400 * flux[1:-1, 1:-1].sum())


def test_two_boxes_do_not_create_water_when_one_has_no_storms():
    water = np.array([[0., 10.]])
    rate = np.array([[2., 0.]])
    loss, target = conservative_exchange(rate, lambda a: np.full_like(a, a.mean()))
    np.testing.assert_allclose(loss * (target(water) - water), [[5., -5.]])


def test_constant_rate_reproduces_the_original_reflected_exchange():
    water = np.random.default_rng(23).random((11, 12))
    mix = lambda a: gauss(a, 2., mode='reflect')
    loss, target = conservative_exchange(np.full_like(water, .3), mix)
    np.testing.assert_allclose(loss * (target(water) - water), .3 * (mix(water) - water), atol=1e-14)
    loss, target = conservative_exchange(np.zeros_like(water), mix)
    np.testing.assert_array_equal(loss * (target(water) - water), 0)


def test_rejects_unaccounted_crest_clipping():
    with pytest.raises(ValueError, match='crest clipping'):
        ClimateModel(Params(eddy_moisture_scheme='conservative', eddy_rainout=.5))


def test_coupled_conservative_moisture_solves_and_reports_boundary_exchange():
    from test_earth import _toy_case
    from rotclimate import earth
    p = Params(steps_per_year=13, t_iters=24, t_relaxation=.5, t_require_convergence=True,
               eddy_moisture_scheme='conservative', eddy_rate=.5, eddy_scale_km=300,
               eddy_moisture_height_km=3., picard_iters=256, moisture_relaxation=.25,
               moisture_residual_tol=.01, moisture_require_convergence=True,
               solver_rtol=1e-7, solver_max_iter=2000, solver_require_convergence=True)
    case = _toy_case()
    r = ClimateModel(earth.earth_params(p, case), grid=case.grid).run(diagnose_moisture=True)
    assert r.numerics['all_checks_passed']
    assert r.numerics['storm_exchange']['max_relative_closure'] < 1e-12
    assert np.isfinite(r.P).all() and r.P.min() >= 0 and r.W.min() >= 0
    sl = (slice(None),) + r.grid.map_slice()
    scaled = r.moisture_budget['absolute_residual'] / np.maximum(r.P[sl] + np.abs(r.E[sl]), .1)
    assert scaled.max() <= p.moisture_residual_tol * 1.0001


@pytest.mark.parametrize('bad_mass', [0., -1., np.nan])
def test_rejects_invalid_column_mass(bad_mass):
    with pytest.raises(ValueError, match='column masses'):
        conservative_exchange(np.ones((3, 4)), lambda a: a, np.full((3, 4), bad_mass))
