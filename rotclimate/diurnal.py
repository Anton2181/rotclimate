"""Day/night temperature swing (the diurnal range) for the simulated world.

The climate model works in daily means, so it has no day and night of its
own. The swing is learned from Earth instead: WorldClim 2.1 monthly mean
daily maximum minus minimum (1970-2000) at land cells between 8 and 62 deg
latitude, as a function of things the model does compute:

    monthly precipitation (log), annual precipitation (log), monthly mean
    temperature, its departure from the annual mean, the annual temperature
    range (continentality), elevation, distance from the sea (log) and
    latitude.

Prediction is k-nearest-neighbour regression (k = 40, inverse-distance
weights) on standardised inputs. Holding out whole 60-degree longitude
sectors - one continent at a time - it explains about half the variance of
the monthly range, with a typical error of ~1.8 C (so ~0.9 C on the daily
high and on the daily low). Deserts, high plateaus and continental interiors
swing 15-20 C; rainy coasts 5-8 C.

The training table is data/dtr_knn.npz, built by scripts/build_dtr_model.py.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np

from .config import DATA

FEATURES = ("logP", "logPann", "T", "Tanom", "Tamp", "elev", "ldist", "alat")
K = 40


def features(T, P, elev_m, dist_km, lat) -> np.ndarray:
    """Rows of inputs, one per month and place.

    T, P: [12, ...] monthly mean temperature (C) and precipitation (mm per
    twelfth of a year); elev_m, dist_km, lat broadcast to T.shape[1:].
    Returns [12 * n, len(FEATURES)] in month-major order."""
    T = np.asarray(T, float)
    P = np.maximum(np.asarray(P, float), 0.0)
    sh = T.shape
    cols = dict(
        logP=np.log1p(P),
        logPann=np.broadcast_to(np.log1p(P.sum(0)), sh),
        T=T,
        Tanom=T - T.mean(0),
        Tamp=np.broadcast_to(T.max(0) - T.min(0), sh),
        elev=np.broadcast_to(np.asarray(elev_m, float) / 1000.0, sh),
        ldist=np.broadcast_to(np.log1p(np.maximum(np.asarray(dist_km, float), 0.0)), sh),
        alat=np.broadcast_to(np.abs(np.asarray(lat, float)), sh),
    )
    return np.stack([np.asarray(cols[k], float).reshape(-1) for k in FEATURES], 1)


@lru_cache(maxsize=1)
def _model():
    from scipy.spatial import cKDTree

    d = np.load(DATA / "dtr_knn.npz")
    z = d["z"].astype(np.float32)
    return cKDTree(z), d["y"].astype(np.float32), d["mu"], d["sd"]


def available() -> bool:
    return (DATA / "dtr_knn.npz").exists()


def dtr(T, P, elev_m, dist_km, lat) -> np.ndarray:
    """Monthly mean day/night range (C), same shape as T ([12, ...])."""
    T = np.asarray(T, float)
    tree, y, mu, sd = _model()
    X = (features(T, P, elev_m, dist_km, lat) - mu) / sd
    dd, ii = tree.query(X, k=K, workers=-1)
    w = 1.0 / (dd + 0.05)
    return ((y[ii] * w).sum(1) / w.sum(1)).reshape(T.shape)


def coast_distance_km(land: np.ndarray, cell_km: float) -> np.ndarray:
    """Distance (km) from each land cell to the nearest water cell."""
    from scipy import ndimage as ndi

    return ndi.distance_transform_edt(land) * cell_km


_GRID_CACHE: dict = {}


def grid_dtr12(result) -> np.ndarray:
    """Day/night range [12, ny, nx] (C) for a model run, in the same 12
    solstice-aligned bins as analogs.model_bins; NaN over water."""
    key = id(result)
    if key in _GRID_CACHE:
        return _GRID_CACHE[key]
    from .analogs import model_bins

    g, p = result.grid, result.params
    T12, P12 = model_bins(result.T, result.P, result.days, p.winter_solstice_day, p.year_days)
    dist = coast_distance_km(g.land, g.cell_km)
    D = np.full(T12.shape, np.nan)
    m = g.land
    D[:, m] = dtr(T12[:, m], P12[:, m], g.elev[m], dist[m], g.lat[m])
    _GRID_CACHE.clear()
    _GRID_CACHE[key] = D
    return D


def at_days(D12, days, winter_solstice_day, year_days=365.0) -> np.ndarray:
    """Interpolate 12 solstice-aligned bins (first axis of D12) to days of the
    year, periodically."""
    D12 = np.asarray(D12, float)
    centers = (np.arange(12) + 0.5) * year_days / 12
    xp = np.concatenate([centers - year_days, centers, centers + year_days])
    fp = np.concatenate([D12, D12, D12])
    ph = (np.asarray(days, float) - winter_solstice_day) % year_days
    flat = fp.reshape(36, -1)
    out = np.stack([np.interp(ph, xp, flat[:, j]) for j in range(flat.shape[1])], -1)
    return out.reshape(ph.shape + D12.shape[1:])
