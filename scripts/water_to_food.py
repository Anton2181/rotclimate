"""First declared water-to-food translation and the Nile/Mesopotamia pass rule (calibration/water_to_food_20261114/plan.json)."""
import argparse, csv, io, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from land_people import CROPS, FARMED_SHARE, NEED_KCAL
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/water_to_food_20261114/plan.json'; OUT = ROOT / 'output/water_to_food_20261114'
BASE = ROOT / 'output/base_flow_20261114'; GEOM = ROOT / 'output/flood_basin_storage_20261114/fields.npz'; EARTH = ROOT / 'output/land_people/earth/earth.npz'
M = 'mesopotamia_euphrates_only'; SOWN = (0.6, 1.0); NILE_MIN, MESO_MAX = 0.8 * 4.5e6, 1.25 * 2.0e6


def e_full():
    c = CROPS['barley']; return c['grain'] * 1000.0 * c['edible'] * c['kcal'] * (1 - c['seed'])


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    base = json.loads((BASE / 'results.json').read_text()); review = json.loads((BASE / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(BASE / 'results.json')
    E = e_full(); assert abs(E - 2710224.0) < 1e-6
    g = np.load(GEOM); earth = np.load(EARTH); arable = np.nan_to_num(earth['arable']).astype(float)
    geo = {r: dict(area=g[r + '__area_km2'], arable=arable[g[r + '__row'], g[r + '__col']]) for r in ('nile', M)}
    z = np.load(BASE / 'fields.npz'); rows = []; perfield = {}
    for row in base['rows']:
        region = row['region']; cov = z[row['case'] + '__root_coverage']; ok = z[row['case'] + '__eligible']; a = geo[region]
        unit = a['area'] * 100.0 * E * a['arable'] * FARMED_SHARE / NEED_KCAL          # people per field if fully watered, before sown factor
        for sown in SOWN:
            people = np.where(ok, cov * unit * sown, 0.0); ceiling = float(np.where(ok, unit * sown, 0.0).sum())
            rows.append(dict(region=region, source_rule=row['source_rule'], calendar=row['calendar'], method=row['method'], sown=sown,
                             supported_people=float(people.sum()), ceiling_people=ceiling, root_coverage=row['root_coverage'], case=row['case']))
            perfield[f"{row['case']}__sown{sown:g}"] = people
    pairs = []
    for rule in ('flood_excess', '0.10', '0.25', '0.50'):
        for cal in ('old', 'fractional'):
            for meth in ('hargreaves', 'penman_monteith'):
                for sown in SOWN:
                    pick = lambda region: next(x for x in rows if x['region'] == region and x['source_rule'] == rule and x['calendar'] == cal and x['method'] == meth and x['sown'] == sown)
                    n, m = pick('nile')['supported_people'], pick(M)['supported_people']
                    pairs.append(dict(source_rule=rule, calendar=cal, method=meth, sown=sown, egypt_people=n, mesopotamia_people=m,
                                      nile_gain=n >= NILE_MIN, mesopotamia_not_inflated=m <= MESO_MAX, passes=bool(n >= NILE_MIN and m <= MESO_MAX)))
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', **perfield)
    b = io.StringIO(newline=''); w = csv.DictWriter(b, fieldnames=list(pairs[0]), lineterminator='\n'); w.writeheader(); w.writerows(pairs); (out / 'pairs.csv').write_text(b.getvalue())
    ceilings = {f'{r}__sown{s:g}': next(x['ceiling_people'] for x in rows if x['region'] == r and x['sown'] == s) for r in ('nile', M) for s in SOWN}
    write(out / 'results.json', dict(status='water_to_food_development_test', adopt=False, e_full_kcal_ha=E, farmed_share=FARMED_SHARE, need_kcal=NEED_KCAL,
        thresholds=dict(egypt_min=NILE_MIN, mesopotamia_max=MESO_MAX), rows=rows, pairs=pairs, ceilings=ceilings,
        passing_pairs=sum(p['passes'] for p in pairs), nile_gain_pairs=sum(p['nile_gain'] for p in pairs), non_inflated_pairs=sum(p['mesopotamia_not_inflated'] for p in pairs),
        sources={str(p.relative_to(ROOT)): sha(p) for p in (BASE / 'results.json', BASE / 'fields.npz', GEOM, EARTH)},
        producers={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), PLAN, ROOT / 'scripts/land_people.py')},
        files_sha256={n: sha(out / n) for n in ('fields.npz', 'pairs.csv')}))
    print('ceilings M', {k: round(v / 1e6, 2) for k, v in ceilings.items()}); print('passing', sum(p['passes'] for p in pairs), '/', len(pairs), 'nile gain', sum(p['nile_gain'] for p in pairs), 'non-inflated', sum(p['mesopotamia_not_inflated'] for p in pairs))
    for p in pairs:
        if p['calendar'] == 'old': print(p['source_rule'], p['method'][:4], p['sown'], round(p['egypt_people'] / 1e6, 2), round(p['mesopotamia_people'] / 1e6, 2), p['passes'])


if __name__ == '__main__':
    a = argparse.ArgumentParser(); a.add_argument('--out', type=Path, default=OUT); main(a.parse_args().out)
