"""Old cores and the settlement model: does distance from the oldest states
explain where the environmental model puts too many or too few people?

    python3 -I scripts/population_cores.py --earth output/land_people/earth/earth.npz \
        --hyde data/cache/hyde33/popc_ce_0.tif data/cache/hyde33/popc_ce_200.tif \
        --shp data/cache/han_ad2/shp/ResearchArea --out output/population_cores/scan.json

The settlement base of harvest.models (scripts/harvest_earth_hyde.py) is
multiplied by a core term, max over cores of exp(-D / L), with D the
great-circle distance to the core. The core sets are declared here before
any scoring:
  cradles     the four Old World river-valley states (Uruk, Memphis,
              Harappa, and Zhengzhou for the Shang city of the Central Plain);
  + Rome      the cradles plus the capital of the Roman empire;
  + Rome, Chang'an / Luoyang
              the cradles plus the capitals of both empires of the period
              (Western Han in AD 2, Eastern Han by 200 CE).
On the fantasy map the cores are a worldbuilding input (old provinces and
capitals); here they test whether such an input helps, and at what scale.

A core rule that needs no history is scored too (dry_river_cores): the
first states rose on irrigable river land in dry climates (Carneiro's
circumscription; Mesopotamia, Egypt, the Indus, the loess Yellow River).
Score each cell's settlement-base people on land within reach of a big
river (irrigation field > 0.3) where rain is under 65 % of potential
evaporation, smooth over ~216 km, and take the strongest peaks at least
1,000 km apart. The same rule runs on any map.

Each setting is scored three ways:
  * HYDE 3.3 at 1 degree (rank correlation, share of people to move); HYDE's
    country totals carry the historical record, so this tests the core term
    against historians' country estimates, spread by HYDE's own weights;
  * the Han AD 2 census by commandery (scripts/han_census_check.py), a
    real count;
  * the 11 historical regions of scripts/land_people_earth.py: the spread
    (standard deviation of log10 recorded / modelled after removing the
    median) of their people against the model.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Poly

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from han_census_check import commanderies, score, used  # noqa: E402
from harvest_earth_hyde import earth_stages  # noqa: E402
from hyde_compare import blocks, hyde_at, metrics  # noqa: E402
from land_people_earth import REGIONS  # noqa: E402

CRADLES = {"Uruk": (31.32, 45.64), "Memphis": (29.85, 31.25), "Harappa": (30.63, 72.86), "Zhengzhou": (34.75, 113.65)}
CORE_SETS = {
    "cradles": CRADLES,
    "cradles + Rome": {**CRADLES, "Rome": (41.9, 12.5)},
    "cradles + Rome, Chang'an": {**CRADLES, "Rome": (41.9, 12.5), "Chang'an": (34.3, 108.9)},
    "cradles + Rome, Luoyang": {**CRADLES, "Rome": (41.9, 12.5), "Luoyang": (34.68, 112.6)},
}
SCALES_KM = (300, 450, 600, 800, 1000, 1500, 2500)


def core_distance(lat, lon, cores):
    """[lat, lon] km to the nearest core, and the distance to each."""
    la, lo = np.radians(lat)[:, None], np.radians(lon)[None, :]
    each = []
    for la0, lo0 in cores.values():
        a, b = np.radians(la0), np.radians(lo0)
        each.append(6371.0 * np.arccos(np.clip(np.sin(la) * np.sin(a) + np.cos(la) * np.cos(a) * np.cos(lo - b), -1, 1)))
    return np.min(each, 0)


def dry_river_cores(z, base, km2, n, box=24, min_sep_km=1000.0):
    """The n strongest peaks of people on irrigable river land in dry
    climates (see the module docstring), as {name: (lat, lon)}."""
    from scipy.ndimage import uniform_filter
    lat, lon, land = z["lat"], z["lon"], z["land"]
    ai = np.nan_to_num(z["P_ann"]) / np.maximum(np.nan_to_num(z["PET_ann"]), 1.0)
    s = uniform_filter(base * ((np.nan_to_num(z["irr"]) > 0.3) & (ai < 0.65)) * land * km2, box)
    peaks = {}
    for k in np.argsort(-s.ravel()):
        i, j = divmod(int(k), s.shape[1])
        if s[i, j] <= 0 or len(peaks) == n:
            break
        if all(core_distance(np.array([lat[i]]), np.array([lon[j]]), {"p": q})[0, 0] > min_sep_km for q in peaks.values()):
            peaks[f"peak {len(peaks) + 1} ({lat[i]:.1f} N, {lon[j]:.1f} E)"] = (float(lat[i]), float(lon[j]))
    return peaks


def core_term(D, scale_km):
    return np.exp(-D / scale_km)


def region_spread(density, km2, land, lat, lon):
    """Standard deviation of log10(recorded / modelled people) over the
    historical regions, after removing the median (scale-free)."""
    LA, LO = np.meshgrid(lat, lon, indexing="ij")
    pts = np.column_stack([LO.ravel(), LA.ravel()])
    res = {}
    for name, r in REGIONS.items():
        inside = Poly(r["poly"]).contains_points(pts).reshape(LA.shape) & land
        area = km2[inside].sum()
        hist = np.sqrt(np.prod(r["people"])) * 1e6 if "people" in r else np.sqrt(np.prod(r["density"])) * area
        res[name] = (hist, float((density * km2)[inside].sum()))
    lr = np.log10(np.array([h for h, _ in res.values()]) / np.array([m for _, m in res.values()]))
    lr -= np.median(lr)
    return float(lr.std()), dict(zip(res, map(float, lr)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--earth", required=True)
    ap.add_argument("--hyde", nargs="+", required=True)
    ap.add_argument("--shp", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2, stages = earth_stages(z)
    base = np.nan_to_num(stages["+ malaria (settlement base)"])
    A = blocks(km2 * land)
    hyde = {}
    for path in a.hyde:
        H = blocks(hyde_at(path, lat, lon) * land)
        hyde[Path(path).name] = (H, (blocks(land.astype(float)) >= 72) & (H > 0))
    han = used(commanderies(a.shp, lat, lon, km2))

    def evaluate(density):
        out = {k: metrics(blocks(density * km2 * land), H, A, ok) for k, (H, ok) in hyde.items()}
        out["Han AD 2"] = score(han, [float((density[i, j] * km2[i, j] * land[i, j]).sum()) for i, j in (x["idx"] for x in han)])
        out["regions_spread"], out["regions"] = region_spread(density, km2, land, lat, lon)
        return out

    results = {"settlement base": evaluate(base)}
    core_sets = dict(CORE_SETS)
    for n in (4, 6, 10):
        core_sets[f"rule, top {n}"] = dry_river_cores(z, base, km2, n)
    for set_name, cores in core_sets.items():
        D = core_distance(lat, lon, cores)
        for L in SCALES_KM:
            results[f"{set_name}, L {L} km"] = evaluate(base * core_term(D, L))
    names = [Path(p).name for p in a.hyde]
    print(f"{'':42s}" + "".join(f"{n.replace('popc_', 'HYDE ').replace('.tif', ''):>22s}" for n in names)
          + f"{'Han AD 2':>22s}{'regions':>9s}")
    for k, v in results.items():
        cols = "".join(f"   rank {v[n]['spearman']:.3f} mv {v[n]['moved_share']:4.0%}" for n in names + ["Han AD 2"])
        print(f"{k:42s}{cols}   sd {v['regions_spread']:.3f}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(core_sets=core_sets, scales_km=SCALES_KM, results=results), indent=1))


if __name__ == "__main__":
    main()
