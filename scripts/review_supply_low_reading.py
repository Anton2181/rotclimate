"""Review of output/supply_low_reading_20261114: decisions rebuilt from stored surfaces, control, fresh replay."""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from review_egypt_sufficiency import crossing
OUT = ROOT / 'output/supply_low_reading_20261114'; r = json.loads((OUT / 'results.json').read_text())
assert r['plan_sha256'] == sha(ROOT / 'calibration/supply_low_reading_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/supply_low_reading.py')
shares = json.loads((ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json').read_text())['parameters']['marketed_share_e']; checks = 0
for reading, v in r['readings'].items():
    ratios = {}
    for L, row in v['surface'].items():
        for part in ('all', 'west', 'east'):
            e = crossing(shares, row[part]['fed_share']); assert (e is None and row[part]['e95'] is None) or abs(e - row[part]['e95']) < 1e-12; checks += 1
        w, e = row['west']['e95'], row['east']['e95']; ratios[L] = None if not (w and e) else abs(math.log(w / e))
    valid = {k: x for k, x in ratios.items() if x is not None}; best = min(valid, key=lambda k: (valid[k], float(k)))
    keep = '270' in valid and (valid['270'] <= math.log(1.25) or valid['270'] <= 1.1 * valid[best]); d = v['decision']
    assert d['cited_270_kept'] == keep and d['transferable'] == all(x is not None and x >= .9 for x in d['transfer'].values())
assert r['low_pass'] == (r['readings']['low']['decision']['cited_270_kept'] and r['readings']['low']['decision']['transferable']) and r['control_max_abs_difference'] < 1e-12
fresh = OUT / 'fresh/results.json'; exact = fresh.exists() and fresh.read_bytes() == (OUT / 'results.json').read_bytes()
write(OUT / 'review.json', dict(status='passed' if exact else 'passed_without_fresh_replay', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), scalar_checks=checks, fresh_byte_exact=bool(exact)))
print('review', exact, checks)
