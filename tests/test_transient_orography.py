import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from rotclimate.orography import expected_uplift


@pytest.mark.parametrize('mean,deviation', [(-.1,.02), (0,.03), (.05,.1), (.3,.1), (.1,1.)])
def test_analytic_uplift_matches_integrated_weather_distribution(mean, deviation):
    reference = quad(lambda x:x*norm.pdf(x, loc=mean, scale=deviation), 0, .2,
                     epsabs=1e-12)[0] + .2*norm.sf(.2, loc=mean, scale=deviation)
    assert float(expected_uplift(mean, deviation)) == pytest.approx(reference, abs=1e-12)


def test_no_weather_variance_reproduces_original_and_flat_ground_stays_flat():
    mean = np.array([-.5, 0, .001, .04, .19, .5])
    np.testing.assert_array_equal(expected_uplift(mean, np.zeros_like(mean)), np.clip(mean, 0, .2))
    assert float(expected_uplift(0, 0)) == 0
    assert float(expected_uplift(0, .03)) > 0


def test_uplift_is_bounded_and_symmetric_under_reversing_the_terrain_velocity():
    mu = np.linspace(-.5, .7, 300)
    sigma = .04
    actual = expected_uplift(mu, sigma)
    assert np.all((actual >= 0) & (actual <= .2))
    np.testing.assert_allclose(actual+expected_uplift(.2-mu, sigma), .2, atol=1e-15)
    assert np.all(np.diff(actual) >= -1e-15)


def test_extremely_weak_variability_cannot_remove_saturated_uplift():
    with np.errstate(all='raise'):
        result = expected_uplift(np.array([-1e20, 0, 1e20]), np.array([1e-200, 0, 1e-200]))
    np.testing.assert_array_equal(result, [0, 0, .2])


@pytest.mark.parametrize('mu,sigma,cap', [(float('nan'),1,.2), (0,-1,.2), (0,1,0), (0,float('inf'),.2)])
def test_invalid_wind_statistics_are_rejected(mu,sigma,cap):
    with pytest.raises(ValueError): expected_uplift(mu,sigma,cap)


def strict_params():
    from rotclimate.config import Params
    return Params(steps_per_year=13, t_iters=24, t_relaxation=.5, t_require_convergence=True,
                  eddy_rate=.5, eddy_scale_km=300, picard_iters=256, moisture_relaxation=.25,
                  moisture_residual_tol=.01, moisture_require_convergence=True,
                  solver_rtol=1e-7, solver_max_iter=2000, solver_require_convergence=True)


def test_flat_ground_is_exactly_unchanged_in_the_coupled_climate():
    from test_earth import _toy_case
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case = _toy_case(); case.grid.elev[:] = 0; case.grid.elev_max[:] = 0
    p = strict_params()
    a = ClimateModel(earth.earth_params(p, case), grid=case.grid).run()
    b = ClimateModel(earth.earth_params(p.replace(orographic_gust_ms=8), case), grid=case.grid).run()
    assert a.numerics['all_checks_passed'] and b.numerics['all_checks_passed']
    for key in ['T', 'P', 'W', 'u', 'v', 'E']:
        np.testing.assert_array_equal(getattr(a,key), getattr(b,key))


def test_weather_uplift_rain_remains_in_the_coupled_water_equation():
    from test_earth import _toy_case
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    case = _toy_case(); g = case.grid
    x = np.arange(g.nx)[None, :]
    g.elev[:] = np.where(g.land, 300+1800*np.exp(-((x-15)/2)**2), 0)
    g.elev_max[:] = g.elev
    p = strict_params().replace(orographic_gust_ms=8)
    r = ClimateModel(earth.earth_params(p, case), grid=g).run(diagnose_moisture=True)
    original = ClimateModel(earth.earth_params(p.replace(orographic_gust_ms=0), case), grid=g).run()
    assert r.numerics['all_checks_passed']
    assert original.numerics['all_checks_passed']
    assert np.max(np.abs(r.P-original.P)) > 1e-4
    assert np.isfinite(r.P).all() and r.P.min() >= 0 and r.W.min() >= 0
    sl = (slice(None),)+g.map_slice()
    residual = r.moisture_budget['absolute_residual']/np.maximum(r.P[sl]+np.abs(r.E[sl]), .1)
    assert residual.max() <= p.moisture_residual_tol*1.0001


def test_default_legacy_climate_never_calls_the_weather_uplift_operator(monkeypatch):
    from test_earth import _toy_case
    from rotclimate import earth, orography
    from rotclimate.model import ClimateModel
    monkeypatch.setattr(orography, 'expected_uplift', lambda *a:pytest.fail('Opt-in operator used by the baseline'))
    case = _toy_case()
    p = strict_params()
    r = ClimateModel(earth.earth_params(p, case), grid=case.grid).run()
    assert r.numerics['all_checks_passed']


@pytest.mark.parametrize('gust', [-1, float('nan'), float('inf')])
def test_invalid_weather_wind_strength_is_rejected_before_grid_build(gust):
    from rotclimate.model import ClimateModel
    from rotclimate.config import Params
    with pytest.raises(ValueError, match='orographic_gust_ms'):
        ClimateModel(Params(orographic_gust_ms=gust))
