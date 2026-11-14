"""Within-bin rain timing that conserves every field's bin total.

A synthetic sensitivity (calibration/rain_timing_20261114/plan.json): uniform
rain, or 1/2/4 equal one-day events per climate bin centred at (j + 0.5)/count
of the bin. Events are synchronized across fields as a declared scenario, not
observed storms.
"""
import numpy as np

EVENT_DAYS = 1.0
COUNTS = (1, 2, 4)


def event_windows(bin_edges_days, count):
    """(bin index, start day, end day) for every event of a pattern."""
    bins = np.asarray(bin_edges_days, dtype=float)
    if isinstance(count, bool) or not isinstance(count, (int, np.integer)) or count < 1:
        raise ValueError('A positive integer event count is required')
    if bins.ndim != 1 or len(bins) < 2 or not np.isfinite(bins).all() or np.any(np.diff(bins) <= 0):
        raise ValueError('Ordered finite climate-bin edges required')
    width = np.diff(bins)
    if np.any(width < count * EVENT_DAYS):
        raise ValueError('Events of one day each do not fit in every climate bin')
    out = []
    for b in range(len(width)):
        for j in range(count):
            centre = bins[b] + (j + 0.5) / count * width[b]
            out.append((b, centre - EVENT_DAYS / 2, centre + EVENT_DAYS / 2))
    return out


def event_edges(bin_edges_days, counts=COUNTS):
    """Every event start and end for the given patterns, for a common clock."""
    edges = [edge for count in counts for _, a, b in event_windows(bin_edges_days, count) for edge in (a, b)]
    return np.unique(np.asarray(edges, dtype=float))


def timed_rain(clock, totals, count):
    """Rain per clock step and field. count None is uniform within each bin.

    Each event carries total/count for its bin, spread over its exact overlap
    with every step, so bin totals are conserved for any clock.
    """
    totals = np.asarray(totals, dtype=float)
    if totals.ndim < 1 or totals.shape[0] != len(clock.bin_edges_days) - 1 or not np.isfinite(totals).all() or np.any(totals < 0):
        raise ValueError('Finite nonnegative totals for every climate bin required')
    if count is None:
        return clock.spread_bin_totals(totals)
    start, end = clock.edges_days[:-1], clock.edges_days[1:]
    rain = np.zeros((len(start),) + totals.shape[1:])
    for b, a, z in event_windows(clock.bin_edges_days, count):
        overlap = np.clip(np.minimum(end, z) - np.maximum(start, a), 0.0, None)
        hit = overlap > 0
        if hit.any():
            share = overlap[hit] / EVENT_DAYS / count
            rain[hit] += share.reshape((-1,) + (1,) * (totals.ndim - 1)) * totals[b]
    return rain
