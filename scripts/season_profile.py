"""Region-mean monthly temperature error (model - WorldClim, deg C) and rain ratio for parameter variants.

    python3 -I scripts/season_profile.py PARAMS '{"name": {...overrides}}' region ...
"""
import json, sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from earth_benchmark import load_params
from rotclimate import earth
from rotclimate.koppen import monthly_stats
SETS = {"base": {}, **json.loads(sys.argv[2])}


def one(job):
    key, region = job
    p = load_params(sys.argv[1]).replace(**SETS[key])
    case = earth.region_case(region, 56.0)
    res = earth.run_case(p, case, steps=p.steps_per_year)
    pr = res.params
    st = monthly_stats(res.T, res.P, res.days, pr.year_days, summer_solstice=pr.winter_solstice_day + pr.year_days / 2)
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
    e = (st["Tm"] - case.obs_T)[:, m]
    return key, region, e.mean(1), float(np.abs(e).mean()), st["Pm"][:, m].mean(1) / np.maximum(case.obs_P[:, m].mean(1), 1e-6)


if __name__ == "__main__":
    jobs = [(k, r) for r in sys.argv[3:] for k in SETS]
    with Pool(4) as pool:
        for key, region, e, mae, pr in pool.map(one, jobs, chunksize=1):
            print(f"{region:15s} {key:14s} T mMAE {mae:4.2f} | T err " + " ".join(f"{x:+4.1f}" for x in e)
                  + " | P ratio " + " ".join(f"{x:3.1f}" for x in pr))
