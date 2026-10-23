"""The atlases' Harvest settlement model on Earth, compared with HYDE 3.3.

    python3 -I scripts/harvest_earth_hyde.py --earth output/land_people/earth/earth.npz \
        --hyde data/cache/hyde33/popc_ce_200.tif --out output/population_hyde/harvest_ce_200.json

Runs harvest.models.settlement_fields (the same food, herding, clearance,
river-access and malaria rules the atlases use) on the Earth food-capacity run
(WorldClim climate, Natural Earth rivers; scripts/land_people_earth.py), then
compares the pattern of each stage with HYDE 3.3 at 1 degree
(scripts/hyde_compare.metrics). Inputs the Earth run does not store are
approximated and stated:
  * Whittaker biome codes from annual temperature and rain (rotclimate.biomes);
  * distance to water from the stored irrigation field, which was built as
    exp(-d / 6 km) beside navigable rivers: d = -6 km x ln(irrigation),
    capped at 300 km (streams and coasts are therefore treated as farther);
  * malaria from the stored MARA climatic suitability, not the atlas's
    Mordecai temperature model.
HYDE is suitability-weighted itself: agreement is a consistency check.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from harvest.models import settlement_fields  # noqa: E402
from hyde_compare import blocks, hyde_at, metrics  # noqa: E402
from rotclimate import biomes  # noqa: E402


def leaching_fertility(z, max_penalty):
    """Low-input fertility of leached soils: 1 - max_penalty x smoothstep of the
    annual water surplus (rain - potential evaporation) from 300 to 1,200 mm.
    Heavily leached, highly weathered soils (south China's red soils, the humid
    tropics) give low-input farmers a fraction of what loess and alluvium give;
    FAO GAEZ applies this as its soil-nutrient constraint (up to ~75 %)."""
    from land_people import smoothstep
    surplus = np.maximum(np.nan_to_num(z["P_ann"]) - np.nan_to_num(z["PET_ann"]), 0.0)
    return 1.0 - max_penalty * smoothstep(surplus, 300.0, 1200.0)


def earth_stages(z, leaching=0.0, reliability=None):
    """Settlement stages of harvest.models on the Earth run (people per km2)."""
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2 = (111.32 / 12) ** 2 * np.cos(np.radians(lat))[:, None] * np.ones((1, len(lon)))
    biome = biomes.classify(np.nan_to_num(z["T_ann"]), np.nan_to_num(z["P_ann"]), land)
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(z["irr"]), 1e-12)), 300.0)
    crops = np.nan_to_num(z["capacity"])
    if leaching > 0:
        crops = crops * leaching_fertility(z, leaching)
    if reliability is not None:
        # (start_days, full_days, power): harvest.models.harvest_reliability
        from harvest.models import harvest_reliability
        crops = crops * harvest_reliability(np.nan_to_num(z["lgp_days"]), z["irr"], *reliability)
    f = settlement_fields(crops, np.nan_to_num(z["npp"]), biome, np.nan_to_num(z["arable"]),
                          water_km, np.nan_to_num(z["malaria"]))
    return km2, {
        "crops only (Earth run)": f["crop_capacity"],
        "crops x clearance + herding": f["crop_capacity"] * f["clearance"] + f["pastoral_capacity"],
        "+ river access": f["settlement_no_malaria"],
        "+ malaria (settlement base)": f["settlement_base"],
        "uniform over land": np.ones_like(km2),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--earth", required=True)
    ap.add_argument("--hyde", nargs="+", required=True)
    ap.add_argument("--leaching", type=float, default=0.0, help="maximum low-input yield penalty of leached soils (0 = off)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(a.earth)
    lat, lon, land = z["lat"], z["lon"], z["land"]
    km2, stages = earth_stages(z, a.leaching)
    f = None
    out = {}
    for path in a.hyde:
        H = blocks(hyde_at(path, lat, lon) * land)
        A = blocks(km2 * land)
        ok = (blocks(land.astype(float)) >= 72) & (H > 0)
        res = {}
        for name, density in stages.items():
            M = blocks(np.nan_to_num(density) * km2 * land)
            res[name] = metrics(M, H, A, ok)
        out[Path(path).name] = res
        print(f"{Path(path).name}  ({int(ok.sum())} land blocks of 1 degree)")
        for name, v in res.items():
            print(f"  {name:30s} rank corr {v['spearman']:.3f}  people to move {v['moved_share']:.1%}  log10 RMSE {v['log_rmse']:.3f}")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
