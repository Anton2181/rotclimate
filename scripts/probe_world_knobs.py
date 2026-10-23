"""Zone-fit sensitivity of the Earth-fit map to world knobs: one layout, ds32.

    python3 -I scripts/probe_world_knobs.py calibration/map_world_r35/start.json output/world_knobs_20261023/probes2.json

Each probe replaces a few settings of the start and prints the zone-fit
objective, the mean rule membership and strict accuracy per painted zone,
the hot humid-summer share the realism guard penalises, and the swamp's and
hot desert's annual mean and the cold-wet zone's coldest month.
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from rotclimate.config import Params
from rotclimate.model import ClimateModel
from rotclimate.score import evaluate, objective
from rotclimate.geography import TARGET_CLASSES

def zone_mat(ev, cid):
    m = ev["_valid"] & (ev["_target"] == cid); return float(ev["indices"]["MAT"][m].mean())
def zone_tc(ev, cid):
    m = ev["_valid"] & (ev["_target"] == cid); return float(ev["indices"]["Tcold"][m].mean())
def swamp_mat(ev):
    return zone_mat(ev, 5)
base = Params.from_json(sys.argv[1]).replace(downsample=32, beyond_seed=1)
probes = json.loads(open(sys.argv[2]).read())
for name, sets in probes.items():
    p = base.replace(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in sets.items()})
    try:
        res = ClimateModel(p).run(); ev = evaluate(res)
        ev["_target"], ev["_valid"] = res.grid.target, res.grid.inmap & res.grid.land
    except Exception as e:
        print(f"{name:14s} FAILED {e!r}", flush=True); continue
    out = []
    for cid, key, _, _ in TARGET_CLASSES:
        out.append(f"{key[:5]} {ev['per_class'][key]:.2f}")
    print(f"{name:14s} zonefit {objective(ev, 'zonefit'):.3f} total {ev['total']:.3f} acc {ev['accuracy']:.3f} | " + " ".join(out) + f" | hot-summer share {ev['realism'].get('wet_summer_hot', 0):.3f} swampMAT {swamp_mat(ev):.1f} hotdryMAT {zone_mat(ev, 7):.1f} coldwetTc {zone_tc(ev, 1):.1f}", flush=True)
