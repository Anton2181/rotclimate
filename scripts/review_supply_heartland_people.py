"""Review of output/supply_heartland_people_20261114: the reviewed decision reconstruction (review_egypt_sufficiency)
applied by path substitution, plus the robustness ratio and fresh replay."""
import json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
src = (ROOT / 'scripts/review_egypt_sufficiency.py').read_text()
for old, new in [("output/egypt_sufficiency_20261114", "output/supply_heartland_people_20261114"),
                 ("calibration/egypt_sufficiency_20261114/plan.json", "calibration/supply_heartland_people_20261114/plan.json"),
                 ("scripts/egypt_sufficiency.py", "scripts/supply_heartland_people.py"),
                 ("    for pre in ('Y', 'YP'):\n        assert v['control']['egypt_surplus_person_years'] <= v[f'{pre}_1.94']['egypt_surplus_person_years'] <= v[f'{pre}_2.16']['egypt_surplus_person_years']\n", ""),
                 ("reviewer_sha256=sha(Path(__file__))", "reviewer_sha256=sha(REVIEWER)")]:
    assert old in src, old; src = src.replace(old, new)
ns = dict(__name__='reviewed', __file__=str(ROOT / 'scripts/review_egypt_sufficiency.py'), REVIEWER=Path(__file__)); exec(compile(src, 'review_egypt_sufficiency.py', 'exec'), ns); ns['main']()
r = json.loads((ROOT / 'output/supply_heartland_people_20261114/results.json').read_text())
adopted = json.loads((ROOT / 'output/settlement_supply_calibration_20261113/without_egypt/results.json').read_text())['decision']['e95_all_at_L_used']
e = r['variants']['P2_without_egypt']['decision']['e95_all_at_L_used']
assert r['adopted_share'] == adopted and r['p2_without_egypt_e95'] == e and r['adopted_share_robust_to_people_pattern'] == (abs(math.log(e / adopted)) <= math.log(1.25))
for n, v in r['variants'].items():
    if v['people_pattern'] != 'committed': assert abs(v['window_people'] - r['variants']['control']['window_people']) / r['variants']['control']['window_people'] < 1e-9, n
print('robustness and totals ok')
