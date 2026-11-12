"""Scale-free town-size shape metrics and catalogue date/extent gates.

Conditional size references are density x area with unknown multipliers, so
only relative sizes are compared. Nothing here turns an area into a census.
"""
import math

import numpy as np

BASIS_GROUPS = ('walls', 'inhabited_area', 'urban_grid', 'other_or_unspecified')


def _year(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def date_blockers(year, start, end) -> tuple:
    """Whole-site catalogue dates can refuse a place for a year; they never certify a phase."""
    if isinstance(year, bool) or not isinstance(year, int):
        raise ValueError('Comparison year must be an integer')
    reasons = []
    if not _year(start):
        reasons.append('catalogue_start_unrecorded')
    elif start > year:
        reasons.append('place_not_yet_founded')
    if not _year(end):
        reasons.append('catalogue_end_unrecorded')
    elif end < year:
        reasons.append('place_ended_before_year')
    return tuple(reasons)


def refused(year, start, end) -> bool:
    """An unrecorded end is kept and flagged; an unrecorded start, unfounded or ended place is refused."""
    return bool(set(date_blockers(year, start, end)) - {'catalogue_end_unrecorded'})


def basis_group(text) -> str:
    """Extent basis from the first words of the catalogue's description."""
    label = '' if text is None else str(text).strip().casefold()
    if label.startswith(('walls', 'ramparts')):
        return 'walls'
    if label.startswith('inhabited area'):
        return 'inhabited_area'
    if label.startswith('urban grid'):
        return 'urban_grid'
    return 'other_or_unspecified'


def relative_sizes(area_ha, exponent):
    """people proportional to area**(1+exponent); the constant is deliberately absent."""
    area = np.asarray(area_ha, float)
    if area.ndim != 1 or not area.size or not np.all(np.isfinite(area)) or np.any(area <= 0):
        raise ValueError('Areas must be finite positive hectares')
    if isinstance(exponent, bool) or not math.isfinite(exponent) or exponent < 0:
        raise ValueError('Declare a finite non-negative density exponent')
    return area ** (1 + exponent)


def largest(sizes, tail):
    """The largest ceil(tail * n) positive sizes, descending."""
    x = np.asarray(sizes, float)
    if x.ndim != 1 or not np.all(np.isfinite(x)) or np.any(x < 0):
        raise ValueError('Sizes must be finite and non-negative')
    x = np.sort(x[x > 0])[::-1]
    if not x.size:
        raise ValueError('No positive sizes')
    if isinstance(tail, bool) or not 0 < tail <= 1:
        raise ValueError('Tail level must lie in (0, 1]')
    return x[:math.ceil(tail * x.size)]


def shape_metrics(sizes, tail=1.0) -> dict:
    x = largest(sizes, tail)
    n = x.size; total = float(x.sum()); ascending = x[::-1]
    gini = float(2 * (np.arange(1, n + 1) * ascending).sum() / (n * total) - (n + 1) / n)
    top = min(100, n); rank = np.log10(np.arange(1, top + 1)); size = np.log10(x[:top])
    centred = rank - rank.mean()
    slope = float((centred * (size - size.mean())).sum() / (centred ** 2).sum()) if top > 1 else float('nan')
    return dict(places=int(n), gini=max(gini, 0.0),
                share_largest_1_percent=float(x[:math.ceil(.01 * n)].sum() / total),
                share_largest_10_percent=float(x[:math.ceil(.1 * n)].sum() / total),
                log10_sd=float(np.log10(x).std()),
                largest_over_median=float(x[0] / np.median(x)),
                rank_size_slope_top100=slope, rank_size_places=int(top))
