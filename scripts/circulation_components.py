"""Pure reference/reconstruction helpers; these never supply a model forcing."""
import numpy as np


def bilinear_monthly(field, lat, lon):
    field = np.asarray(field, float)
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    if field.shape != (12, 73, 144) or lat.shape != lon.shape:
        raise ValueError('Expected monthly NCEP 2.5-degree grid and matching coordinates')
    if not np.isfinite(field).all() or not np.isfinite(lat).all() or not np.isfinite(lon).all() or (np.abs(lat) > 90).any():
        raise ValueError('Invalid reference or geographic coordinates')
    y, x = (90 - lat) / 2.5, (lon % 360) / 2.5
    i, j = np.floor(y).astype(int), np.floor(x).astype(int)
    a, b = y - i, x - j
    ni, nj = np.minimum(i + 1, 72), (j + 1) % 144
    return ((1-a)*(1-b)*field[:, i, j] + a*(1-b)*field[:, ni, j]
            + (1-a)*b*field[:, i, nj] + a*b*field[:, ni, nj])


def pressure_velocity(pressure, lat, drag, dx, omega, rho):
    px = np.gradient(pressure, axis=-1) / dx
    py = -np.gradient(pressure, axis=-2) / dx
    f = 2 * omega * np.sin(np.radians(lat))
    denominator = rho * (drag ** 2 + f ** 2)
    return -(drag * px + f * py) / denominator, (f * px - drag * py) / denominator
