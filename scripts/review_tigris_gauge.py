"""Independent review of the Tigris gauge step: regex parse, Decimal year means, scalar phase.

Imports neither the production parser, the year filter nor the phase primitive.
"""
import csv, hashlib, html, json, re, sys
from decimal import Decimal, localcontext
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/tigris_gauge_20261114'; CACHE = ROOT / 'data/cache/tigris_gauge_20261114'
OLDCACHE = ROOT / 'data/cache/flood_basin_seasonality_20261113'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
SECONDS = Decimal(365) / 12 * 86400


def parse(path):
    rows = []
    for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>', path.read_text(), re.S):
        cells = [html.unescape(re.sub('<[^>]+>', '', v)).strip() for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tr, re.S)]
        if cells and re.fullmatch(r'\d{4}-\d{2}-\d{2}', cells[0]): rows.append(cells)
    return rows


def years(rows, y0, y1):
    by = {}
    for day, value in rows: by.setdefault(int(day[:4]), []).append((int(day[5:7]), value))
    good = {}
    for y in range(y0, y1 + 1):
        data = by.get(y, [])
        try: ok = len(data) == 12 and len({m for m, _ in data}) == 12 and all(Decimal(v) >= 0 for _, v in data)
        except Exception: ok = False
        if ok: good[y] = [Decimal(v) for _, v in sorted(data)]
    return good


def phase(mean, crop, lead=3):
    top = max(mean); s = [v / top for v in mean] if top > 0 else [0.0] * 12; avg = sum(s) / 12
    ex = [max(v - avg, 0.0) for v in s]; tot = sum(ex); out = []
    for sow in range(12):
        pre = sum(ex[(sow - d) % 12] for d in range(1, lead + 1)) / tot if tot > 0 else 0.0
        dur = sum(ex[(sow + d) % 12] for d in range(crop)) / tot if tot > 0 else 0.0
        pre, dur = min(max(pre, 0.0), 1.0), min(max(dur, 0.0), 1.0); out.append((pre, dur, max(0.0, pre - dur)))
    return out


def main():
    r = json.loads((OUT / 'results.json').read_text()); plan = json.loads((ROOT / 'calibration/tigris_gauge_20261114/plan.json').read_text())
    for name, digest in {**r['sources'], **r['producers'], **r['unchanged_sha256']}.items(): assert sha(ROOT / name) == digest, name
    for name, digest in r['files_sha256'].items(): assert sha(OUT / name) == digest, name
    assert r['controls']['status'] == 'passed_before_outputs' and not r['field_runs'] and not r['adopt']
    z = np.load(OUT / 'fields.npz'); checks = 0; means = {}
    with localcontext() as ctx:
        ctx.prec = 40
        for spec in plan['sources']:
            key = spec['id']; row = next(v for v in r['rows'] if v['id'] == key); rows = parse(CACHE / f'{key}.html')
            assert len(rows) == row['source_rows'] and len({a for a, _ in rows}) == len(rows)
            good = years(rows, *spec['primary_years']); assert sorted(good) == row['complete_years'], key
            assert row['qualified'] == (len(good) >= 5)
            if not row['qualified']: continue
            mean = [sum(good[y][m] for y in good) / len(good) for m in range(12)]; means[key] = (good, mean)
            assert np.allclose([float(v) for v in mean], row['mean_monthly_flow_m3s'], rtol=1e-14)
            assert np.array_equal(z[key + '__monthly_flow'], np.array([[float(v) for v in good[y]] for y in sorted(good)]))
            excess = sum(max(v - sum(mean) / 12, 0) for v in mean) * SECONDS / Decimal(10) ** 9
            assert abs(float(excess) - row['positive_excess_km3']) < 1e-9, key
            assert row['peak_month'] == int(np.argmax([float(v) for v in mean])) + 1
            for p in row['phase']:
                ref = phase([float(v) for v in mean], p['crop_months'])
                for sow in range(12):
                    for j, n in enumerate(('pre_sowing_excess_share', 'standing_crop_excess_share', 'compatibility')):
                        assert abs(ref[sow][j] - p[n][sow]) < 1e-12; checks += 1
        hit = years(parse(OLDCACHE / 'hit.html'), 1932, 1972); assert sorted(hit) == r['comparison']['hit_own_years']['complete_years']
        common = sorted(set(hit) & set(means['mosul'][0])); assert common == r['comparison']['common_years']['years']
        both = [sum(hit[y][m] + means['mosul'][0][y][m] for y in common) / len(common) for m in range(12)]
        assert np.allclose([float(v) for v in both], z['hit_plus_mosul__common_mean_flow'], rtol=1e-14)
        excess = sum(max(v - sum(both) / 12, 0) for v in both) * SECONDS / Decimal(10) ** 9
        assert abs(float(excess) - r['comparison']['common_years']['hit_plus_mosul']['positive_excess_km3']) < 1e-9
    with (OUT / 'phase.csv').open() as f: assert sum(1 for _ in csv.DictReader(f)) == 7 * 12
    fresh = OUT / 'fresh'; exact = {}
    for name in ['results.json', 'fields.npz', 'phase.csv', 'gauge_monthly.csv', 'sources.json']:
        assert (fresh / name).read_bytes() == (OUT / name).read_bytes(), name; exact[name] = sha(OUT / name)
    (OUT / 'review.json').write_text(json.dumps(dict(status='passed', reviewer_sha256=sha(Path(__file__)), results_sha256=sha(OUT / 'results.json'),
        phase_values_checked=checks, fresh_byte_exact=exact,
        method='Regex HTML parse, Decimal 40-digit year means and excess volumes, scalar phase recomputation; production parser, filter and primitive not imported'), indent=1) + '\n')
    print('passed', checks, 'phase values')


if __name__ == '__main__':
    main()
