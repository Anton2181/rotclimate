"""Compare r39's column water, rain and pressure with NCEP/NCAR by region and month.

    python -I scripts/compare_column_water.py --params calibration/local_accuracy_20261023/r39_params.json \
        --out output/physics_gaps_20261030/column_water_r39.json

Rain is column water times an ascent rate, so a region's rain error is either
too much (or too little) water in the column or too much (too little) of it
raining out. This runs each region once, records the model's monthly
precipitable water (W) and diagnosed sea-level pressure anomaly over the
scored land, and sets them beside the reanalysis precipitable water and
sea-level pressure (minus its zonal mean at each latitude, the part the
model's temperature-driven pressure describes) and WorldClim rain. Diagnostic
only.
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

import attribute_observed_forcing as att  # noqa: E402
from benchmark_local import DEV12_SPECS, DEV31  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats, monthly_weights  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402


def monthly(field, days, year_days):
    """Monthly means of a [nt, ...] field, weighted as koppen.monthly_stats weights rain."""
    field = np.asarray(field)
    return (monthly_weights(days, year_days) @ field.reshape(len(days), -1)).reshape((12,) + field.shape[1:])


def one(job):
    region, params_path, specs = job
    earth.REGIONS.update(specs)
    case = earth.region_case(region, 56.0)
    g = case.grid
    p = earth.earth_params(load_params(params_path), case)
    model = ClimateModel(p, g)
    pres, day = {}, [None]
    season, wind = model.season_index, model.pressure_wind

    def season_index(d, *rest):                           # called once at the start of every step
        day[0] = d
        return season(d, *rest)

    def pressure_wind(T_anom):                            # the step's last pressure wins
        out = wind(T_anom)
        pres[day[0]] = model.last_pres.copy()
        return out
    model.season_index, model.pressure_wind = season_index, pressure_wind
    res = model.run(steps=p.steps_per_year)
    m = g.inmap & g.land & np.isfinite(case.obs_P).all(0)
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    W = monthly(res.W, res.days, p.year_days)[:, m].mean(1)
    ref = att.ncep_at(case, ("pw", "slp"))
    full = att.reference()["slp"]
    zonal = full.mean(axis=2)                              # [12, 73] zonal mean by latitude
    south = earth.REGIONS[region]["lat0"] < 0
    lat = -g.lat if south else g.lat
    zm = np.stack([np.interp(-lat, -np.linspace(90, -90, 73), zonal[k]) for k in range(12)])
    if south:
        zm = np.roll(zm, 6, axis=0)
    slp_anom = (ref["slp"] - zm)[:, m].mean(1)
    days = np.array(sorted(pres))[-len(res.days):]          # the recorded year (after any spin-up)
    pres_m = monthly(np.stack([pres[d] for d in days]), days, p.year_days)[:, m].mean(1) / 100.0
    return region, dict(W=W.tolist(), pw=ref["pw"][:, m].mean(1).tolist(),
                        rain=st["Pm"][:, m].mean(1).tolist(), rain_obs=case.obs_P[:, m].mean(1).tolist(),
                        pres_hpa=pres_m.tolist(), slp_anom_hpa=slp_anom.tolist())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--params", required=True)
    ap.add_argument("--regions", nargs="+", default=["dev31"])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    specs = json.loads(DEV12_SPECS.read_text())
    regions = DEV31 if args.regions == ["dev31"] else args.regions
    att.reference()
    out = {}
    with Pool(args.workers) as pool:
        for region, rec in pool.imap_unordered(one, [(r, args.params, specs) for r in regions]):
            out[region] = rec
            print(region, flush=True)
    Path(args.out).write_text(json.dumps(dict(params=args.params, regions=out), indent=1))


if __name__ == "__main__":
    main()
