"""Calibrate the unknowns of the world against the painted target zones.

Unknown "world" facts (what the map does not tell us) and uncertain physics
constants are searched together with CMA-ES.  Categorical choices (spin
direction, what lies beyond each edge) are encoded as continuous genes and
thresholded, which CMA-ES copes with fine at this population size.

    python -m rotclimate.calibrate --out calibration/run1 --evals 600
"""
from __future__ import annotations

import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # one BLAS thread per worker process

import argparse
import json
import multiprocessing as mp
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .config import Params

BEYOND_MODES = ["ocean", "land", "extend"]

# name, low, high  (genes are mapped linearly from [0, 1] to [low, high])
SPACE = [
    ("lat_center", 26.0, 48.0),
    ("tilt", 8.0, 45.0),
    ("retrograde", 0.0, 1.0),
    ("beyond_north", 0.0, 2.999),
    ("beyond_south", 0.0, 2.999),
    ("beyond_west", 0.0, 2.999),
    ("beyond_east", 0.0, 2.999),
    ("beyond_north_gap_km", 0.0, 1000.0),
    ("beyond_south_gap_km", 0.0, 1000.0),
    ("beyond_west_gap_km", 0.0, 1000.0),
    ("beyond_east_gap_km", 0.0, 1000.0),
    ("tier1", 100.0, 900.0),
    ("tier2_add", 200.0, 1200.0),
    ("tier3_add", 300.0, 1800.0),
    ("tier4_add", 500.0, 3000.0),
    ("land_tau_days", 0.6, 5.0),
    ("ocean_tau_days", 0.5, 3.0),
    ("current_strength", 0.0, 8.0),
    ("sst_offset", -4.0, 4.0),
    ("land_offset", -5.0, 5.0),
    ("inland_sea_warming", 0.0, 8.0),
    ("hadley_edge", 22.0, 40.0),
    ("hadley_shift", 0.0, 10.0),
    ("itcz_mean", 0.0, 10.0),
    ("itcz_shift", 2.0, 16.0),
    ("trade_speed", 2.0, 10.0),
    ("westerly_speed", 2.0, 12.0),
    ("monsoon_strength", 0.0, 3.0),
    ("monsoon_scale_km", 250.0, 900.0),
    ("cross_isobar_deg", 10.0, 60.0),
    ("terrain_drag", 0.0, 2.0),
    ("ocean_rh", 0.65, 0.9),
    ("evap_tau_days", 0.5, 5.0),
    ("land_recycling", 0.0, 0.8),
    ("precip_tau_days", 2.0, 15.0),
    ("rh_threshold", 0.2, 0.7),
    ("storm_track", 0.0, 5.0),
    ("storm_width", 4.0, 15.0),
    ("convective", 0.0, 6.0),
    ("orographic", 0.0, 6.0),
    ("subsidence", 0.0, 0.95),
    ("subsidence_asym", 0.0, 1.0),
]
NAMES = [s[0] for s in SPACE]
LO = np.array([s[1] for s in SPACE])
HI = np.array([s[2] for s in SPACE])


def decode(x: np.ndarray, base: Params) -> Params:
    x = np.clip(x, 0.0, 1.0)
    v = dict(zip(NAMES, LO + x * (HI - LO)))
    kw = {}
    for k, val in v.items():
        if k == "retrograde":
            kw[k] = bool(val > 0.5)
        elif k.startswith("beyond_") and not k.endswith("_km"):
            kw[k] = BEYOND_MODES[int(val)]
        elif k.startswith("tier"):
            continue
        else:
            kw[k] = float(val)
    t1 = v["tier1"]
    t2 = t1 + v["tier2_add"]
    t3 = t2 + v["tier3_add"]
    t4 = t3 + v["tier4_add"]
    kw["tier_tops"] = (round(t1), round(t2), round(t3), round(t4))
    return base.replace(**kw)


