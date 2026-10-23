"""Stage A: refit atmosphere settings for per-location accuracy, scored by the
frozen local gate (calibration/local_accuracy_20261023/policy.json).

    python3 -I scripts/fit_local.py --base PARAMS --set SEA.json --regions ... --out DIR [--evals N] [--resume]

Cost = mean over the fitting regions of
    0.5 * T_monthly_mae / T_ref + 0.5 * rainfall_loss / P_ref
with per-region references from the r29 baseline benchmark
(output/local_20261023/baseline_56km/summary.json), so every region counts
equally. The search varies SPACE only; everything else, including the
sea-surface settings passed with --set, stays fixed. CMA-ES state is saved
every generation (--resume continues). The best parameters are written to
DIR/best_params.json; judge them with scripts/benchmark_local.py and
scripts/gate_local.py on regions not used here.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from dataclasses import asdict
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from earth_benchmark import load_params  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402

SPACE = [("land_tau_days", 0.3, 2.5), ("land_radiative_days", 3.0, 40.0), ("land_coupling_insolation", 0.5, 3.0),
         ("continentality", 0.2, 1.5), ("land_offset", -1.5, 2.5), ("land_amplitude", 0.7, 1.4),
         ("ocean_rh", 0.62, 0.78), ("rh_threshold", 0.25, 0.5)]
REF = ROOT / "output" / "local_20261023" / "baseline_56km" / "summary.json"


def region_cost(job):
    region, pdict, ref = job
    try:
        p = Params(**pdict)
        case = earth.region_case(region, 56.0)
        res = earth.run_case(p, case, steps=p.steps_per_year)
        pr = res.params
        st = monthly_stats(res.T, res.P, res.days, pr.year_days, summer_solstice=pr.winter_solstice_day + pr.year_days / 2)
        g = case.grid
        m = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        tm = float(np.abs(st["Tm"][:, m] - case.obs_T[:, m]).mean())
        pl = local_metrics(np.maximum(st["Pm"], 0.0), np.nan_to_num(case.obs_P), m)["loss"]
        return region, dict(T=tm, P=pl, S=0.5 * tm / ref[region]["T"] + 0.5 * pl / ref[region]["P"])
    except Exception as e:  # noqa: BLE001  (numerical failure scores badly, never silently)
        return region, dict(T=None, P=None, S=9.0, error=repr(e)[:200])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--set", help="json file of fixed overrides (e.g. the Stage B sea settings)")
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--evals", type=int, default=150)
    ap.add_argument("--popsize", type=int, default=10)
    ap.add_argument("--sigma", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=231023)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    import cma
    base = load_params(a.base)
    if a.set:
        base = base.replace(**json.loads(Path(a.set).read_text()))
    refs = json.loads(REF.read_text())["regions"]
    ref = {r: dict(T=refs[r]["temperature"]["monthly_mae_C"], P=refs[r]["rain"]["loss"]) for r in a.regions}
    lo = np.array([g[1] for g in SPACE]); hi = np.array([g[2] for g in SPACE])

    def params(x):
        return base.replace(**{g[0]: float(v) for g, v in zip(SPACE, lo + np.clip(x, 0, 1) * (hi - lo))})

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    state = out / "state.pkl"
    with Pool(4) as pool:
        def cost(x):
            res = dict(pool.map(region_cost, [(r, asdict(params(x)), ref) for r in a.regions], chunksize=1))
            return float(np.mean([res[r]["S"] for r in a.regions])), res
        if a.resume and state.exists():
            es, best, n = pickle.loads(state.read_bytes())
            print(f"resumed at {n} evals, best {best[0]:.4f}", flush=True)
        else:
            x0 = np.clip((np.array([getattr(base, g[0]) for g in SPACE], float) - lo) / (hi - lo), 0, 1)
            es = cma.CMAEvolutionStrategy(x0, a.sigma, dict(bounds=[0, 1], popsize=a.popsize, seed=a.seed, verbose=-9))
            c0, r0 = cost(x0)
            best, n = (c0, x0, r0), 1
            print(f"start cost {c0:.4f}", flush=True)
        log = (out / "evals.jsonl").open("a")
        while n < a.evals:
            xs = es.ask()
            cs = []
            for x in xs:
                c, r = cost(x)
                cs.append(c)
                log.write(json.dumps(dict(cost=c, params={g[0]: float(v) for g, v in zip(SPACE, lo + np.clip(x, 0, 1) * (hi - lo))},
                                          regions=r)) + "\n")
                if c < best[0]:
                    best = (c, np.asarray(x), r)
            es.tell(xs, cs); n += len(xs); log.flush()
            (out / "best_params.json").write_text(json.dumps(asdict(params(best[1])), indent=1))
            state.write_bytes(pickle.dumps((es, best, n)))
            print(f"[{n:4d}] best {best[0]:.4f} gen-median {np.median(cs):.4f}", flush=True)
        print("best:", json.dumps({g[0]: round(float(v), 4) for g, v in zip(SPACE, lo + np.clip(best[1], 0, 1) * (hi - lo))}))


if __name__ == "__main__":
    main()
