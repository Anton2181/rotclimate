"""One-setting-at-a-time scan from a base fit on 13 Earth regions (8 training / 5 held out).
    python3 -I scripts/earth_coord_scan.py BASE.json out.json '{"name": {...overrides}, ...}'"""
import json, sys
from multiprocessing import Pool
sys.path.insert(0, "/home/user/rotclimate"); sys.path.insert(0, "/home/user/rotclimate/scripts")
from earth_benchmark import load_params
from rotclimate import earth
TRAIN = ["california", "iberia", "southeast_us", "levant", "central_asia", "east_china", "east_australia", "mexico"]
HOLD = ["chile", "cape", "sw_australia", "south_brazil", "japan"]
SETS = {"base": {}, **json.loads(sys.argv[3])}
def one(job):
    key, name = job
    try:
        p = load_params(sys.argv[1]).replace(**SETS[key])
        case = earth.region_case(name, 56.0)
        return key, name, earth.compare(earth.run_case(p, case), case)["climate_distance"]
    except Exception as e:  # noqa: BLE001
        return key, name, 9.9
if __name__ == "__main__":
    jobs = [(k, n) for k in SETS for n in TRAIN + HOLD]
    with Pool(4) as pool:
        res = pool.map(one, jobs, chunksize=1)
    d = {}
    for k, n, v in res: d.setdefault(k, {})[n] = v
    json.dump(d, open(sys.argv[2], "w"), indent=1)
    b = d["base"]; bt = sum(b[n] for n in TRAIN) / 8; bh = sum(b[n] for n in HOLD) / 5
    print(f"{'setting':14s} tr8    ho5    " + " ".join(f"{n[:6]:>6s}" for n in TRAIN + HOLD))
    for k, v in d.items():
        t = sum(v[n] for n in TRAIN) / 8; h = sum(v[n] for n in HOLD) / 5
        flag = "  <== both better" if (k != "base" and t < bt and h < bh) else ""
        print(f"{k:14s} {t:.3f} {h:.3f}  " + " ".join(f"{v[n]:6.2f}" for n in TRAIN + HOLD) + flag)
