"""Which physics makes a zone appear? Swap groups of physics constants from a
donor fit into a base fit (the world is the base's) and score the map.

    python -I scripts/physics_attribution.py --base calibration/earth/joint_e1_retro.json \
        --donor calibration/earth/free_e2new_retro.json --out output/earth_on_map/attribution.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rotclimate.calibrate import evaluate_params  # noqa: E402
from rotclimate.config import Params  # noqa: E402

GROUPS = {
    "circulation": ["hadley_edge", "hadley_shift", "itcz_mean", "itcz_shift", "trade_speed", "westerly_speed",
                    "monsoon_strength", "monsoon_scale_km", "cross_isobar_deg", "terrain_drag", "circulation_lag_days"],
    "temperature": ["land_tau_days", "ocean_tau_days", "heat_diffusion", "current_strength", "sst_offset", "land_offset",
                    "inland_sea_warming", "lake_coupling", "land_amplitude", "wet_cooling", "land_heat_capacity",
                    "continentality", "upwelling", "lapse_rate"],
    "moisture_supply": ["ocean_rh", "evap_tau_days", "land_recycling"],
    "rain": ["precip_tau_days", "rh_threshold", "storm_track", "storm_width", "convective", "orographic", "instability",
             "storm_asym", "storm_reach", "storm_seasonality", "background_ascent", "convective_rain", "convective_rh",
             "subcloud_evaporation", "land_coupling_insolation"],
    "sinking_air": ["subsidence", "subsidence_asym", "subsidence_summer", "subsidence_width", "sverdrup",
                    "subsidence_drying"],
    "storm_eddies": ["eddy_rate", "eddy_scale_km", "eddy_seasonality"],
}


def load(path):
    d = json.loads(Path(path).read_text())
    d = d.get("params", d)
    return Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__})


def score(p):
    r = evaluate_params(p, "zonefit")
    return dict(zonefit=r["score"], strict=r["accuracy"], recall=r["recall"], mediterranean=r["mediterranean"])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", required=True)
    ap.add_argument("--donor", required=True)
    ap.add_argument("--downsample", type=int, default=16)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    over = dict(downsample=a.downsample, solver_rtol=1e-5, solver_require_convergence=False)
    base, donor = load(a.base).replace(**over), load(a.donor)
    rows = {"base": score(base)}
    print("base", rows["base"]["recall"], flush=True)
    for name, genes in GROUPS.items():
        p = base.replace(**{g: getattr(donor, g) for g in genes})
        rows[name] = score(p)
        rows[name]["changed"] = {g: [getattr(base, g), getattr(donor, g)] for g in genes
                                 if getattr(base, g) != getattr(donor, g)}
        r = rows[name]
        print(f"{name:16s} zonefit {r['zonefit']:.3f} strict {r['strict']:.1%} cold_dry {r['recall']['cold_dry']:.1%} "
              f"med {r['recall']['med']:.1%} hot_dry {r['recall']['hot_dry']:.1%}", flush=True)
    Path(a.out).write_text(json.dumps(dict(base=a.base, donor=a.donor, rows=rows), indent=1))


if __name__ == "__main__":
    main()
