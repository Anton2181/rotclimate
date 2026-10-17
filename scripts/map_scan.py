"""Score setting overrides on top of one map fit against the painted zones.

    python -I scripts/map_scan.py --start calibration/earth/free_d2_polish_ds16.json \
        --grid '[{}, {"slp_large": 2.0}]' --downsample 16 --out output/map_scan.json
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from physics_attribution import load  # noqa: E402
from rotclimate.calibrate import evaluate_params  # noqa: E402


def one(args):
    start, over, ds = args
    p = load(start).replace(downsample=ds, solver_rtol=1e-5, solver_require_convergence=False, **over)
    try:
        m = evaluate_params(p, "zonefit")
    except Exception as e:          # e.g. the temperature-wind iteration not converging
        return dict(over=over, score=-1.0, accuracy=0.0, recall=None, mediterranean=None, error=repr(e)[:200])
    return dict(over=over, score=m["score"], accuracy=m["accuracy"], recall=m.get("recall"),
                mediterranean=m.get("mediterranean"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--grid", required=True)
    ap.add_argument("--downsample", type=int, default=16)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    t0, rows = time.time(), []
    with mp.get_context("fork").Pool(a.workers) as pool:
        for r in pool.imap(one, [(a.start, g, a.downsample) for g in json.loads(a.grid)]):
            rows.append(r)
            print(f"[{time.time() - t0:5.0f}s] {json.dumps(r['over'])} zonefit {r['score']:.4f} strict {r['accuracy']:.3f}", flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
