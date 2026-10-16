"""Calibrate the model's physics constants on real regions (Earth mode).

Only physics genes are searched; geography, tilt, spin and calendar are
Earth's own. Objective (minimised): the mean over regions of the mean
climate distance to WorldClim (rotclimate.earth.climate_distance).

    python -I scripts/earth_calibrate.py --start output/overnight_mediterranean/selected_params.json \
        --regions california iberia --evals 240 --out calibration/earth_r1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import multiprocessing as mp  # noqa: E402

import numpy as np  # noqa: E402

from rotclimate import calibrate as C  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.config import Params  # noqa: E402

# genes that describe the world rather than its physics: fixed on Earth
WORLD = {"lat_center", "tilt", "retrograde", "north_bearing", "tier1", "tier2_add", "tier3_add", "tier4_add",
         "beyond_north_land", "beyond_south_land", "beyond_west_land", "beyond_east_land", "beyond_continuity_km",
         "beyond_relief_m", "beyond_southeast_land", "beyond_northeast_land"}
# numerics: converged moisture equation (the old fixed two half-steps are badly
# wrong) with linear solves at 1e-5 (same result as 1e-7; at 1e-3 the moisture
# equation cannot reach its tolerance in Iberia)
NUMERICS = dict(moisture_residual_tol=0.01, moisture_require_convergence=True, solver_rtol=1e-5,
                solver_require_convergence=False, steps_per_year=25)
SPACES = {"v9": [g for g in C.SPACE_V8 if g[0] not in WORLD] + [("eddy_seasonality", 0.0, 0.9)]}
SPACES["e1"] = SPACES["v9"] + [g for g in C.SPACE_E1 if g[0] not in {n for n, *_ in C.SPACE_V9}]
# on Earth the terrain heights are known, so the near-surface lapse rate (held at
# 6 K/km on the map, where it would trade off against the unknown tier heights)
# can be fitted too; WorldClim's own along-terrain rates are 3-5.5 K/km
SPACES["e1"] = SPACES["e1"] + [("lapse_rate", 4.0, 7.0)]
SPACES["e2"] = SPACES["e1"] + [g for g in C.SPACE_E2 if g[0] not in {n for n, *_ in C.SPACE_E1}]
SPACE = SPACES["v9"]
_CASES = {}


def physics(x, base):
    names = [g[0] for g in SPACE]
    lo = np.array([g[1] for g in SPACE]); hi = np.array([g[2] for g in SPACE])
    v = lo + np.clip(x, 0, 1) * (hi - lo)
    return base.replace(**{n: float(val) for n, val in zip(names, v)})


def encode(p):
    lo = np.array([g[1] for g in SPACE]); hi = np.array([g[2] for g in SPACE])
    v = np.array([getattr(p, g[0]) for g in SPACE], float)
    return np.clip((v - lo) / (hi - lo), 0, 1)


def evaluate(args):
    x, base_dict, regions, cell_km = args
    p = physics(np.asarray(x), Params(**base_dict))
    out = dict(params=asdict(p), regions={})
    try:
        for r in regions:
            if (r, cell_km) not in _CASES:
                _CASES[(r, cell_km)] = earth.region_case(r, cell_km)
            case = _CASES[(r, cell_km)]
            res = earth.run_case(p, case, steps=p.steps_per_year)
            out["regions"][r] = earth.compare(res, case)
        out["cost"] = float(np.mean([out["regions"][r]["climate_distance"] for r in regions]))
    except Exception as e:      # non-convergence or numerical failure
        out["cost"] = 99.0
        out["error"] = repr(e)[:300]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--regions", nargs="+", default=["california", "iberia"])
    ap.add_argument("--cell-km", type=float, default=28.0)
    ap.add_argument("--evals", type=int, default=240)
    ap.add_argument("--popsize", type=int, default=12)
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--holdout", nargs="*", default=[], help="regions scored only for the final best")
    ap.add_argument("--physics", default="v9", choices=list(SPACES))
    ap.add_argument("--bounds", default="{}", help='json of search bounds to override, e.g. {"hadley_edge": [28, 34]}')
    ap.add_argument("--set", default="{}", help="json of parameter overrides for the start point")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import cma

    global SPACE
    bounds = json.loads(a.bounds)
    SPACE = [(n, *bounds.get(n, (lo, hi))) for n, lo, hi in SPACES[a.physics]]   # set before the workers fork

    d = json.loads(Path(a.start).read_text())
    d = d.get("params", d)
    base = Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__}).replace(**NUMERICS).replace(**json.loads(a.set))
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (out / "space.json").write_text(json.dumps(dict(args=vars(a), space=SPACE), indent=1))
    log = (out / "evals.jsonl").open("a")
    es = cma.CMAEvolutionStrategy(encode(base), a.sigma, dict(bounds=[0, 1], popsize=a.popsize, seed=a.seed,
                                                                 verbose=-9))
    bd = asdict(base)
    best, n, t0 = None, 0, time.time()
    with mp.get_context("fork").Pool(a.workers) as pool:
        first = pool.map(evaluate, [(encode(base), bd, a.regions, a.cell_km)])[0]
        log.write(json.dumps(first) + "\n"); log.flush(); best = first; n = 1
        print(f"start cost {first['cost']:.4f} {first.get('error', '')} " + " ".join(f"{r} {v['climate_distance']:.3f}/K{v['koppen_full_model']['exact']:.0%}"
                                                       for r, v in first.get("regions", {}).items()), flush=True)
        while n < a.evals:
            xs = es.ask()
            res = pool.map(evaluate, [(x, bd, a.regions, a.cell_km) for x in xs], chunksize=1)
            es.tell(xs, [r["cost"] for r in res])
            for r in res:
                log.write(json.dumps(r) + "\n")
                if r["cost"] < best["cost"]:
                    best = r
            log.flush(); n += len(xs)
            Path(out / "best_params.json").write_text(json.dumps(best["params"], indent=1))
            br = best.get("regions", {})
            print(f"[{n:4d} evals, {time.time() - t0:5.0f}s] best {best['cost']:.4f} gen-median {np.median([r['cost'] for r in res]):.3f} | "
                  + " ".join(f"{k}: d {v['climate_distance']:.3f} Kop {v['koppen_full_model']['exact']:.0%} "
                             f"Cs kept {_pct(v['koppen_full_model']['cs_retained'])} T {v['temperature']['bias_C']:+.1f} "
                             f"rain {v['rain']['sim_mean_annual_mm']:.0f}/{v['rain']['obs_mean_annual_mm']:.0f}"
                             for k, v in br.items()), flush=True)
        if a.holdout:
            h = pool.map(evaluate, [(encode(Params(**best["params"])), bd, [r], a.cell_km) for r in a.holdout])
            held = {r: x.get("regions", {}).get(r, x.get("error")) for r, x in zip(a.holdout, h)}
            Path(out / "holdout.json").write_text(json.dumps(held, indent=1))
            for r, v in held.items():
                print(f"holdout {earth.summary_line(v) if isinstance(v, dict) else r + ' ' + str(v)}"
                      + (f" | d {v['climate_distance']:.3f}" if isinstance(v, dict) else ""), flush=True)


def _pct(x):
    return "n/a" if x is None else f"{x:.0%}"


if __name__ == "__main__":
    main()
