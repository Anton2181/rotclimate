"""T10c: Earth-analog stand-ins for the Earth-only observed fields (NCEP 500 hPa omega and RH), usable on any grid.

Each target cell takes the distance-weighted mean of its K nearest Earth 2.5-degree samples in a climatic-position
feature space - |latitude|, land share, distance to the coast, distance to the ocean westward and eastward along the
latitude circle, elevation - in LOCAL-SEASON months (southern samples shifted by six, as the mirrored Earth regions
and the northern-hemisphere world use). On Earth, samples within exclude_km of the target region are left out, so the
score measures what transfers to a world cell with no Earth counterpart nearby.
"""
from functools import lru_cache
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

STEP = 2.5
SCALE = dict(alat=4.0, land=0.5, coast=400.0, west=1200.0, east=1200.0, elev=600.0)   # feature units per 1 'distance'
K = 24


def _features(land, elev, lat):
    """land [ny, nx] share, elev [ny, nx] m, lat [ny] deg, on a regular lon-wrapping grid of STEP degrees."""
    ny, nx = land.shape
    km_lat = 111.2 * STEP
    km_lon = np.maximum(km_lat * np.cos(np.radians(lat)), 30.0)[:, None] * np.ones((1, nx))
    isl = land >= 0.5
    coast = ndi.distance_transform_edt(isl) * km_lat
    west = np.zeros((ny, nx)); east = np.zeros((ny, nx))
    for i in range(ny):
        row = isl[i]
        if row.all() or not row.any():
            west[i] = east[i] = 5000.0 * row; continue
        for j in np.where(row)[0]:
            k = 1
            while row[(j - k) % nx] and k < nx: k += 1
            west[i, j] = k * km_lon[i, j]
            k = 1
            while row[(j + k) % nx] and k < nx: k += 1
            east[i, j] = k * km_lon[i, j]
    cap = 5000.0
    return np.stack([np.abs(lat)[:, None] * np.ones((1, nx)), land, np.minimum(coast, cap),
                     np.minimum(west, cap), np.minimum(east, cap), np.where(isl, elev, 0.0)], -1)


def _scaled(F):
    return F / np.array([SCALE[k] for k in ("alat", "land", "coast", "west", "east", "elev")])


@lru_cache(maxsize=1)
def earth_samples():
    """(features [n, 6], lat [n], lon [n], omega [n, 12], rh500 [n, 12]) in local-season months."""
    from . import earth
    lat = 90.0 - STEP / 2 - STEP * np.arange(int(180 / STEP))
    lon = -180.0 + STEP / 2 + STEP * np.arange(int(360 / STEP))
    e = earth._wc("elev")                                        # 5' (2160 x 4320), NaN over sea
    b = int(STEP * 12)
    blk = e.reshape(len(lat), b, len(lon), b)
    land = np.isfinite(blk).mean(axis=(1, 3))
    with np.errstate(invalid="ignore"):
        elev = np.nan_to_num(np.nanmean(blk, axis=(1, 3)))
    F = _features(land, elev, lat)
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    om = earth.observed_omega(LA, LO); rh = earth.observed_rh500(LA, LO)
    south = LA < 0
    om = np.where(south[None], np.roll(om, 6, axis=0), om); rh = np.where(south[None], np.roll(rh, 6, axis=0), rh)
    n = LA.size
    return (F.reshape(n, 6), LA.ravel(), LO.ravel(), om.reshape(12, n).T, rh.reshape(12, n).T,
            dict(lat=lat, lon=lon, F=F))


def earth_features_at(lat, lon):
    """Earth climatic-position features at real (lat, lon) points, sampled from the 2.5-degree sample grid."""
    *_, grid = earth_samples()
    i = np.clip(((90.0 - np.asarray(lat)) / STEP).astype(int), 0, len(grid["lat"]) - 1)
    j = np.clip(((np.asarray(lon) + 180.0) % 360.0 / STEP).astype(int), 0, len(grid["lon"]) - 1)
    return grid["F"][i, j]


def predict(F_target, centre=None, exclude_km=0.0):
    """Analog omega [12, ...] and rh500 [12, ...] (local-season months) for target features [..., 6]."""
    Fs, la, lo, om, rh, _ = earth_samples()
    keep = np.ones(len(la), bool)
    if centre is not None and exclude_km > 0:
        c0, c1 = np.radians(centre[0]), np.radians(centre[1])
        d = 6371.0 * np.arccos(np.clip(np.sin(np.radians(la)) * np.sin(c0)
                                       + np.cos(np.radians(la)) * np.cos(c0) * np.cos(np.radians(lo) - c1), -1, 1))
        keep = d > exclude_km
    tree = cKDTree(_scaled(Fs[keep]))
    shape = F_target.shape[:-1]
    dist, idx = tree.query(_scaled(F_target.reshape(-1, 6)), k=K)
    w = 1.0 / (dist + 0.3) ** 2; w /= w.sum(1, keepdims=True)
    o = np.einsum("nk,nkm->nm", w, om[keep][idx]); r = np.einsum("nk,nkm->nm", w, rh[keep][idx])
    return o.T.reshape((12,) + shape), r.T.reshape((12,) + shape)
