"""Forest share in walking cost (C2, calibration/forest_travel_20261116/plan.json; adopted narrowly on Earth 16 Nov 2026).

Opt-in: ROTCLIMATE_FOREST_TRAVEL=1. Walking coefficient = open x (1 - f) + forest x f, where f is the Earth-fitted C1b forest
share (scripts/forest_map.py; 0.60 x moisture ramp x warmth ramp), open = the biome coefficient with forest biomes at 1.2 and
forest = the forest biome's coefficient, else 1.5. Swamp and snow as polity.control.terrain_coefficient. Horse travel keeps
its biome forest flag."""
import copy
import os
import numpy as np

FOREST_BIOMES = (3, 4, 7, 9)


def enabled():
    return os.environ.get('ROTCLIMATE_FOREST_TRAVEL', '0') not in ('', '0')


def share(t, p, dtr, lat, tilt, solstice_day):
    """C1b forest share from monthly mean temperature t, rain p (mm), diurnal range dtr, latitude (12 x ... arrays)."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    import land_people as LP
    shp = t.shape[1:]
    pet = LP.hargreaves(t.reshape(12, -1), np.maximum(dtr, 0.1).reshape(12, -1),
                        LP.sunlight_top(np.broadcast_to(lat, shp).ravel(), tilt, solstice_day)).reshape(t.shape)
    ai = p.sum(0) / np.maximum(pet.sum(0), 1.0); gdd = np.sum(np.maximum(t - 5.0, 0.0), 0) * LP.DAYS
    return 0.60 * np.clip((ai - 0.3) / 0.2, 0, 1) * np.clip((gdd - 300.0) / 300.0, 0, 1)


def map_forest(data, meta, mode, shape):
    """The atlas's forest share (raw or corrected climate) on a grid of the given shape (nearest cell)."""
    from harvest.export import climate_arrays, surface_months
    m = copy.deepcopy(meta); folder = data
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'):
            m[k] = meta['corrected_climate'][k]
        folder = data / 'corrected'
    a = climate_arrays(folder, m); t, p, d, lat = surface_months(m, a)
    f = share(t, p, d, lat, meta['world']['tilt'], float(meta.get('solstice_day', 22.0)))
    h, w = shape
    return f[(np.arange(h) * f.shape[0] // h)][:, (np.arange(w) * f.shape[1] // w)]


def coefficient(biome, swamp, forest, base_table, swamp_coefficient):
    b = np.asarray(biome).astype(int); base = np.vectorize(lambda v: base_table.get(int(v), 1.2))(b)
    fb = np.isin(b, FOREST_BIOMES); f = np.clip(np.asarray(forest, float), 0, 1)
    eta = np.where(fb, 1.2, base) * (1 - f) + np.where(fb, base, 1.5) * f
    return np.where(swamp, np.maximum(eta, swamp_coefficient), eta)
