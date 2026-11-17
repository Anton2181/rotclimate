"""Exhaustive independent pairing/reduction check against archived scalar results."""
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/annual_assumption_impact_20261117'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def rows(p):
    with p.open() as f:
        return list(csv.DictReader(f))


def close(a, b):
    assert math.isclose(float(a), float(b), rel_tol=2e-12, abs_tol=2e-8), (a, b)


def main():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    receipt = read(OUT / 'results.json')
    for n, h in {**receipt['sources_sha256'], **receipt['protected_sha256']}.items():
        assert sha(ROOT / n) == h, n
    for n, h in receipt['files_sha256'].items():
        assert sha(OUT / n) == h, n
    for n in ['results.json', *receipt['files_sha256']]:
        assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    source = read(ROOT / 'output/urban_candidate_supply_20261116/results.json')
    factors = ['density', 'extraction', 'hours_worker_year']
    metrics = ['residents', 'coverage_percentage_points', 'rural_shortfall_person_years',
               'town_shortfall_person_years', 'short_towns']
    expected = {}
    for model, climate in itertools.product(['control', 'candidate'], ['raw', 'corrected']):
        for name, s in source['variants'][model]['climates'][climate]['scenarios'].items():
            d = source['diagnostics'][model][climate][name]
            v = {k: s[k] for k in factors}
            v.update(residents=s['residents'], coverage_percentage_points=s['residents_fed'] / s['residents'] * 100,
                     rural_shortfall_person_years=d['rural_food_shortfall_person_years'],
                     town_shortfall_person_years=s['residents'] - s['residents_fed'], short_towns=s['short_towns'])
            close(v['town_shortfall_person_years'], d['town_unfed_person_years'])
            expected[model, climate, name] = v
    exported = rows(OUT / 'cases.csv')
    assert len(exported) == len(expected) == 32
    assert {(r['model'], r['climate'], r['scenario']) for r in exported} == set(expected)
    values_checked = 0
    for r in exported:
        e = expected[r['model'], r['climate'], r['scenario']]
        assert r['density'] == e['density']
        for k in factors[1:] + metrics:
            close(r[k], e[k]); values_checked += 1
    combos = read(OUT / 'availability.json')
    extractions = sorted({e['extraction'] for e in expected.values()})
    required = set(itertools.product(['control', 'candidate'], ['raw', 'corrected'], ['low', 'central'], extractions, [300., 600.]))
    seen = set()
    for r in combos:
        key = tuple(r[k] for k in ['model', 'climate', *factors])
        assert key not in seen
        seen.add(key)
        present = [n for (m, c, n), e in expected.items() if m == r['model'] and c == r['climate'] and all(e[f] == r[f] for f in factors)]
        assert r['available'] == bool(present)
        assert r['scenario'] == (present[0] if present else None)
        if not present:
            assert r['hours_worker_year'] == 300 and r['extraction'] in extractions[:2]
    assert seen == required and len(combos) == 48
    # Enumerate Cartesian factor settings, rather than the producer's case-pair filter.
    allowed = {}
    for model, climate, factor in itertools.product(['control', 'candidate'], ['raw', 'corrected'], factors):
        settings = sorted({e[factor] for (m, c, _), e in expected.items() if (m, c) == (model, climate)},
                          key=(lambda x: ['low', 'central'].index(x)) if factor == 'density' else None)
        for lo, hi in itertools.combinations(settings, 2):
            for ka, ea in expected.items():
                if ka[:2] != (model, climate) or ea[factor] != lo:
                    continue
                for kb, eb in expected.items():
                    if kb[:2] == (model, climate) and eb[factor] == hi and all(ea[f] == eb[f] for f in factors if f != factor):
                        allowed[model, climate, factor, ka[2], kb[2]] = {k: math.fsum([eb[k], -ea[k]]) for k in metrics}
    contrasts = rows(OUT / 'contrasts.csv')
    keys = [(r['model'], r['climate'], r['factor'], r['from_scenario'], r['to_scenario']) for r in contrasts]
    assert len(keys) == len(set(keys)) == len(allowed) == 48 and set(keys) == set(allowed)
    for r, k in zip(contrasts, keys):
        for metric in metrics:
            close(r[metric + '_delta'], allowed[k][metric]); values_checked += 1
        for label, scenario in [('from', k[3]), ('to', k[4])]:
            value = expected[k[0], k[1], scenario][k[2]]
            if k[2] == 'density': assert r[label + '_value'] == value
            else: close(r[label + '_value'], value)
    ranking = rows(OUT / 'rankings.csv')
    assert len(ranking) == 60
    rank_keys = set()
    for r in ranking:
        m, c, f, metric = r['model'], r['climate'], r['factor'], r['outcome']
        rank_keys.add((m, c, metric, f))
        group = {k: v[metric] for k, v in allowed.items() if k[:3] == (m, c, f)}
        magnitudes = [abs(v) for v in group.values()]
        close(r['max_absolute_delta'], max(magnitudes)); close(r['median_absolute_delta'], statistics.median(magnitudes))
        assert int(r['pairs']) == len(group) == {'density': 4, 'extraction': 6, 'hours_worker_year': 2}[f]
        selected = (m, c, f, r['max_from'], r['max_to'])
        close(r['signed_max_delta'], group[selected]); close(abs(group[selected]), max(magnitudes))
        maxima = [max(abs(v[metric]) for k, v in allowed.items() if k[:3] == (m, c, ff)) for ff in factors]
        assert int(r['rank']) == 1 + sum(v > max(magnitudes) + 2e-8 for v in maxima)
    assert rank_keys == set(itertools.product(['control', 'candidate'], ['raw', 'corrected'], metrics, factors))
    hierarchy = read(ROOT / 'output/urban_hierarchy_candidate_20261116/results.json')
    for h in hierarchy['comparison']:
        for model, resident_key in [('candidate', 'candidate_allocated_residents'), ('control', 'legacy_residents')]:
            for (m, climate, name), e in expected.items():
                if (m, climate, e['density']) == (model, h['mode'], h['reading']):
                    close(e['residents'], h[resident_key])
                    s = source['variants'][m]['climates'][climate]['scenarios'][name]
                    close(math.fsum([s['residents'], s['rural_people']]), h['world_people'])
    result = dict(status='passed_exhaustive_archived_scalar_availability_pairing_and_ranking_review',
        results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(Path(__file__)), cases=32,
        availability_combinations=48, absent_combinations=16, matched_contrasts=48, ranking_rows=60,
        scalar_values_checked=values_checked, fresh_exports_byte_exact=True,
        scope='Independent scalar reduction and Cartesian pairing; archived food/work/freight calculations reused, not revalidated.',
        model_solver_calls=0, new_fit=False, adopt=False)
    (OUT / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
