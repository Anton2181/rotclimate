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


def grid(window=None):
    from rotclimate.earth import _wc
    t = np.stack([_wc("tavg", m) for m in range(1, 13)]); p = np.stack([_wc("prec", m) for m in range(1, 13)])
    f = int(round(STEP * 12)); H, W = t.shape[1] // f, t.shape[2] // f
    lat = 90 - (np.arange(H) + 0.5) * STEP; lon = -180 + (np.arange(W) + 0.5) * STEP
    if window is None:
        window = lambda la, lo: (la > -39.5) & (la < -10.5) & (lo > 112.5) & (lo < 154)
    yy, xx = np.nonzero(window(lat[:, None], lon[None, :]))
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


def simulate_fast(K, nbrs, coords, n_max, seed):
    """Layer 1b: frontier-driven fill (same rules, faster): a random empty cell next to occupied land joins a random neighbouring group."""
    rng = np.random.default_rng(seed)
    n = len(K); owner = -np.ones(n, int); groups = {}; pops = {}; gid = 0
    front, pos = [], {}
    def add_front(c):
        if owner[c] < 0 and c not in pos:
            pos[c] = len(front); front.append(c)
    def pop_front(i):
        c = front[i]; last = front.pop()
        if i < len(front):
            front[i] = last; pos[last] = i
        del pos[c]; return c
    def seed_at(c):
        nonlocal gid
        owner[c] = gid; groups[gid] = [c]; pops[gid] = float(K[c]); gid += 1
        for j in nbrs[c]: add_front(j)
    seed_at(int(rng.integers(n))); left = n - 1
    while left > 0:
        if not front:
            seed_at(int(rng.choice(np.flatnonzero(owner < 0)))); left -= 1; continue
        c = pop_front(int(rng.integers(len(front))))
        adj = [owner[j] for j in nbrs[c] if owner[j] >= 0]
        g = adj[int(rng.integers(len(adj)))]
        owner[c] = g; groups[g].append(c); pops[g] += float(K[c]); left -= 1
        for j in nbrs[c]: add_front(j)
        if pops[g] > n_max and len(groups[g]) > 1:
            cs = np.array(groups[g]); xy = coords[cs]; axis = int(np.ptp(xy[:, 0]) < np.ptp(xy[:, 1]))
            order = cs[np.argsort(xy[:, axis])]; cum = np.cumsum(K[order]); k = int(np.searchsorted(cum, cum[-1] / 2)) + 1
            k = min(max(k, 1), len(order) - 1)
            groups[g] = list(order[:k]); pops[g] = float(K[order[:k]].sum())
            groups[gid] = list(order[k:]); pops[gid] = float(K[order[k:]].sum()); owner[order[k:]] = gid; gid += 1
    extra = np.maximum(np.ceil(K / n_max) - 1, 0)
    return owner, groups, extra


def window_setup(window, region_filter):
    cells = grid(window)
    dens, area, lat, lon = capacity(cells)
    ys = np.array([c[0] for c in cells]); xs = np.array([c[1] for c in cells]); index = {(y, x): i for i, (y, x) in enumerate(zip(ys, xs))}
    nbrs = [[index[(y + dy, x + dx)] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (y + dy, x + dx) in index] for y, x in zip(ys, xs)]
    coords = np.column_stack([lon * np.cos(np.radians(lat)), lat])
    langs = [r for r in csv.DictReader(open(ROOT / "data/cache/glottolog/languages.csv")) if r["Level"] == "language" and r["Latitude"] and region_filter(r)]
    P = np.array([c[5].sum() for c in cells])
    return dict(cells=cells, dens=dens, area=area, lat=lat, lon=lon, nbrs=nbrs, coords=coords, P=P,
                glat=np.array([float(r["Latitude"]) for r in langs]), glon=np.array([float(r["Longitude"]) for r in langs]))


def rain_density(P):
    """log10 density = a + b log10 annual rain, fitted on Binford's 280 groups (no languages involved)."""
    from forager_earth_test import binford, site_climate, worldclim_months
    df = binford(); df = df[(df["subpop"] == "n") & (df["density"].astype(float) > 0)]
    tavg, prec = worldclim_months(); x, y = [], []
    for _, r in df.iterrows():
        c = site_climate(tavg, prec, float(r["latitude"]), float(r["longitude"]))
        if c is None:
            continue
        x.append(np.log10(max(np.sum(c[1]), 1.0))); y.append(np.log10(float(r["density"]) / 100.0))
    b, a = np.polyfit(x, y, 1)
    return 10 ** (a + b * np.log10(np.maximum(P, 1.0))), dict(a=float(a), b=float(b))


