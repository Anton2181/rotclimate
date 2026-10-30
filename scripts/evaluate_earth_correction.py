"""Score the Earth temperature correction on a benchmark_local run.

    python -I scripts/evaluate_earth_correction.py --run DIR --correction calibration/earth_correction_20261030 \
        --holdout --out output/earth_correction_20261030/eval_dev31.json

With --holdout, a region in one of the training clusters is corrected by the
fold model trained without its whole cluster (the honest score for a region
the final model has seen); any other region (a sealed one) by the final
model. Rain is left as simulated. Besides the monthly temperature metrics this
reports the warmest- and coldest-month errors and Koppen class agreement with
the observed climate (the classes use simulated rain in both columns' model
side), since those decide the map's climate zones. Corrected cells are saved
next to the JSON for maps.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS, GROUPS, temperature_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.correction import TemperatureCorrection, season_phase, static_features  # noqa: E402
from rotclimate.koppen import CODES, classify, summer_months  # noqa: E402
from train_earth_correction import cluster_of  # noqa: E402

EARTH_PHASE = season_phase(365.0, 354.5)
SUMMER = summer_months(365, 12, 354.5 + 365 / 2)


def extra_metrics(Ts, To, Ps, Po):
    k_sim, k_obs = np.array(CODES)[classify(Ts, Ps, SUMMER)], np.array(CODES)[classify(To, Po, SUMMER)]
    return dict(warm_month_mae_C=float(np.abs(Ts.max(0) - To.max(0)).mean()),
                cold_month_mae_C=float(np.abs(Ts.min(0) - To.min(0)).mean()),
                koppen_exact=float((k_sim == k_obs).mean()),
                koppen_main=float(np.mean([a[0] == b[0] for a, b in zip(k_sim, k_obs)])))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--correction", required=True, help="training output folder (correction.npz, folds/)")
    ap.add_argument("--holdout", action="store_true", help="use each training cluster's held-out fold model")
    ap.add_argument("--region-specs", help="json of extra region definitions (sealed regions)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    if args.region_specs:
        earth.REGIONS.update({k: v for k, v in json.loads(Path(args.region_specs).read_text()).items() if isinstance(v, dict) and "lat0" in v})
    summary = json.loads((Path(args.run) / "summary.json").read_text())
    final = TemperatureCorrection.load(Path(args.correction) / "correction.npz")
    out = Path(args.out)
    cell_dir = out.with_suffix("")
    cell_dir.mkdir(parents=True, exist_ok=True)
    regions, used = {}, {}
    for r, rec in sorted(summary["regions"].items()):
        if rec["status"] != "passed":
            raise ValueError(f"{r}: benchmark region did not pass")
        cl = cluster_of(r) if args.holdout else None
        model = TemperatureCorrection.load(Path(args.correction) / "folds" / f"{cl}.npz") if cl else final
        used[r] = f"fold {cl}" if cl else "final"
        z = np.load(Path(args.run) / "cells" / f"{r}.npz")
        case = earth.region_case(r, summary["cell_km"])
        static = static_features(case.grid)
        i, j = z["i"], z["j"]
        if not np.allclose(case.grid.lat[i, j], z["lat"]):
            raise ValueError(f"{r}: saved cells do not match the rebuilt grid")
        Ts, To, Ps, Po = (z[k].astype(float) for k in ("Ts", "To", "Ps", "Po"))
        Tc = Ts + model.offsets({k: v[i, j] for k, v in static.items()}, Ts, Ps, EARTH_PHASE)
        regions[r] = dict(model=used[r], cells=int(Ts.shape[1]),
                          raw=dict(temperature_metrics(Ts, To), **extra_metrics(Ts, To, Ps, Po)),
                          corrected=dict(temperature_metrics(Tc, To), **extra_metrics(Tc, To, Ps, Po)))
        np.savez_compressed(cell_dir / f"{r}.npz", Tc=Tc.astype(np.float32), Ts=Ts.astype(np.float32),
                            To=To.astype(np.float32), i=i, j=j)
    keys = ("monthly_mae_C", "annual_mae_C", "range_mae_C", "warm_month_mae_C", "cold_month_mae_C", "koppen_exact", "koppen_main")
    groups = dict(GROUPS, all=sorted(regions))
    table = {}
    for g, members in groups.items():
        rs = [r for r in members if r in regions]
        if rs:
            table[g] = {k: dict(raw=float(np.mean([regions[r]["raw"][k] for r in rs])),
                                corrected=float(np.mean([regions[r]["corrected"][k] for r in rs]))) for k in keys}
    result = dict(run=str(args.run), run_identity=summary["identity"], cell_km=summary["cell_km"],
                  correction=str(args.correction), correction_meta_sha256=final.meta["physics_params_sha256"],
                  holdout=args.holdout, regions=regions, groups=table)
    out.write_text(json.dumps(result, indent=1))
    for g, row in table.items():
        print(f"[{g}] " + "  ".join(f"{k} {v['raw']:.3f}->{v['corrected']:.3f}" for k, v in row.items()))


if __name__ == "__main__":
    main()
