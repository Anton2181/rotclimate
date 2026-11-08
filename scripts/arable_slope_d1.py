"""Plan D1 (calibration/geography_control_20261107/plan_D1.json): the arable share of a ~1.85 km cell from the slope the
map resolves, fitted on Earth against the GAEZ slope rule applied at 90 m (Copernicus GLO-90).

    .venv/bin/python -I scripts/arable_slope_d1.py fetch      # the 24 frozen 1-degree tiles (development + blind)
    .venv/bin/python -I scripts/arable_slope_d1.py dev        # fit a(S) on the development tiles, choose
    .venv/bin/python -I scripts/arable_slope_d1.py blind      # the single blind evaluation
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.optimize import curve_fit

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_D1.json"
CACHE = ROOT / "data/cache/copdem90"
OUT = ROOT / "output/arable_slope_d1"
URL = "https://copernicus-dem-90m.s3.amazonaws.com/{n}/{n}.tif"
CLASSES = ((8.0, 1.0), (16.0, 0.6), (30.0, 0.3), (np.inf, 0.05))     # GAEZ slope classes (%) and arable factors
TIER_TOPS = (62.0, 814.0, 1135.0, 2528.0)
DEG_M = 111320.0
log = lambda *a: print(*a, flush=True)  # noqa: E731


def tile_name(t):
    lat, lon = t[:3], t[3:]
    return f"Copernicus_DSM_COG_30_{lat[0]}{int(lat[1:]):02d}_00_{lon[0]}{int(lon[1:]):03d}_00_DEM"


def tiles(group):
    return json.loads(PLAN.read_text())["D1"]["tiles"][group]


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    for group in ("development", "blind"):
        for t in tiles(group):
            n = tile_name(t); path = CACHE / f"{n}.tif"
            if path.exists():
                continue
            urllib.request.urlretrieve(URL.format(n=n), path); log(t, path.stat().st_size // 1024, "kB")


def cells(t):
    """Per ~1.85 km cell: Earth target (GAEZ rule on 90 m slopes), block-mean elevation, coarse slope (deg), land."""
    import tifffile
    z = tifffile.imread(CACHE / f"{tile_name(t)}.tif").astype(float)
    n_lat = int(t[1:3]) * (1 if t[0] == "N" else -1)
    ny, nx = z.shape                                                  # rows from the north
    lat = n_lat + 1 - (np.arange(ny) + 0.5) / ny
    dy = DEG_M / ny; dx = DEG_M / nx * np.cos(np.radians(lat))[:, None]
    gy, gx = np.gradient(z, dy, axis=0), np.gradient(z, axis=1) / dx
    slope = 100.0 * np.hypot(gy, gx)                                  # percent
    land = z > 0
    flat = (gy == 0) & (gx == 0)
    fac = np.select([slope < c for c, _ in CLASSES], [f for _, f in CLASSES])
    by = 20; bx = int(round(20 / np.cos(np.radians(n_lat + 0.5))))
    H, W = (ny // by) * by, (nx // bx) * bx
    blk = lambda a: a[:H, :W].reshape(H // by, by, W // bx, bx)
    landf = blk(land).mean((1, 3)); flatf = blk(flat & land).mean((1, 3)) / np.maximum(landf, 1e-9)
    target = (blk(np.where(land, fac, 0.0)).sum((1, 3)) / np.maximum(blk(land).sum((1, 3)), 1))
    zb = blk(np.where(land, z, 0.0)).sum((1, 3)) / np.maximum(blk(land).sum((1, 3)), 1)
    cy = DEG_M * by / ny; cx = DEG_M * bx / nx * np.cos(np.radians(n_lat + 0.5))
    Gy, Gx = np.gradient(zb, cy, axis=0), np.gradient(zb, cx, axis=1)
    S = np.degrees(np.arctan(np.hypot(Gy, Gx)))
    ok = (landf >= 0.9) & (flatf <= 0.5)
    ok &= ndi.binary_erosion(ok, np.ones((3, 3)))                     # the coarse gradient needs land neighbours
    return dict(target=target[ok], elev=zb[ok], S=S[ok], cell_km=(cy / 1000, cx / 1000))


def a_S(S, lo, hi, S0, k):
    return lo + (hi - lo) / (1.0 + np.power(np.maximum(S, 1e-6) / S0, k))


def baseline(elev):
    from land_people import ARABLE_BY_TIER
    band = 1 + np.searchsorted(np.asarray(TIER_TOPS), elev, side="right")
    return np.vectorize(lambda b: ARABLE_BY_TIER[min(b, 4)])(band).astype(float)


UPLAND_M = 814.0                                                       # lowland = tiers 1-2, upland = tiers 3-4


def fit(cs):
    """Least squares over development cells, every tile weighted equally."""
    S = np.concatenate([c["S"] for c in cs]); y = np.concatenate([c["target"] for c in cs])
    e = np.concatenate([c["elev"] for c in cs])
    w = np.concatenate([np.full(c["S"].size, 1.0 / c["S"].size) for c in cs])
    p, _ = curve_fit(a_S, S, y, p0=(0.05, 1.0, 5.0, 2.0), sigma=1 / np.sqrt(w), bounds=([0, 0, 0.01, 0.2], [1, 1, 60, 10]))
    def fb(X, lo, h_low, h_up, S0, k):
        s, up = X
        return lo + (np.where(up, h_up, h_low) - lo) / (1.0 + np.power(np.maximum(s, 1e-6) / S0, k))
    pb, _ = curve_fit(fb, (S, e >= UPLAND_M), y, p0=(p[0], p[1], p[1], p[2], p[3]), sigma=1 / np.sqrt(w),
                      bounds=([0, 0, 0, 0.01, 0.2], [1, 1, 1, 60, 10]))
    return dict(S=dict(lo=p[0], hi=p[1], S0=p[2], k=p[3]), S_band=dict(lo=pb[0], hi_low=pb[1], hi_up=pb[2], S0=pb[3], k=pb[4]))


def predict(name, prm, c):
    if name == "baseline":
        return baseline(c["elev"])
    if name == "S":
        return a_S(c["S"], prm["lo"], prm["hi"], prm["S0"], prm["k"])
    hi = np.where(c["elev"] >= UPLAND_M, prm["hi_up"], prm["hi_low"])
    return prm["lo"] + (hi - prm["lo"]) / (1.0 + np.power(np.maximum(c["S"], 1e-6) / prm["S0"], prm["k"]))


def scores(name, prm, cs, names):
    out = {}
    for t, c in zip(names, cs):
        p = predict(name, prm, c); out[t] = dict(rmse=float(np.sqrt(np.mean((p - c["target"]) ** 2))),
                                                 bias=float(np.mean(p - c["target"])), cells=int(c["S"].size),
                                                 target_mean=float(np.mean(c["target"])))
    allp = np.concatenate([predict(name, prm, c) for c in cs]); ally = np.concatenate([c["target"] for c in cs])
    out["_all"] = dict(rmse=float(np.sqrt(np.mean((allp - ally) ** 2))), bias=float(np.mean(allp - ally)),
                       tile_mean_rmse=float(np.mean([out[t]["rmse"] for t in names])))
    return out


def dev():
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    names = tiles("development"); cs = [cells(t) for t in names]
    prm = fit(cs)
    res = {k: scores(k, prm.get(k), cs, names) for k in ("baseline", "S", "S_band")}
    gain = res["S"]["_all"]["tile_mean_rmse"] - res["S_band"]["_all"]["tile_mean_rmse"]
    chosen = "S_band" if gain >= 0.01 else "S"
    out = dict(plan=str(PLAN.relative_to(ROOT)), params=prm, scores=res, chosen=chosen, chosen_params=prm[chosen],
               S_band_gain=gain, upland_m=UPLAND_M, seconds=time.time() - t0,
               slope_pct={t: dict(S_deg=np.percentile(c["S"], [10, 50, 90]).round(2).tolist(),
                                  target=np.percentile(c["target"], [10, 50, 90]).round(2).tolist()) for t, c in zip(names, cs)})
    (OUT / "dev.json").write_text(json.dumps(out, indent=1, default=float))
    for k in ("baseline", "S", "S_band"):
        log(k, {t: round(v["rmse"], 3) for t, v in res[k].items() if t != "_all"}, "all", round(res[k]["_all"]["tile_mean_rmse"], 3),
            "bias", round(res[k]["_all"]["bias"], 3))
    log("params", json.dumps(prm, default=float)); log("chosen", chosen, f"(S_band gain {gain:.3f})")


def blind():
    d = json.loads((OUT / "dev.json").read_text()); name, prm = d["chosen"], d["chosen_params"]
    names = tiles("blind"); cs = [cells(t) for t in names]
    base, cand = scores("baseline", None, cs, names), scores(name, prm, cs, names)
    wins = sum(cand[t]["rmse"] < base[t]["rmse"] for t in names)
    gate = dict(tiles_better=wins, need=8, total_better=cand["_all"]["rmse"] < base["_all"]["rmse"],
                bias_ok=abs(cand["_all"]["bias"]) <= 0.05)
    adopt = bool(wins >= 8 and gate["total_better"] and gate["bias_ok"])
    out = dict(plan=str(PLAN.relative_to(ROOT)), chosen=name, params=prm, baseline=base, candidate=cand, gate=gate, adopt=adopt)
    (OUT / "blind.json").write_text(json.dumps(out, indent=1, default=float))
    for t in names:
        log(f"  {t}: baseline {base[t]['rmse']:.3f} -> {cand[t]['rmse']:.3f} (target mean {cand[t]['target_mean']:.2f}, bias {cand[t]['bias']:+.3f})")
    log("all:", round(base["_all"]["rmse"], 3), "->", round(cand["_all"]["rmse"], 3), "bias", round(cand["_all"]["bias"], 3), gate, "adopt:", adopt)


if __name__ == "__main__":
    {"fetch": fetch, "dev": dev, "blind": blind}[sys.argv[1]]()
