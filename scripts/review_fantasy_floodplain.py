"""Independent review of the fantasy floodplain port: timing rebuilt from the stored flow with the Earth reviewer's
separate run-finding code (shifted to solstice months), dry test rebuilt, and fields unchanged."""
import json, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from review_floodplain_rule import last_run_end

OUT = ROOT / 'output/fantasy_floodplain_20261114'; r = json.loads((OUT / 'results.json').read_text())
assert r['plan_sha256'] == sha(ROOT / 'calibration/fantasy_floodplain_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/fantasy_floodplain.py')
rows = {}
for mode, v in r['modes'].items():
    f = np.load(OUT / f'fields_{mode}.npz'); flow = f['flow']
    ends = {b: last_run_end(flow[:, b] > 1.0) for b in range(1, flow.shape[1])}                 # 1-based month index from last_run_end
    ok = [b for b, e in ends.items() if e is not None and (e - 1) in (6, 7, 8, 9)]
    assert ok == v['basins_timing_ok'] == [] and all((e - 1 if e else None) == v['last_flood_month_after_solstice'][str(b)] for b, e in ends.items())
    assert not f['qualifying'].any() and not (f['share'] > 0).any() and np.array_equal(f['crop_before'], f['crop_after'])
    assert abs(v['settlement_base_total_after'] / v['settlement_base_total_before'] - 1) < 1e-6
    assert v['published_control_max_abs'] < 0.01 and v['tail_control_max_abs'] < 1e-3
    rows[mode] = dict(basins=len(ends), timing_ok=0, latest_flood_end_after_solstice=max(e - 1 for e in ends.values() if e))
write(OUT / 'review.json', dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), modes=rows))
print('review passed', rows)
