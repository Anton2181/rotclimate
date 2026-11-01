"""Sailing constants against Casson and ORBIS (calibration/polity_20261025/addendum_sailing_20261031.json).

    python -I scripts/polity_sail_check.py --out output/polity_sail_20261101

T6 (selection, seen): Casson's (1951) passages in the Rome window, the
model's mean May-September days. T7 (blind): ORBIS's July coastal and
overseas edges. Variants: V0 (close-hauled share 0.85, fair speed 5 knots),
V1 (close-hauled 0.45), V2 (close-hauled 0.45, fair speed 4-6 knots).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

import polity_earth_check as P  # noqa: E402
from polity import control as C  # noqa: E402
from polity import earth as E  # noqa: E402
from polity import network as N  # noqa: E402
from polity import transport as X  # noqa: E402

PLAN = ROOT / "calibration/polity_20261025/addendum_sailing_20261031.json"
VARIANTS = {"V0": (0.85, 5.0), "V1": (0.45, 5.0), **{f"V2_{k:g}": (0.45, k) for k in (4.0, 4.5, 5.0, 5.5, 6.0)}}
WEST = {"Rome", "Narbo", "Massilia", "Carthage", "Tarraco", "Gibraltar", "Utica", "Naples"}


def set_variant(share, knots):
    X.CLOSE_HAULED_SHARE, X.SAIL_FAIR_KNOTS = share, knots
    X.POLAR_MEAN = float(X.polar(np.linspace(0.0, 180.0, 1801)).mean())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_sail_20261101")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    P.apply_sea()
    g = P.load_window("rome")
    world = P.world_of(g); st = N.statics(world); cl = N.climate(world, st)
    W = g["land"].shape[1]
    idx = {k: int(r[0]) * W + int(c[0]) for k, (r, c) in
           ((k, P.snap(g, np.array([la]), np.array([lo]), "water")[:2]) for k, (la, lo) in P.PORTS.items())}
    sources = sorted({r[0] for r in P.CASSON} | {r[0] for r in P.PLINY})
    sites, edges = E.orbis_edges()
    by_src = {}
    for e in edges:
        if e["kind"] not in ("coastal", "overseas"):
            continue
        s, t = sites.get(e["source"]), sites.get(e["target"])
        if not s or not t:
            continue
        rs, cs, oks = P.snap(g, np.array([s["lat"]]), np.array([s["lon"]]), "water")
        rt, ct, okt = P.snap(g, np.array([t["lat"]]), np.array([t["lon"]]), "water")
        if oks[0] and okt[0]:
            by_src.setdefault(int(rs[0]) * W + int(cs[0]), []).append((int(rt[0]) * W + int(ct[0]), e))

    def net(m):
        return C.Network(st["land"].size, [X.sea_edges(st["water"], world["u"][m], world["v"][m], world["wind"][m],
                                                        cl["steadiness"][m], cl["sea"][m], world["cell_km"], st["coast_km"])])
    res = dict(addendum=str(PLAN.relative_to(ROOT)), variants={})
    for name, (share, knots) in VARIANTS.items():
        set_variant(share, knots)
        model = {}
        fair = {}
        for m in (4, 5, 6, 7, 8):
            nm = net(m)
            for s_ in sources:
                d = nm.days([idx[s_]])
                for t_ in P.PORTS:
                    model.setdefault((s_, t_), []).append(float(d[idx[t_]]))
        rows = []
        for s_, t_, lo_, hi_ in P.CASSON:
            md = float(np.mean(model[(s_, t_)])); cas = (lo_ + hi_) / 2
            rows.append(dict(route=f"{s_}-{t_}", casson=cas, model=md, ratio=md / cas, west=s_ in WEST and t_ in WEST))
        cas = np.array([r["casson"] for r in rows]); mod = np.array([r["model"] for r in rows])
        lr = np.log(mod / cas)
        t6 = dict(spearman=P.spearman(mod, cas), median_ratio=float(np.exp(np.median(lr))), median_abs_log=float(np.median(np.abs(lr))),
                  west_median_ratio=float(np.exp(np.median(lr[[r["west"] for r in rows]]))),
                  long_median_ratio=float(np.exp(np.median(lr[cas >= 20]))), routes=rows)
        # T7: ORBIS July
        set_variant(share, knots)
        nm = net(6)
        o = []
        for src, lst in by_src.items():
            d = nm.days([src])
            for dst, e in lst:
                if np.isfinite(d[dst]) and d[dst] > 0:
                    o.append((e["kind"], e["days"], float(d[dst])))
        oa = np.array([(r[1], r[2]) for r in o])
        l7 = np.log(oa[:, 1] / oa[:, 0])
        t7 = dict(n=len(o), spearman=P.spearman(oa[:, 1], oa[:, 0]), median_ratio=float(np.exp(np.median(l7))),
                  median_abs_log=float(np.median(np.abs(l7))),
                  by_kind={k: float(np.exp(np.median([np.log(r[2] / r[1]) for r in o if r[0] == k]))) for k in ("coastal", "overseas")})
        res["variants"][name] = dict(close_hauled=share, knots=knots, T6=t6, T7=t7)
        print(f"{name:7s} T6 rho {t6['spearman']:.3f} med x{t6['median_ratio']:.2f} |log| {t6['median_abs_log']:.3f} west x{t6['west_median_ratio']:.2f} long x{t6['long_median_ratio']:.2f}"
              f" | T7 rho {t7['spearman']:.3f} med x{t7['median_ratio']:.2f} |log| {t7['median_abs_log']:.3f}", flush=True)
    set_variant(0.85, 5.0)
    sel = min(VARIANTS, key=lambda k: (round(res["variants"][k]["T6"]["median_abs_log"], 6), list(VARIANTS).index(k)))
    v0, vs = res["variants"]["V0"]["T7"], res["variants"][sel]["T7"]
    adopted = sel != "V0" and vs["spearman"] >= v0["spearman"] - 0.01 and vs["median_abs_log"] < v0["median_abs_log"]
    res.update(selected=sel, adopted=bool(adopted), rule=json.loads(PLAN.read_text())["adopt_if"])
    (a.out / "sail.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(dict(selected=sel, adopted=adopted, T7_V0=[v0["spearman"], v0["median_abs_log"]],
                          T7_sel=[vs["spearman"], vs["median_abs_log"]]), indent=1))


if __name__ == "__main__":
    main()
