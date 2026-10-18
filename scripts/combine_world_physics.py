"""Start point for an Earth-fit map: the physics of an Earth fit with the
world of a map fit.

Everything that describes the world (latitude, tilt, spin, orientation, the
drawn tiers' heights, the calendar, the surroundings beyond the map and the
map's own geometry and numerics) comes from the map fit; every physics
constant comes from the Earth fit. A world-only calibration then fits the
world to the painted zones with the Earth physics held fixed.

    python -I scripts/combine_world_physics.py --world calibration/earth/free_e5p_ds16.json \
        --physics calibration/earth/earth_e6_r11.json --out calibration/earth/earthfit_start.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# keys the map's world owns; everything else is physics
WORLD_KEYS = {"lat_center", "north_bearing", "tilt", "retrograde", "eccentricity", "perihelion_after_solstice",
              "year_days", "winter_solstice_day", "map_width_mi", "map_height_mi", "tier_tops", "pad_km",
              "downsample", "steps_per_year", "picard_iters", "moisture_relaxation", "moisture_residual_tol",
              "moisture_require_convergence", "transport_scheme", "solver_rtol", "solver_max_iter",
              "solver_require_convergence", "t_iters", "t_relaxation", "t_adaptive_retries", "t_require_convergence"}


def params(path):
    d = json.loads(Path(path).read_text())
    return d.get("params", d)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--world", required=True)
    ap.add_argument("--physics", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    world, phys = params(a.world), params(a.physics)
    out = dict(phys)
    for k, v in world.items():
        if k in WORLD_KEYS or k.startswith("beyond_"):
            out[k] = v
    # far_fetch stays the Earth fit's: on the map the grid's edge carries the
    # land share of the procedural surroundings (geography.chi_far)
    Path(a.out).write_text(json.dumps(out, indent=1))
    changed = sorted(k for k in out if k in phys and k in world and out[k] != world[k])
    print(f"{len(changed)} physics settings taken from the Earth fit; world from {a.world}")


if __name__ == "__main__":
    main()
