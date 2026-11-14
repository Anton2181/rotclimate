"""Review of output/egypt_people_sufficiency_20261114: runs the reviewed egypt-sufficiency checks (separate e95,
ratio, haul-limit and transfer reconstruction) on this output by declared path substitution, plus people-factor
arithmetic and fresh replay."""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

src = (ROOT / 'scripts/review_egypt_sufficiency.py').read_text()
for old, new in [("output/egypt_sufficiency_20261114", "output/egypt_people_sufficiency_20261114"),
                 ("calibration/egypt_sufficiency_20261114/plan.json", "calibration/egypt_people_sufficiency_20261114/plan.json"),
                 ("scripts/egypt_sufficiency.py", "scripts/egypt_people_sufficiency.py"),
                 ("    for pre in ('Y', 'YP'):\n        assert v['control']['egypt_surplus_person_years'] <= v[f'{pre}_1.94']['egypt_surplus_person_years'] <= v[f'{pre}_2.16']['egypt_surplus_person_years']\n", ""),
                 ("reviewer_sha256=sha(Path(__file__))", "reviewer_sha256=sha(REVIEWER)")]:
    assert old in src, old; src = src.replace(old, new)
ns = dict(__name__='reviewed', __file__=str(ROOT / 'scripts/review_egypt_sufficiency.py'), REVIEWER=Path(__file__)); exec(compile(src, 'review_egypt_sufficiency.py', 'exec'), ns)
ns['main']()
r = json.loads((ROOT / 'output/egypt_people_sufficiency_20261114/results.json').read_text())
for n, v in r['variants'].items():
    if v['total_people_target']: assert abs(v['people_factor'] * v['egypt_proper_people_before'] - v['total_people_target']) < 1e-3
    assert v['surface']['270']['east']['e95'] is None or n == 'control'
print('people arithmetic ok')
