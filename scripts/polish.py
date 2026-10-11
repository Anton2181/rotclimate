"""Polish a calibrated best fit with a batch pattern search.

CMA-ES moves in random directions, so near an optimum it can miss simple
one-gene improvements (sensitivity screening showed several on round 17's
reversed-spin fit). Each iteration here tries every active gene at +-step
(in parallel, on the same worlds), then the combination of all improving
moves and of the best few; it keeps the best candidate if it improves and
otherwise halves the step. Genes in --freeze stay put.

    python scripts/polish.py calibration/round17_retrograde.json --out calibration/r18_retrograde \
        --freeze itcz_mean,itcz_shift --evals 330
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
from rotclimate.config import Params  # noqa: E402

SPACES = {"v6": "SPACE_V6", "v7": "SPACE_V7", "v8": "SPACE_V8", "v9": "SPACE_V9"}


def _job(a):
    x, base_dict, space, seeds, mode = a
    C._set_space(space)
    p = C.decode(np.asarray(x), Params(**base_dict))
    try:
        r = C.evaluate_params(p, mode, seeds)
    except Exception as e:  # keep going on numerical failures
        r = dict(score=-1.0, accuracy=0.0, f1={}, error=repr(e))
    r["params"] = asdict(p)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("params")
    ap.add_argument("--out", required=True)
    ap.add_argument("--physics", default="v8", choices=list(SPACES))
    ap.add_argument("--objective", default="f1r")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--freeze", default="", help="comma list of genes to hold fixed")
    ap.add_argument("--bounds", default="{}", help="json of search bounds to override")
    ap.add_argument("--step", type=float, default=0.1)
    ap.add_argument("--min-step", type=float, default=0.02)
    ap.add_argument("--evals", type=int, default=330)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    space = getattr(C, SPACES[a.physics])
    bounds = json.loads(a.bounds)
    space = [(n, *bounds.get(n, (lo, hi))) for n, lo, hi in space]
    C._set_space(space)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    seeds = [int(s) for s in a.seeds.split(",")]
    frozen = {g for g in a.freeze.split(",") if g} | {"retrograde"}
    active = [i for i, n in enumerate(C.NAMES) if n not in frozen]
    base = Params.from_json(a.params).replace(downsample=8, steps_per_year=25, picard_iters=2)
    bd = asdict(base)
    x = C.encode(base)
    log = (out / "evals.jsonl").open("a")
    used = 0
    t0 = time.time()

    def run(xs):
        nonlocal used
        with mp.get_context("fork").Pool(a.workers) as pool:
            res = pool.map(_job, [(xx, bd, space, seeds, a.objective) for xx in xs], chunksize=1)
        used += len(xs)
        for r in res:
            log.write(json.dumps(r) + "\n")
        log.flush()
        return res

    best = run([x])[0]
    step = a.step
    print(f"start {best['score']:.4f} (correct {best['accuracy']:.3f}); {len(active)} active genes", flush=True)
    while used < a.evals and step >= a.min_step:
        moves = []
        for i in active:
            for sgn in (-1, 1):
                xx = x.copy()
                xx[i] = np.clip(xx[i] + sgn * step, 0, 1)
                if abs(xx[i] - x[i]) > 1e-9:
                    moves.append((i, xx[i] - x[i], xx))
        res = run([m[2] for m in moves])
        gains = sorted(((r["score"] - best["score"], m) for r, m in zip(res, moves)), key=lambda t: -t[0])
        cand = [(r, m[2]) for r, m in zip(res, moves)]
        # combinations of the improving moves (one direction per gene)
        good, seen = [], set()
        for g, (i, d, _) in gains:
            if g > 0 and i not in seen:
                good.append((i, d)); seen.add(i)
        combos = []
        for k in sorted({len(good), min(len(good), 5), min(len(good), 2)}):
            if k >= 2:
                xx = x.copy()
                for i, d in good[:k]:
                    xx[i] = np.clip(xx[i] + d, 0, 1)
                combos.append(xx)
        if combos:
            cand += list(zip(run(combos), combos))
        r_best, x_best = max(cand, key=lambda t: t[0]["score"])
        if r_best["score"] > best["score"] + 1e-4:
            gained = r_best["score"] - best["score"]
            best, x = r_best, x_best
            print(f"[{used:4d} evals, {time.time() - t0:5.0f}s] step {step:.3f}: {best['score']:.4f} (+{gained:.4f}), "
                  f"correct {best['accuracy']:.3f}; {len(good)} improving genes", flush=True)
        else:
            step /= 2
            print(f"[{used:4d} evals, {time.time() - t0:5.0f}s] no gain; step -> {step:.3f}", flush=True)
        Path(out / "best_params.json").write_text(json.dumps(best["params"], indent=1))
    Path(out / "best_params.json").write_text(json.dumps(best["params"], indent=1))
    print(json.dumps(best["f1"], indent=1), best["score"])


if __name__ == "__main__":
    main()
