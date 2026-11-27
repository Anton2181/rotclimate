"""Geometry and calendar for an explicit Earth surface-wind diagnostic."""
import numpy as np


def project_monthly(east, north, geometry):
    """Preserve the equidistant projection's metric as well as its rotation."""
    east, north = np.asarray(east), np.asarray(north)
    ex, ey, nx, ny, determinant = geometry
    if east.shape != north.shape or east.shape != (12, *np.shape(ex)):
        raise ValueError('Need twelve geographic fields on the projection grid')
    if not all(np.isfinite(a).all() for a in [east, north, *geometry]) or (determinant <= 0).any():
        raise ValueError('Invalid wind or projection')
    return np.stack([ex * east + nx * north, ey * east + ny * north], axis=1)


def at_day(monthly, day, year=365.):
    """Interpolate equally spaced monthly centers, including December/January."""
    monthly = np.asarray(monthly)
    if monthly.shape[0] != 12 or not np.isfinite(day) or not np.isfinite(year) or year <= 0:
        raise ValueError('Need twelve months and a finite positive calendar')
    position = (day / year * 12 - .5) % 12
    first = int(np.floor(position))
    fraction = position - first
    return (1 - fraction) * monthly[first] + fraction * monthly[(first + 1) % 12]
