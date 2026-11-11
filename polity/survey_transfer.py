"""Conditional presence-only diagnostics; background is not absence evidence."""
import numpy as np
from scipy.spatial import cKDTree


def relative_ranks(values, background):
    """Empirical percentiles with half weight on ties, including zero scores."""
    values = np.asarray(values, float)
    background = np.sort(np.asarray(background, float))
    if not len(background) or not np.isfinite(background).all() or not np.isfinite(values).all():
        raise ValueError('Ranks require finite values and nonempty background')
    return (np.searchsorted(background, values, side='left')
            + np.searchsorted(background, values, side='right')) / (2 * len(background))


def capture_fraction(cells, towns, width, cell_km, radius_km):
    """Distinct source-cell capture, without a false-positive/precision claim."""
    cells = np.unique(np.asarray(cells, int))
    if not len(cells):
        return None
    towns = np.asarray(towns, int).reshape(-1, 2)
    if not len(towns):
        return 0.
    points = np.column_stack(np.divmod(cells, width)) * cell_km
    distances = cKDTree(towns * cell_km).query(points)[0]
    return float(np.mean(distances <= radius_km))


def sphere_distance(lat, lon, lat0, lon0):
    a, b = np.radians(lat), np.radians(lat0)
    h = np.sin((a-b)/2)**2 + np.cos(a)*np.cos(b)*np.sin(np.radians(lon-lon0)/2)**2
    return 6371. * 2 * np.arcsin(np.sqrt(np.clip(h, 0, 1)))
