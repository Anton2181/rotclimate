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
# physics v3: storm-eddy mixing + procedural surroundings (land fraction per
# side instead of ocean/land/extend blocks); enabled with --physics v3
_BLOCK_GENES = {"beyond_north", "beyond_south", "beyond_west", "beyond_east",
                "beyond_north_gap_km", "beyond_south_gap_km", "beyond_west_gap_km",
                "beyond_east_gap_km"}
SPACE_V3 = [g for g in SPACE if g[0] not in _BLOCK_GENES] + [
    ("beyond_north_land", 0.0, 1.0),
    ("beyond_south_land", 0.0, 1.0),
    ("beyond_west_land", 0.0, 1.0),
    ("beyond_east_land", 0.0, 1.0),
    ("beyond_continuity_km", 100.0, 700.0),
    ("beyond_relief_m", 0.0, 1500.0),
    ("eddy_rate", 0.0, 2.0),
    ("eddy_scale_km", 200.0, 900.0),
]
# physics v4: lakes and small seas follow the land temperature
SPACE_V4 = SPACE_V3 + [("lake_coupling", 0.0, 0.95), ("land_amplitude", 0.7, 1.7)]
# physics v5: east-west asymmetric storm track
SPACE_V5 = SPACE_V4 + [("storm_asym", 0.0, 1.0), ("storm_reach", 0.0, 10.0)]
# physics v6: convective instability of hot moist air
SPACE_V6 = SPACE_V5 + [("instability", 0.0, 3.0), ("beyond_southeast_land", 0.0, 1.0),
                       ("beyond_northeast_land", 0.0, 1.0)]
# physics v7: summer-strengthened subtropical highs, and the search box set
# on physical grounds, the same for both spins. Modelling choices that either
# spin's best fit had pinned (round 14 / 15p) are widened; true limits
# (land fraction, current strength >= 0, sea-air humidity <= 0.9, surface
# westerlies >= 2 m/s) stay.
_V7_BOUNDS = {
    "tier1": (50.0, 900.0),              # lowland top: coastal plains can be lower
    "tier3_add": (300.0, 2500.0),
    "land_tau_days": (0.3, 5.0),
    "evap_tau_days": (0.3, 5.0),
    "monsoon_strength": (0.0, 5.0),      # round 15p's 2.95 gives land winds <= 7.5 m/s
    "monsoon_scale_km": (250.0, 1500.0),  # thermal lows are continent-sized
    "storm_track": (0.0, 8.0),
    "beyond_continuity_km": (100.0, 1200.0),
    "land_amplitude": (0.7, 2.0),
}
SPACE_V7 = [(n, *_V7_BOUNDS.get(n, (lo, hi))) for n, lo, hi in SPACE_V6] + [("subsidence_summer", 0.0, 1.0)]
# physics v8: wet ground evaporates away part of the summer warmth
SPACE_V8 = SPACE_V7 + [("wet_cooling", 0.0, 0.8)]


def _set_space(space):
    global SPACE, NAMES, LO, HI
    SPACE = space
    NAMES = [s[0] for s in SPACE]
    LO = np.array([s[1] for s in SPACE])
    HI = np.array([s[2] for s in SPACE])


_set_space(SPACE)


def decode(x: np.ndarray, base: Params) -> Params:
    x = np.clip(x, 0.0, 1.0)
    v = dict(zip(NAMES, LO + x * (HI - LO)))
    kw = {}
    for k, val in v.items():
        if k == "retrograde":
            kw[k] = bool(val > 0.5)
        elif k in ("beyond_north", "beyond_south", "beyond_west", "beyond_east"):
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
        if f"beyond_{side}" in NAMES:
            v[f"beyond_{side}"] = BEYOND_MODES.index(getattr(p, f"beyond_{side}")) + 0.5
    t = p.tier_tops
    v["tier1"], v["tier2_add"], v["tier3_add"], v["tier4_add"] = t[0], t[1] - t[0], t[2] - t[1], t[3] - t[2]
    x = (np.array([v[k] for k in NAMES], float) - LO) / (HI - LO)
    return np.clip(x, 0.0, 1.0)


