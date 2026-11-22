"""Break one region's land temperature into the model's stages (diagnostic taps in ClimateModel.run).

    python3 -I scripts/land_budget.py REGION PARAMS.json OUT.json
For each stage the step-to-step change of the land column, averaged over the scored land cells, per calendar month
(last year of the run), plus the air temperature and the observed monthly mean.
"""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.model import ClimateModel

region, pf, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
p = Params(**json.loads((ROOT / pf).read_text()))
for f in ['calibration/sealed_20261031/regions.json', 'calibration/sealed_20261031b/regions.json',
          'calibration/sealed_20261101c/regions.json', 'calibration/tropical_check_20261122t/regions.json']:
    earth.REGIONS.update(json.loads((ROOT / f).read_text()))
case = earth.region_case(region, 56)
g = case.grid; m = g.inmap & g.land & np.isfinite(case.obs_T).all(0)
rec = {}
ClimateModel.tap = staticmethod(lambda name, d, a: rec.setdefault(name, {}).__setitem__(round(float(d), 3), float(np.mean(np.asarray(a)[m]))))
res = earth.run_case(p, case, steps=p.steps_per_year)
ClimateModel.tap = None
names = ['zonal', 'continental', 'subsidence', 'wet_cooling', 'wet_sun', 'dry_heating', 'cloud', 'land_eq', 'air']
days = sorted(rec['air']); yd = p.year_days
month = lambda d: int((d % yd) / yd * 12)
# hemisphere-local months are not used here: calendar months 1-12 for the northern hemisphere
res_m = {}
for n in names:
    v = np.zeros(12); c = np.zeros(12)
    for d, x in rec[n].items(): v[month(d)] += x; c[month(d)] += 1
    res_m[n] = (v / np.maximum(c, 1)).round(2).tolist()
obs = np.asarray(case.obs_T)[:, m].mean(1).round(2).tolist()
res_m['observed'] = obs
out.write_text(json.dumps(res_m, indent=1) + '\n')
hdr = 'stage         ' + ' '.join(f'{i:>6d}' for i in range(1, 13))
print(hdr)
prev = None
for n in names + ['observed']:
    print(f'{n:13s} ' + ' '.join(f'{x:6.1f}' for x in res_m[n]))
