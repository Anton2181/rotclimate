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
from .numerics import matrix_product

A_OLR = 209.0      # W m-2   (OLR at 0 C)
B_OLR = 2.05       # W m-2 K-1
D_DIFF = 0.50      # W m-2 K-1  (diffusion in x = sin(lat))
D_TROPICS = 2.5    # extra diffusion inside the Hadley cells (flat tropics)
C_LAND = 1.2e7     # J m-2 K-1  (atmosphere column + soil)
C_OCEAN = 1.1e8    # J m-2 K-1  (~26 m mixed layer)
NU = 5.0           # W m-2 K-1  land-sea exchange inside a band
F_LAND = 0.3
N_BANDS = 90

# Earth's land fraction in 2-degree bands from 90 S to 90 N (WorldClim 2.1 5'
# land mask, Antarctica included). The southern mid-latitudes are nearly all
# sea (5 % land at 40 S against 48 % at 40 N): with a uniform 30 % the model
# gave South America's summers 6-9 C too hot and the Sahara's 4-8 C too cool.
EARTH_LAND = (
    1.0, 1.0, 0.986, 0.901, 0.801, 0.79, 0.766, 0.688, 0.579, 0.48, 0.322, 0.167, 0.013, 0.005, 0.001, 0.0, 0.0,
    0.014, 0.017, 0.021, 0.026, 0.027, 0.035, 0.04, 0.042, 0.052, 0.078, 0.094, 0.155, 0.196, 0.212, 0.221, 0.233,
    0.251, 0.252, 0.239, 0.249, 0.233, 0.212, 0.2, 0.229, 0.248, 0.248, 0.262, 0.244, 0.229, 0.211, 0.228, 0.248,
    0.258, 0.242, 0.24, 0.264, 0.291, 0.321, 0.34, 0.371, 0.38, 0.406, 0.426, 0.445, 0.418, 0.429, 0.442, 0.452,
    0.48, 0.494, 0.536, 0.567, 0.581, 0.601, 0.618, 0.572, 0.555, 0.571, 0.674, 0.73, 0.785, 0.78, 0.677, 0.468,
    0.339, 0.268, 0.239, 0.252, 0.237, 0.085, 0.0, 0.0, 0.0)


def land_profile(name):
    """Land fraction per 2-degree band (90 S .. 90 N), or None for uniform."""
    if name in (None, "", "uniform"):
        return None
    if name == "earth":
        return EARTH_LAND
    if name == "earth_mirrored":          # southern regions run as their northern mirror image
        return EARTH_LAND[::-1]
    raise ValueError(f"unknown ebm_land profile {name!r}")


ALB_P2 = 0.15


def _albedo(x, T, surface):
    p2 = 0.5 * (3 * x**2 - 1)
    free = (0.295 if surface == "land" else 0.285) + ALB_P2 * p2
    ice = 0.60 if surface == "land" else 0.55
    w = 0.5 * (1 - np.tanh((T + (2.0 if surface == "land" else 8.0)) / 4.0))
    return free + (ice - free) * w


def _band_land(lat, profile):
    if profile is None:
        return np.full(lat.shape, F_LAND)
    centres = np.arange(-89.0, 90.0, 2.0)
    return np.clip(np.interp(lat, centres, np.asarray(profile, float)), 0.02, 0.95)