def evaluate_params(p: Params, mode="mean", seeds=None, cutoff=None) -> dict:
    """Score a parameter set; with several seeds the unknown surroundings are
    re-generated for each and the zone scores averaged (ensemble).

    Racing: with a `cutoff`, a candidate whose first world already scores
    below it skips the remaining worlds (it cannot become the best; the
    best is always scored on every world)."""
    from .model import ClimateModel
    from .score import evaluate, objective

    evs = []
    seeds = seeds or [None]
    for i, sd in enumerate(seeds):
        q = p if sd is None else p.replace(beyond_seed=int(sd))
        evs.append(evaluate(ClimateModel(q).run()))
        if cutoff is not None and i == 0 and len(seeds) > 1 and objective(evs[0], mode) < cutoff:
            break
    ev = dict(evs[0])
    ev["per_class"] = {k: float(np.mean([e["per_class"][k] for e in evs])) for k in ev["per_class"]}
    ev["total"] = float(np.nanmean(list(ev["per_class"].values())))
    for key in ("precision", "f1"):
        ev[key] = {k: float(np.mean([e[key][k] for e in evs])) for k in ev[key]}
    ev["accuracy"] = float(np.mean([e["accuracy"] for e in evs]))
    ev["realism"] = {k: float(np.mean([e["realism"][k] for e in evs])) for k in ev["realism"]}
    return dict(score=objective(ev, mode), mean=ev["total"], accuracy=ev["accuracy"], raced=len(evs) < len(seeds),
                per_class=ev["per_class"], f1=ev["f1"], precision=ev["precision"], realism=ev["realism"],
                spread=float(np.std([e["total"] for e in evs])))


def _worker(args):
    x, base_dict, mode, space, seeds, cutoff = args
    _set_space(space)
    p = decode(np.asarray(x), Params(**base_dict))
    try:
        out = evaluate_params(p, mode, seeds, cutoff)
    except Exception as e:  # keep the search alive on numerical failures
        out = dict(score=-1.0, mean=0.0, accuracy=0.0, per_class={}, error=repr(e))
    out["params"] = asdict(p)
    return out


def calibrate(out_dir: Path, evals: int, base: Params, x0=None, sigma0=0.25,
              popsize=16, workers=4, seed=1, fixed=None, mode="mean", seeds=None, race=0.06):
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
    n = n_raced = 0
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
            cutoff = best[0] - race if (race and best[1] is not None) else None
            res = pool.map(_worker, [(x, base_dict, mode, SPACE, seeds, cutoff) for x in full], chunksize=1)
            n_raced += sum(bool(r.get("raced")) for r in res)
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
            f1 = best[1].get("f1", {}) if mode == "f1" else {}
            print(f"[{n:5d} evals, {n_raced} raced, {time.time() - t0:6.0f}s] best {best[0]:.3f} "
                  f"(mean {best[1].get('mean', best[0]):.3f})  gen-mean "
                  f"{np.mean([r['score'] for r in res]):.3f}  "
                  + " ".join(f"{k}={v:.2f}" + (f"/F{f1[k]:.2f}" if k in f1 else "") for k, v in pc.items()),
                  flush=True)
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
    ap.add_argument("--objective", default="mean", choices=["mean", "balanced", "f1", "f1r"])
    ap.add_argument("--physics", default="v2", choices=["v2", "v3", "v4", "v5", "v6", "v7", "v8"])
    ap.add_argument("--seeds", default="", help="comma list of surroundings seeds (ensemble)")
    ap.add_argument("--race", type=float, default=0.06,
                    help="skip the other worlds for candidates whose first world scores this far below the best (0 = off)")
    ap.add_argument("--set", default="{}", help="json of parameter overrides for the start point")
    a = ap.parse_args()
    if a.physics == "v3":
        _set_space(SPACE_V3)
    elif a.physics == "v4":
        _set_space(SPACE_V4)
    elif a.physics == "v5":
        _set_space(SPACE_V5)
    elif a.physics == "v6":
        _set_space(SPACE_V6)
    elif a.physics == "v7":
        _set_space(SPACE_V7)
    elif a.physics == "v8":
        _set_space(SPACE_V8)
    base = Params.from_json(a.start) if a.start else Params()
    base = base.replace(downsample=a.downsample, steps_per_year=a.steps, picard_iters=2)
    if a.physics in ("v3", "v4", "v5", "v6", "v7", "v8"):
        base = base.replace(beyond_style="procedural")
    base = base.replace(**{k: (tuple(v) if isinstance(v, list) else v)
                           for k, v in json.loads(a.set).items()})
    seeds = [int(x) for x in a.seeds.split(",") if x.strip()] or None
    fixed = json.loads(a.fix)
    best = calibrate(Path(a.out), a.evals, base, sigma0=a.sigma, popsize=a.popsize,
                     workers=a.workers, seed=a.seed, fixed=fixed, mode=a.objective, seeds=seeds, race=a.race)
    print(json.dumps(best["per_class"], indent=1), best["score"])


if __name__ == "__main__":
    main()
