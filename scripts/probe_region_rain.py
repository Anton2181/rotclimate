"""Quick one-region probes of rain settings (development only, not the gate).

    python3 -I scripts/probe_region_rain.py --fit calibration/local_accuracy_20261023/r35_params.json \
        --regions north_india east_china --probes '{"base": {}, "mh1": {"monsoon_heating": 1.0}}'

Prints, per region and probe, the map's monthly rain against WorldClim, the
rainfall loss, and the monthly temperature error.
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402


def one(job):
    fit, region, name, overrides, cell_km = job
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    p = load_params(fit).replace(**overrides)
    case = earth.region_case(region, cell_km)
    res = earth.run_case(p, case, steps=p.steps_per_year)
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    m = case.grid.inmap & case.grid.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    Pm = np.maximum(st["Pm"], 0)
    rain = local_metrics(Pm, np.nan_to_num(case.obs_P), m)
    T_mae = float(np.abs(st["Tm"][:, m] - np.asarray(case.obs_T)[:, m]).mean())
    return dict(region=region, name=name, loss=rain["loss"], T_mae=T_mae, ok=bool(res.numerics.get("all_checks_passed")),
                sim=Pm[:, m].mean(1).tolist(), obs=np.asarray(case.obs_P)[:, m].mean(1).tolist(),
                log_rmse=rain["annual_log_rmse"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", required=True)
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--probes", required=True, help="json {name: overrides}")
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    probes = json.loads(a.probes)
    jobs = [(a.fit, r, n, o, a.cell_km) for r in a.regions for n, o in probes.items()]
    with Pool(a.workers) as pool:
        rows = pool.map(one, jobs)
    for r in a.regions:
        obs = next(x["obs"] for x in rows if x["region"] == r)
        print(f"{r}: observed mm/month " + " ".join(f"{v:4.0f}" for v in obs))
        for x in rows:
            if x["region"] == r:
                print(f"  {x['name']:14s} loss {x['loss']:.3f} logRMSE {x['log_rmse']:.3f} T {x['T_mae']:.2f}{'' if x['ok'] else ' UNVERIFIED'} | "
                      + " ".join(f"{v:4.0f}" for v in x["sim"]))


if __name__ == "__main__":
    main()
