"""Scan storm-eddy settings: map zone recall vs Earth climate distance.

    python -I scripts/eddy_scan.py --base calibration/earth/joint_e1_retro.json \
        --grid '[[896,0.22],[700,0.5],[550,0.7]]' --out output/earth_on_map/eddy_scan.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from rotclimate import earth  # noqa: E402
from rotclimate.calibrate import evaluate_params  # noqa: E402
from earth_calibrate import NUMERICS  # noqa: E402
from physics_attribution import load  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--grid", required=True, help="json list of [eddy_scale_km, eddy_seasonality(, eddy_rate)]")
    ap.add_argument("--regions", nargs="+", default=list(earth.REGIONS))
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--downsample", type=int, default=16)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    base = load(a.base)
    cases = {r: earth.region_case(r, a.cell_km) for r in a.regions}
    rows = []
    for g in json.loads(a.grid):
        over = dict(eddy_scale_km=float(g[0]), eddy_seasonality=float(g[1]))
        if len(g) > 2:
            over["eddy_rate"] = float(g[2])
        p = base.replace(**over)
        m = evaluate_params(p.replace(downsample=a.downsample, solver_rtol=1e-5, solver_require_convergence=False),
                            "zonefit")
        q = p.replace(**NUMERICS)
        d = {r: earth.climate_distance(earth.run_case(q, c, steps=q.steps_per_year), c) for r, c in cases.items()}
        row = dict(over, zonefit=m["score"], strict=m["accuracy"], recall=m["recall"], earth=d,
                   earth_mean=float(np.mean(list(d.values()))))
        rows.append(row)
        print(f"scale {over['eddy_scale_km']:5.0f} seas {over['eddy_seasonality']:.2f} | zonefit {m['score']:.3f} "
              f"strict {m['accuracy']:.1%} cold_dry {m['recall']['cold_dry']:.1%} med {m['recall']['med']:.1%} "
              f"| Earth d {row['earth_mean']:.3f} (C Asia {d.get('central_asia', float('nan')):.2f}, "
              f"SE US {d.get('southeast_us', float('nan')):.2f})", flush=True)
        Path(a.out).write_text(json.dumps(dict(base=a.base, rows=rows), indent=1))


if __name__ == "__main__":
    main()
