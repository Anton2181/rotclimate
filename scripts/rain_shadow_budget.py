"""Moisture budget of windward and lee boxes (calibration/rain_shadow_20261115/plan.json pairs), r44 or a variant.

    python3 -I scripts/rain_shadow_budget.py OUT.json REGION [--set JSON]
Terms in mm/day, medians over the box's lowland cells, cold half (6 months with most observed rain) and annual.
"""
import json, sys, numpy as np
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.model import ClimateModel

def main():
    out, region = sys.argv[1], sys.argv[2]
    sets = json.loads(sys.argv[sys.argv.index('--set') + 1]) if '--set' in sys.argv else {}
    plan = json.loads((ROOT / 'calibration/rain_shadow_20261115/plan.json').read_text())
    base = Params.from_json(ROOT / plan['reference']).replace(**sets)
    case = earth.region_case(region, 56.0)
    p = earth.earth_params(base, case).replace(steps_per_year=base.steps_per_year)
    res = ClimateModel(p, grid=case.grid).run(diagnose_moisture=True)
    g = case.grid; sl = g.map_slice(); B = res.moisture_budget
    lon, lat, elev, land = case.lon[sl], g.lat[sl], g.elev[sl], g.land[sl]
    rep = {}
    for side, (x0, x1, y0, y1) in plan['pairs'][region].items():
        m = land & (lon >= x0) & (lon < x1) & (lat >= y0) & (lat < y1) & (elev < 1800)
        row = {}
        for key in ('advection', 'diffusion', 'storm_exchange', 'evaporation', 'column_drying', 'residual'):
            a = B[key][:, m]; row[key] = float(np.median(a.mean(0)))
        row['rain'] = float(np.median(res.P[(slice(None),) + tuple(sl)][:, m].mean(0))) if res.P.ndim == 3 else None
        row['W'] = float(np.median(res.W[(slice(None),) + tuple(sl)][:, m].mean(0)))
        row['cells'] = int(m.sum()); rep[side] = row
    Path(out).write_text(json.dumps(dict(region=region, sets=sets, boxes=rep), indent=1) + '\n'); print(json.dumps(rep, indent=1))

if __name__ == '__main__':
    main()
