"""Forager language territories from FORGE (calibration/language_areas_20261101/plan.json, layer 1): the Australia test.

    python -I scripts/language_areas_earth.py --out output/language_areas_20261101
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

PLAN = ROOT / "calibration/language_areas_20261101/plan.json"
STEP = 0.5


def grid():
    from rotclimate.earth import _wc
    t = np.stack([_wc("tavg", m) for m in range(1, 13)]); p = np.stack([_wc("prec", m) for m in range(1, 13)])
    f = int(round(STEP * 12)); H, W = t.shape[1] // f, t.shape[2] // f
    lat = 90 - (np.arange(H) + 0.5) * STEP; lon = -180 + (np.arange(W) + 0.5) * STEP
    yy, xx = np.nonzero((lat[:, None] > -39.5) & (lat[:, None] < -10.5) & (lon[None, :] > 112.5) & (lon[None, :] < 154))
    cells = []
    for y, x in zip(yy, xx):
        bt = t[:, y * f:(y + 1) * f, x * f:(x + 1) * f]; bp = p[:, y * f:(y + 1) * f, x * f:(x + 1) * f]
        land = np.isfinite(bt[0])
        if land.mean() < 0.5:
            continue
        cells.append((y, x, lat[y], lon[x], np.nanmean(bt.reshape(12, -1), 1), np.nanmean(bp.reshape(12, -1), 1), land.mean()))
    return cells


def capacity(cells):
    from binford_aquatic_inputs import RADIUS_KM, chord, coast_distance, lake_share, load_lakes, river_points, unit
    from rotclimate.earth import _wc, observed_sst
    from forager_salmon import run_D
    from foraging.forcing import miami_npp, specification
    water = ~np.isfinite(_wc("tavg", 1))
    rp, rw = river_points(); tree = cKDTree(unit(rp[:, 0], rp[:, 1])); lakes = load_lakes()
    disc = math.pi * RADIUS_KM ** 2
    s = dict(T=np.array([c[4] for c in cells]).T, P=np.array([c[5] for c in cells]).T)
    lat = np.array([c[2] for c in cells]); lon = np.array([c[3] for c in cells])
    s["npp"] = miami_npp(s["T"], s["P"])
    s["d_coast_km"] = np.array([coast_distance(water, a, o) for a, o in zip(lat, lon)])
    sst = observed_sst(lat, lon); s["sst_annual_c"] = np.nanmean(np.asarray(sst), 0)
    fresh = []
    for a, o in zip(lat, lon):
        near = tree.query_ball_point(unit(a, o), chord(RADIUS_KM))
        fresh.append(100.0 * float(rw[near].sum()) / disc + 10.0 * lake_share(a, o, lakes))
    s["w_fresh"] = np.array(fresh); s["s_salmon"] = np.zeros(len(cells))
    dens = run_D(s, specification(), 0)["density_people_km2"]
    area = np.array([(111.2 * STEP) ** 2 * math.cos(math.radians(a)) * c[6] for a, c in zip(lat, cells)])
    return dens, area, lat, lon


def simulate(K, nbrs, coords, n_max, seed):
    rng = np.random.default_rng(seed)
    n = len(K); owner = -np.ones(n, int); groups = {}; gid = 0
    start = int(rng.integers(n)); owner[start] = gid; groups[gid] = [start]; gid += 1
    def pop(g): return float(K[groups[g]].sum())
    while (owner < 0).any():
        expandable = [g for g in groups if any(owner[j] < 0 for c in groups[g] for j in nbrs[c])]
        if not expandable:                               # disconnected land: seed a new group there
            c = int(rng.choice(np.flatnonzero(owner < 0))); owner[c] = gid; groups[gid] = [c]; gid += 1; continue
        g = expandable[int(rng.integers(len(expandable)))]
        cand = sorted({j for c in groups[g] for j in nbrs[c] if owner[j] < 0})
        c = cand[int(rng.integers(len(cand)))]; owner[c] = g; groups[g].append(c)
        if pop(g) > n_max and len(groups[g]) > 1:
            cs = np.array(groups[g]); xy = coords[cs]; axis = int(np.ptp(xy[:, 0]) < np.ptp(xy[:, 1]))
            order = cs[np.argsort(xy[:, axis])]; cum = np.cumsum(K[order]); k = int(np.searchsorted(cum, cum[-1] / 2)) + 1
            k = min(max(k, 1), len(order) - 1)
            groups[g] = list(order[:k]); groups[gid] = list(order[k:])
            owner[order[k:]] = gid; gid += 1
    extra = np.maximum(np.ceil(K / n_max) - 1, 0)             # dense cells hold several groups
    return owner, groups, extra


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/language_areas_20261101")
    ap.add_argument("--reps", type=int, default=50)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    cells = grid(); print(len(cells), "land cells", flush=True)
    dens, area, lat, lon = capacity(cells); K = dens * area
    print("FORGE population %.0f, density median %.3f /km2" % (K.sum(), np.median(dens)), flush=True)
    ys = np.array([c[0] for c in cells]); xs = np.array([c[1] for c in cells]); index = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    nbrs = [[index[(y + dy, x + dx)] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (y + dy, x + dx) in index] for y, x in zip(ys, xs)]
    coords = np.column_stack([lon * np.cos(np.radians(lat)), lat])
    langs = [r for r in csv.DictReader(open(ROOT / "data/cache/glottolog/languages.csv")) if r["Level"] == "language" and r["Macroarea"] == "Australia"
             and r["Latitude"] and -39.5 < float(r["Latitude"]) < -10 and 113 < float(r["Longitude"]) < 154 and "AU" in r["Countries"]]
    glat = np.array([float(r["Latitude"]) for r in langs]); glon = np.array([float(r["Longitude"]) for r in langs])
    blk = lambda la, lo: (np.floor((la + 40) / 2).astype(int), np.floor((lo - 112) / 2).astype(int))
    by, bx = blk(lat, lon); keys = sorted(set(zip(by, bx)))
    land_share = {k: 0 for k in keys}
    for k in zip(by, bx): land_share[k] += 1
    keys = [k for k in keys if land_share[k] >= 0.5 * 16]
    gy, gx = blk(glat, glon)
    obs = np.array([np.sum((gy == k[0]) & (gx == k[1])) for k in keys], float)
    pct = json.loads(PLAN.read_text())
    out = dict(plan=str(PLAN.relative_to(ROOT)), cells=len(cells), glottolog_languages=len(langs), forge_population=float(K.sum()), runs={})
    for label, n_max in (("p75_1296", 1296.0), ("twice_median_1124", 1124.0)):
        counts, rich = [], []
        for seed in range(a.reps):
            owner, groups, extra = simulate(K, nbrs, coords, n_max, seed)
            counts.append(len(groups) + int(extra.sum()))
            r = []
            for k in keys:
                m = (by == k[0]) & (bx == k[1])
                r.append(len(set(owner[m])) + extra[m].sum())
            rich.append(r)
        rich = np.array(rich, float).mean(0)
        from scipy.stats import pearsonr, spearmanr
        r2 = float(pearsonr(rich, obs)[0] ** 2); rho = float(spearmanr(rich, obs)[0])
        out["runs"][label] = dict(n_max=n_max, count_mean=float(np.mean(counts)), count_sd=float(np.std(counts)), richness_r2=r2, richness_spearman=rho)
        print(label, out["runs"][label], flush=True)
    bd = np.array([np.log10(np.maximum(dens[(by == k[0]) & (bx == k[1])].mean(), 1e-4)) for k in keys])
    out["correlative_reference_r2"] = float(np.corrcoef(bd, obs)[0, 1] ** 2)
    main_run = out["runs"]["p75_1296"]
    out["adopted"] = bool(277 <= main_run["count_mean"] <= 461 and main_run["richness_r2"] >= 0.30); out["rule"] = pct["adopt_if"]
    (a.out / "australia.json").write_text(json.dumps(out, indent=1))
    np.savez_compressed(a.out / "australia_cells.npz", lat=lat, lon=lon, density=dens, K=K, owner_seed0=simulate(K, nbrs, coords, 1296.0, 0)[0], glat=glat, glon=glon)
    print(json.dumps({k: v for k, v in out.items() if k != "rule"}, indent=1))


if __name__ == "__main__":
    main()
