"""Earth calibration of the atlas's unmarked-town model (calibration/settlement_model_20261107/plan.json).

    .venv/bin/python -I scripts/settlement_model_earth.py prepare      # pool inputs (development pools only)
    .venv/bin/python -I scripts/settlement_model_earth.py grid         # development grid over the site weights
    .venv/bin/python -I scripts/settlement_model_earth.py blind        # the single blind evaluation (after the grid)
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/settlement_model_20261107"
PLAN = ROOT / "calibration/settlement_model_20261107/plan.json"
GRID = dict(a=[0.5, 1.0, 1.5], w_r=[0.0, 1.0, 3.0], w_c=[0.0, 0.5, 1.5], w_d=[0.0, 0.5, 1.5], k_f=[0.0, 20.0, 60.0])
CURRENT = dict(a=1.0, w_r=1.0, w_c=0.5, w_d=0.5, k_f=20.0)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def inputs(g, road, allowed):
    """Model inputs on an Earth window: density, water distance, aridity (P / Hargreaves PET)."""
    import land_people_earth as LPE
    from land_people import hargreaves, sunlight_top
    land = g["land"].astype(bool)
    water_km = ndi.distance_transform_edt(~g["river"].astype(bool)) * g["cell_km"]
    T = g["tavg"].astype(float); P = g["prec"].astype(float); D = (g["tmax"] - g["tmin"]).astype(float)
    PET = hargreaves(T.reshape(12, -1), D.reshape(12, -1), sunlight_top(g["lat"].ravel(), LPE.TILT, LPE.WS_DAY)).reshape(T.shape)
    aridity = P.sum(0) / np.maximum(PET.sum(0), 1e-6)
    return dict(density=np.where(land, g["density"], 0.0), land=land, water_km=water_km, road=road, elev=g["elev"].astype(float),
                cell_km=float(g["cell_km"]), aridity=aridity, allowed=allowed & land)


def prepare():
    import polity_earth_check as P
    from polity import earth as E
    OUT.mkdir(parents=True, exist_ok=True)
    pools = {}
    g = P.load_window("rome"); land = g["land"].astype(bool); W = land.shape[1]
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    t = E.hanson_towns(150); r, c, ok = P.snap(g, np.array([x["lat"] for x in t]), np.array([x["lon"] for x in t]))
    pools["rome_150"] = (g, road, E.inside_polygons(g, E.cliopatria("Roman Empire", 150)), np.unique((r * W + c)[ok]))
    g = P.load_window("han"); land = g["land"].astype(bool); W = land.shape[1]
    s = E.han_seats(); r, c, ok = P.snap(g, np.array([x["lat"] for x in s]), np.array([x["lon"] for x in s]))
    ids, _ = E.han_commanderies(g)
    pools["han_2"] = (g, np.zeros(land.shape, bool), ids >= 0, np.unique((r * W + c)[ok]))
    B = ROOT / "output/earth_control_20261106/blind"
    g = dict(np.load(B / "B1_window.npz"))
    for k in ("cell_km", "lat0", "lon0"):
        g[k] = float(g[k])
    st = dict(np.load(B / "B1_setup.npz"))
    pools["hellenistic"] = (g, np.zeros(g["land"].shape, bool), st["inside"], st["nodes"])
    for name, (g, road, allowed, nodes) in pools.items():
        x = inputs(g, road, allowed)
        np.savez_compressed(OUT / f"{name}_inputs.npz", **x, real=nodes, lat=g["lat"], lon=g["lon"])
        log(f"{name}: {len(nodes)} real towns, allowed land {x['allowed'].sum():,} cells")


def place(x, weights, spacing=None, max_count=None, score_override=None):
    from polity.settle import place_towns
    towns, _, _ = place_towns(x["density"], x["land"], x["water_km"], x["road"], x["elev"], float(x["cell_km"]), [],
                              allowed=x["allowed"], seed=1, aridity=x["aridity"], weights=weights, spacing=spacing, max_count=max_count,
                              score_override=score_override)
    return towns


SPACINGS = [0.4, 0.6, 0.8, 1.0, 1.3, 1.6]
FEATURES = ["log_food", "river3", "river15", "coast6", "coast30", "elev_km", "slope", "rel_elev", "log_arid", "road4"]


def features(x):
    """Map-derivable site fields (amendment 2)."""
    land = x["land"]; cell = float(x["cell_km"])
    coast = ndi.distance_transform_edt(land) * cell
    gy, gx = np.gradient(x["elev"], cell * 1000.0)
    road = x["road"].astype(bool)
    road_km = ndi.distance_transform_edt(~road) * cell if road.any() else np.full(land.shape, 1e9)
    f = dict(log_food=np.log1p(ndi.gaussian_filter(x["density"], 1.0)), river3=np.exp(-x["water_km"] / 3.0), river15=np.exp(-x["water_km"] / 15.0),
             coast6=(coast <= 6.0).astype(float), coast30=np.exp(-coast / 30.0), elev_km=x["elev"] / 1000.0, slope=np.hypot(gx, gy) * 100.0,
             rel_elev=(x["elev"] - ndi.gaussian_filter(x["elev"], 50.0 / cell)) / 1000.0, log_arid=np.log(np.clip(x["aridity"], 0.02, 5.0)),
             road4=(road_km <= 4.0).astype(float))
    return np.stack([f[k] for k in FEATURES], -1)


def fit_suitability(pools, names, seed=1):
    from sklearn.linear_model import LogisticRegression
    X, y, g = [], [], []
    rng = np.random.default_rng(seed)
    for i, p in enumerate(names):
        x = pools[p]; F = features(x).reshape(-1, len(FEATURES)); W = x["land"].shape[1]
        real = np.asarray(x["real"]); real = real[x["allowed"].ravel()[real]]
        allowed = np.flatnonzero(x["allowed"].ravel())
        bg = rng.choice(allowed, size=min(len(allowed), 10 * len(real)), replace=False)
        X += [F[real], F[bg]]; y += [np.ones(len(real)), np.zeros(len(bg))]; g += [np.full(len(real) + len(bg), i)]
    X = np.concatenate(X); y = np.concatenate(y); g = np.concatenate(g)
    mu, sd = X.mean(0), X.std(0) + 1e-9
    D = np.c_[(X - mu) / sd, np.eye(len(names))[g]]                 # one intercept per pool
    m = LogisticRegression(C=1.0, fit_intercept=False, max_iter=2000).fit(D, y)
    return dict(coef=m.coef_[0][:len(FEATURES)], mu=mu, sd=sd)


def suitability(x, model):
    F = features(x)
    return np.exp(((F - model["mu"]) / model["sd"]) @ model["coef"])


def fit3():
    pools = {p: dict(np.load(OUT / f"{p}_inputs.npz")) for p in ("rome_150", "han_2", "hellenistic")}
    names = list(pools); res = {}
    for held in names:                                              # leave one pool out
        model = fit_suitability(pools, [p for p in names if p != held])
        res[held] = metrics(pools[held], place(pools[held], CURRENT, score_override=suitability(pools[held], model)))
        log(f"held out {held}: F1 {res[held]['F1']:.3f} M1 {res[held]['M1']:.3f} M3 {res[held]['M3']:.3f} M4 {res[held]['M4']:.3f}")
    full = fit_suitability(pools, names)
    lopo = dict(F1=float(np.mean([r["F1"] for r in res.values()])), M1=float(np.mean([r["M1"] for r in res.values()])), M3=float(np.mean([r["M3"] for r in res.values()])))
    passes = lopo["F1"] > 0.463 and lopo["M1"] >= 0.274
    out = dict(features=FEATURES, coef=dict(zip(FEATURES, map(float, full["coef"]))), mu=full["mu"].tolist(), sd=full["sd"].tolist(),
               leave_one_out=res, mean=lopo, adopted_for_blind=bool(passes))
    (OUT / "fit3.json").write_text(json.dumps(out, indent=1))
    log("leave-one-pool-out mean:", {k: round(v, 3) for k, v in lopo.items()}, "-> stage 3", "ADOPTED for the blind test" if passes else "not adopted")
    log("coefficients (standardised):", {k: round(v, 2) for k, v in out["coef"].items()})



def grid2():
    """Amendment 1: count-limited placement (E1 count, smaller spacing) x {current, stage-1} weights."""
    pools = {p: dict(np.load(OUT / f"{p}_inputs.npz")) for p in ("rome_150", "han_2", "hellenistic")}
    stage1 = json.loads((OUT / "grid.json").read_text())["candidate"]["weights"]
    counts = {p: len(place(x, CURRENT)) for p, x in pools.items()}           # the E1 count of the current model
    rows = []
    for wname, w in (("current", CURRENT), ("stage1", stage1)):
        for sp in SPACINGS:
            res = {p: metrics(x, place(x, w, sp, counts[p])) for p, x in pools.items()}
            rows.append(dict(weights=wname, spacing=sp, pools=res, F1=float(np.mean([r["F1"] for r in res.values()])),
                             M1=float(np.mean([r["M1"] for r in res.values()])), M3=float(np.mean([r["M3"] for r in res.values()]))))
            log(f"{wname:8s} s {sp:.1f}: F1 {rows[-1]['F1']:.3f} M1 {rows[-1]['M1']:.3f} M3 {rows[-1]['M3']:.3f}  " +
                "  ".join(f"{p} F1 {v['F1']:.3f}/M1 {v['M1']:.3f}/M3 {v['M3']:.3f}" for p, v in res.items()))
    cur = next(r for r in rows if r["weights"] == "current" and r["spacing"] == 1.6)
    ok = [r for r in rows if r["M1"] >= cur["M1"]]
    best = max(ok, key=lambda r: r["F1"])
    (OUT / "grid2.json").write_text(json.dumps(dict(counts=counts, stage1_weights=stage1, current=cur, candidate=best, rows=rows), indent=1))
    log("candidate:", best["weights"], "spacing", best["spacing"], f"F1 {best['F1']:.3f} M1 {best['M1']:.3f} M3 {best['M3']:.3f}")


def metrics(x, towns, block_km=100.0):
    cell = float(x["cell_km"]); shape = x["land"].shape; W = shape[1]
    real = np.asarray(x["real"]); real = real[x["allowed"].ravel()[real]]
    ry, rx = real // W, real % W
    n = len(real)
    if not len(towns):
        return dict(M1=0.0, recall=0.0, precision=0.0, F1=0.0, M3=1.0, M4=9.9, n_real=int(n), n_model=0)
    ty = np.array([t[0] for t in towns]); tx = np.array([t[1] for t in towns])
    my, mx = ty[:n], tx[:n]                                          # matched count: the n best placed sites
    R = cKDTree(np.c_[ry, rx] * cell); M = cKDTree(np.c_[my, mx] * cell)
    recall = float(np.mean(M.query(np.c_[ry, rx] * cell)[0] <= 25.0)); precision = float(np.mean(R.query(np.c_[my, mx] * cell)[0] <= 25.0))
    f1 = 0.0 if recall + precision == 0 else 2 * recall * precision / (recall + precision)
    b = max(1, int(round(block_km / cell))); ny, nx = shape[0] // b, shape[1] // b
    def counts(yy, xx):
        k = np.zeros((ny, nx)); ok = (yy // b < ny) & (xx // b < nx)
        np.add.at(k, (yy[ok] // b, xx[ok] // b), 1); return k
    allowed_b = x["allowed"][:ny * b, :nx * b].reshape(ny, b, nx, b).mean((1, 3)) >= 0.3
    from scipy.stats import spearmanr, ks_2samp
    m1 = float(spearmanr(counts(ry, rx)[allowed_b], counts(my, mx)[allowed_b]).statistic)
    nn = lambda yy, xx: cKDTree(np.c_[yy, xx] * cell).query(np.c_[yy, xx] * cell, k=2)[0][:, 1]
    m3 = float(ks_2samp(nn(ry, rx), nn(my, mx)).statistic) if len(my) > 2 else 1.0
    m4 = float(abs(np.log10(max(len(towns), 1) / max(n, 1))))
    return dict(M1=m1, recall=recall, precision=precision, F1=f1, M3=m3, M4=m4, n_real=int(n), n_model=int(len(towns)))


def grid():
    pools = {p: dict(np.load(OUT / f"{p}_inputs.npz")) for p in ("rome_150", "han_2", "hellenistic")}
    rows = []
    keys = list(GRID)
    t0 = time.time()
    for k, vals in enumerate(itertools.product(*GRID.values())):
        w = dict(zip(keys, vals))
        res = {p: metrics(x, place(x, w)) for p, x in pools.items()}
        rows.append(dict(weights=w, pools=res, F1=float(np.mean([r["F1"] for r in res.values()])), M1=float(np.mean([r["M1"] for r in res.values()]))))
        if k % 20 == 0:
            log(f"   {k + 1}/{np.prod([len(v) for v in GRID.values()])} ({time.time() - t0:.0f}s)")
    cur = next(r for r in rows if r["weights"] == CURRENT)
    ok = [r for r in rows if r["M1"] >= cur["M1"]]
    best = max(ok, key=lambda r: r["F1"])
    res = dict(plan=str(PLAN.relative_to(ROOT)), current=cur, candidate=best, rows=rows)
    (OUT / "grid.json").write_text(json.dumps(res, indent=1))
    for tag, r in (("current", cur), ("candidate", best)):
        log(f"{tag}: {r['weights']}  mean F1 {r['F1']:.3f}  mean M1 {r['M1']:.3f}  " +
            "  ".join(f"{p}: F1 {v['F1']:.3f} M1 {v['M1']:.3f} M3 {v['M3']:.3f} M4 {v['M4']:.3f}" for p, v in r["pools"].items()))


def blind():
    """The single blind evaluation (plan.json gates G1-G4): current weights against the stage-1 candidate."""
    import pandas as pd
    import polity_earth_check as P
    import earth_control_blind2 as B2
    from polity import earth as E
    from polity.settle import site_score
    from sklearn.metrics import roc_auc_score
    cand = json.loads((OUT / "grid.json").read_text())["candidate"]["weights"]
    res = dict(plan=str(PLAN.relative_to(ROOT)), candidate=cand, current=CURRENT)
    # S1: CHGIS AD 610 seats in the Han window, allowed = Cliopatria Sui Dynasty 610
    g = P.load_window("han"); land = g["land"].astype(bool); W = land.shape[1]
    pts = B2.seats(610); r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    inside, n = B2.target(g, 610, ("Sui Dynasty",))
    x = inputs(g, np.zeros(land.shape, bool), inside); x["real"] = np.unique((r * W + c)[ok])
    s1 = {k: metrics(x, place(x, w)) for k, w in (("current", CURRENT), ("candidate", cand))}
    res["S1_sui_610"] = dict(seats=int(len(pts)), polygons=int(n), **s1)
    # S2: cities of 1300 (>= 5,000) beyond the Roman frontier in the Rome window: site-rank AUC
    d = pd.read_stata(ROOT / "data/cache/bosker_cities_20261107/cities.tab"); y = d[(d["year"] == 1300) & (d["citypop_le5"] > 0)]
    g = P.load_window("rome"); land = g["land"].astype(bool); W = land.shape[1]
    roman = E.inside_polygons(g, E.cliopatria("Roman Empire", 150))
    region = land & ~roman & (g["lat"] > 45) & (g["lon"] < 30)
    r, c, ok = P.snap(g, y["latitude"].values.astype(float), y["longitude"].values.astype(float))
    cells = (r * W + c)[ok & (y["latitude"].values > 45) & (y["longitude"].values < 30)]
    cells = np.unique(cells[region.ravel()[cells]])
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    x2 = inputs(g, road, region)
    lab = np.zeros(land.size, bool); lab[cells] = True; sel = region.ravel()
    s2 = {}
    for k, w in (("current", CURRENT), ("candidate", cand)):
        score, _ = site_score(x2["density"], land, x2["water_km"], ndi.distance_transform_edt(land) * x2["cell_km"], road, x2["elev"], x2["cell_km"], w)
        s2[k] = dict(auc=float(roc_auc_score(lab[sel], score.ravel()[sel])))
    res["S2_beyond_limes_1300"] = dict(cities=int(len(cells)), region_cells=int(region.sum()), **s2)
    a, b = s1["current"], s1["candidate"]
    gates = dict(G1=b["F1"] >= a["F1"], G2=s2["candidate"]["auc"] >= s2["current"]["auc"], G3=b["M1"] >= a["M1"] - 0.02, G4=b["M3"] <= a["M3"])
    res["gates"] = {k: bool(v) for k, v in gates.items()}; res["adopt"] = bool(all(gates.values()))
    (OUT / "blind.json").write_text(json.dumps(res, indent=1))
    log(f"S1 Sui 610 ({len(pts)} seats): current F1 {a['F1']:.3f} M1 {a['M1']:.3f} M3 {a['M3']:.3f} M4 {a['M4']:.3f} | candidate F1 {b['F1']:.3f} M1 {b['M1']:.3f} M3 {b['M3']:.3f} M4 {b['M4']:.3f}")
    log(f"S2 beyond the limes 1300 ({len(cells)} cities): AUC current {s2['current']['auc']:.3f}, candidate {s2['candidate']['auc']:.3f}")
    log("gates:", res["gates"], "adopt:", res["adopt"])


if __name__ == "__main__":
    {"prepare": prepare, "grid": grid, "grid2": grid2, "fit3": fit3, "blind": blind}[sys.argv[1]]()
