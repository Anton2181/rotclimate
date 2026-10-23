"""Which history-free rule finds the old cores? Tested on Earth.

    python3 -I scripts/population_core_rules.py --earth output/population_reliability/earth_m1/earth.npz \
        --hyde data/cache/hyde33/popc_ce_200.tif --shp data/cache/han_ad2/shp/ResearchArea \
        --xlsx data/cache/hanson2016/cities.xlsx --out output/population_cores/rules.json

A map has no recorded history, so its old cores must come from a rule that
also works on Earth. Two rules take the strongest peaks of people, smoothed
over ~200 km and at least min_sep_km apart:
  dry river   people on irrigable river land in dry climates (population_cores.dry_river_cores:
              the first states rose there; Carneiro's circumscription);
  settlement  people of the settlement base anywhere (the richest farmland).
Each set of peaks multiplies the settlement base by the core term (travel cost:
forest x2, relief 1/km, sea as land; L 800 km), and is scored against HYDE 3.3
at 200 CE, the Han AD 2 census and the Roman towns of AD 150 (Hanson 2016),
next to the declared historical cores (cradles + Rome).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from scipy.ndimage import uniform_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from han_census_check import commanderies, score, used  # noqa: E402
from harvest_earth_hyde import earth_stages  # noqa: E402
from hyde_compare import blocks, hyde_at, metrics, spearman  # noqa: E402
from population_cores import CORE_SETS, core_distance, core_term, dry_river_cores, travel_distance  # noqa: E402
from roman_cities_check import BLOCK, towns  # noqa: E402


def settlement_peaks(z, base, km2, n, box=24, min_sep_km=1000.0):
    """The n strongest ~200 km concentrations of settlement-base people."""
    lat, lon, land = z["lat"], z["lon"], z["land"]
    s = uniform_filter(base * land * km2, box)
    peaks = {}
    for k in np.argsort(-s.ravel()):
        i, j = divmod(int(k), s.shape[1])
        if s[i, j] <= 0 or len(peaks) == n:
            break
        if all(core_distance(np.array([lat[i]]), np.array([lon[j]]), {"p": q})[0, 0] > min_sep_km for q in peaks.values()):
            peaks[f"peak {len(peaks) + 1} ({lat[i]:.1f} N, {lon[j]:.1f} E)"] = (float(lat[i]), float(lon[j]))
    return peaks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--earth", required=True)
    ap.add_argument("--hyde", required=True)
    ap.add_argument("--shp", required=True)
    ap.add_argument("--xlsx", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2, st = earth_stages(z)
    base = np.nan_to_num(st["+ malaria (settlement base)"])
    A = blocks(km2 * land)
    H = blocks(hyde_at(a.hyde, lat, lon) * land)
    ok = (blocks(land.astype(float)) >= 72) & (H > 0)
    han = used(commanderies(a.shp, lat, lon, km2))
    T = towns(a.xlsx)
    ny, nx = land.shape[0] // BLOCK, land.shape[1] // BLOCK
    count = np.zeros((ny, nx))
    step_lat, step_lon = lat[0] - lat[1], lon[1] - lon[0]
    for t in T:
        i = int((lat[0] + step_lat / 2 - t["lat"]) / step_lat) // BLOCK
        j = int((t["lon"] - lon[0] + step_lon / 2) / step_lon) // BLOCK
        if 0 <= i < ny and 0 <= j < nx:
            count[i, j] += 1
    A2 = blocks(km2 * land, BLOCK)
    near = np.zeros((ny, nx), bool)
    for i, j in zip(*np.nonzero(count)):
        near[max(0, i - 1):i + 2, max(0, j - 1):j + 2] = True
    ok2 = near & (blocks(land.astype(float), BLOCK) / BLOCK ** 2 >= 0.3)

    def evaluate(density):
        h = metrics(blocks(density * km2 * land), H, A, ok)["spearman"]
        c = score(han, [float((density[i, j] * km2[i, j] * land[i, j]).sum()) for i, j in (x["idx"] for x in han)])["spearman"]
        M = blocks(density * km2 * land, BLOCK)[ok2]
        r = spearman(M / A2[ok2], count[ok2] / A2[ok2])
        return dict(hyde_200=h, han=c, roman_towns=r, mean=(h + c + r) / 3)

    sets = {"declared: cradles + Rome": CORE_SETS["cradles + Rome"]}
    for n in (4, 6, 8, 10):
        sets[f"dry river, top {n}"] = dry_river_cores(z, base, km2, n)
        sets[f"settlement, top {n}"] = settlement_peaks(z, base, km2, n)
    results = {"settlement base, no cores": dict(evaluate(base), cores={})}
    print(f"{'rule':30s} {'HYDE 200':>9s} {'Han':>7s} {'Roman':>7s} {'mean':>7s}")
    r = results["settlement base, no cores"]
    print(f"{'settlement base, no cores':30s} {r['hyde_200']:9.3f} {r['han']:7.3f} {r['roman_towns']:7.3f} {r['mean']:7.3f}")
    for name, cores in sets.items():
        D = travel_distance(z, cores, 2.0, 1.0, 1.0)
        r = dict(evaluate(base * core_term(D, 800)), cores=cores)
        results[name] = r
        print(f"{name:30s} {r['hyde_200']:9.3f} {r['han']:7.3f} {r['roman_towns']:7.3f} {r['mean']:7.3f}   "
              + "; ".join(k.split("(")[-1].rstrip(")") for k in cores), flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
