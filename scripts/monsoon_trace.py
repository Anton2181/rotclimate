"""Trace r49's rain-step inputs (desert-air share chi, instability, convective rate, column RH) over a region's scored land,
monthly means (diagnostic for calibration/monsoon_convection_20261121).

    .venv/bin/python -I scripts/monsoon_trace.py REGION [--specs FILE] [--set JSON]
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from earth_benchmark import load_params
from rotclimate import earth
from rotclimate.model import ClimateModel

ap = argparse.ArgumentParser(); ap.add_argument('region'); ap.add_argument('--specs'); ap.add_argument('--set', default='{}'); a = ap.parse_args()
if a.specs: earth.REGIONS.update(json.loads(Path(a.specs).read_text()))
base = load_params(ROOT / 'calibration/local_accuracy_20261023/r49_params.json').replace(**json.loads(a.set))
case = earth.region_case(a.region, 56.0); p = earth.earth_params(base, case).replace(steps_per_year=base.steps_per_year)
g = case.grid; m = g.inmap & g.land; ti, tj = np.nonzero(m)
model = ClimateModel(p, grid=g); model.trace_cells = (ti, tj); model.run()
keys = ['T', 'W', 'Ws', 'P', 'chi', 'instab', 'conv_rate']
rows = {}
for rec in model.trace:
    mo = int(rec['day'] // (p.year_days / 12.0)) % 12
    r = rows.setdefault(mo, {k: [] for k in keys + ['RH']})
    for k in keys: r[k].append(float(np.mean(rec[k])) if k in rec else np.nan)
    r['RH'].append(float(np.mean(rec['W'] / np.maximum(rec['Ws'], 1e-6))))
out = {mo + 1: {k: round(float(np.nanmean(v)), 3) for k, v in r.items()} for mo, r in sorted(rows.items())}
for mo, r in out.items(): print(a.region, mo, r)
(ROOT / 'output/monsoon_probe_20261121').mkdir(parents=True, exist_ok=True)
(ROOT / f'output/monsoon_probe_20261121/trace_{a.region}.json').write_text(json.dumps(out, indent=1))
