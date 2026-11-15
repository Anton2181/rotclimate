"""Settlement-hierarchy map step (calibration/settlement_hierarchy_map_20261115/plan.json): release-3 sizes rebuilt with M1C.

build_settlement_release2.build is executed with two literal substitutions (allow M1C; add coef[2] x capital to the mean);
the original script is not modified."""
import csv, json, sys, types
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from polity import settlement_sizes as Z
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_hierarchy_map_20261115'; FIT = ROOT / 'output/size_capital_term_20261115/results.json'
BASE = ROOT / 'output/sizes_greek_walls_20261114/results.json'; DATA = ROOT / 'atlases/earth_fit/data'


def seats(mode):
    with open(DATA / ('release3/hierarchy/corrected/hierarchy_links.csv' if mode == 'corrected' else 'release3/hierarchy/hierarchy_links.csv'), encoding='utf-8') as h:
        return sorted({r['province_seat'] for r in csv.DictReader(h)})


HIER = ROOT / 'output/settlement_hierarchy_20261115/results_soft.json'


def earth_results():
    base = json.loads(BASE.read_text()); h = json.loads(HIER.read_text())['full_fit']; prim = dict(base['sizes']['primary'])
    coef = h['m1_coefficients'] + [h['c']]
    prim['models'] = dict(prim['models'], M1C=dict(terms=['intercept', 'lnH', 'capital'], full_coefficients=coef, heldout_sigma=h['sigma'], hierarchy_phi=h['phi'], source='settlement_hierarchy A4 full fit'))
    prim['selected'] = 'M1C'; prim['gate'] = dict(prim['gate'], passed=True, hierarchy_heldout_gate=json.loads(HIER.read_text())['gate'])
    out = dict(base, sizes=dict(base['sizes'], primary=prim), status='release2_sizes_refit_greek_walls_settlement_hierarchy',
               hierarchy_source_sha256=sha(HIER), owner_decision='hierarchy model adopted on the owner request; held-out exceed share 0.8% vs 6.3% (limit 5 points) recorded as a narrow miss')
    OUT.mkdir(parents=True, exist_ok=True); write(OUT / 'earth_results.json', out); return out


def patched_build():
    src = (ROOT / 'scripts/build_settlement_release2.py').read_text()
    for old, new in [("if not size['gate']['passed'] or names != ('lnH',):", "if not size['gate']['passed'] or names not in (('lnH',), ('lnH', 'capital')):"),
                     ("mean = np.full(len(sites), np.nan); mean[valid] = coef[0] + coef[1] * np.log(H[valid])",
                      "mean = np.full(len(sites), np.nan); CAP = np.array([1.0 if (s['marked'] and s['name'] in CAPITAL_SEATS[mode]) else 0.0 for s in sites]); "
                      "mean[valid] = coef[0] + coef[1] * np.log(H[valid]) + (coef[2] * CAP[valid] if len(coef) == 3 else 0.0)"),
                     ("e = e_new; order = ranked", "order = ranked                                   # capital-term map plan A1: draws stay in site order"),
                     ("    area = np.where(valid, Z.generate_area(np.nan_to_num(mean), sigma, e, low_ha, high_ha), 0.0)",
                      "    # settlement hierarchy (calibration/settlement_hierarchy_map_20261115): each marked centre takes the largest residual of its own and half its cluster\n"
                      "    _rc = np.array([[s['row'], s['column']] for s in sites]); _mk = np.array([bool(s['marked']) for s in sites]); _M = np.flatnonzero(_mk & valid); _U = np.flatnonzero(~_mk & valid)\n"
                      "    _d = np.sqrt(((_rc[_U][:, None, :] - _rc[_M][None, :, :]) ** 2).sum(2)) * cell; _own = np.where(_d.min(1) <= 75.0, _M[_d.argmin(1)], -1)\n"
                      "    e = np.array(e, float); _rng = np.random.default_rng(2026)\n"
                      "    for _m in _M:\n"
                      "        _mem = _rng.permutation(_U[_own == _m]); _pool = np.r_[_m, _mem[:int(round(HIER_PHI * len(_mem)))]]\n"
                      "        _j = _pool[np.argmax(e[_pool])]; e[_m], e[_j] = e[_j], e[_m]\n"
                      "    HIER_STATS[mode] = dict(centres=int(len(_M)), assigned=int((_own >= 0).sum()))\n"
                      "    area = np.where(valid, Z.generate_area(np.nan_to_num(mean), sigma, e, low_ha, high_ha), 0.0)\n"
                      "    HIER_STATS[mode]['larger_than_centre'] = int(sum(1 for u, o in zip(_U, _own) if o >= 0 and area[u] > area[o]))"),
                     ("area[ranked] = np.sort(area[ranked])[::-1]",
                      "area[ranked] = np.sort(area[ranked])[::-1]\n"
                      "    top = [i for i in ranked if kind[i] in ('imperial capital', 'major imperial city')]; k = len(top)   # capital-term map plan A2\n"
                      "    if k:\n"
                      "        biggest = list(np.argsort(-area, kind='stable')[:k]); values = np.sort(area)[::-1][:k].copy()\n"
                      "        freed = sorted([area[i] for i in top if i not in biggest], reverse=True); holders = sorted(i for i in biggest if i not in top)\n"
                      "        area[top] = values\n"
                      "        for _hold, _val in zip(holders, freed): area[_hold] = _val")]:
        assert src.count(old) == 1, old; src = src.replace(old, new)
    mod = types.ModuleType('build_settlement_release2_m1c'); mod.__file__ = str(ROOT / 'scripts/build_settlement_release2.py')
    mod.CAPITAL_SEATS = {m: set(seats(m)) for m in ('raw', 'corrected')}; mod.HIER_STATS = {}
    mod.HIER_PHI = json.loads(HIER.read_text())['full_fit']['phi']
    exec(compile(src, 'build_settlement_release2.py', 'exec'), mod.__dict__); return mod


if __name__ == '__main__':
    Z.MODELS['M1C'] = ('lnH', 'capital'); earth_results()
    import build_settlement_release3 as B
    mod = patched_build(); B.build = mod.build; B.EARTH = OUT
    (OUT / 'results.json').write_bytes((OUT / 'earth_results.json').read_bytes())     # builder reads EARTH/results.json
    r = B.run(OUT / 'release3'); print('hierarchy', mod.HIER_STATS)
    for m, c in r['climates'].items():
        print(m, {k: (round(v['total']), round(v['largest'])) for k, v in c['residents'].items()}, c['area_quantiles_ha'])
