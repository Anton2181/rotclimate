"""Local sensitivity screening around a calibrated best fit.

Each search gene is nudged by +-STEP of its search range (one at a time,
clipped to the box) and the candidate scored on the same worlds as the base,
so differences are not surroundings noise. Reports, per gene, the change in
the objective, in each zone's F1 and in painted land correct; genes that move
nothing are candidates to freeze.

    python scripts/sensitivity.py calibration/round17_earthlike.json --physics v8 \
        --out calibration/sensitivity_r17_earthlike.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import multiprocessing as mp  # noqa: E402
from dataclasses import asdict  # noqa: E402

import numpy as np  # noqa: E402

from rotclimate import calibrate as C  # noqa: E402
from rotclimate.config import Params  # noqa: E402

STEP = 0.1
SPACES = {"v6": "SPACE_V6", "v7": "SPACE_V7", "v8": "SPACE_V8"}


def _job(a):
    label, x, base_dict, space, seeds, mode = a
    C._set_space(space)
    p = C.decode(np.asarray(x), Params(**base_dict))
    r = C.evaluate_params(p, mode, seeds)
    return label, dict(score=r["score"], accuracy=r["accuracy"], f1=r["f1"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("params")
    ap.add_argument("--physics", default="v8", choices=list(SPACES))
    ap.add_argument("--objective", default="f1r")
    ap.add_argument("--seeds", default="1,2,3")
    ap.add_argument("--step", type=float, default=STEP)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    space = getattr(C, SPACES[a.physics])
    C._set_space(space)
    base = Params.from_json(a.params).replace(downsample=8, steps_per_year=25, picard_iters=2)
    x0 = C.encode(base)
    seeds = [int(s) for s in a.seeds.split(",")]
    jobs = [("base", x0, None)]
    for i, name in enumerate(C.NAMES):
        if name == "retrograde":
            continue
        for sgn in (-1, 1):
            x = x0.copy()
            x[i] = np.clip(x[i] + sgn * a.step, 0, 1)
            if abs(x[i] - x0[i]) > 1e-9:
                jobs.append((f"{name}{'+' if sgn > 0 else '-'}", x, None))
    bd = asdict(base)
    with mp.get_context("fork").Pool(a.workers) as pool:
        res = dict(pool.map(_job, [(lab, x, bd, space, seeds, a.objective) for lab, x, _ in jobs], chunksize=1))
    b = res.pop("base")
    rows = []
    for name in C.NAMES:
        ds = [res[k] for k in (f"{name}-", f"{name}+") if k in res]
        if not ds:
            continue
        d_obj = max(abs(r["score"] - b["score"]) for r in ds)
        d_acc = max(abs(r["accuracy"] - b["accuracy"]) for r in ds)
        d_zone = max(abs(r["f1"][z] - b["f1"][z]) for r in ds for z in b["f1"])
        best_gain = max(r["score"] - b["score"] for r in ds)
        rows.append(dict(gene=name, d_objective=d_obj, d_correct=d_acc, d_zone_f1=d_zone, best_gain=best_gain))
    rows.sort(key=lambda r: -max(r["d_objective"], r["d_zone_f1"]))
    print(f"base objective {b['score']:.4f}, correct {b['accuracy']:.3f}; nudges of +-{a.step:.0%} of each range")
    print(f"{'gene':24s} {'|d obj|':>8s} {'|d zone F1|':>11s} {'|d correct|':>11s} {'best gain':>9s}")
    for r in rows:
        print(f"{r['gene']:24s} {r['d_objective']:8.4f} {r['d_zone_f1']:11.4f} {r['d_correct']:11.4f} {r['best_gain']:+9.4f}")
    if a.out:
        Path(a.out).write_text(json.dumps(dict(params=a.params, step=a.step, seeds=seeds, base=b, genes=rows,
                                               runs=res), indent=1))


if __name__ == "__main__":
    main()
