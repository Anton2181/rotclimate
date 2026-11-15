"""Capital-term map step (calibration/capital_term_map_20261115/plan.json): release-3 sizes rebuilt with M1C.

build_settlement_release2.build is executed with two literal substitutions (allow M1C; add coef[2] x capital to the mean);
the original script is not modified."""
import csv, json, sys, types
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import settlement_sizes as Z
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/capital_term_map_20261115'; FIT = ROOT / 'output/size_capital_term_20261115/results.json'
BASE = ROOT / 'output/sizes_greek_walls_20261114/results.json'; DATA = ROOT / 'atlases/earth_fit/data'


def seats(mode):
    with open(DATA / ('release3/hierarchy/corrected/hierarchy_links.csv' if mode == 'corrected' else 'release3/hierarchy/hierarchy_links.csv'), encoding='utf-8') as h:
        return sorted({r['province_seat'] for r in csv.DictReader(h)})


def earth_results():
    base = json.loads(BASE.read_text()); m = json.loads(FIT.read_text())['models']['M1C']; prim = dict(base['sizes']['primary'])
    prim['models'] = dict(prim['models'], M1C=dict(terms=m['terms'], full_coefficients=m['full_coefficients'], heldout_sigma=m['heldout_sigma'], heldout_mae=m['heldout_mae']))
    prim['selected'] = 'M1C'; prim['gate'] = dict(prim['gate'], m1c_gate=m['gate'], passed=bool(m['gate']['passed']))
    out = dict(base, sizes=dict(base['sizes'], primary=prim), status='release2_sizes_refit_greek_walls_capital_term_owner_adopted',
               capital_term_source_sha256=sha(FIT), owner_decision='M1C adopted by the owner after the declared all-town rule was narrowly missed')
    OUT.mkdir(parents=True, exist_ok=True); write(OUT / 'earth_results.json', out); return out


def patched_build():
    src = (ROOT / 'scripts/build_settlement_release2.py').read_text()
    for old, new in [("if not size['gate']['passed'] or names != ('lnH',):", "if not size['gate']['passed'] or names not in (('lnH',), ('lnH', 'capital')):"),
                     ("mean = np.full(len(sites), np.nan); mean[valid] = coef[0] + coef[1] * np.log(H[valid])",
                      "mean = np.full(len(sites), np.nan); CAP = np.array([1.0 if (s['marked'] and s['name'] in CAPITAL_SEATS[mode]) else 0.0 for s in sites]); "
                      "mean[valid] = coef[0] + coef[1] * np.log(H[valid]) + (coef[2] * CAP[valid] if len(coef) == 3 else 0.0)"),
                     ("e = e_new; order = ranked", "order = ranked                                   # capital-term map plan A1: draws stay in site order"),
                     ("area[ranked] = np.sort(area[ranked])[::-1]",
                      "area[ranked] = np.sort(area[ranked])[::-1]\n"
                      "    top = [i for i in ranked if kind[i] in ('imperial capital', 'major imperial city')]; k = len(top)   # capital-term map plan A2\n"
                      "    if k:\n"
                      "        biggest = list(np.argsort(-area, kind='stable')[:k]); values = np.sort(area)[::-1][:k].copy()\n"
                      "        freed = sorted([area[i] for i in top if i not in biggest], reverse=True); holders = sorted(i for i in biggest if i not in top)\n"
                      "        area[top] = values\n"
                      "        for _hold, _val in zip(holders, freed): area[_hold] = _val"),
                     ("    x = dict(np.load(LEDGER / f'{mode}_inputs.npz'))",
                      "    # lore neighbourhood rule (owner, calibration/lore_neighbourhood_20261115): no proposed town larger than its nearest marked place within 75 km\n"
                      "    _rc = np.array([[s['row'], s['column']] for s in sites]); _mk = np.array([bool(s['marked']) for s in sites])\n"
                      "    _M = np.flatnonzero(_mk & valid); _U = np.flatnonzero(~_mk & valid)\n"
                      "    _d = np.sqrt(((_rc[_U][:, None, :] - _rc[_M][None, :, :]) ** 2).sum(2)) * cell\n"
                      "    _own = np.where(_d.min(1) <= 75.0, _M[_d.argmin(1)], -1); NEIGHBOUR_SWAPS[mode] = 0\n"
                      "    for _it in range(200):\n"
                      "        _changed = False\n"
                      "        for _m in _M:\n"
                      "            _nb = _U[_own == _m]\n"
                      "            if len(_nb) and area[_nb].max() > area[_m]:\n"
                      "                _u = _nb[np.argmax(area[_nb])]; area[_m], area[_u] = area[_u], area[_m]; _changed = True; NEIGHBOUR_SWAPS[mode] += 1\n"
                      "        area[ranked] = np.sort(area[ranked])[::-1]\n"
                      "        if k:\n"
                      "            biggest = list(np.argsort(-area, kind='stable')[:k]); values = np.sort(area)[::-1][:k].copy()\n"
                      "            freed = sorted([area[i] for i in top if i not in biggest], reverse=True); holders = sorted(i for i in biggest if i not in top)\n"
                      "            area[top] = values\n"
                      "            for _hold, _val in zip(holders, freed): area[_hold] = _val\n"
                      "        if not _changed and not any(len(_U[_own == _m]) and area[_U[_own == _m]].max() > area[_m] for _m in _M): break\n"
                      "    else:\n"
                      "        raise ValueError('lore neighbourhood rule did not converge')\n"
                      "    if any(len(_U[_own == _m]) and area[_U[_own == _m]].max() > area[_m] for _m in _M): raise ValueError('lore neighbourhood rule violated')\n"
                      "    x = dict(np.load(LEDGER / f'{mode}_inputs.npz'))")]:
        assert src.count(old) == 1, old; src = src.replace(old, new)
    mod = types.ModuleType('build_settlement_release2_m1c'); mod.__file__ = str(ROOT / 'scripts/build_settlement_release2.py')
    mod.CAPITAL_SEATS = {m: set(seats(m)) for m in ('raw', 'corrected')}; mod.NEIGHBOUR_SWAPS = {}
    exec(compile(src, 'build_settlement_release2.py', 'exec'), mod.__dict__); return mod


if __name__ == '__main__':
    Z.MODELS['M1C'] = ('lnH', 'capital'); earth_results()
    import build_settlement_release3 as B
    mod = patched_build(); B.build = mod.build; B.EARTH = OUT
    (OUT / 'results.json').write_bytes((OUT / 'earth_results.json').read_bytes())     # builder reads EARTH/results.json
    r = B.run(OUT / 'release3'); print('neighbour swaps', mod.NEIGHBOUR_SWAPS)
    for m, c in r['climates'].items():
        print(m, {k: (round(v['total']), round(v['largest'])) for k, v in c['residents'].items()}, c['area_quantiles_ha'])
