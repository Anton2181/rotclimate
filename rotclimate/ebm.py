"""Planet-wide seasonal energy-balance model (North & Coakley style).

Each equal-area latitude band holds a land column and an ocean (mixed-layer)
column that share one atmosphere: heat diffuses poleward with the zonal mean
temperature, and land and sea exchange heat inside the band.

  C_l dT_l/dt = (1-a_l) Q - (A + B T_l) + D L[T] + nu (T_o - T_l)
  C_o dT_o/dt = (1-a_o) Q - (A + B T_o) + D L[T] + nu f_l/f_o (T_l - T_o)

This is what makes the *axial tilt* and the map's *latitude* physically
meaningful: it supplies the zonal-mean sea-surface temperature and the
"deep continental interior" temperature for every latitude and day, which the
2-D map model then mixes using winds and coastlines.

The constants below were tuned (grid search) so that with Earth's tilt the
model gives Earth-like values between 30 and 60 deg: e.g. at 40 deg the
continental column swings 0 .. 29 C and the sea surface 10 .. 21 C, with the
land peaking ~4 weeks and the sea ~11 weeks after the solstice.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .astronomy import insolation_table

A_OLR = 209.0      # W m-2   (OLR at 0 C)
B_OLR = 2.05       # W m-2 K-1
D_DIFF = 0.50      # W m-2 K-1  (diffusion in x = sin(lat))
D_TROPICS = 2.5    # extra diffusion inside the Hadley cells (flat tropics)
C_LAND = 1.2e7     # J m-2 K-1  (atmosphere column + soil)
C_OCEAN = 1.1e8    # J m-2 K-1  (~26 m mixed layer)
NU = 5.0           # W m-2 K-1  land-sea exchange inside a band
F_LAND = 0.3
N_BANDS = 90


ALB_P2 = 0.15


def _albedo(x, T, surface):
    p2 = 0.5 * (3 * x**2 - 1)
    free = (0.295 if surface == "land" else 0.285) + ALB_P2 * p2
    ice = 0.60 if surface == "land" else 0.55
    w = 0.5 * (1 - np.tanh((T + (2.0 if surface == "land" else 8.0)) / 4.0))
    return free + (ice - free) * w


@lru_cache(maxsize=64)
def _solve(tilt, ecc, peri, ws_day, year_days, years=10):
    from types import SimpleNamespace

    p = SimpleNamespace(tilt=tilt, eccentricity=ecc, perihelion_after_solstice=peri,
                        winter_solstice_day=ws_day, year_days=year_days)
    N = N_BANDS
    xe = np.linspace(-1, 1, N + 1)
    x = 0.5 * (xe[1:] + xe[:-1])
    lat = np.rad2deg(np.arcsin(x))
    dx = xe[1] - xe[0]
    days = np.arange(year_days) + 0.5
    Q = insolation_table(p, lat, days)              # [day, band]

    # diffusion operator L (N x N)
    L = np.zeros((N, N))
    w = (1 - xe**2) * (1 + D_TROPICS * np.exp(-(np.rad2deg(np.arcsin(xe)) / 22.0) ** 2))
    for j in range(N):
        if j > 0:
            L[j, j - 1] += w[j] / dx**2
            L[j, j] -= w[j] / dx**2
        if j < N - 1:
            L[j, j + 1] += w[j + 1] / dx**2
            L[j, j] -= w[j + 1] / dx**2
    fl, fo = F_LAND, 1 - F_LAND
    dt = 86400.0
    I = np.eye(N)
    M = np.block([
        [(C_LAND / dt + B_OLR + NU) * I - D_DIFF * fl * L, -D_DIFF * fo * L - NU * I],
        [-D_DIFF * fl * L - NU * fl / fo * I, (C_OCEAN / dt + B_OLR + NU * fl / fo) * I - D_DIFF * fo * L],
    ])
    Minv = np.linalg.inv(M)

    Tl = 15 - 30 * x**2
    To = Tl.copy()
    out_l = np.zeros((year_days, N))
    out_o = np.zeros((year_days, N))
    for yr in range(years):
        for d in range(year_days):
            Fl = (1 - _albedo(x, Tl, "land")) * Q[d] - A_OLR
            Fo = (1 - _albedo(x, To, "ocean")) * Q[d] - A_OLR
            rhs = np.concatenate([C_LAND / dt * Tl + Fl, C_OCEAN / dt * To + Fo])
            T = Minv @ rhs
            Tl, To = T[:N], T[N:]
            if yr == years - 1:
                out_l[d] = Tl
                out_o[d] = To
    return lat, out_l, out_o


class ZonalClimate:
    """Interpolated EBM output: land / ocean temperature for (lat, day)."""

    def __init__(self, params):
        lat, Tl, To = _solve(round(params.tilt, 3), round(params.eccentricity, 4),
                             round(params.perihelion_after_solstice, 2),
                             round(params.winter_solstice_day, 2), params.year_days)
        self.lat, self.Tl, self.To = lat, Tl, To
        self.Tz = F_LAND * Tl + (1 - F_LAND) * To
        self.year_days = params.year_days

    def _interp(self, arr, lat, day):
        lat = np.asarray(lat, float)
        d = np.asarray(day, float) % self.year_days
        d0 = np.floor(d - 0.5).astype(int) % self.year_days
        d1 = (d0 + 1) % self.year_days
        wd = (d - 0.5) - np.floor(d - 0.5)
        row = (1 - wd) * arr[d0] + wd * arr[d1]
        return np.interp(lat, self.lat, row)

    def land(self, lat, day):
        return self._interp(self.Tl, lat, day)

    def land_annual(self, lat):
        return np.interp(np.asarray(lat, float), self.lat, self.Tl.mean(0))

    def ocean(self, lat, day):
        return self._interp(self.To, lat, day)

    def zonal(self, lat, day):
        return self._interp(self.Tz, lat, day)
