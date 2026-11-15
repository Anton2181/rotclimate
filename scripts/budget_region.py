import json, sys, numpy as np
sys.path[:0]=[str(__import__('pathlib').Path(__file__).resolve().parents[1]), str(__import__('pathlib').Path(__file__).resolve().parent)]
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.koppen import monthly_weights
from rotclimate.model import ClimateModel
region=sys.argv[1]; sets=json.loads(sys.argv[2]) if len(sys.argv)>2 else {}
earth.REGIONS.update(json.load(open('/home/user/rotclimate/output/northern_steppe_20261115/winter_screen/region_specs.json')))
base=Params.from_json('/home/user/rotclimate/calibration/local_accuracy_20261023/r44_params.json').replace(**sets)
case=earth.region_case(region,56.0); p=earth.earth_params(base,case).replace(steps_per_year=base.steps_per_year)
res=ClimateModel(p,grid=case.grid).run(diagnose_moisture=True)
g=case.grid; sl=tuple(g.map_slice()); B=res.moisture_budget
m=(g.inmap&g.land)[sl]
wm=monthly_weights(res.days,p.year_days)
def mon(a): return (wm@a.reshape(a.shape[0],-1)).reshape((12,)+a.shape[1:])
print(region, sets)
for k in ('advection','diffusion','storm_exchange','evaporation','column_drying'):
    print('  %-15s'%k,' '.join('%6.2f'%v for v in mon(B[k])[:,m].mean(1)))
for k in ('P','W','u','v'):
    a=getattr(res,k)[(slice(None),)+sl]; print('  %-15s'%k,' '.join('%6.2f'%v for v in mon(a)[:,m].mean(1)))
# W along the west edge of the full grid vs map
W=mon(res.W); print('  W Jan by column (west->east, every 4th):',' '.join('%.1f'%x for x in W[0][g.land.any(1)].mean(0)[::4]))
