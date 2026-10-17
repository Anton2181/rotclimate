"""Score a list of setting overrides on top of one Earth fit, region by region.

    python -I scripts/earth_scan.py --start calibration/earth/earth_e2_r5.json \
        --grid '[{}, {"slp_large": 1.0, "slp_local": 0.4}]' --out output/earth_scan.json
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import earth_calibrate as E  # noqa: E402
from earth_calibrate import Params, asdict  # noqa: E402

REGIONS = ["california", "iberia", "southeast_us", "levant", "central_asia", "east_china"]


def one(args):
    over, base, regions, cell_km = args
    E.SPACE = []                                # score the parameters as given
    out = E.evaluate(([], asdict(Params(**base).replace(**over)), regions, cell_km))
    out["over"] = over
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--grid", required=True, help="json list of override dicts")
    ap.add_argument("--set", default="{}", help="json overrides applied to every point")
    ap.add_argument("--regions", nargs="+", default=REGIONS)
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    d = json.loads(Path(a.start).read_text())
    d = d.get("params", d)
    base = Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__}).replace(**E.NUMERICS).replace(**json.loads(a.set))
    grid = json.loads(a.grid)
    t0, rows = time.time(), []
    with mp.get_context("fork").Pool(a.workers) as pool:
        for r in pool.imap(one, [(g, asdict(base), a.regions, a.cell_km) for g in grid]):
            rows.append(dict(over=r["over"], cost=r["cost"], error=r.get("error"),
                             regions={k: v["climate_distance"] for k, v in r.get("regions", {}).items()}))
            print(f"[{time.time() - t0:5.0f}s] {json.dumps(r['over'])} cost {r['cost']:.4f} "
                  + " ".join(f"{k} {v['climate_distance']:.3f}" for k, v in r.get("regions", {}).items()), flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
