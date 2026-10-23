import numpy as np
import pytest
from scipy.integrate import quad
from scipy.stats import norm

from experiments.transient_orography import expected_uplift


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