@lru_cache(maxsize=64)
def _solve(tilt, ecc, peri, ws_day, year_days, years=10, c_land_scale=1.0, profile=None, ocean_transport=0.0,
           c_ocean_scale=1.0, c_ocean_season=0.0):
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
    fl = _band_land(lat, profile)
    fo = 1 - fl
    # land-sea exchange per unit land area: NU at the uniform 30 % land, more
    # where the land is a thin strip in a wide ocean, less inside big
    # continents (exchange runs across coastlines)
    nu = NU * fo / (1 - F_LAND) if profile is not None else np.full(N, NU)
    C_L = C_LAND * c_land_scale     # e1: heat capacity of the land column (seasonal lag)
    C_O = C_OCEAN * c_ocean_scale   # mixed-layer heat capacity (1 = ~26 m; the effective seasonal layer is deeper)
    dt = 86400.0
    I = np.eye(N)
    Lfl, Lfo = L * fl[None, :], L * fo[None, :]     # diffusion of the zonal mean fl T_l + fo T_o
    M = np.block([
        [np.diag(C_L / dt + B_OLR + nu) - D_DIFF * Lfl, -D_DIFF * Lfo - np.diag(nu)],
        [-D_DIFF * Lfl - np.diag(nu * fl / fo), np.diag(C_O / dt + B_OLR + nu * fl / fo) - D_DIFF * Lfo],
    ])
    if ocean_transport > 0:
        # e27: the oceans carry heat poleward themselves (~2 PW: gyres and the
        # overturning circulation), which the zonal diffusion of the column
        # leaves to the air: without it the sea ran several degrees too cold
        # at 45-60 deg and too warm in the subtropics. A flux-form diffusion of
        # the ocean temperature through the ocean's share of each band, per
        # unit ocean area, ocean_transport x D_DIFF.
        fo_e = np.interp(xe, x, fo)
        wo = (1 - xe**2) * fo_e
        Lo = np.zeros((N, N))
        for j in range(N):
            if j > 0:
                Lo[j, j - 1] += wo[j] / dx**2
                Lo[j, j] -= wo[j] / dx**2
            if j < N - 1:
                Lo[j, j + 1] += wo[j + 1] / dx**2
                Lo[j, j] -= wo[j + 1] / dx**2
        M[N:, N:] -= ocean_transport * D_DIFF * Lo / fo[:, None]
    Minv = np.linalg.inv(M)

    Tl = 15 - 30 * x**2
    To = Tl.copy()
    out_l = np.zeros((year_days, N))
    out_o = np.zeros((year_days, N))
    year_o = np.zeros((year_days, N))
    T_deep = To.copy()
    if c_ocean_season > 0:
        # e29: the mixed layer shoals as spring warming stratifies the sea and
        # deepens as winter cooling overturns it (mid-latitude ~20 m in late
        # summer, ~100 m in late winter): the sea warms fast and cools slowly.
        # Heat capacity x (1 - c_ocean_season x w x s), s = +1 a month after
        # the local summer solstice, w ramping in over 0-30 deg of latitude.
        w = np.clip(np.abs(lat) / 30.0, 0.0, 1.0) * np.sign(lat)
        s_nh = -np.cos(2 * np.pi * (days - ws_day - 30.0) / year_days)
        C_Od = C_O * (1.0 - c_ocean_season * w[None, :] * s_nh[:, None])       # [day, band]
    for yr in range(years):
        for d in range(year_days):
            Fl = (1 - _albedo(x, Tl, "land")) * Q[d] - A_OLR
            Fo = (1 - _albedo(x, To, "ocean")) * Q[d] - A_OLR
            if c_ocean_season > 0:
                # a deepening layer entrains water from below the mixed layer
                # (taken at last year's annual mean); a shoaling one leaves its
                # heat behind, so the layer keeps its temperature
                prev = C_Od[d - 1]
                deeper = C_Od[d] > prev
                To = np.where(deeper, (prev * To + (C_Od[d] - prev) * T_deep) / C_Od[d], To)
                Md = M.copy()
                Md[N:, N:] += np.diag((C_Od[d] - C_O) / dt)
                T = np.linalg.solve(Md, np.concatenate([C_L / dt * Tl + Fl, C_Od[d] / dt * To + Fo]))
            else:
                rhs = np.concatenate([C_L / dt * Tl + Fl, C_O / dt * To + Fo])
                T = matrix_product(Minv, rhs)
            Tl, To = T[:N], T[N:]
            year_o[d] = To
            if yr == years - 1:
                out_l[d] = Tl
                out_o[d] = To
        T_deep = year_o.mean(0)
    return lat, out_l, out_o, fl


class ZonalClimate:
    """Interpolated EBM output: land / ocean temperature for (lat, day)."""

    def __init__(self, params):
        scale = round(getattr(params, "land_heat_capacity", 1.0), 3)
        extra = {} if scale == 1.0 else {"c_land_scale": scale}
        profile = land_profile(getattr(params, "ebm_land", "uniform"))
        if profile is not None:
            extra["profile"] = profile
        if getattr(params, "ocean_transport", 0.0) > 0:
            extra["ocean_transport"] = round(params.ocean_transport, 3)
        if getattr(params, "ocean_heat_capacity", 1.0) != 1.0:
            extra["c_ocean_scale"] = round(params.ocean_heat_capacity, 3)
        if getattr(params, "ocean_mixed_seasonality", 0.0) > 0:
            extra["c_ocean_season"] = round(params.ocean_mixed_seasonality, 3)
        lat, Tl, To, fl = _solve(round(params.tilt, 3), round(params.eccentricity, 4),
                                 round(params.perihelion_after_solstice, 2),
                                 round(params.winter_solstice_day, 2), params.year_days, **extra)
        self.lat, self.Tl, self.To = lat, Tl, To
        self.Tz = fl * Tl + (1 - fl) * To
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
