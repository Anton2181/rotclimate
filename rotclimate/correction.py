"""Earth-trained monthly temperature correction (model output statistics).

The physical model leaves temperature errors that repeat from one Earth region
to the next. The largest is a seasonal lag on maritime coasts in the
westerlies: air over the British Isles, western Europe, New Zealand and
Patagonia follows a sea whose seasonal swing is too large, so spring runs
2-5 C too cold and late autumn too warm (seasons peak 3-4 weeks late).
Arid subtropical interiors also run too cold and some monsoon coasts too warm.

This stage learns the monthly temperature error from the Earth development
regions as two gradient-boosted tree ensembles, evaluated here in numpy:

* shape: the month-to-month pattern of the error (its annual mean removed),
  which carries the phase and amplitude errors; and
* level: the annual-mean error, applied at a reduced weight because region
  levels transfer less reliably between continents.

Inputs are only fields every grid has: the simulated monthly temperature and
rain, the season measured from the winter solstice, latitude, terrain smoothed
over 100, 200 and 400 km, the land share at those scales and the distance to
the coast. No longitude, region name or observation enters, so the same file
applies to an invented map. Corrections of regional rain amounts did not
transfer between continents (see reports/EARTH_CORRECTION_20261030.md); the
separate RainPatternCorrection below only redistributes rain within a domain,
using the simulated winds over the terrain (windward slopes, rain shadows).
A correction is fitted to one physics version and is valid only for runs of
that physics; the raw simulation is always kept alongside it.

    python -I scripts/train_earth_correction.py --run DIR --out calibration/earth_correction_YYYYMMDD
    python -I scripts/train_rain_pattern.py --run DIR --fields DIR --out calibration/earth_rain_pattern_YYYYMMDD
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

SCALES_KM = (100, 200, 400)
COAST_CAP_KM = 1500.0
RAIN_FLOOR_MM = 5.0            # monthly mm added before taking logs of simulated rain
FEATURES = ("lat", "elev", "elev_s100", "elev_s200", "elev_s400", "elev_rel200", "coast_km",
            "land_s100", "land_s200", "land_s400", "T_annual", "T_range", "P_annual_log",
            "season_cos", "season_sin", "T_month", "T_month_anomaly", "P_month_log", "P_month_share")
WIND_FEATURES = ("wind_speed", "upslope_s100", "upslope_s300", "barrier_up150", "barrier_up400",
                 "barrier_down150", "barrier_down400", "sea_up300", "sea_up1000")
RAIN_FEATURES = FEATURES + WIND_FEATURES
BARRIER_SMOOTH_KM = 50.0       # terrain smoothing before looking for ridges up- and downwind
RAIN_OFFSET_MM = 10.0          # monthly mm added to rain before the log ratio
RAIN_LOCAL_KM = 300.0          # the pattern's local mean over this Gaussian scale is removed


def static_features(grid) -> dict:
    """2-D map fields shared by every month: terrain and land share smoothed
    in km (so they mean the same at any cell size), distance to the coast
    and latitude (absolute: mirrored southern grids are already northern).
    Sea counts as zero height."""
    from scipy import ndimage as ndi

    land = np.asarray(grid.land, bool)
    elev = np.where(land, np.asarray(grid.elev, float), 0.0)
    out = dict(lat=np.abs(np.asarray(grid.lat, float)), elev=elev,
               coast_km=np.minimum(ndi.distance_transform_edt(land) * grid.cell_km, COAST_CAP_KM))
    for s in SCALES_KM:
        sigma = s / grid.cell_km
        out[f"elev_s{s}"] = ndi.gaussian_filter(elev, sigma, mode="nearest")
        out[f"land_s{s}"] = ndi.gaussian_filter(land.astype(float), sigma, mode="nearest")
    out["elev_rel200"] = elev - out["elev_s200"]
    return out


def season_phase(year_days=365.0, winter_solstice_day=354.5):
    """Angle of each of the 12 equal months after the winter solstice."""
    centre = (np.arange(12) + 0.5) * year_days / 12.0
    return 2.0 * np.pi * ((centre - winter_solstice_day) % year_days) / year_days


def feature_stack(static_cells: dict, Tm, Pm, phase) -> np.ndarray:
    """[cells, 12, len(FEATURES)] from [12, cells] monthly temperature (C) and
    rain (mm per month) and the static fields at the same cells."""
    Tm, Pm = np.asarray(Tm, float), np.maximum(np.asarray(Pm, float), 0.0)
    if Tm.ndim != 2 or Tm.shape[0] != 12 or Pm.shape != Tm.shape:
        raise ValueError("Expected paired [12, cells] monthly fields")
    n = Tm.shape[1]
    Tann, Pann = Tm.mean(0), Pm.sum(0)
    shared = {k: np.asarray(v, float) for k, v in static_cells.items()}
    shared.update(T_annual=Tann, T_range=Tm.max(0) - Tm.min(0), P_annual_log=np.log(Pann + 50.0))
    X = np.empty((n, 12, len(FEATURES)))
    for m in range(12):
        month = dict(shared, season_cos=np.full(n, np.cos(phase[m])), season_sin=np.full(n, np.sin(phase[m])),
                     T_month=Tm[m], T_month_anomaly=Tm[m] - Tann, P_month_log=np.log(Pm[m] + RAIN_FLOOR_MM),
                     P_month_share=Pm[m] / np.maximum(Pann, 1.0))
        X[:, m] = np.column_stack([month[k] for k in FEATURES])
    return X


@dataclass
class TreeEnsemble:
    """Sum of regression trees: baseline + leaf values (learning rate folded
    in). A sample goes left when feature <= threshold."""
    baseline: float
    offsets: np.ndarray       # [trees + 1] start of each tree in the node arrays
    feature: np.ndarray
    threshold: np.ndarray
    left: np.ndarray          # absolute node indices
    right: np.ndarray
    leaf: np.ndarray          # bool
    value: np.ndarray

    FIELDS = ("offsets", "feature", "threshold", "left", "right", "leaf", "value")

    def predict(self, X) -> np.ndarray:
        X = np.asarray(X, float)
        used = self.feature[~self.leaf]
        if X.ndim != 2 or not np.isfinite(X).all() or (used.size and X.shape[1] <= used.max()):
            raise ValueError("Correction features must be a finite [samples, features] array")
        rows = np.arange(len(X))
        total = np.full(len(X), self.baseline)
        for start in self.offsets[:-1]:
            node = np.full(len(X), start)
            active = ~self.leaf[node]
            while active.any():
                k = node[active]
                go_left = X[rows[active], self.feature[k]] <= self.threshold[k]
                node[active] = np.where(go_left, self.left[k], self.right[k])
                active = ~self.leaf[node]
            total += self.value[node]
        return total

    def arrays(self, prefix):
        out = {f"{prefix}_{k}": getattr(self, k) for k in self.FIELDS}
        out[f"{prefix}_baseline"] = np.array(self.baseline)
        return out

    @classmethod
    def from_arrays(cls, z, prefix):
        return cls(float(z[f"{prefix}_baseline"]), *(np.asarray(z[f"{prefix}_{k}"]) for k in cls.FIELDS))

    @classmethod
    def from_sklearn(cls, model):
        """Export a fitted HistGradientBoostingRegressor (training only)."""
        if model.n_trees_per_iteration_ != 1:
            raise ValueError("Expected a single-output regressor")
        parts, offsets, start = [], [0], 0
        for (tree,) in model._predictors:
            nd = tree.nodes
            if nd["is_categorical"].any():
                raise ValueError("Categorical splits are not supported")
            parts.append((nd["feature_idx"].astype(np.int32), nd["num_threshold"].astype(float),
                          nd["left"].astype(np.int64) + start, nd["right"].astype(np.int64) + start,
                          nd["is_leaf"].astype(bool), nd["value"].astype(float)))
            start += len(nd)
            offsets.append(start)
        cat = [np.concatenate([p[i] for p in parts]) for i in range(6)]
        return cls(float(np.ravel(model._baseline_prediction)[0]), np.array(offsets, np.int64), *cat)


class TemperatureCorrection:
    """Monthly temperature offsets for the land cells of a run."""

    def __init__(self, shape: TreeEnsemble, level: TreeEnsemble, meta: dict):
        self.shape, self.level, self.meta = shape, level, meta

    @property
    def shape_weight(self):
        return float(self.meta["shape_weight"])

    @property
    def level_weight(self):
        return float(self.meta["level_weight"])

    def components(self, static_cells, Tm, Pm, phase):
        """Unweighted (shape [12, cells] with zero annual mean, level [cells])."""
        X = feature_stack(static_cells, Tm, Pm, phase)
        self._check(X)
        n = X.shape[0]
        flat = X.reshape(-1, len(FEATURES))
        shape = self.shape.predict(flat).reshape(n, 12)
        shape -= shape.mean(1, keepdims=True)
        level = self.level.predict(flat).reshape(n, 12).mean(1)
        return shape.T, level

    def offsets(self, static_cells, Tm, Pm, phase):
        """Temperature offset (C) to add, [12, cells]."""
        shape, level = self.components(static_cells, Tm, Pm, phase)
        return self.shape_weight * shape + self.level_weight * level[None]

    def _check(self, X):
        if X.shape[-1] != len(FEATURES):
            raise ValueError("Temperature correction expects the base feature set")

    def apply(self, Tm, Pm, grid, year_days=365.0, winter_solstice_day=354.5, mask=None):
        """Corrected monthly temperature [12, ny, nx]; cells outside mask
        (default: land) keep the raw simulation. Rain is returned unchanged
        by design and is not an output here."""
        mask = np.asarray(grid.land, bool) if mask is None else np.asarray(mask, bool)
        Tc = np.array(Tm, float)
        if mask.any():
            static = static_features(grid)
            Tc[:, mask] += self.offsets({k: v[mask] for k, v in static.items()}, Tc[:, mask],
                                        np.asarray(Pm, float)[:, mask], season_phase(year_days, winter_solstice_day))
        return Tc

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = dict(self.meta, features=list(FEATURES), scales_km=list(SCALES_KM),
                    coast_cap_km=COAST_CAP_KM, rain_floor_mm=RAIN_FLOOR_MM)
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("wb") as stream:
            np.savez_compressed(stream, meta=np.array(json.dumps(meta, sort_keys=True)),
                                **self.shape.arrays("shape"), **self.level.arrays("level"))
        tmp.replace(path)

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            if (tuple(meta["features"]) != FEATURES or tuple(meta["scales_km"]) != SCALES_KM
                    or meta["coast_cap_km"] != COAST_CAP_KM or meta["rain_floor_mm"] != RAIN_FLOOR_MM):
                raise ValueError(f"{path}: correction features differ from this code version")
            return cls(TreeEnsemble.from_arrays(z, "shape"), TreeEnsemble.from_arrays(z, "level"), meta)


def wind_terrain_features(grid, um, vm, mask) -> dict:
    """Monthly wind-over-terrain fields [12, cells] at the masked cells, from
    monthly surface winds um, vm [12, ny, nx] (m/s, east and north; rows run
    south). Lengths are in km, so the fields mean the same at any cell size:

    * upslope_s100/s300: wind along the terrain gradient (smoothed over 100 or
      300 km), the forced vertical motion, mm/s;
    * barrier_up150/400: the highest ground within 150 or 400 km upwind above
      the cell's own (terrain smoothed over 50 km): a rain shadow when positive;
    * barrier_down150/400: the same downwind: the windward approach to a range;
    * sea_up300/1000: the sea share along 300 or 1,000 km upwind (moisture
      supply), and the wind speed.
    """
    from scipy import ndimage as ndi

    um, vm = np.asarray(um, float), np.asarray(vm, float)
    mask = np.asarray(mask, bool)
    if um.shape != vm.shape or um.shape[1:] != mask.shape or um.shape[0] != 12:
        raise ValueError("Expected monthly [12, ny, nx] winds matching the grid")
    cell = float(grid.cell_km)
    land = np.asarray(grid.land, bool)
    h = np.where(land, np.asarray(grid.elev, float), 0.0)
    rows, cols = np.nonzero(mask)
    speed = np.hypot(um, vm)
    ux = um / np.maximum(speed, 1e-6)
    vy = vm / np.maximum(speed, 1e-6)
    out = dict(wind_speed=speed[:, rows, cols])
    for s in (100, 300):
        hs = ndi.gaussian_filter(h, s / cell, mode="nearest")
        hx = np.gradient(hs, axis=1) / (cell * 1e3)
        hy = -np.gradient(hs, axis=0) / (cell * 1e3)
        out[f"upslope_s{s}"] = ((um * hx + vm * hy) * 1e3)[:, rows, cols]
    hb = ndi.gaussian_filter(h, BARRIER_SMOOTH_KM / cell, mode="nearest")
    sea = 1.0 - land.astype(float)
    dx, dy = ux[:, rows, cols], vy[:, rows, cols]          # [12, cells] unit wind
    own = hb[rows, cols]

    def along(field, d, sign):                             # sign +1 downwind, -1 upwind
        r = rows[None] - sign * dy * d / cell
        c = cols[None] + sign * dx * d / cell
        return ndi.map_coordinates(field, [r.ravel(), c.ravel()], order=1, mode="nearest").reshape(r.shape)

    for name, sign, reach in (("barrier_up", -1, 150), ("barrier_up", -1, 400), ("barrier_down", 1, 150), ("barrier_down", 1, 400)):
        best = np.full(dx.shape, -np.inf)
        for d in np.arange(cell / 2, reach + 1e-6, cell / 2):
            best = np.maximum(best, along(hb, d, sign) - own[None])
        out[f"{name}{reach}"] = best
    for reach in (300, 1000):
        steps = np.arange(cell / 2, reach + 1e-6, max(cell / 2, reach / 20))
        out[f"sea_up{reach}"] = sum(along(sea, d, -1) for d in steps) / len(steps)
    return out


def rain_feature_stack(static_cells, wind_cells, Tm, Pm, phase) -> np.ndarray:
    """[cells, 12, len(RAIN_FEATURES)]: the base features plus the wind fields."""
    X = feature_stack(static_cells, Tm, Pm, phase)
    W = np.stack([np.asarray(wind_cells[k], float).T for k in WIND_FEATURES], axis=2)
    return np.concatenate([X, W], axis=2)


def local_mean(values, mask, cell_km, scale_km=RAIN_LOCAL_KM):
    """Gaussian-weighted mean of [12, cells] values over the masked cells
    around each cell (scale in km; cells outside the mask carry no weight)."""
    from scipy import ndimage as ndi

    mask = np.asarray(mask, bool)
    sigma = scale_km / cell_km
    weight = ndi.gaussian_filter(mask.astype(float), sigma, mode="constant")[mask]
    out = np.empty_like(np.asarray(values, float))
    full = np.zeros(mask.shape)
    for m in range(out.shape[0]):
        full[mask] = values[m]
        out[m] = ndi.gaussian_filter(full, sigma, mode="constant")[mask] / np.maximum(weight, 1e-12)
    return out


class RainPatternCorrection:
    """Redistributes simulated rain locally: a monthly log ratio
    log((P_obs + c) / (P_sim + c)) predicted from the wind over the terrain,
    minus its own Gaussian mean over RAIN_LOCAL_KM, so it only moves rain
    between windward slopes, rain shadows and their surroundings; amounts at
    larger scales stay the model's own, on any domain size."""

    def __init__(self, pattern: TreeEnsemble, meta: dict):
        self.pattern, self.meta = pattern, meta

    @property
    def weight(self):
        return float(self.meta["pattern_weight"])

    def log_ratio(self, static_cells, wind_cells, Tm, Pm, phase, mask, cell_km):
        """Unweighted local pattern [12, cells] for the cells of mask (in
        np.nonzero order), with its local mean removed."""
        X = rain_feature_stack(static_cells, wind_cells, Tm, Pm, phase)
        n = X.shape[0]
        r = self.pattern.predict(X.reshape(-1, len(RAIN_FEATURES))).reshape(n, 12).T
        return r - local_mean(r, mask, cell_km)

    def apply_cells(self, static_cells, wind_cells, Tm, Pm, phase, mask, cell_km):
        P = np.maximum(np.asarray(Pm, float), 0.0)
        r = self.log_ratio(static_cells, wind_cells, Tm, P, phase, mask, cell_km)
        return np.maximum((P + RAIN_OFFSET_MM) * np.exp(self.weight * r) - RAIN_OFFSET_MM, 0.0)

    def apply(self, Tm, Pm, um, vm, grid, year_days=365.0, winter_solstice_day=354.5, mask=None):
        """Corrected monthly rain [12, ny, nx] (mm per month) on mask
        (default: drawn land, grid.land & grid.inmap), whose cells alone
        enter the local means; other cells keep the raw simulation."""
        mask = (np.asarray(grid.land, bool) & np.asarray(grid.inmap, bool)) if mask is None else np.asarray(mask, bool)
        Pc = np.maximum(np.array(Pm, float), 0.0)
        if mask.any():
            static = {k: v[mask] for k, v in static_features(grid).items()}
            wind = wind_terrain_features(grid, um, vm, mask)
            Pc[:, mask] = self.apply_cells(static, wind, np.asarray(Tm, float)[:, mask], Pc[:, mask],
                                           season_phase(year_days, winter_solstice_day), mask, grid.cell_km)
        return Pc

    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = dict(self.meta, features=list(RAIN_FEATURES), scales_km=list(SCALES_KM), coast_cap_km=COAST_CAP_KM,
                    rain_floor_mm=RAIN_FLOOR_MM, barrier_smooth_km=BARRIER_SMOOTH_KM, rain_offset_mm=RAIN_OFFSET_MM,
                    rain_local_km=RAIN_LOCAL_KM)
        tmp = path.with_name(path.name + ".tmp")
        with tmp.open("wb") as stream:
            np.savez_compressed(stream, meta=np.array(json.dumps(meta, sort_keys=True)), **self.pattern.arrays("pattern"))
        tmp.replace(path)

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
            if (tuple(meta["features"]) != RAIN_FEATURES or tuple(meta["scales_km"]) != SCALES_KM
                    or meta["barrier_smooth_km"] != BARRIER_SMOOTH_KM or meta["rain_offset_mm"] != RAIN_OFFSET_MM
                    or meta.get("rain_local_km") != RAIN_LOCAL_KM
                    or meta["coast_cap_km"] != COAST_CAP_KM or meta["rain_floor_mm"] != RAIN_FLOOR_MM):
                raise ValueError(f"{path}: rain pattern features differ from this code version")
            return cls(TreeEnsemble.from_arrays(z, "pattern"), meta)