def encode(p: Params) -> np.ndarray:
    v = {k: getattr(p, k) for k in NAMES if hasattr(p, k)}
    v["retrograde"] = 0.75 if p.retrograde else 0.25
    for side in ("north", "south", "west", "east"):
        v[f"beyond_{side}"] = BEYOND_MODES.index(getattr(p, f"beyond_{side}")) + 0.5
    t = p.tier_tops
    v["tier1"], v["tier2_add"], v["tier3_add"], v["tier4_add"] = t[0], t[1] - t[0], t[2] - t[1], t[3] - t[2]
    x = (np.array([v[k] for k in NAMES], float) - LO) / (HI - LO)
    return np.clip(x, 0.0, 1.0)


def evaluate_params(p: Params) -> dict:
    from .model import ClimateModel
    from .score import evaluate

    r = ClimateModel(p).run()
    ev = evaluate(r)
    return dict(score=ev["total"], accuracy=ev["accuracy"], per_class=ev["per_class"])


def _worker(args):
    x, base_dict = args
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    p = decode(np.asarray(x), Params(**base_dict))
    try:
        out = evaluate_params(p)
    except Exception as e:  # keep the search alive on numerical failures
        out = dict(score=0.0, accuracy=0.0, per_class={}, error=repr(e))
    out["params"] = asdict(p)
    return out


def calibrate(out_dir: Path, evals: int, base: Params, x0=None, sigma0=0.25,
              popsize=16, workers=4, seed=1, fixed=None):
    import cma

    out_dir.mkdir(parents=True, exist_ok=True)
    log = open(out_dir / "evals.jsonl", "a")
    x0 = encode(base) if x0 is None else np.asarray(x0)
    fixed = fixed or {}
    fixed_idx = {NAMES.index(k): v for k, v in fixed.items()}
    free = [i for i in range(len(NAMES)) if i not in fixed_idx]
    es = cma.CMAEvolutionStrategy(x0[free], sigma0,
                                  {"bounds": [0, 1], "popsize": popsize, "seed": seed,
                                   "verbose": -9})
    best = (-1, None)
    n = 0
    t0 = time.time()
    base_dict = asdict(base)
    with mp.get_context("fork").Pool(workers) as pool:
        while n < evals and not es.stop():
            sols = es.ask()
            full = []
            for s in sols:
                x = x0.copy()
                x[free] = s
                for i, v in fixed_idx.items():
                    x[i] = v
                full.append(x)
            res = pool.map(_worker, [(x, base_dict) for x in full])
            es.tell(sols, [-r["score"] for r in res])
            for x, r in zip(full, res):
                n += 1
                r["eval"] = n
                r["x"] = list(map(float, x))
                log.write(json.dumps(r) + "\n")
                if r["score"] > best[0]:
                    best = (r["score"], r)
                    Params(**r["params"]).to_json(out_dir / "best_params.json")
            log.flush()
            pc = best[1]["per_class"]
            print(f"[{n:5d} evals, {time.time() - t0:6.0f}s] best {best[0]:.3f}  gen-mean "
                  f"{np.mean([r['score'] for r in res]):.3f}  "
                  + " ".join(f"{k}={v:.2f}" for k, v in pc.items()), flush=True)
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="calibration/run")
    ap.add_argument("--evals", type=int, default=600)
    ap.add_argument("--start", default=None, help="params json to start from")
    ap.add_argument("--downsample", type=int, default=16)
    ap.add_argument("--steps", type=int, default=25)
    ap.add_argument("--sigma", type=float, default=0.25)
    ap.add_argument("--popsize", type=int, default=16)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--fix", default="{}", help='json of genes to hold fixed, e.g. {"retrograde":0.75}')
    a = ap.parse_args()
    base = Params.from_json(a.start) if a.start else Params()
    base = base.replace(downsample=a.downsample, steps_per_year=a.steps, picard_iters=2)
    fixed = json.loads(a.fix)
    best = calibrate(Path(a.out), a.evals, base, sigma0=a.sigma, popsize=a.popsize,
                     workers=a.workers, seed=a.seed, fixed=fixed)
    print(json.dumps(best["per_class"], indent=1), best["score"])


if __name__ == "__main__":
    main()
