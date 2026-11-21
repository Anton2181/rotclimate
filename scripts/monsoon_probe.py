"""Probe r49's monsoon failure: column water, column RH and rain over scored land, January vs July-August.

    .venv/bin/python -I scripts/monsoon_probe.py REGION [REGION ...] [--specs FILE] [--set JSON]
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from earth_benchmark import load_params
from rotclimate import earth
from rotclimate.model import w_sat

ap = argparse.ArgumentParser(); ap.add_argument('regions', nargs='+'); ap.add_argument('--specs'); ap.add_argument('--set', default='{}')
a = ap.parse_args()
if a.specs: earth.REGIONS.update(json.loads(Path(a.specs).read_text()))
p = load_params(ROOT / 'calibration/local_accuracy_20261023/r49_params.json').replace(**json.loads(a.set))
out = {}
for region in a.regions:
    case = earth.region_case(region, 56.0); res = earth.run_case(p, case, steps=p.steps_per_year); g = case.grid
    m = g.inmap & g.land
    month = (np.floor(res.days / (p.year_days / 12.0)).astype(int)) % 12
    def mean(field, months): k = np.isin(month, months); return float(field[k][:, m].mean())
    rows = {}
    for name, months in (('Jan', [0]), ('JulAug', [6, 7])):
        k = np.isin(month, months); T = res.T[k][:, m]; W = res.W[k][:, m]
        rows[name] = dict(P_mm_day=mean(res.P, months), W_mm=float(W.mean()), RH_col=float((W / np.maximum(w_sat(T), 1e-6)).mean()),
                          u=mean(res.u, months), v=mean(res.v, months), E_mm_day=mean(res.E, months), T=float(T.mean()))
    out[region] = rows; print(region, json.dumps({k: {x: round(y, 3) for x, y in v.items()} for k, v in rows.items()}), flush=True)
(ROOT / 'output/monsoon_probe_20261121' / ('probe_' + '_'.join(a.regions) + '.json')).write_text(json.dumps(dict(set=json.loads(a.set), regions=out), indent=1))
