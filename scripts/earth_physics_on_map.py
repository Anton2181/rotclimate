"""Put physics fitted on Earth onto the fantasy map.

Takes the world (latitude, tilt, spin, orientation, terrain tiers, what lies
beyond the map) and the numerics from --world, and every physics constant that
the Earth calibration fits from --physics; runs the map and scores it with the
measures the handoff's promotion guards use: strict painted-zone agreement,
per-zone recall, the share of painted Mediterranean classed dry (Koppen B) and
its Cs share. --compare scores the --world file itself with the same numerics,
so both rows are like for like.

    python -I scripts/earth_physics_on_map.py --physics calibration/earth_r2/best_params.json \
        --world output/overnight_mediterranean/selected_params.json --downsample 16 --compare \
        --out output/earth_on_map/r2_ds16
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np  # noqa: E402

from rotclimate.config import Params  # noqa: E402
from rotclimate.geography import TARGET_CLASSES  # noqa: E402
from rotclimate.koppen import CODES  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from earth_calibrate import SPACES  # noqa: E402

PHYSICS = [g[0] for g in SPACES["e1"]]


def load(path):
    d = json.loads(Path(path).read_text())
    d = d.get("params", d)
    return Params(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in d.items()
                     if k in Params.__dataclass_fields__})


def merged(world: Params, physics: Params) -> Params:
    return world.replace(**{k: getattr(physics, k) for k in PHYSICS})


def score(p: Params) -> dict:
    from rotclimate.model import ClimateModel
    from rotclimate.score import evaluate

    t = time.time()
    res = ClimateModel(p).run()
    ev = evaluate(res)
    g = res.grid
    valid = g.inmap & g.land
    from rotclimate.koppen import classify
    st = ev["monthly"]
    codes = np.array(CODES)[classify(st["Tm"], st["Pm"], st["summer"])]
    med = valid & (g.target == 4)
    return dict(
        seconds=round(time.time() - t, 1),
        accuracy=ev["accuracy"], display_accuracy=ev["label_policy_audit"]["display_accuracy"],
        zone_recall={k: (None if not np.isfinite(v) else float(v)) for k, v in ev["recall"].items()},
        mediterranean=dict(dry_share=float(np.char.startswith(codes[med], "B").mean()),
                           cs_share=float(np.char.startswith(codes[med], "Cs").mean())),
        fuzzy_mean=ev["total"], map_median_rain_mm=ev["realism"]["map_median"],
        moisture_converged=bool(all(x is not False for x in getattr(res, "moisture_converged", []) or [True])),
        params=asdict(p))


def line(name, r):
    z = r["zone_recall"]
    return (f"{name:14s} strict {r['accuracy']:.1%} | Med dry {r['mediterranean']['dry_share']:.1%}, "
            f"Cs {r['mediterranean']['cs_share']:.1%} | " + " ".join(f"{k} {v:.0%}" for k, v in z.items() if v is not None)
            + f" | {r['seconds']:.0f}s")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--physics", required=True)
    ap.add_argument("--world", required=True)
    ap.add_argument("--downsample", type=int)
    ap.add_argument("--set", default="{}", help="json of overrides applied to both rows")
    ap.add_argument("--compare", action="store_true", help="also score --world itself")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    world = load(a.world)
    over = json.loads(a.set)
    if a.downsample:
        over["downsample"] = a.downsample
    rows = {}
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.compare:
        rows["world_as_is"] = score(world.replace(**over))
        print(line("world as is", rows["world_as_is"]), flush=True)
    rows["earth_physics"] = score(merged(world, load(a.physics)).replace(**over))
    print(line("Earth physics", rows["earth_physics"]), flush=True)
    (out / "summary.json").write_text(json.dumps(dict(physics=a.physics, world=a.world, overrides=over,
                                                      rows=rows), indent=1))


if __name__ == "__main__":
    main()
