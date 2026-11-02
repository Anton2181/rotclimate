"""Kinematic hypothesis: net descent cannot include resolved convergent ascent."""
import numpy as np


def net_descent_rate(requested_s, convergence_s, strength=1.0):
    if not np.isfinite(strength) or not 0 <= strength <= 1:
        raise ValueError('Continuity strength must be finite and in [0, 1]')
    if strength == 0:
        return requested_s
    requested_s, convergence_s = np.broadcast_arrays(requested_s, convergence_s)
    if not np.isfinite(requested_s).all() or (requested_s < 0).any() or not np.isfinite(convergence_s).all():
        raise ValueError('Need nonnegative finite descent and finite signed convergence rates')
    return np.maximum(requested_s - strength * np.maximum(convergence_s, 0), 0)
