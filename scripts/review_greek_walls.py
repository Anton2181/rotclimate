"""Review of output/greek_walls_20261114: decisions rebuilt from stored surfaces (reviewed crossing code), inhabited
shares re-derived from the raw areas table, control within float tolerance of the Frier run, fresh replay."""
import csv, io, json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from review_egypt_sufficiency import crossing

OUT = ROOT / 'output/greek_walls_20261114'; r = json.loads((OUT / 'results.json').read_text())
assert r['plan_sha256'] == sha(ROOT / 'calibration/greek_walls_20261114/plan.json') and r['producer_sha256'] == sha(ROOT / 'scripts/greek_walls.py')
shares = json.loads((ROOT / 'calibration/settlement_supply_calibration_20261113/plan.json').read_text())['parameters']['marketed_share_e']
cache = ROOT / 'data/cache/roman_city_source_recovery_20261113'
areas = {row['Primary Key']: row for row in csv.DictReader(io.StringIO((cache / 'areas.csv').read_bytes().decode('utf-8-sig')))}
cities = [row for row in csv.DictReader(io.StringIO((cache / 'cities.csv').read_bytes().decode('cp1252')))
          if float(row['Start Date']) <= 150 and (row['End Date'].strip().upper() == 'NULL' or float(row['End Date']) >= 150)]
scope = {'greece': {'Achaea', 'Macedonia', 'Epirus'}, 'greece_and_asia_minor': {'Achaea', 'Macedonia', 'Epirus', 'Asia', 'Lycia et Pamphylia'}}
checks = 0; passing = []
for n, v in r['variants'].items():
    if v['scope']:
        expect = sorted((c['Ancient Toponym'], float(areas[c['Primary Key']]['Area'])) for c in cities if c['Primary Key'] in areas and c['Province'] in scope[v['scope']]
                        and areas[c['Primary Key']]['Estimate Basis'].startswith('Walls'))
        got = sorted((c['name'], c['walled_ha']) for c in v['changed']); assert expect == got, n
        for c in v['changed']: assert c['inhabited_share'] == (1 / 3 if c['walled_ha'] >= 100 else 1 / 2); checks += 1
    ratios = {}
    for L, row in v['surface'].items():
        for part in ('all', 'west', 'east'):
            e = crossing(shares, row[part]['fed_share']); assert (e is None and row[part]['e95'] is None) or abs(e - row[part]['e95']) < 1e-12; checks += 1
        w, e = row['west']['e95'], row['east']['e95']; ratios[L] = None if not (w and e) else abs(math.log(w / e))
    valid = {k: x for k, x in ratios.items() if x is not None}; best = min(valid, key=lambda k: (valid[k], float(k)))
    keep = '270' in valid and (valid['270'] <= math.log(1.25) or valid['270'] <= 1.1 * valid[best]); d = v['decision']
    assert d['cited_270_kept'] == keep and d['transferable'] == all(x is not None and x >= .9 for x in d['transfer'].values())
    if n != 'control' and keep and d['transferable']: passing.append(n)
assert passing == r['passing_variants']
ref = json.loads((ROOT / 'output/supply_people_level_20261114/results.json').read_text())['variants']['frier']['surface']
diff = max(abs(a - b) for L in ref for part in ('all', 'west', 'east') for a, b in zip(ref[L][part]['fed_share'], r['variants']['control']['surface'][L][part]['fed_share']))
assert diff < 1e-12
fresh = OUT / 'fresh/results.json'; exact = fresh.exists() and fresh.read_bytes() == (OUT / 'results.json').read_bytes()
write(OUT / 'review.json', dict(status='passed' if exact else 'passed_without_fresh_replay', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'),
    scalar_checks=checks, passing_variants=passing, control_max_abs_difference_from_frier_run=diff, control_note='not bit-identical: the people level is computed as p2 x 61.4e6 / total instead of p2 x (61.4e6 / total)', fresh_byte_exact=bool(exact)))
print('review', exact, checks, diff)
