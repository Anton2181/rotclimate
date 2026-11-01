"""The sailing waiting rule against Casson and ORBIS (calibration/polity_20261025/addendum_sailing_wait_20261101.json).

    python -I scripts/polity_sail_wait.py --out output/polity_sail_20261101
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

PLAN = ROOT / "calibration/polity_20261025/addendum_sailing_wait_20261101.json"
TAU = 4.0


def edges_rule(water, u, v, wind, steadiness, season, cell_km, coast_km, mode, today=None):
    """Sea edges for the fair-wind network (mode 'fair') or the waiting network (mode 'wait')."""
    water = np.asarray(water, bool); h, w = water.shape
    coastal = coast_km <= X.COAST_KM
    speed = np.hypot(u, v)
    ex = np.where(speed > 1e-6, u / np.maximum(speed, 1e-6), 0.0); ny = np.where(speed > 1e-6, v / np.maximum(speed, 1e-6), 0.0)
    nodes = np.arange(h * w).reshape(h, w)
    rows, cols, cost = [], [], []
    fair_km_day = X.SAIL_FAIR_KNOTS * X.KNOT_KM_H * 24.0
    for dy, dx in X.NEIGHBOURS:
        y0, y1 = max(0, -dy), min(h, h - dy); x0, x1 = max(0, -dx), min(w, w - dx)
        src = np.s_[y0:y1, x0:x1]; dst = np.s_[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = water[src] & water[dst]
        if dy and dx:
            ok &= water[y0:y1, x0 + dx:x1 + dx] & water[y0 + dy:y1 + dy, x0:x1]
        norm = np.hypot(dy, dx)
        km_day = fair_km_day * np.where(coastal[src] & coastal[dst], X.COAST_FACTOR, 1.0) * np.minimum(season[src], season[dst])
        days = cell_km * norm / np.maximum(km_day, 1e-6)
        if mode in ("wait", "beat", "p"):
            cos_t = (dx * 0.5 * (ex[src] + ex[dst]) - dy * 0.5 * (ny[src] + ny[dst])) / norm
            theta = np.degrees(np.arccos(np.clip(cos_t, -1, 1)))
            s = np.clip(0.5 * (steadiness[src] + steadiness[dst]), 0, 1)
            p = np.maximum(s * (theta <= X.CLOSE_HAULED) + (1 - s) * X.CLOSE_HAULED / 180.0, 0.05)
            if mode == "p":
                days = p
            else:
                days = days * (1.0 + (1.0 - p) / p)
            if mode == "beat":
                km_t = X.sail_km_day(cos_t, s, 0.5 * (wind[src] + wind[dst]), coastal[src] & coastal[dst], np.minimum(season[src], season[dst]))
                days = np.minimum(days, cell_km * norm / np.maximum(km_t, 1e-6))
        rows.append(nodes[src][ok]); cols.append(nodes[dst][ok]); cost.append(days[ok])
    return np.concatenate(rows), np.concatenate(cols), np.concatenate(cost)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/polity_sail_20261101")
    ap.add_argument("--credit", action="store_true", help="addendum_sailing_wait2: the first spell sailed on the chosen wind")
    ap.add_argument("--beat", action="store_true", help="addendum_sailing_wait3: beat or wait per step; fair departures only where p_route >= 0.5")
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    plan = ROOT / ("calibration/polity_20261025/addendum_sailing_wait3_20261101.json" if a.beat else
                   "calibration/polity_20261025/addendum_sailing_wait2_20261101.json" if a.credit else str(PLAN.relative_to(ROOT)))

    def combine(df, dw):
        if a.credit:
            return df + (dw - df) * max(0.0, 1.0 - TAU / max(df, 1e-9))
        return df if df <= TAU else dw
    P.apply_sea()
    g = P.load_window("rome")
    world = P.world_of(g); st = N.statics(world); cl = N.climate(world, st)
    W = g["land"].shape[1]
    idx = {k: int(r[0]) * W + int(c[0]) for k, (r, c) in
           ((k, P.snap(g, np.array([la]), np.array([lo]), "water")[:2]) for k, (la, lo) in P.PORTS.items())}
    sources = sorted({r[0] for r in P.CASSON})
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

    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    n_nodes = st["land"].size

    class Beat:
        """Beat-or-wait network with fair-wind departures where p_route >= 0.5 (addendum wait3)."""
        def __init__(self, args):
            fs, fd, fc = edges_rule(*args, mode="fair"); _, _, pc = edges_rule(*args, mode="p")
            bs, bd, bc = edges_rule(*args, mode="beat")
            self.F = csr_matrix((fc, (fs, fd)), shape=(n_nodes, n_nodes))
            self.Pm = csr_matrix((pc, (fs, fd)), shape=(n_nodes, n_nodes))
            self.B = C.Network(n_nodes, [(bs, bd, bc)])

        def days(self, srcs):
            src = srcs[0]
            df, pred = dijkstra(self.F, directed=True, indices=src, return_predecessors=True)
            db = self.B.days([src])
            out = db.copy()
            return df, pred, db

        def time(self, src_out, dst):
            df, pred, db = src_out
            if not np.isfinite(df[dst]):
                return float(db[dst])
            ps, node = [], dst
            while node != -9999 and pred[node] >= 0:
                ps.append(self.Pm[pred[node], node]); node = pred[node]
            p_route = float(np.mean(ps)) if ps else 1.0
            if p_route >= 0.5:
                return float(df[dst] + (db[dst] - df[dst]) * max(0.0, 1.0 - TAU / max(df[dst], 1e-9)))
            return float(db[dst])

    def nets(m):
        args = (st["water"], world["u"][m], world["v"][m], world["wind"][m], cl["steadiness"][m], cl["sea"][m], world["cell_km"], st["coast_km"])
        today = C.Network(st["land"].size, [X.sea_edges(*args)])
        fair = C.Network(st["land"].size, [edges_rule(*args, mode="fair")])
        wait = Beat(args) if a.beat else C.Network(st["land"].size, [edges_rule(*args, mode="wait")])
        return today, fair, wait
    casson = {(s, t): (lo + hi) / 2 for s, t, lo, hi in P.CASSON}
    model = {"today": {}, "rule": {}}
    for m in (4, 5, 6, 7, 8):
        today, fair, wait = nets(m)
        for s_ in sources:
            dt, df, dw = today.days([idx[s_]]), fair.days([idx[s_]]), wait.days([idx[s_]])
            for (a_, b_) in casson:
                if a_ != s_:
                    continue
                model["today"].setdefault((a_, b_), []).append(float(dt[idx[b_]]))
                model["rule"].setdefault((a_, b_), []).append(wait.time(dw, idx[b_]) if a.beat else float(combine(df[idx[b_]], dw[idx[b_]])))
    res = {}
    for name in ("today", "rule"):
        mod = np.array([np.mean(model[name][k]) for k in casson]); cas = np.array([casson[k] for k in casson])
        lr = np.log(mod / cas)
        res[name] = dict(T6=dict(spearman=P.spearman(mod, cas), median_ratio=float(np.exp(np.median(lr))), median_abs_log=float(np.median(np.abs(lr))),
                                 long_median_ratio=float(np.exp(np.median(lr[cas >= 20]))), short_median_ratio=float(np.exp(np.median(lr[cas <= 4])))))
    today, fair, wait = nets(6)
    o = {"today": [], "rule": []}
    for src, lst in by_src.items():
        dt, df, dw = today.days([src]), fair.days([src]), wait.days([src])
        for dst, e in lst:
            if np.isfinite(dt[dst]) and dt[dst] > 0:
                o["today"].append((e["days"], float(dt[dst])))
                o["rule"].append((e["days"], wait.time(dw, dst) if a.beat else float(combine(df[dst], dw[dst]))))
    for name in ("today", "rule"):
        oa = np.array(o[name]); l7 = np.log(oa[:, 1] / oa[:, 0])
        res[name]["T7"] = dict(n=len(oa), spearman=P.spearman(oa[:, 1], oa[:, 0]), median_ratio=float(np.exp(np.median(l7))),
                               median_abs_log=float(np.median(np.abs(l7))))
    t, r = res["today"], res["rule"]
    ok = (r["T7"]["spearman"] >= t["T7"]["spearman"] - 0.01 and r["T7"]["median_abs_log"] < t["T7"]["median_abs_log"]
          and r["T6"]["median_abs_log"] < t["T6"]["median_abs_log"])
    out = dict(addendum=str(plan.relative_to(ROOT)), tau_days=TAU, results=res, adopted=bool(ok), rule=json.loads(plan.read_text())["adopt_if"])
    (a.out / ("sail_wait3.json" if a.beat else "sail_wait2.json" if a.credit else "sail_wait.json")).write_text(json.dumps(out, indent=1))
    print(json.dumps(out["results"], indent=1)); print("adopted", ok)


if __name__ == "__main__":
    main()
