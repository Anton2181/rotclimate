"""Harvest reliability on Earth: does the bad-year limit fix the dryland bias?

    python3 -I scripts/population_reliability.py --earth output/land_people/earth/earth.npz \
        --hyde data/cache/hyde33/popc_ce_0.tif data/cache/hyde33/popc_ce_200.tif \
        --shp data/cache/han_ad2/shp/ResearchArea --out output/population_reliability/scan.json

The plan (output/population_reliability/plan.json) was frozen before any
result. Each setting (start, full, power) of harvest.models.harvest_reliability
multiplies the crop capacity of the Earth run; the settlement base and the full
model (x old cores, cradles + Rome, travel cost forest x2, relief 1/km, L 800
km) are scored against HYDE 3.3 at 0 and 200 CE and the Han AD 2 census, as
in scripts/population_cores.py. The density-by-growing-season table of the
Old World's dry belt (15-50 N, 20 W-125 E, away from rivers) shows what each
setting does to the dryland bias.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from han_census_check import commanderies, score, used  # noqa: E402
from harvest_earth_hyde import earth_stages  # noqa: E402
from hyde_compare import blocks, hyde_at, metrics  # noqa: E402
from population_cores import CORE_SETS, core_term, region_spread, travel_distance  # noqa: E402

LGP_BINS = [(0, 30), (30, 60), (60, 90), (90, 120), (120, 150), (150, 180), (180, 240), (240, 400)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--earth", required=True)
    ap.add_argument("--hyde", nargs="+", required=True)
    ap.add_argument("--shp", required=True)
    ap.add_argument("--plan", default=str(ROOT / "output/population_reliability/plan.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    plan = json.loads(Path(a.plan).read_text())["grid"]
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2, _ = earth_stages(z)
    A = blocks(km2 * land)
    hyde, hyde_fine = {}, None
    for path in a.hyde:
        raw = hyde_at(path, lat, lon)
        H = blocks(raw * land)
        hyde[Path(path).name] = (H, (blocks(land.astype(float)) >= 72) & (H > 0))
        hyde_fine = raw / km2
    han = used(commanderies(a.shp, lat, lon, km2))
    core = core_term(travel_distance(z, CORE_SETS["cradles + Rome"], 2.0, 1.0, 1.0), 800)
    LA = lat[:, None] * np.ones((1, len(lon))); LO = np.ones((len(lat), 1)) * lon[None, :]
    belt = land.astype(bool) & (LA > 15) & (LA < 50) & (LO > -20) & (LO < 125) & (np.nan_to_num(z["irr"]) <= 0.3)
    lgp = np.nan_to_num(z["lgp_days"])

    def rel(x):
        return x / (np.sum(x[belt] * km2[belt]) / np.sum(km2[belt]))

    def by_lgp(x):
        r = rel(x)
        return [float(np.sum(r[m] * km2[m]) / np.sum(km2[m])) for m in
                (belt & (lgp >= lo) & (lgp < hi) for lo, hi in LGP_BINS)]

    def evaluate(density):
        out = {k: metrics(blocks(density * km2 * land), H, A, ok) for k, (H, ok) in hyde.items()}
        out["Han AD 2"] = score(han, [float((density[i, j] * km2[i, j] * land[i, j]).sum()) for i, j in (x["idx"] for x in han)])
        out["regions_spread"], _ = region_spread(density, km2, land, lat, lon)
        return out

    settings = [None] + list(itertools.product(plan["start_days"], plan["full_days"], plan["power"]))
    results = {"HYDE by growing season (belt, away from rivers)": by_lgp(hyde_fine)}
    h200 = [n for n in hyde if "200" in n][0]
    print(f"{'setting':22s} {'base HYDE200':>12s} {'base Han':>9s} | {'cored HYDE0':>11s} {'HYDE200':>8s} {'Han':>6s} {'mean':>6s} | "
          "belt density by growing season (" + " ".join(f"{lo}-{hi}" for lo, hi in LGP_BINS) + ")")
    print(f"{'HYDE 200 CE':22s} {'':>12s} {'':>9s} | {'':>11s} {'':>8s} {'':>6s} {'':>6s} | "
          + " ".join(f"{v:5.2f}" for v in results["HYDE by growing season (belt, away from rivers)"]))
    for s in settings:
        _, st = earth_stages(z, reliability=s)
        base = np.nan_to_num(st["+ malaria (settlement base)"])
        b, c = evaluate(base), evaluate(base * core)
        mean = 0.5 * (c[h200]["spearman"] + c["Han AD 2"]["spearman"])
        name = "none" if s is None else f"start {s[0]:g} full {s[1]:g} pow {s[2]:g}"
        results[name] = dict(setting=s, base=b, cored=c, fit_mean=mean, by_lgp=by_lgp(base))
        hy0 = [n for n in hyde if "_0." in n][0]
        print(f"{name:22s} {b[h200]['spearman']:12.3f} {b['Han AD 2']['spearman']:9.3f} | {c[hy0]['spearman']:11.3f} "
              f"{c[h200]['spearman']:8.3f} {c['Han AD 2']['spearman']:6.3f} {mean:6.3f} | "
              + " ".join(f"{v:5.2f}" for v in results[name]["by_lgp"]), flush=True)
    ranked = sorted(((v["fit_mean"], k) for k, v in results.items() if isinstance(v, dict)), reverse=True)
    best = ranked[0]
    # ties within 0.005 go to the smaller change: the earliest start, then the shortest full, then power 1
    close = [k for m, k in ranked if best[0] - m <= 0.005 and k != "none"]
    if close and best[1] != "none":
        def size(k):
            s = results[k]["setting"]
            return (s[0], s[1], s[2])
        chosen = min(close, key=size)
    else:
        chosen = best[1]
    print(f"chosen: {chosen} (mean {results[chosen]['fit_mean']:.3f}; none {results['none']['fit_mean']:.3f})")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(results=results, chosen=chosen, lgp_bins=LGP_BINS), indent=1, default=float))


if __name__ == "__main__":
    main()
