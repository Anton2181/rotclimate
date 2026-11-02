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

A plan may opt into policy v3 with ``"scoring_policy": "v3"``. In that
case S includes dev31 and all extra development groups with equal region
weights; group scores are reported without penalties. Only the existing
1% temperature/rain safeguards contribute a penalty. ``initial_mean`` may
specify a separate CMA centre in normalised knob coordinates for independent
restarts; the actual starting profile is always evaluated first.

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
    region, params = job[:2]
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    if len(job) > 2 and job[2]:
        earth.REGIONS.update(job[2])           # extra development regions (plan["extra_groups"])
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


def score(errors, reference, groups, extra=None, *, policy="v2"):
    if policy not in {"v2", "v3"}:
        raise ValueError("Unknown scoring policy: " + policy)
    if policy == "v3":
        members = [n for group in (*groups.values(), *(extra or {}).values()) for n in group]
        if not members or len(members) != len(set(members)):
            raise ValueError("Development regions must be nonempty and unique across groups")
        if set(errors) != set(members) or not set(members) <= set(reference):
            raise ValueError("Candidate and reference must cover every development region")
        for values in (errors, reference):
            a = np.asarray([values[n] for n in members], float)
            if a.shape != (len(members), 2) or not np.isfinite(a).all() or (a < 0).any():
                raise ValueError("Nonfinite or negative climate errors")
        if (np.mean([reference[n] for n in members], axis=0) <= 0).any():
            raise ValueError("Reference mean errors must be positive")
    def means(names):
        return (np.mean([errors[n][0] for n in names]), np.mean([errors[n][1] for n in names]))

    def s(names):
        t, p = means(names); tr, pr = (np.mean([reference[n][0] for n in names]), np.mean([reference[n][1] for n in names]))
        return 0.5 * t / tr + 0.5 * p / pr
    names = [n for members in groups.values() for n in members]
    scored = names if policy == "v2" else names + [n for m in (extra or {}).values() for n in m]
    overall = s(scored)
    group = {g: s(members) for g, members in groups.items()}
    t, p = means(scored)
    tr, pr = np.mean([reference[n][0] for n in scored]), np.mean([reference[n][1] for n in scored])
    penalty = sum(2 * max(0.0, v - 1.0) for v in group.values()) if policy == "v2" else 0.0
    penalty += 2 * max(0.0, t / tr - 1.01) + 2 * max(0.0, p / pr - 1.01)
    # extra development groups (e.g. a retired sealed set): penalised like the policy
    # groups when they worsen, but outside S, which stays the policy's 31-region score
    for g, members in (extra or {}).items():
        group[g] = s(members)
        if policy == "v2":
            penalty += 2 * max(0.0, group[g] - 1.0)
    info = dict(S=overall, groups=group, T=t, P=p, penalty=penalty)
    if policy == "v3":
        info.update(S31=s(names), n=len(scored), T_relative=t / tr - 1, P_relative=p / pr - 1)
    return overall + penalty, info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--hours", type=float, default=1.9, help="stop cleanly after this long (resume later)")
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    scoring_policy = plan.get("scoring_policy", "v2")
    if scoring_policy not in {"v2", "v3"}:
        ap.error("scoring_policy must be v2 or v3")
    groups = json.loads(POLICY.read_text())["groups"]
    regions = [n for members in groups.values() for n in members]
    ref = json.loads((ROOT / plan["reference"] / "summary.json").read_text())["regions"]
    reference = {n: (ref[n]["temperature"]["monthly_mae_C"], ref[n]["rain"]["loss"]) for n in regions}
    extra, extra_specs = {}, {}
    for g, spec in plan.get("extra_groups", {}).items():
        specs = json.loads((ROOT / spec["spec"]).read_text()); extra_specs.update(specs); extra[g] = list(specs)
        er = json.loads((ROOT / spec["reference"] / "summary.json").read_text())["regions"]
        reference.update({n: (er[n]["temperature"]["monthly_mae_C"], er[n]["rain"]["loss"]) for n in specs})
    all_regions = regions + [n for members in extra.values() for n in members]
    if scoring_policy == "v3":
        # Catch weighting/coverage mistakes before running any climate cases.
        score(reference, reference, groups, extra, policy="v3")
        if len(all_regions) != 49:
            ap.error("Policy v3 requires exactly the declared 49 development regions")
        for folder in [plan["reference"], *(s["reference"] for s in plan.get("extra_groups", {}).values())]:
            summary = json.loads((ROOT / folder / "summary.json").read_text())
            if summary.get("complete") is not True or any(
                r.get("status") != "passed" or r.get("numerics", {}).get("all_checks_passed") is not True
                for r in summary["regions"].values()
            ):
                ap.error("Policy v3 requires complete, numerically verified references: " + folder)
    base = load_params(ROOT / plan["start"]).replace(**plan.get("set", {}))
    knobs = plan["knobs"]                             # [[name, lo, hi], ...]
    lo = np.array([k[1] for k in knobs], float); hi = np.array([k[2] for k in knobs], float)

    def decode(x):
        v = lo + np.clip(x, 0, 1) * (hi - lo)
        return base.replace(**{k[0]: float(val) for k, val in zip(knobs, v)})
    x0 = np.clip((np.array([getattr(base, k[0]) for k in knobs], float) - lo) / (hi - lo), 0, 1)
    initial_mean = np.asarray(plan.get("initial_mean", x0), float)
    if initial_mean.shape != x0.shape or not np.isfinite(initial_mean).all() or ((initial_mean < 0) | (initial_mean > 1)).any():
        ap.error("initial_mean must give one finite [0, 1] coordinate per knob")
    a.out.mkdir(parents=True, exist_ok=True)
    state_path, log_path = a.out / "state.pkl", a.out / "evals.jsonl"
    import cma
    from dataclasses import asdict
    if scoring_policy == "v3":
        # A resume must never mix objectives, source revisions or reference data.
        from local_benchmark_protocol import file_hash, freeze
        refs = [ROOT / plan["reference"] / "summary.json"]
        for spec in plan.get("extra_groups", {}).values():
            refs.extend([ROOT / spec["spec"], ROOT / spec["reference"] / "summary.json"])
        refs.extend([Path(__file__), ROOT / "scripts/rainfall_metrics.py", ROOT / "scripts/benchmark_local.py"])
        refs.extend((ROOT / "rotclimate").glob("*.py"))
        if state_path.exists() and not (a.out / "search_identity.json").exists():
            ap.error("Cannot resume a legacy search under v3; use a new output directory")
        freeze(a.out / "search_identity.json", dict(plan=plan, sources={str(f.relative_to(ROOT)): file_hash(f) for f in refs}))
    if a.resume and state_path.exists():
        with state_path.open("rb") as f:
            es, pending, best, n = pickle.load(f)
        print(f"resumed at {n} evaluations, best {best['cost']:.4f}", flush=True)
    else:
        if log_path.exists():
            raise SystemExit("Refusing to append a new search to existing results; use --resume")
        (a.out / "plan.json").write_text(json.dumps(plan, indent=1))
        es = cma.CMAEvolutionStrategy(initial_mean, plan.get("sigma", 0.25),
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
            rows = dict(pool.map(region_errors, [(r, asdict(p), extra_specs) for r in all_regions]))
            if any(v is None for v in rows.values()):
                cost, info = 99.0, dict(failed=[r for r, v in rows.items() if v is None])
            else:
                cost, info = score(rows, reference, groups, extra, policy=scoring_policy)
            rec = dict(n=n, cost=cost, knobs={k[0]: getattr(p, k[0]) for k in knobs}, **info,
                       regions={r: v for r, v in rows.items()})
            log.write(json.dumps(rec, default=float) + "\n"); log.flush()
            if n == 0 and plan.get("require_reference_reproduction"):
                mismatch = [r for r in all_regions if rows[r] is None or not np.allclose(
                    rows[r], reference[r], rtol=0, atol=1e-10)]
                if mismatch:
                    raise RuntimeError("Starting control does not reproduce the frozen reference: " + ', '.join(mismatch))
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
