"""Review of the capital-term map build: the reviewed release-2 fantasy checks (scripts/review_settlement_release2_fantasy.py)
run on output/capital_term_map_20261115 with declared substitutions for M1C (capital term), plan A1 (no top-draw promotion)
and plan A2 (3-town permutation: full area multiset unchanged, at most that many unranked towns differ), plus the imperial
capital being the largest town."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
N = 'output/capital_term_map_20261115'
src = (ROOT / 'scripts/review_settlement_release2_fantasy.py').read_text()
SUBS = [("output/settlement_release2_20261113", N), ("output/settlement_release3_20261113", N + '/release3'), ("['models']['M1']", "['models']['M1C']"),
 ("    drawn = np.clip(np.exp(coef[0] + coef[1] * np.log(H) + sigma * e), lo, hi)",
  "    import csv as _c; _p = DATA / ('release3/hierarchy/corrected/hierarchy_links.csv' if mode == 'corrected' else 'release3/hierarchy/hierarchy_links.csv')\n"
  "    _s = {r['province_seat'] for r in _c.DictReader(open(_p, encoding='utf-8'))}\n"
  "    CAP = np.array([1.0 if (s['marked'] and s['name'] in _s) else 0.0 for s in sites]); assert int(CAP.sum()) == 19\n"
  "    drawn = np.clip(np.exp(coef[0] + coef[1] * np.log(H) + coef[2] * CAP + sigma * e), lo, hi)"),
 ("if (cls == a).any() and (cls > a).any() and e[cls == a].min() < e[cls > a].max(): problems.append(f'{mode} lore residual order {a}')", "pass"),
 ("    if not np.allclose(area[cls == 9], drawn[cls == 9], rtol=1e-9): problems.append(mode + ' unranked areas')",
  "    _top = int(np.isin(sym, ['imperial capital', 'major imperial city']).sum())\n"
  "    if (~np.isclose(area[cls == 9], drawn[cls == 9], rtol=1e-9)).sum() > _top: problems.append(mode + ' unranked areas')\n"
  "    if not np.allclose(np.sort(area), np.sort(drawn), rtol=1e-9): problems.append(mode + ' area multiset changed')\n"
  "    _c0 = np.flatnonzero(sym == 'imperial capital')\n"
  "    if len(_c0) != 1 or area[_c0[0]] < area.max(): problems.append(mode + ' imperial capital not the largest town')"),
 ("    if not np.allclose(np.sort(area[cls < 9]), np.sort(drawn[cls < 9]), rtol=1e-9): problems.append(mode + ' ranked area set changed')", "    pass")]
for old, new in SUBS:
    assert src.count(old) >= 1, old; src = src.replace(old, new)
sys.argv = [str(ROOT / 'scripts/review_settlement_release2_fantasy.py'), 'release3']
exec(compile(src, 'review_settlement_release2_fantasy.py', 'exec'), {'__name__': '__main__', '__file__': str(ROOT / 'scripts/review_settlement_release2_fantasy.py')})
