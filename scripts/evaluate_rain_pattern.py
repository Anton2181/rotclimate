"""Score the Earth rain-pattern correction (with the temperature correction) on a run.

    python -I scripts/evaluate_rain_pattern.py --run DIR --fields DIR --rain calibration/earth_rain_pattern_20261030 \
        --temperature calibration/earth_correction_20261030 --holdout --out output/.../eval_rain_dev31_holdout.json

With --holdout, regions of a training cluster use the fold models trained
without their whole cluster, for both corrections; other (sealed) regions use
the final models. The rain pattern's local means use each region's scored land.
Reports the rain metrics before and after, and Koppen class agreement with the
observed climate for the raw model, temperature-corrected, and both corrected.
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

from benchmark_local import DEV12_SPECS, GROUPS  # noqa: E402
from evaluate_earth_correction import EARTH_PHASE, extra_metrics  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.correction import RainPatternCorrection, TemperatureCorrection, static_features, wind_terrain_features  # noqa: E402
from train_earth_correction import cluster_of  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--fields", required=True)
    ap.add_argument("--rain", required=True)
    ap.add_argument("--temperature", required=True)
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--region-specs")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    if args.region_specs:
        earth.REGIONS.update({k: v for k, v in json.loads(Path(args.region_specs).read_text()).items() if isinstance(v, dict) and "lat0" in v})
    summary = json.loads((Path(args.run) / "summary.json").read_text())
    out = Path(args.out)
    cell_dir = out.with_suffix("")
    cell_dir.mkdir(parents=True, exist_ok=True)
    regions = {}
    for r, rec in sorted(summary["regions"].items()):
        if rec["status"] != "passed":
            raise ValueError(f"{r}: benchmark region did not pass")
        cl = cluster_of(r) if args.holdout else None
        model = f"folds/{cl}.npz" if cl else "correction.npz"
        rain = RainPatternCorrection.load(Path(args.rain) / model)
        temp = TemperatureCorrection.load(Path(args.temperature) / model)
        z, f = np.load(Path(args.run) / "cells" / f"{r}.npz"), np.load(Path(args.fields) / f"{r}.npz")
        i, j = z["i"], z["j"]
        if not (np.array_equal(f["Tm"][:, i, j], z["Ts"]) and np.array_equal(f["Pm"][:, i, j], z["Ps"])):
            raise ValueError(f"{r}: fields do not belong to this run")
        g = earth.region_case(r, summary["cell_km"]).grid
        mask = np.zeros(g.land.shape, bool)
        mask[i, j] = True
        if not (np.array_equal(np.nonzero(mask)[0], i) and np.array_equal(np.nonzero(mask)[1], j)):
            raise ValueError(f"{r}: saved cells are not in grid order")
        static = {k: v[mask] for k, v in static_features(g).items()}
        wind = wind_terrain_features(g, f["um"], f["vm"], mask)
        Ts, To, Ps, Po = (z[k].astype(float) for k in ("Ts", "To", "Ps", "Po"))
        Tc = Ts + temp.offsets(static, Ts, Ps, EARTH_PHASE)
        Pc = rain.apply_cells(static, wind, Ts, Ps, EARTH_PHASE, mask, g.cell_km)
        ones = np.ones(Ts.shape[1], bool)
        regions[r] = dict(models=f"fold {cl}" if cl else "final", cells=int(Ts.shape[1]),
                          rain_raw=local_metrics(Ps, Po, ones), rain_corrected=local_metrics(Pc, Po, ones),
                          koppen=dict(raw=extra_metrics(Ts, To, Ps, Po), temperature=extra_metrics(Tc, To, Ps, Po),
                                      both=extra_metrics(Tc, To, Pc, Po)))
        np.savez_compressed(cell_dir / f"{r}.npz", Pc=Pc.astype(np.float32), Ps=Ps.astype(np.float32), Po=Po.astype(np.float32),
                            Tc=Tc.astype(np.float32), i=i, j=j)
    groups = dict(GROUPS, all=sorted(regions))
    table = {}
    for gname, members in groups.items():
        rs = [r for r in members if r in regions]
        if not rs:
            continue
        mean = lambda fn: float(np.mean([fn(regions[r]) for r in rs]))
        table[gname] = dict(
            rain={k: dict(raw=mean(lambda x: x["rain_raw"][k]), corrected=mean(lambda x: x["rain_corrected"][k]))
                  for k in ("loss", "annual_log_rmse", "monthly_mae_mm", "annual_within_25pct")},
            koppen={k: {s: mean(lambda x: x["koppen"][s][k]) for s in ("raw", "temperature", "both")}
                    for k in ("koppen_exact", "koppen_main")})
    (out).write_text(json.dumps(dict(run=str(args.run), cell_km=summary["cell_km"], rain=str(args.rain),
                                     temperature=str(args.temperature), holdout=args.holdout, regions=regions, groups=table), indent=1))
    for gname, row in table.items():
        print(f"[{gname}] " + "  ".join(f"{k} {v['raw']:.3f}->{v['corrected']:.3f}" for k, v in row["rain"].items())
              + " | " + "  ".join(f"{k} " + "/".join(f"{v[s]:.3f}" for s in ("raw", "temperature", "both")) for k, v in row["koppen"].items()))


if __name__ == "__main__":
    main()
