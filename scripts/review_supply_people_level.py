"""Review of output/supply_people_level_20261114: decisions rebuilt from stored surfaces with the reviewed crossing code,
level factor arithmetic, and fresh replay."""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from review_egypt_sufficiency import crossing

OUT = ROOT / 'output/supply_people_level_20261114'
r = json.loads((OUT / 'results.json').read_text()); assert r['plan_sha256'] == sha(ROOT / 'calibration/supply_people_level_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/supply_people_level.py')
shares = json.loads((ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json').read_text())['parameters']['marketed_share_e']; checks = 0; passing = []
for n, v in r['variants'].items():
    ratios = {}
    for L, row in v['surface'].items():
        for part in ('all', 'west', 'east'):
            e = crossing(shares, row[part]['fed_share']); assert (e is None and row[part]['e95'] is None) or abs(e - row[part]['e95']) < 1e-12; checks += 1
        w, e = row['west']['e95'], row['east']['e95']; ratios[L] = None if not (w and e) else abs(math.log(w / e))
    valid = {k: x for k, x in ratios.items() if x is not None}; best = min(valid, key=lambda k: (valid[k], float(k)))
    keep = '270' in valid and (valid['270'] <= math.log(1.25) or valid['270'] <= 1.1 * valid[best]); d = v['decision']
    assert d['best_L_by_west_east_agreement'] == best and d['cited_270_kept'] == keep
    trans = all(x is not None and x >= 0.9 for x in d['transfer'].values()); assert d['transferable'] == trans
    if keep and trans: passing.append(n)
    if n.startswith('frier'): assert abs(v['empire_people'] - 61.4e6) < 1.0 and abs(v['level_factor'] * v['p2_empire_people_unscaled'] - 61.4e6) < 1.0
    else: assert v['level_factor'] == 1.0
assert passing == r['passing_variants'] and r['primary_pass'] == ('frier' in passing)
fresh = OUT / 'fresh/results.json'; exact = fresh.exists() and fresh.read_bytes() == (OUT / 'results.json').read_bytes()
write(OUT / 'review.json', dict(status='passed' if exact else 'passed_without_fresh_replay', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'), scalar_checks=checks, passing_variants=passing, fresh_byte_exact=bool(exact)))
print('review', exact, checks)
