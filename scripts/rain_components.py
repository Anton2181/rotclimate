"""Split each region's monthly rain into the model's rain-making factors.

    python -I scripts/rain_components.py --params calibration/local_accuracy_20261023/r40_params.json \
        --out output/summer_rain_20261030/components_r40.json

The rain rate is A x gate(RH) x instability / tau (+ convective closure,
x sub-cloud evaporation, + overflow), with the ascent A = (background +
storms + convergence + upslope + sub-grid hills) x damping (subtropical
sinking, lee drying, highs, divergence, Sverdrup). This records every factor
at the scored land cells through the model's own rain-step trace and keeps
monthly means beside WorldClim's rain, so a seasonal rain error can be put on
the factor that causes it. Diagnostic only; the climate is unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS, DEV31  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats, monthly_weights  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402

KEYS = ("T", "W", "Ws", "P", "E", "background", "storm", "conv", "orog", "damp", "instab", "A", "gain", "sinkd", "conv_rate")


def one(job):
    region, params_path, specs = job
    earth.REGIONS.update(specs)
    case = earth.region_case(region, 56.0)
    g = case.grid
    p = earth.earth_params(load_params(params_path), case)
    m = g.inmap & g.land & np.isfinite(case.obs_P).all(0) & np.isfinite(case.obs_T).all(0)
    model = ClimateModel(p, g)
    model.trace_cells = np.nonzero(m)
    res = model.run(steps=p.steps_per_year)
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    days = np.array([t["day"] for t in model.trace])
    wm = monthly_weights(days, p.year_days)
    out = {k: (wm @ np.stack([t[k] for t in model.trace])).mean(1).tolist() for k in KEYS}
    rh = np.stack([t["W"] / np.maximum(t["Ws"], 1e-6) for t in model.trace])
    gate = np.clip((rh - p.rh_threshold) / (1 - p.rh_threshold), 0, 2) ** 1.5
    out["RH"] = (wm @ rh).mean(1).tolist()
    out["gate"] = (wm @ gate).mean(1).tolist()
    large = np.stack([t["A"] * t["instab"] for t in model.trace]) * gate / p.precip_tau_days * np.stack([t["W"] for t in model.trace])
    out["large_scale_mm_day"] = (wm @ large).mean(1).tolist()       # before sub-cloud evaporation
    out["rain"] = st["Pm"][:, m].mean(1).tolist()
    out["rain_obs"] = case.obs_P[:, m].mean(1).tolist()
    out["T_obs"] = case.obs_T[:, m].mean(1).tolist()
    out["T_sim"] = st["Tm"][:, m].mean(1).tolist()
    return region, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--params", required=True)
    ap.add_argument("--regions", nargs="+", default=["dev31"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    specs = json.loads(DEV12_SPECS.read_text())
    regions = DEV31 if args.regions == ["dev31"] else args.regions
    out = {}
    with Pool(args.workers) as pool:
        for region, rec in pool.imap_unordered(one, [(r, args.params, specs) for r in regions]):
            out[region] = rec
            print(region, flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(params=args.params, regions=out), indent=1))


if __name__ == "__main__":
    main()