def richness(W, owner, extra):
    blk = lambda la, lo: (np.floor((la + 90) / 2).astype(int), np.floor((lo + 180) / 2).astype(int))
    by, bx = blk(W["lat"], W["lon"]); keys = sorted(set(zip(by, bx)))
    cnt = {k: 0 for k in keys}
    for k in zip(by, bx): cnt[k] += 1
    keys = [k for k in keys if cnt[k] >= 8]
    gy, gx = blk(W["glat"], W["glon"])
    obs = np.array([np.sum((gy == k[0]) & (gx == k[1])) for k in keys], float)
    sim = np.array([len(set(owner[(by == k[0]) & (bx == k[1])])) + extra[(by == k[0]) & (bx == k[1])].sum() for k in keys], float)
    return sim, obs


def stage_1b(out):
    from scipy.stats import pearsonr, spearmanr
    na_window = lambda la, lo: (((lo > -170) & (lo < -105) & (la > 32)) | ((lo > -170) & (lo < -52) & (la > 55))) & (la < 72)
    na_filter = lambda r: r["Macroarea"] == "North America" and na_window(float(r["Latitude"]), float(r["Longitude"])) and \
        any(c in r["Countries"] for c in ("US", "CA"))
    au_filter = lambda r: r["Macroarea"] == "Australia" and -39.5 < float(r["Latitude"]) < -10 and 113 < float(r["Longitude"]) < 154 and "AU" in r["Countries"]
    NA = window_setup(na_window, na_filter); AU = window_setup(None, au_filter)
    print("North America window:", len(NA["cells"]), "cells,", len(NA["glat"]), "Glottolog languages; Australia:", len(AU["cells"]), len(AU["glat"]), flush=True)
    res = dict(plan="calibration/language_areas_20261101/plan_1b.json", na_cells=len(NA["cells"]), na_languages=int(len(NA["glat"])),
               au_languages=int(len(AU["glat"])), variants={})
    for variant in ("forge", "rain"):
        if variant == "forge":
            Kna, Kau = NA["dens"] * NA["area"], AU["dens"] * AU["area"]; fit = None
        else:
            dna, fit = rain_density(NA["P"]); dau, _ = rain_density(AU["P"]); Kna, Kau = dna * NA["area"], dau * AU["area"]
        cal = {}
        for nm in (500, 750, 1000, 1500, 2000, 3000, 4000, 6000):
            counts = []
            for seed in range(20):
                o, g, e = simulate_fast(Kna, NA["nbrs"], NA["coords"], float(nm), seed); counts.append(len(g) + int(e.sum()))
            cal[nm] = float(np.mean(counts)); print(variant, "N_max", nm, "NA count", round(cal[nm], 1), flush=True)
        best = min(cal, key=lambda k: (abs(cal[k] - len(NA["glat"])), k))
        counts, rich = [], []
        for seed in range(50):
            o, g, e = simulate_fast(Kau, AU["nbrs"], AU["coords"], float(best), seed); counts.append(len(g) + int(e.sum()))
            sim, obs = richness(AU, o, e); rich.append(sim)
        sim = np.mean(rich, 0)
        res["variants"][variant] = dict(rain_fit=fit, na_population=float(Kna.sum()), au_population=float(Kau.sum()), calibration=cal, n_max=best,
                                        au_count_mean=float(np.mean(counts)), au_count_sd=float(np.std(counts)),
                                        au_richness_r2=float(pearsonr(sim, obs)[0] ** 2), au_richness_spearman=float(spearmanr(sim, obs)[0]))
        print(variant, json.dumps(res["variants"][variant]), flush=True)
    f = res["variants"]["forge"]
    res["adopted"] = bool(277 <= f["au_count_mean"] <= 461 and f["au_richness_r2"] >= 0.30)
    (out / "layer1b.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(adopted=res["adopted"]), indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/language_areas_20261101")
    ap.add_argument("--reps", type=int, default=50)
    ap.add_argument("--stage", default="1")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    if a.stage == "1b":
        return stage_1b(a.out)
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
