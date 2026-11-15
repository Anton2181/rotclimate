"""Cold-dry (northern steppe) aridity under world-knob probes, coarse grid.

    python3 -I scripts/probe_steppe_world.py atlases/earth_fit/params.json PROBES.json 32
"""
import sys, json
sys.path.insert(0,'/home/user/rotclimate')
import numpy as np
from rotclimate.config import Params
from rotclimate.model import ClimateModel
from rotclimate.score import evaluate, objective
from rotclimate.geography import TARGET_CLASSES
base = Params.from_json(sys.argv[1]).replace(downsample=int(sys.argv[3]))
probes = json.loads(open(sys.argv[2]).read())
for name, sets in probes.items():
    p = base.replace(**sets)
    res = ClimateModel(p).run(); ev = evaluate(res)
    t, v = res.grid.target, res.grid.inmap & res.grid.land
    ix = ev['indices']; ar = ix['MAP']/(10*ix['Pth'])
    z = {}
    for cid, key, _, _ in TARGET_CLASSES:
        m = v & (t == cid); z[key] = (ev['per_class'][key], float(np.median(ar[m])) if m.any() else np.nan)
    print(f"{name:16s} zonefit {objective(ev,'zonefit'):.3f} acc {ev['accuracy']:.3f} | cold_dry member {z['cold_dry'][0]:.2f} aridity {z['cold_dry'][1]:.2f} | " +
          " ".join(f"{k[:6]} {a:.2f}/{b:.2f}" for k,(a,b) in z.items()), flush=True)
