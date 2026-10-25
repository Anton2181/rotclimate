"""Market access and Roman town sizes (calibration/polity_20261025/plan_trade.json).

    python3 -I scripts/polity_trade_check.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))

import polity_earth_check as P                    # noqa: E402
from polity import earth as E                      # noqa: E402
from polity import network as N                    # noqa: E402
from polity import trade as T                      # noqa: E402
from polity import transport as X                  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025"
OUT = PLAN / "trade.json"
SCALES = [30, 100, 200, 400, 800, 1600, 3200]
log = P.log


def ols(X_, y):
    A = np.column_stack([np.ones(len(y))] + list(X_))
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return coef


def predict(coef, X_):
    return coef[0] + sum(c * x for c, x in zip(coef[1:], X_))


def r2(y, yhat):
    return float(1 - ((y - yhat) ** 2).sum() / ((y - y.mean()) ** 2).sum())


def main():
    P.apply_sea()
    g = P.load_window("rome")
    land = g["land"].astype(bool); W = land.shape[1]
    road = E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land
    inside = E.inside_polygons(g, E.cliopatria("Roman Empire", 150)) & land
    towns = E.hanson_towns(150)
    r, c, ok = P.snap(g, np.array([t["lat"] for t in towns]), np.array([t["lon"] for t in towns]))
    towns = [dict(t, row=int(y), col=int(x)) for t, y, x, k in zip(towns, r, c, ok) if k]
    places = [(t["row"], t["col"]) for t in towns]
    sel = [t for t in towns if inside[t["row"], t["col"]] and t["area_ha"] > 0]
    log(len(towns), "towns in the window,", len(sel), "inside the empire with an area")
    world = P.world_of(g, road)
    st = N.statics(world); cl = N.climate(world, st)
    ports = X.ports_of(places, st["water"])
    from scipy import ndimage as ndi
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [(y, x) for y, x in places if near_river[y, x]]
    t0 = time.time()
    nets = [T.cost_network(world, st, cl, m, ports, river_places) for m in T.TRADE_MONTHS]
    log(f"cost networks {time.time() - t0:.0f}s")
    people = np.where(land, g["density"], 0.0) * g["cell_km"] ** 2
    src = np.array([t["row"] * W + t["col"] for t in sel])
    t0 = time.time()
    ma = T.market_access(nets, src, people, SCALES)
    log(f"market access {time.time() - t0:.0f}s")
    lon = np.array([t["lon"] for t in sel]); y = np.log10([t["area_ha"] for t in sel])
    L = np.log10(np.maximum(ma, 1.0))
    west, east = lon < 20.0, lon >= 20.0
    log(f"west {west.sum()}, east {east.sum()} towns")
    from scipy.stats import spearmanr
    base = ols([L[0][west]], y[west])
    fits = {}
    for k, s in enumerate(SCALES[1:], 1):
        coef = ols([L[0][west], L[k][west]], y[west])
        fits[s] = dict(coef=[float(v) for v in coef], r2_west=r2(y[west], predict(coef, [L[0][west], L[k][west]])),
                       spearman_west=float(spearmanr(predict(coef, [L[0][west], L[k][west]]), y[west]).statistic))
        log(f"   MA {s}: west R2 {fits[s]['r2_west']:.4f} Spearman {fits[s]['spearman_west']:.4f} coef {np.round(coef, 3)}")
    b_r2 = r2(y[west], predict(base, [L[0][west]]))
    log(f"   LOCAL alone: west R2 {b_r2:.4f}")
    c_fit = max(fits, key=lambda s: fits[s]["r2_west"])
    out = dict(plan="plan_trade.json", towns=len(sel), west=int(west.sum()), east=int(east.sum()),
               F_trade=dict(by_scale={str(k): v for k, v in fits.items()}, local_only=dict(coef=[float(v) for v in base],
                                                                                      r2_west=b_r2), c_fit=c_fit))
    OUT.write_text(json.dumps(out, indent=1))
    k = SCALES.index(c_fit)
    coef = fits[c_fit]["coef"]
    pe = predict(coef, [L[0][east], L[k][east]]); pb = predict(base, [L[0][east]])
    s_comb = float(spearmanr(pe, y[east]).statistic); s_base = float(spearmanr(pb, y[east]).statistic)
    out["T_trade1"] = dict(spearman_combined=s_comb, spearman_local=s_base, r2_oos_combined=r2(y[east], pe),
                           r2_oos_local=r2(y[east], pb), passed=bool(s_comb >= s_base + 0.02))
    log("T_trade1:", out["T_trade1"])
    names = np.array([t["name"] for t in sel])
    full = predict(coef, [L[0], L[k]])
    out["largest_predicted"] = [(str(n), float(10 ** v)) for n, v in zip(names[np.argsort(-full)[:10]], np.sort(full)[::-1][:10])]
    out["largest_actual"] = [(str(n), float(10 ** v)) for n, v in zip(names[np.argsort(-y)[:10]], np.sort(y)[::-1][:10])]
    log("largest predicted:", out["largest_predicted"]); log("largest actual:", out["largest_actual"])
    OUT.write_text(json.dumps(out, indent=1))
    np.savez_compressed(ROOT / "output/polity_earth/trade.npz", ma=ma, scales=SCALES, area=y, lon=lon,
                        lat=np.array([t["lat"] for t in sel]), names=names)


if __name__ == "__main__":
    main()
