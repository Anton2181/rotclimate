"""One-setting-at-a-time scan from a base fit on 13 Earth regions (8 training / 5 held out).
    python3 -I scripts/earth_coord_scan.py BASE.json out.json '{"name": {...overrides}, ...}'"""
import json, sys
from multiprocessing import Pool
sys.path.insert(0, "/home/user/rotclimate"); sys.path.insert(0, "/home/user/rotclimate/scripts")
from earth_benchmark import load_params
from rotclimate import earth
TRAIN = ["california", "iberia", "southeast_us", "levant", "central_asia", "east_china", "east_australia", "mexico"]
HOLD = ["chile", "cape", "sw_australia", "south_brazil", "japan"]
# mid-latitude regions added after e25, scored as a third group with a 4th argument "fresh"
FRESH = ["pacific_nw", "western_europe", "eastern_europe", "us_midwest", "manchuria", "new_zealand"]
GROUPS = TRAIN + HOLD + (FRESH if len(sys.argv) > 4 and sys.argv[4] == "fresh" else [])
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
    jobs = [(k, n) for k in SETS for n in GROUPS]
    with Pool(4) as pool:
        res = pool.map(one, jobs, chunksize=1)
    d = {}
    for k, n, v in res: d.setdefault(k, {})[n] = v
    json.dump(d, open(sys.argv[2], "w"), indent=1)
    b = d["base"]; bt = sum(b[n] for n in TRAIN) / 8; bh = sum(b[n] for n in HOLD) / 5
    fr = GROUPS[13:]
    print(f"{'setting':14s} tr8    ho5    " + ("fr6    " if fr else "") + " ".join(f"{n[:6]:>6s}" for n in GROUPS))
    for k, v in d.items():
        t = sum(v[n] for n in TRAIN) / 8; h = sum(v[n] for n in HOLD) / 5
        f6 = f"{sum(v[n] for n in fr) / len(fr):.3f}  " if fr else ""
        flag = "  <== both better" if (k != "base" and t < bt and h < bh) else ""
        print(f"{k:14s} {t:.3f} {h:.3f}  " + f6 + " ".join(f"{v[n]:6.2f}" for n in GROUPS) + flag)
