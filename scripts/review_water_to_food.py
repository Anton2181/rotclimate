"""Independent review of the water-to-food test: Fraction-based constant, explicit loops, pass rule re-applied."""
import csv, hashlib, json, sys
from fractions import Fraction
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/water_to_food_20261114'; M = 'mesopotamia_euphrates_only'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    r = json.loads((OUT / 'results.json').read_text()); plan = json.loads((ROOT / 'calibration/water_to_food_20261114/plan.json').read_text())
    for name, digest in {**r['sources'], **r['producers']}.items(): assert sha(ROOT / name) == digest, name
    for name, digest in r['files_sha256'].items(): assert sha(OUT / name) == digest, name
    E = Fraction(1) * 1000 * Fraction('0.87') * 3540 * (1 - Fraction('0.12')); assert E == 2710224 and r['e_full_kcal_ha'] == float(E)
    assert '2,710,224' in plan['translation']
    g = dict(np.load(ROOT / 'output/flood_basin_storage_20261114/fields.npz')); arable_grid = np.load(ROOT / 'output/land_people/earth/earth.npz')['arable']
    z = dict(np.load(ROOT / 'output/base_flow_20261114/fields.npz')); base = json.loads((ROOT / 'output/base_flow_20261114/results.json').read_text())
    per = float(100 * E * Fraction('0.6') / Fraction(1100000)); worst = 0.; mine = {}
    for row in base['rows']:
        region = row['region']; area = g[region + '__area_km2']; rr, cc = g[region + '__row'], g[region + '__col']
        cov = z[row['case'] + '__root_coverage']; ok = z[row['case'] + '__eligible']
        for sown in (0.6, 1.0):
            total = 0.; ceiling = 0.
            for i in range(len(area)):
                a = float(arable_grid[rr[i], cc[i]]); a = 0. if a != a else a
                if ok[i]: total += float(cov[i]) * float(area[i]) * a * per * sown; ceiling += float(area[i]) * a * per * sown
            got = next(x for x in r['rows'] if x['case'] == row['case'] and x['sown'] == sown)
            worst = max(worst, abs(got['supported_people'] - total) / max(total, 1), abs(got['ceiling_people'] - ceiling) / max(ceiling, 1))
            mine[(region, row['source_rule'], row['calendar'], row['method'], sown)] = total
    assert worst < 1e-9, worst
    with (OUT / 'pairs.csv').open() as f: pairs = list(csv.DictReader(f))
    assert len(pairs) == 32
    for p in pairs:
        key = (p['source_rule'], p['calendar'], p['method'], float(p['sown'])); n, m = mine[('nile',) + key], mine[(M,) + key]
        assert abs(float(p['egypt_people']) - n) <= 1e-6 * n and abs(float(p['mesopotamia_people']) - m) <= 1e-6 * max(m, 1)
        assert (p['passes'] == 'True') == (n >= 0.8 * 4.5e6 and m <= 1.25 * 2.0e6)
    assert r['passing_pairs'] == sum(p['passes'] == 'True' for p in pairs)
    fresh = OUT / 'fresh'; exact = {}
    for name in ('results.json', 'fields.npz', 'pairs.csv'):
        assert (fresh / name).read_bytes() == (OUT / name).read_bytes(), name; exact[name] = sha(OUT / name)
    (OUT / 'review.json').write_text(json.dumps(dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'),
        max_relative_difference=worst, fresh_byte_exact=exact, method='Exact Fraction constant, per-field scalar loops over all 64 base-flow runs x 2 sown values, pass rule re-applied; producer not imported'), indent=1) + '\n')
    print('passed; max relative difference', worst)


if __name__ == '__main__':
    main()
