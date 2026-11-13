"""Post-hoc diagnostics for the Earth supply calibration (not part of the declared decision rules).

1. The declared statistics with Egyptian cities left out of the score (they still draw grain).
2. The fantasy headline scenario at longer haul limits.
"""
import json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import settlement_supply_calibration as C
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_supply_calibration_20261113'

if __name__ == '__main__':
    z = np.load(OUT / 'calibration.npz'); x = np.load(C.PILOT.POOL)
    res, nodes, fed, west = z['residents'], z['nodes'], z['fed'], z['west']; shares = [float(v) for v in z['shares']]; limits = [int(v) for v in z['limits']]
    lon, lat = x['lon'].ravel()[nodes], x['lat'].ravel()[nodes]; egypt = (lon >= 29.0) & (lat <= 32.0)
    keep = ~egypt; table = {}
    for i, L in enumerate(limits):
        row = {}
        for name, mask in (('all', keep), ('west', keep & west), ('east', keep & ~west)):
            F = [float(fed[i, j][mask].sum() / res[mask].sum()) for j in range(len(shares))]; row[name] = dict(fed_share=F, e95=C.e95(shares, F))
        w, e = row['west']['e95'], row['east']['e95']; row['west_east_ratio'] = None if not (w and e) else float(w / e); table[str(L)] = row
    regions = {}
    j = shares.index(0.3333); i = limits.index(270)
    for name, m in (('Egypt', egypt), ('Levant and Syria', (lon >= 34) & (lat > 32) & (lat < 38)), ('Asia Minor', (lon > 26) & (lon < 34) & (lat >= 36)),
                    ('Greece and Balkans', (lon > 19) & (lon <= 26)), ('Italy', (lon > 7) & (lon <= 19) & (lat > 36)), ('North-west provinces', (lat > 43) & (lon <= 7))):
        regions[name] = dict(cities=int(m.sum()), residents=float(res[m].sum()), fed_share=float(fed[i, j][m].sum() / res[m].sum()))
    fantasy = {}
    if '--fantasy' in sys.argv:
        from polity import wide_supply as W
        import build_wide_supply_release3 as B
        from polity.release3_placement import install
        install(); original = W.delivered_share
        for L in (270.0, 400.0, 540.0):
            W.VALUE_LIMIT_ROAD_KM = L; W.delivered_share = lambda c, limit=L, f=original: f(c, limit)
            scratch = Path('/tmp/claude-0/fantasy_limit_%d' % L); scratch.mkdir(parents=True, exist_ok=True)
            s = B.build('corrected', scratch)['scenarios']['central_x33']
            fantasy[str(int(L))] = dict(fed_share_of_residents=s['fed_share_of_residents'], short_towns=s['short_towns'],
                self_sufficient_towns=s['self_sufficient_towns'], fed_with_imports_towns=s['fed_with_imports_towns'])
            print('fantasy', L, fantasy[str(int(L))], flush=True)
        W.delivered_share = original; W.VALUE_LIMIT_ROAD_KM = 270.0
    else:
        fantasy = json.loads((OUT / 'diagnostics.json').read_text())['fantasy_headline_by_haul_limit']
    write(OUT / 'diagnostics.json', dict(status='post_hoc_diagnostics_not_decision_rules', calibration_sha256=sha(OUT / 'results.json'),
        egypt_definition='city cells at longitude >= 29 E and latitude <= 32 N', egypt_cities=int(egypt.sum()), egypt_residents=float(res[egypt].sum()),
        without_egypt_in_score=table, regions_at_270_one_third=regions, fantasy_headline_by_haul_limit=fantasy, producer_sha256=sha(__file__)))
    for L, r in table.items(): print(L, 'e95 all/west/east', r['all']['e95'], r['west']['e95'], r['east']['e95'], 'ratio', r['west_east_ratio'], 'F(1/3)', round(r['all']['fed_share'][j], 3))
    print({k: (v['cities'], round(v['residents'] / 1e6, 2), round(v['fed_share'], 2)) for k, v in regions.items()})
