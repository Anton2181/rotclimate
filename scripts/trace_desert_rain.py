"""Which rain term wets the deserts? Trace the rain step at interior cells of a region (P5 diagnosis).

    python -I scripts/trace_desert_rain.py --region najd_arabia --specs calibration/sealed_20261031b/regions.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fit", default="calibration/local_accuracy_20261023/r41_params.json")
    ap.add_argument("--region", required=True); ap.add_argument("--specs")
    ap.add_argument("--set", default="{}"); ap.add_argument("--cell-km", type=float, default=56.0)
    a = ap.parse_args()
    if a.specs:
        earth.REGIONS.update(json.loads(Path(a.specs).read_text()))
    case = earth.region_case(a.region, a.cell_km)
    p = earth.earth_params(load_params(ROOT / a.fit).replace(**json.loads(a.set)), case)
    g = case.grid
    m = g.inmap & g.land
    ii, jj = np.nonzero(m)
    cy, cx = np.median(ii), np.median(jj)
    order = np.argsort((ii - cy) ** 2 + (jj - cx) ** 2)[:9]          # nine cells nearest the centre
    model = ClimateModel(p, grid=g)
    model.trace_cells = (ii[order], jj[order])
    model.run()
    tr = model.trace
    days = np.array([t["day"] for t in tr])
    month = np.minimum((days / p.year_days * 12).astype(int), 11)
    keys = ["P", "W", "Ws", "E", "background", "storm", "conv", "orog", "damp", "A", "T", "chi"]
    out = {}
    for k in keys:
        if k not in tr[0]:
            continue
        v = np.array([np.mean(t[k]) for t in tr])
        out[k] = [float(v[month == mm].mean()) if (month == mm).any() else None for mm in range(12)]
    rh = [w / ws if w is not None and ws else None for w, ws in zip(out["W"], out["Ws"])]
    print(f"{a.region}: nine centre cells, monthly means")
    for k in ["P", "E", "background", "storm", "conv", "orog", "damp", "A", "T"]:
        if k in out:
            print(f"  {k:10s}", " ".join(f"{x:6.2f}" for x in out[k]))
    print(f"  {'RH':10s}", " ".join(f"{x:6.2f}" for x in rh))
    Path(ROOT / "output/desert_heat_20261101").mkdir(parents=True, exist_ok=True)
    (ROOT / "output/desert_heat_20261101" / f"trace_{a.region}.json").write_text(json.dumps(dict(region=a.region, monthly=out, rh=rh), indent=1))


if __name__ == "__main__":
    main()
