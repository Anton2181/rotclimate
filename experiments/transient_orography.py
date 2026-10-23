"""Prototype: average terrain uplift over unresolved weather-scale winds.

Monthly mean wind removes upslope episodes when wind directions fluctuate.
For isotropic Gaussian horizontal wind anomalies, the vertical terrain
velocity anomaly has standard deviation wind_rms * |terrain_gradient|.
This is an explicit hypothesis about unresolved winds, not a cloud model.
"""
import numpy as np
from scipy.special import ndtr


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
