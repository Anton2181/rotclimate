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


def place(x, weights):
    from polity.settle import place_towns
    towns, _, _ = place_towns(x["density"], x["land"], x["water_km"], x["road"], x["elev"], float(x["cell_km"]), [],
                              allowed=x["allowed"], seed=1, aridity=x["aridity"], weights=weights)
    return towns


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


if __name__ == "__main__":
    {"prepare": prepare, "grid": grid}[sys.argv[1]]()
