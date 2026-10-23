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


FOREST_SHARE = {1: 0.5, 3: 1.0, 4: 1.0, 7: 1.0, 9: 1.0}     # rotclimate.biomes codes: savanna half, forests whole


def travel_distance(z, cores, forest_cost=1.0, sea_cost=1.0, relief_cost=0.0, coarsen=3):
    """[lat, lon] effective km to the nearest core along the cheapest path:
    each km costs 1 on open land, forest_cost in forest (biome share from
    rotclimate.biomes), sea_cost at sea, plus relief_cost x the local relief
    in km. 8-neighbour Dijkstra on a grid coarsened by `coarsen` (5' x 3 =
    15', ~28 km), then repeated back to full resolution."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    from rotclimate import biomes
    lat, lon, land = z["lat"], z["lon"], z["land"]
    biome = biomes.classify(np.nan_to_num(z["T_ann"]), np.nan_to_num(z["P_ann"]), land)
    forest = np.zeros(land.shape)
    for code, share in FOREST_SHARE.items():
        forest[biome == code] = share
    relief = np.clip(np.nan_to_num(z["relief"]), 0, 3000) / 1000.0
    c = coarsen
    ny, nx = land.shape[0] // c, land.shape[1] // c

    def co(a):
        return a[:ny * c, :nx * c].reshape(ny, c, nx, c).mean((1, 3))
    lf = co(land.astype(float))
    cost = np.where(lf >= 0.5, 1.0 + (forest_cost - 1.0) * co(forest * land) / np.maximum(lf, 1e-9)
                    + relief_cost * co(relief * land) / np.maximum(lf, 1e-9), sea_cost)
    clat = lat[:ny * c].reshape(ny, c).mean(1)
    clon = lon[:nx * c].reshape(nx, c).mean(1)
    dy_km = abs(clat[1] - clat[0]) * 111.32
    idx = np.arange(ny * nx).reshape(ny, nx)
    rows, cols, w = [], [], []
    for di, dj in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = idx[max(0, -di):ny - max(0, di), max(0, -dj):nx - max(0, dj)]
        b = idx[max(0, di):ny - max(0, -di) or None, max(0, dj):nx - max(0, -dj) or None]
        ia = a // nx
        dx_km = abs(clon[1] - clon[0]) * 111.32 * np.cos(np.radians(0.5 * (clat[ia] + clat[b // nx])))
        d = np.hypot(di * dy_km, dj * dx_km)
        wt = 0.5 * (cost.ravel()[a] + cost.ravel()[b]) * d
        rows += [a.ravel(), b.ravel()]; cols += [b.ravel(), a.ravel()]; w += [wt.ravel(), wt.ravel()]
    g = coo_matrix((np.concatenate(w), (np.concatenate(rows), np.concatenate(cols))), shape=(ny * nx, ny * nx)).tocsr()
    src = [int(np.argmin(np.abs(clat - la0))) * nx + int(np.argmin(np.abs(clon - lo0))) for la0, lo0 in cores.values()
           if clat.min() - 1 <= la0 <= clat.max() + 1 and clon.min() - 1 <= lo0 <= clon.max() + 1]
    dist = dijkstra(g, indices=src, min_only=True).reshape(ny, nx)
    full = np.repeat(np.repeat(dist, c, 0), c, 1)
    out = np.full(land.shape, np.inf)
    out[:ny * c, :nx * c] = full
    out[ny * c:, :] = out[ny * c - 1:ny * c, :]
    out[:, nx * c:] = out[:, nx * c - 1:nx * c]
    return out


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
    ap.add_argument("--travel", action="store_true", help="scan travel-cost distances (forest, sea, relief) instead")
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
    if a.travel:
        cores = CORE_SETS["cradles + Rome"]
        for fc, sc, rc in [(1.0, 1.0, 0.0), (2.0, 1.0, 0.0), (3.0, 1.0, 0.0), (1.0, 1.0, 1.0), (2.0, 1.0, 1.0),
                           (2.0, 3.0, 0.0), (2.0, 3.0, 1.0)]:
            D = travel_distance(z, cores, fc, sc, rc)
            for L in (450, 600, 800, 1000, 1500):
                results[f"travel forest x{fc:g} sea x{sc:g} relief {rc:g}/km, L {L}"] = evaluate(base * core_term(D, L))
        report(results, a)
        return
    core_sets = dict(CORE_SETS)
    for n in (4, 6, 10):
        core_sets[f"rule, top {n}"] = dry_river_cores(z, base, km2, n)
    for set_name, cores in core_sets.items():
        D = core_distance(lat, lon, cores)
        for L in SCALES_KM:
            results[f"{set_name}, L {L} km"] = evaluate(base * core_term(D, L))
    report(results, a, core_sets)


def report(results, a, core_sets=None):
    names = [Path(p).name for p in a.hyde]
    print(f"{'':42s}" + "".join(f"{n.replace('popc_', 'HYDE ').replace('.tif', ''):>22s}" for n in names)
          + f"{'Han AD 2':>22s}{'regions':>9s}")
    for k, v in results.items():
        cols = "".join(f"   rank {v[n]['spearman']:.3f} mv {v[n]['moved_share']:4.0%}" for n in names + ["Han AD 2"])
        print(f"{k:42s}{cols}   sd {v['regions_spread']:.3f}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(dict(core_sets=core_sets or CORE_SETS, scales_km=SCALES_KM, results=results), indent=1))


if __name__ == "__main__":
    main()
