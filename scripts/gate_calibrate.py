"""Search physics knobs on the 31 development regions with the gate's own score.

    python3 -I scripts/gate_calibrate.py --plan calibration/rain_knobs_20261024/plan.json \
        --out calibration/rain_knobs_20261024/search [--resume]

The plan names the start (a parameter file), the knobs with their bounds, the
reference run whose equal-region means normalise the score, and the budget.
Each candidate runs all 31 regions at 56 km (regions in parallel) and is scored
as scripts/gate_local.py scores it: S = 0.5 T/T_ref + 0.5 P/P_ref over the 31,
plus a penalty of 2 x (group score - 1) for every policy group that worsens and
of 2 x (relative change - 1 %) when T or P worsens by more than 1 %. CMA-ES
(bounds mapped to [0, 1]); the state is saved after every candidate, so a run
stopped by a time limit resumes where it was.

A searched candidate is still only a candidate: it takes the frozen gate
against a fresh reference, the paired 28 km check and the sealed six once.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS, temperature_metrics  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402

POLICY = ROOT / "calibration/local_accuracy_20261023/policy_v2.json"


def region_errors(job):
    region, params = job
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    p = Params(**params)
    case = earth.region_case(region, 56.0)
    try:
        res = earth.run_case(p, case, steps=p.steps_per_year)
        if res.numerics.get("all_checks_passed") is not True:
            return region, None
    except Exception:          # non-convergence counts as a failed candidate
        return region, None
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    t = temperature_metrics(st["Tm"][:, m], np.asarray(case.obs_T)[:, m])
    r = local_metrics(np.maximum(st["Pm"], 0.0), np.nan_to_num(case.obs_P), m)
    return region, (t["monthly_mae_C"], r["loss"])


def score(errors, reference, groups):
    def means(names):
        return (np.mean([errors[n][0] for n in names]), np.mean([errors[n][1] for n in names]))

    def s(names):
        t, p = means(names); tr, pr = (np.mean([reference[n][0] for n in names]), np.mean([reference[n][1] for n in names]))
        return 0.5 * t / tr + 0.5 * p / pr
    names = [n for members in groups.values() for n in members]
    overall = s(names)
    group = {g: s(members) for g, members in groups.items()}
    t, p = means(names)
    tr, pr = np.mean([reference[n][0] for n in names]), np.mean([reference[n][1] for n in names])
    penalty = sum(2 * max(0.0, v - 1.0) for v in group.values())
    penalty += 2 * max(0.0, t / tr - 1.01) + 2 * max(0.0, p / pr - 1.01)
    return overall + penalty, dict(S=overall, groups=group, T=t, P=p, penalty=penalty)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--hours", type=float, default=1.9, help="stop cleanly after this long (resume later)")
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    groups = json.loads(POLICY.read_text())["groups"]
    regions = [n for members in groups.values() for n in members]
    ref = json.loads((ROOT / plan["reference"] / "summary.json").read_text())["regions"]
    reference = {n: (ref[n]["temperature"]["monthly_mae_C"], ref[n]["rain"]["loss"]) for n in regions}
    base = load_params(ROOT / plan["start"]).replace(**plan.get("set", {}))
    knobs = plan["knobs"]                             # [[name, lo, hi], ...]
    lo = np.array([k[1] for k in knobs], float); hi = np.array([k[2] for k in knobs], float)

    def decode(x):
        v = lo + np.clip(x, 0, 1) * (hi - lo)
        return base.replace(**{k[0]: float(val) for k, val in zip(knobs, v)})
    x0 = np.clip((np.array([getattr(base, k[0]) for k in knobs], float) - lo) / (hi - lo), 0, 1)
    a.out.mkdir(parents=True, exist_ok=True)
    state_path, log_path = a.out / "state.pkl", a.out / "evals.jsonl"
    import cma
    from dataclasses import asdict
    if a.resume and state_path.exists():
        with state_path.open("rb") as f:
            es, pending, best, n = pickle.load(f)
        print(f"resumed at {n} evaluations, best {best['cost']:.4f}", flush=True)
    else:
        if log_path.exists():
            raise SystemExit("Refusing to append a new search to existing results; use --resume")
        (a.out / "plan.json").write_text(json.dumps(plan, indent=1))
        es = cma.CMAEvolutionStrategy(x0, plan.get("sigma", 0.25),
                                      dict(bounds=[0, 1], popsize=plan.get("popsize", 8), seed=plan.get("seed", 1), verbose=-9))
        es._told = []
        pending, best, n = [x0], None, 0      # the start point is scored first, outside the search
    t0 = time.time()
    with Pool(a.workers) as pool, log_path.open("a") as log:
        while n < plan["evals"] and time.time() - t0 < a.hours * 3600:
            if not pending:
                pending = list(es.ask())
            x = pending.pop(0)
            p = decode(x)
            rows = dict(pool.map(region_errors, [(r, asdict(p)) for r in regions]))
            if any(v is None for v in rows.values()):
                cost, info = 99.0, dict(failed=[r for r, v in rows.items() if v is None])
            else:
                cost, info = score(rows, reference, groups)
            rec = dict(n=n, cost=cost, knobs={k[0]: getattr(p, k[0]) for k in knobs}, **info,
                       regions={r: v for r, v in rows.items()})
            log.write(json.dumps(rec, default=float) + "\n"); log.flush()
            if best is None or cost < best["cost"]:
                best = rec
                (a.out / "best_params.json").write_text(json.dumps(asdict(p), indent=1))
            if n > 0:
                es._told.append((x, cost))
            if len(es._told) == es.popsize:
                es.tell([t[0] for t in es._told], [t[1] for t in es._told]); es._told = []
            n += 1
            print(f"[{n:3d}] cost {cost:.4f} S {info.get('S', float('nan')):.4f} best {best['cost']:.4f} | "
                  + " ".join(f"{k[0]}={getattr(p, k[0]):.3g}" for k in knobs), flush=True)
            with (a.out / "state.tmp").open("wb") as f:
                pickle.dump((es, pending, best, n), f)
            (a.out / "state.tmp").replace(state_path)
    print(f"stopped at {n} evaluations; best cost {best['cost']:.4f}: " + json.dumps(best["knobs"]), flush=True)


if __name__ == "__main__":
    main()
