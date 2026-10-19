"""Climate distance of several Earth fits on a set of regions, side by side
(a fresh-region test of fits made elsewhere):

    python3 -I scripts/earth_fresh_check.py out.json --regions pacific_nw ... --fits NAME=PARAMS.json ...
"""
import argparse, json, sys
from multiprocessing import Pool
sys.path.insert(0, "/home/user/rotclimate"); sys.path.insert(0, "/home/user/rotclimate/scripts")
from earth_benchmark import load_params
from rotclimate import earth


def one(job):
    fit, path, name = job
    case = earth.region_case(name, 56.0)
    r = earth.compare(earth.run_case(load_params(path), case), case)
    return fit, name, dict(d=r["climate_distance"], T=r["temperature"]["bias_C"], Trmse=r["temperature"]["rmse_C"],
                           rain=r["rain"]["sim_mean_annual_mm"], rain_obs=r["rain"]["obs_mean_annual_mm"],
                           koppen=r["koppen_full_model"]["exact"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("out")
    ap.add_argument("--regions", nargs="+", required=True)
    ap.add_argument("--fits", nargs="+", required=True)
    a = ap.parse_args()
    fits = dict(f.split("=", 1) for f in a.fits)
    with Pool(4) as pool:
        res = pool.map(one, [(k, v, n) for k, v in fits.items() for n in a.regions], chunksize=1)
    d = {}
    for k, n, v in res:
        d.setdefault(k, {})[n] = v
    json.dump(d, open(a.out, "w"), indent=1)
    print(f"{'fit':8s} mean   " + " ".join(f"{n[:9]:>9s}" for n in a.regions))
    for k in fits:
        print(f"{k:8s} {sum(d[k][n]['d'] for n in a.regions) / len(a.regions):.3f}  "
              + " ".join(f"{d[k][n]['d']:9.2f}" for n in a.regions))
    for n in a.regions:
        print(f"  {n:15s} " + " | ".join(f"{k} T {d[k][n]['T']:+.1f} rain {d[k][n]['rain']:.0f}/{d[k][n]['rain_obs']:.0f}"
                                       for k in fits))
