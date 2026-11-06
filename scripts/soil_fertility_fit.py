"""Development fit of the soil-fertility state on SPENT pools only (Broadbalk plot 3 and
FYM-only, Woburn unmanured and FYM-only wheat and barley), then write the frozen
selection. calibration/soil_fertility_20261106/plan.json + amendment_evaporation.json.

Every plot in a stratum is simulated with its own treatment history and the stratum
value is the area-weighted mean, as the observed strata are built.

    python -I scripts/soil_fertility_fit.py --out output/soil_fertility_20261106
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

import soil_fertility_common as C  # noqa: E402
from harvest.soil_fertility import Params  # noqa: E402
from woburn_yields import stratum as woburn_stratum  # noqa: E402

CACHE = C.CACHE
RAPE_CAKE_CN = 8.0          # oilseed cake (declared); only enters histories of plots outside the strata' years
BOUNDS = dict(input_n=(0.0, 60.0), uptake_rate=(0.05, 0.9), kappa=(1.0, 5.0), prior_manure=(0.0, 3.0))
PRODUCERS = ("harvest/soil_fertility.py", "scripts/soil_fertility_common.py", "scripts/soil_fertility_fit.py",
             "harvest/soil_water_dual.py", "calibration/soil_fertility_20261106/plan.json",
             "calibration/soil_fertility_20261106/amendment_evaporation.json")


def broadbalk_series():
    prepared = json.loads((CACHE / "prepared_wheat.json").read_text())["cases"]
    obs = {"BB_nil": {}, "BB_fym": {}}
    weights = {}
    for c in prepared:
        if c["stratum"] == "unmanured_plot3":
            obs["BB_nil"][c["year"]] = c["observed_t_ha"]
            weights[("BB_nil", c["year"])] = {"3": 1.0}
        elif c["stratum"] == "fym_only":
            obs["BB_fym"][c["year"]] = c["observed_t_ha"]
            w = {}
            for r in c["source_records"]:
                key = "2.2" if r["plot"] in ("2", "2.2") else r["plot"]
                w[key] = w.get(key, 0.0) + r["area"]
            weights[("BB_fym", c["year"])] = w
    calendar = {y: "wheat" for y in range(1844, 1926)}
    fym = lambda first: {(y, 10): [("fym", 35 * C.FYM_C_PER_T, 225.0)] for y in range(first, 1925)}   # noqa: E731
    plots = {"3": {}, "2.2": fym(1843), "2.1": fym(1884)}          # 2.1: FYM since harvest 1885, nil before (declared)
    return dict(site="rothamsted", first=1843, last=1925, calendar=calendar, plots=plots, obs=obs, weights=weights)


def woburn_series(crop, zipname, prefix):
    z = zipfile.ZipFile(CACHE / zipname)
    rows = list(csv.DictReader(io.StringIO(z.read(f"{prefix}/crop_data.csv").decode("utf-8-sig"))))
    plots, obs_acc, weights = {}, {}, {}
    for r in rows:
        y = int(r["harvest_year"])
        if y > 1900:
            continue
        key = "/".join(x for x in (r["plot"], r["sub_plot"], r["sub_sub_plot"]) if x not in ("*", ""))
        ev = plots.setdefault(key, {})
        month = (y, 2)                                   # Woburn: FYM applied to the crop in February
        f = float(r["fym_amount"] or 0) if r["fym_factor_level"] != "nil" else 0.0
        if f > 0:
            ev.setdefault(month, []).append(("fym", f * C.FYM_C_PER_T, float(r["fym_n"])))
        n = float(r["fertilizer_n_amount"]) if r["n_factor_level"] != "nil" and r["fertilizer_n_amount"] not in ("", "*") else 0.0
        if n > 0:
            ev.setdefault((y, 4), []).append(("fert", n))
        rc = float(r["rape_cake_n"]) if r["rape_cake_factor_level"] != "nil" and r["rape_cake_n"] not in ("", "*") else 0.0
        if rc > 0:
            ev.setdefault(month, []).append(("residue", rc * RAPE_CAKE_CN / 1000.0, RAPE_CAKE_CN))
        s = woburn_stratum(r)
        if s is None or y < 1879:
            continue
        try:
            grain, area = float(r["grain"]), float(r["area_ha"])
        except ValueError:
            continue
        if not math.isfinite(grain) or grain < 0 or area <= 0:
            continue
        name = f"W{crop[0].upper()}_{'nil' if s == 'unmanured' else 'fym'}"
        a = obs_acc.setdefault((name, y), [0.0, 0.0])
        a[0] += grain * area; a[1] += area
        weights.setdefault((name, y), {})
        weights[(name, y)][key] = weights[(name, y)].get(key, 0.0) + area
    obs = {}
    for (name, y), (ga, aa) in obs_acc.items():
        if C.a0(y, "wheat" if crop == "wheat" else "barley") is not None:     # valid weather, as scored before
            obs.setdefault(name, {})[y] = ga / aa
    weights = {k: v for k, v in weights.items() if k[1] in obs.get(k[0], {})}
    calendar = {y: crop for y in range(1877, 1901)}
    return dict(site="woburn", first=1876, last=1900, calendar=calendar, plots=plots, obs=obs, weights=weights)


def build():
    groups = [broadbalk_series(), woburn_series("wheat", "woburn_wheat_0.zip", "01-WXW6YLD7726"),
              woburn_series("barley", "woburn_barley_0.zip", "01-WXB6YLD7726")]
    for g in groups:
        g["drainage"], g["drainage_residual"] = C.monthly_drainage(g["site"], g["first"], g["last"], g["calendar"])
        needed = {p for w in g["weights"].values() for p in w}
        g["plots"] = {k: v for k, v in g["plots"].items() if k in needed}
    return groups


def predict(groups, params):
    out = {}
    for g in groups:
        sims = {}
        for key, ev in g["plots"].items():
            res = C.run(g["site"], g["first"], g["last"], g["calendar"], ev, params, drainage=g["drainage"])
            sims[key] = {s["harvest"][0]: s["grain_t_ha"] for s in res["seasons"] if s["grain_t_ha"] is not None}
        for (name, y), w in g["weights"].items():
            tot = sum(w.values())
            out.setdefault(name, {})[y] = sum(sims[k][y] * a for k, a in w.items()) / tot
    return out


def objective(groups, params):
    pred = predict(groups, params)
    loss = 0.0
    obs = {k: v for g in groups for k, v in g["obs"].items()}
    for name, series in obs.items():
        e = [math.log(max(series[y], 0.05) / max(pred[name][y], 0.05)) for y in series]
        loss += float(np.mean(np.square(e)))
    return loss


def series_metrics(groups, params):
    pred = predict(groups, params)
    obs = {k: v for g in groups for k, v in g["obs"].items()}
    out = {}
    for name, s in obs.items():
        ys = sorted(s)
        y = np.array([s[t] for t in ys]); p = np.array([pred[name][t] for t in ys])
        a0 = np.array([C.potential(t, "wheat" if name in ("BB_nil", "BB_fym", "WW_nil", "WW_fym") else "barley")[0] for t in ys])
        err = lambda q: float(np.mean(np.abs(np.log10(np.maximum(y, .05) / np.maximum(q, .05)))))   # noqa: E731
        out[name] = dict(n=len(ys), observed_mean=float(y.mean()), predicted_mean=float(p.mean()), A0_mean=float(a0.mean()),
                         MAE_log10=err(p), A0_MAE_log10=err(a0), Pearson_r=float(np.corrcoef(p, y)[0, 1]),
                         years=ys, observed=y.tolist(), predicted=p.tolist())
    return out


class Objective:
    def __init__(self, groups, names):
        self.groups, self.names = groups, names

    def __call__(self, v):
        return objective(self.groups, Params(**dict(zip(self.names, v))))


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main():
    from scipy.optimize import differential_evolution
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/soil_fertility_20261106")
    ap.add_argument("--maxiter", type=int, default=40)
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    groups = build()
    names = list(BOUNDS)
    t = time.time()
    f = Objective(groups, names)
    print("one evaluation", round(f([20, 0.4, 3, 0.5]), 4), round(time.time() - t, 2), "s", flush=True)
    res = differential_evolution(f, [BOUNDS[n] for n in names], seed=20261106, maxiter=a.maxiter, popsize=10,
                                 tol=1e-6, polish=True, updating="deferred", workers=a.workers)
    best = dict(zip(names, map(float, res.x)))
    params = Params(**best)
    metrics = series_metrics(groups, params)
    selection = dict(plan="calibration/soil_fertility_20261106/plan.json",
                     amendment="calibration/soil_fertility_20261106/amendment_evaporation.json",
                     status="development fit on spent pools; frozen before the single Exhaustion Land evaluation",
                     parameters=best, objective=float(res.fun), evaluations=int(res.nfev),
                     producers={p: sha(p) for p in PRODUCERS},
                     drainage_mm_per_year={g["site"] + ":" + next(iter(set(g["calendar"].values()))):
                                           float(sum(g["drainage"].values()) / (g["last"] - g["first"] + 1)) for g in groups},
                     series={k: {kk: vv for kk, vv in v.items() if kk not in ("years", "observed", "predicted")} for k, v in metrics.items()})
    (a.out / "selection.json").write_text(json.dumps(selection, indent=1))
    (a.out / "development_series.json").write_text(json.dumps(metrics, indent=1))
    print(json.dumps(best), "loss", round(res.fun, 4), "nfev", res.nfev)
    for k, v in metrics.items():
        print(f"  {k:7s} n {v['n']:2d} obs {v['observed_mean']:.2f} pred {v['predicted_mean']:.2f} A0 {v['A0_mean']:.2f} | "
              f"MAE {v['MAE_log10']:.3f} (A0 {v['A0_MAE_log10']:.3f}) r {v['Pearson_r']:+.2f}")


if __name__ == "__main__":
    main()
