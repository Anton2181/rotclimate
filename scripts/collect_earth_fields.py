"""Rerun a benchmark_local run's regions and keep full-grid monthly fields.

    python -I scripts/collect_earth_fields.py --run output/earth_correction_20261030/r39_dev31 \
        --params calibration/local_accuracy_20261023/r39_params.json --out output/earth_correction_20261030/fields_dev31

benchmark_local keeps only the scored cells' temperature and rain. Corrections
that look at the wind over terrain need the simulated monthly surface winds
on the whole grid, so this reruns each region with the same parameters and
saves monthly T (C), rain (mm/month), u and v (m/s). The run is
deterministic: every region's scored cells must reproduce the benchmark's
saved cells exactly, or nothing is written for it.
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

from benchmark_local import DEV12_SPECS  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats, monthly_weights  # noqa: E402
from rotclimate.numerics import matrix_product  # noqa: E402


def one(job):
    region, params_path, run, cell_km, out, specs = job
    earth.REGIONS.update(specs)
    target = Path(out) / f"{region}.npz"
    if target.exists():
        return region, "kept"
    p = load_params(params_path)
    case = earth.region_case(region, cell_km)
    res = earth.run_case(p, case, steps=p.steps_per_year)
    if res.numerics.get("all_checks_passed") is not True:
        raise RuntimeError(f"{region}: numerical checks failed")
    pr = res.params
    st = monthly_stats(res.T, res.P, res.days, pr.year_days, summer_solstice=pr.winter_solstice_day + pr.year_days / 2)
    Wm = monthly_weights(res.days, pr.year_days)
    shp = res.u.shape[1:]
    um = matrix_product(Wm, res.u.reshape(len(res.days), -1)).reshape((12,) + shp)
    vm = matrix_product(Wm, res.v.reshape(len(res.days), -1)).reshape((12,) + shp)
    z = np.load(Path(run) / "cells" / f"{region}.npz")
    i, j = z["i"], z["j"]
    if not (np.array_equal(st["Tm"][:, i, j].astype(np.float32), z["Ts"])
            and np.array_equal(np.maximum(st["Pm"][:, i, j], 0.0).astype(np.float32), z["Ps"])):
        raise RuntimeError(f"{region}: rerun does not reproduce the benchmark cells")
    tmp = target.with_name(target.name + ".tmp")
    with tmp.open("wb") as stream:
        np.savez_compressed(stream, Tm=st["Tm"].astype(np.float32), Pm=np.maximum(st["Pm"], 0.0).astype(np.float32),
                            um=um.astype(np.float32), vm=vm.astype(np.float32))
    tmp.replace(target)
    return region, "reproduced"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--region-specs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    specs = json.loads(DEV12_SPECS.read_text())
    if args.region_specs:
        specs.update({k: v for k, v in json.loads(Path(args.region_specs).read_text()).items() if isinstance(v, dict) and "lat0" in v})
    summary = json.loads((Path(args.run) / "summary.json").read_text())
    Path(args.out).mkdir(parents=True, exist_ok=True)
    jobs = [(r, args.params, args.run, summary["cell_km"], args.out, specs) for r in sorted(summary["regions"])]
    with Pool(args.workers) as pool:
        for region, status in pool.imap_unordered(one, jobs):
            print(f"{region}: {status}", flush=True)


if __name__ == "__main__":
    main()
