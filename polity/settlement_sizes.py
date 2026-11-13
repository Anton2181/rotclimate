"""Earth-calibrated settlement area/resident model (release 2).

Small pure functions shared by the Earth calibration and the fantasy rebuild.
Areas are hectares. Residents come from a declared density scenario and are
never treated as independent observations.
"""
from __future__ import annotations

import hashlib

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

MAX_HINTERLAND_KM = 60.0
CLIP_SIGMA = 2.5


def hinterlands(centres, land, people, cell_km, max_km=MAX_HINTERLAND_KM):
    """Nearest-centre partition of land cells within max_km.

    centres: (n, 2) integer row/col, distinct. A cell exactly equidistant from
    several nearest centres is shared equally between them (common on an
    integer grid; no arbitrary tie order). Returns (cell_flat_index,
    centre_index, weight) triples and the people summed by centre.
    """
    centres = np.asarray(centres, int).reshape(-1, 2)
    land = np.asarray(land, bool)
    if len({(int(r), int(c)) for r, c in centres}) != len(centres):
        raise ValueError('Distinct centre cells required')
    rows, cols = np.nonzero(land)
    k = min(8, len(centres))
    dist, idx = cKDTree(centres.astype(float)).query(np.column_stack([rows, cols]).astype(float), k=k)
    dist, idx = dist.reshape(len(rows), k), idx.reshape(len(rows), k)
    # integer grid: squared distances are exact integers, so ties are exact
    d2 = np.rint(dist ** 2).astype(np.int64)
    tied = d2 == d2[:, :1]
    if k > 1 and tied[:, -1].any():
        raise ValueError('More equidistant centres than the tie search covers')
    near = d2[:, 0] * float(cell_km) ** 2 <= max_km ** 2
    tied &= near[:, None]
    weight = tied / np.maximum(tied.sum(1, keepdims=True), 1)
    cell_index = np.repeat((rows * land.shape[1] + cols)[:, None], k, 1)[tied]
    centre_index = idx[tied]; w = weight[tied]
    total = np.bincount(centre_index, weights=w * np.asarray(people, float).ravel()[cell_index], minlength=len(centres))
    return (cell_index, centre_index, w), total


def site_predictors(centres, land, water_km, road, cell_km, core_km):
    """coast, river, road, core columns for centre cells (declared definitions)."""
    centres = np.asarray(centres, int).reshape(-1, 2)
    r, c = centres[:, 0], centres[:, 1]
    coast_km = ndi.distance_transform_edt(land) * cell_km
    road_km = ndi.distance_transform_edt(~np.asarray(road, bool)) * cell_km
    water = np.nan_to_num(np.asarray(water_km, float), nan=1e9)
    return dict(coast=(coast_km[r, c] <= cell_km).astype(float),
                river=(water[r, c] <= 3.0).astype(float),
                road=(road_km[r, c] <= cell_km * 1.5).astype(float),
                core=np.asarray(core_km, float)[r, c] / 1000.0)


MODELS = {'M0': (), 'M1': ('lnH',), 'M2': ('lnH', 'coast', 'river', 'road'),
          'M3': ('lnH', 'coast', 'river', 'road', 'core')}


def design(columns, names):
    n = len(next(iter(columns.values())))
    return np.column_stack([np.ones(n)] + [np.asarray(columns[k], float) for k in names])


def fit(columns, names, y):
    coef, *_ = np.linalg.lstsq(design(columns, names), np.asarray(y, float), rcond=None)
    return coef


def predict(columns, names, coef):
    return design(columns, names) @ np.asarray(coef, float)


def province_fold(name):
    return hashlib.sha256(name.encode('utf-8')).digest()[0] % 4


def draws(n, seed):
    return np.clip(np.random.default_rng(seed).standard_normal(n), -CLIP_SIGMA, CLIP_SIGMA)


def generate_area(mean_ln, sigma, e, low_ha, high_ha):
    return np.clip(np.exp(np.asarray(mean_ln, float) + sigma * np.asarray(e, float)), low_ha, high_ha)


def density_per_ha(area_ha, scenario='central'):
    """Declared resident-density scenarios (persons per hectare)."""
    a = np.asarray(area_ha, float)
    if scenario == 'low':
        return np.full(a.shape, 100.0)
    if scenario != 'central':
        raise ValueError('Unknown density scenario')
    t = np.clip((np.log(np.maximum(a, 1e-9)) - np.log(50.0)) / (np.log(400.0) - np.log(50.0)), 0.0, 1.0)
    return 100.0 + 400.0 * t


def residents(area_ha, scenario='central'):
    return np.asarray(area_ha, float) * density_per_ha(area_ha, scenario)
