"""Average terrain uplift over unresolved weather-scale winds.

Monthly mean wind removes upslope episodes when wind directions fluctuate.
For isotropic Gaussian horizontal wind anomalies, the vertical terrain
velocity anomaly has standard deviation wind_rms * |terrain_gradient|.
This is an explicit hypothesis about unresolved winds, not a cloud model.
"""
import numpy as np
from scipy.special import ndtr


def validate_terrain_samples(samples, shape):
    """Require a complete, nonnegative area quadrature for every climate cell."""
    samples = np.asarray(samples, float)
    if (samples.ndim != 4 or samples.shape[0] != 3 or samples.shape[1] < 1 or
            samples.shape[2:] != tuple(shape) or not np.isfinite(samples).all()):
        raise ValueError('Need finite terrain samples [3, samples, ny, nx]')
    weights = samples[2]
    if (weights < 0).any() or not np.allclose(weights.sum(0), 1., rtol=0, atol=1e-10):
        raise ValueError('Terrain sample areas must be nonnegative and sum to one')
    return samples


def terrain_uplift(samples, u, v, wind_std=0., cap=.2):
    """Area mean capped positive uplift on supplied fine terrain slopes.

    Wind and vapor are uniform within a climate cell. Fine terrain slopes are
    deterministic; optional isotropic Gaussian wind anomalies are averaged at
    each slope before taking the area mean. This introduces no water source.
    """
    samples = np.asarray(samples, float)
    if samples.ndim != 4: raise ValueError('Need four-dimensional terrain samples')
    samples = validate_terrain_samples(samples, samples.shape[2:])
    sx, sy, weights = samples
    u, v, wind_std = [np.broadcast_to(np.asarray(a, float), sx.shape[1:]) for a in (u, v, wind_std)]
    if not np.isfinite(u).all() or not np.isfinite(v).all() or not np.isfinite(wind_std).all() or (wind_std < 0).any():
        raise ValueError('Need finite winds and nonnegative wind deviation')
    upward = expected_uplift(u*sx + v*sy, wind_std*np.hypot(sx, sy), cap=cap)
    return np.sum(weights*upward, axis=0)


def expected_uplift(mean, deviation, cap=.2):
    """E[clip(X, 0, cap)] for X ~ Normal(mean, deviation²), in m/s.

    Average the capped uplift itself; clipping an averaged uncapped uplift
    would overestimate strong, infrequent events. Zero deviation returns the
    original deterministic uplift exactly. This supplies no water source:
    precipitation must still be drawn from the coupled vapor equation.
    """
    mean, deviation = np.broadcast_arrays(np.asarray(mean, float), np.asarray(deviation, float))
    if (not np.isfinite(mean).all() or not np.isfinite(deviation).all() or
            (deviation < 0).any() or not np.isfinite(cap) or cap <= 0):
        raise ValueError('Need finite means, nonnegative deviations and a positive cap')

    with np.errstate(over='ignore'):
        a = np.divide(-mean, deviation, out=np.zeros_like(mean), where=deviation > 0)
        b = np.divide(cap-mean, deviation, out=np.zeros_like(mean), where=deviation > 0)
    def density(z):
        # An unrepresentably small Gaussian tail legitimately tends to zero.
        with np.errstate(under='ignore'):
            return np.exp(-.5*np.minimum(np.abs(z), 40)**2)/np.sqrt(2*np.pi)
    # Use survival probabilities in the positive tail. Subtracting two
    # near-unit CDFs would otherwise erase rare upslope episodes.
    probability = np.where(a > 0, ndtr(-a)-ndtr(-b), ndtr(b)-ndtr(a))
    expected = np.clip(mean*probability + deviation*(density(a)-density(b)) + cap*ndtr(-b), 0, cap)
    return np.where(deviation > 0, expected, np.clip(mean, 0, cap))
