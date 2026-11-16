"""Bounded redistribution of requested residents; no food-feasibility claim."""
import numpy as np

from polity.settlement_sizes import residents


def area_from_people(people, scenario='central'):
    """Invert the existing monotone area/density reading, including zero."""
    p = np.asarray(people, float)
    if np.any(~np.isfinite(p)) or np.any(p < 0):
        raise ValueError('Finite nonnegative requests required')
    if scenario == 'low':
        return p / 100
    if scenario != 'central':
        raise ValueError('Unknown density scenario')
    lo, hi = p / 500, p / 100
    for _ in range(70):
        mid = (lo + hi) / 2
        below = residents(mid) < p
        lo = np.where(below, mid, lo)
        hi = np.where(below, hi, mid)
    return np.where(p <= 5000, p / 100,
                    np.where(p >= 200000, p / 500, (lo + hi) / 2))


def redistribute(baseline, weights, lower, upper, available_people):
    """Solve clip(lambda * weights, lower, upper) at the baseline total.

    Inactive sites must have zero baseline, weight and bounds. A positive weight
    is required at every active site. The identity control returns exact copies.
    """
    b, w, lo, hi = [np.asarray(a, float) for a in (baseline, weights, lower, upper)]
    if b.ndim != 1 or any(a.shape != b.shape for a in (w, lo, hi)):
        raise ValueError('Matching one-dimensional vectors required')
    if any(np.any(~np.isfinite(a)) or np.any(a < 0) for a in (b, w, lo, hi)):
        raise ValueError('Finite nonnegative vectors required')
    if np.any(lo > b) or np.any(b > hi):
        raise ValueError('Baseline outside bounds')
    active = hi > 0
    if np.any(w[active] <= 0) or np.any(w[~active] != 0):
        raise ValueError('Weights must be positive exactly at active sites')
    budget = float(b.sum())
    if not np.isfinite(available_people) or available_people < budget:
        raise ValueError('Insufficient available population')
    if np.array_equal(b, w) or not active.any():
        return b.copy()
    left, right = 0., float(np.max(hi[active] / w[active]))
    for _ in range(100):
        mid = (left + right) / 2
        if np.clip(mid * w, lo, hi).sum() < budget:
            left = mid
        else:
            right = mid
    result = np.clip((left + right) / 2 * w, lo, hi)
    if abs(float(result.sum()) - budget) > max(1e-6, budget * 1e-12):
        raise ArithmeticError('Request conservation failed')
    return result
