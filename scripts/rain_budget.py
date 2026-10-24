"""Where a region's rain water comes from, month by month.

    python3 -I scripts/rain_budget.py --fit calibration/local_accuracy_20261023/r35_params.json \
        --regions manchuria north_india mexico east_australia us_midwest

Runs each region once with the moisture budget switched on and prints, over
the map's land, mm/month of rain (model and WorldClim) and of its supply:
mean-wind advection, diffusion, storm-eddy exchange and land evaporation.
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
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402


def one(job):
    fit, region, overrides = job
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    p = earth.earth_params(load_params(fit).replace(**overrides), earth.region_case(region, 56.0))
    case = earth.region_case(region, 56.0)
    res = ClimateModel(p.replace(steps_per_year=p.steps_per_year), grid=case.grid).run(diagnose_moisture=True)
    g = case.grid; sl = g.map_slice()
    m = (g.land & g.inmap & np.isfinite(case.obs_P).all(0))[sl]

    def month(field):          # [nt, ...] mm/day -> [12] mm/month over the map's land
        st = monthly_stats(field, np.maximum(field, 0), res.days, p.year_days,
                           summer_solstice=p.winter_solstice_day + p.year_days / 2)
        return (st["Tm"][:, m] * 30.4).mean(1)
    out = dict(region=region, obs=np.asarray(case.obs_P)[:, g.inmap & g.land & np.isfinite(case.obs_P).all(0)].mean(1).tolist())
    out["rain"] = month(res.P[:, sl[0], sl[1]]).tolist()
    out["evaporation"] = month(res.E[:, sl[0], sl[1]]).tolist()
    for k in ("advection", "diffusion", "storm_exchange"):
        out[k] = month(np.nan_to_num(res.moisture_budget[k])).tolist()
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", required=True)
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--set", default="{}")
    ap.add_argument("--out")
    a = ap.parse_args()
    with Pool(4) as pool:
        rows = pool.map(one, [(a.fit, r, json.loads(a.set)) for r in a.regions])
    for r in rows:
        print(f"{r['region']} (mm/month over the map's land)")
        for k in ("obs", "rain", "advection", "diffusion", "storm_exchange", "evaporation"):
            print(f"  {k:15s} " + " ".join(f"{v:5.0f}" for v in r[k]) + f" | year {sum(r[k]):6.0f}")
    if a.out:
        Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
