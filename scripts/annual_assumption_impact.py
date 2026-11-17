"""Reduce reviewed annual cases into matched one-input sensitivities; no solver."""
import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/annual_assumption_impact_20261117'
SUPPLY = ROOT / 'output/urban_candidate_supply_20261116'
PARENT = ROOT / 'output/levant_spatial_diagnostic_20261117'
PLANS = ['calibration/roman_benchmark_20261117/annual_assumption_impact.json',
         'calibration/roman_benchmark_20261117/annual_impact_reduction.json']
FACTORS = ['density', 'extraction', 'hours_worker_year']
OUTCOMES = ['residents', 'coverage_percentage_points', 'rural_shortfall_person_years',
            'town_shortfall_person_years', 'short_towns']


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def table(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main(out):
    assert not (out / 'results.json').exists(), 'Use a fresh --out directory'
    q = read(PARENT / 'qualification.json')
    protected = {**q['protected_sha256'], **q['sources_sha256']}
    protected.update({str((PARENT / n).relative_to(ROOT)): d for n, d in q['files_sha256'].items()})
    protected[str((PARENT / 'qualification.json').relative_to(ROOT))] = sha(PARENT / 'qualification.json')
    for n, d in protected.items():
        assert sha(ROOT / n) == d, n
    sources = {n: sha(ROOT / n) for n in PLANS + ['scripts/annual_assumption_impact.py']}
    for folder in [SUPPLY, ROOT / 'output/urban_hierarchy_candidate_20261116']:
        review = read(folder / 'review.json')
        assert review['status'] == 'passed'
        assert sha(folder / 'results.json') == review['results_sha256']
        for name in ['results.json', 'review.json']:
            p = folder / name
            sources[str(p.relative_to(ROOT))] = sha(p)
    d = read(SUPPLY / 'results.json')
    cases = []
    for model in ['candidate', 'control']:
        for climate in ['raw', 'corrected']:
            scenarios = d['variants'][model]['climates'][climate]['scenarios']
            for name, s in sorted(scenarios.items()):
                diag = d['diagnostics'][model][climate][name]
                cases.append(dict(model=model, climate=climate, scenario=name,
                    **{k: s[k] for k in FACTORS}, residents=s['residents'],
                    coverage_percentage_points=100 * s['fed_share_of_residents'],
                    rural_shortfall_person_years=diag['rural_food_shortfall_person_years'],
                    town_shortfall_person_years=diag['town_unfed_person_years'], short_towns=s['short_towns']))
    availability = []
    extractions = sorted({c['extraction'] for c in cases})
    for model, climate, density, extraction, hours in itertools.product(
            ['candidate', 'control'], ['raw', 'corrected'], ['low', 'central'], extractions, [300., 600.]):
        found = [c for c in cases if (c['model'], c['climate'], c['density'], c['extraction'], c['hours_worker_year']) ==
                 (model, climate, density, extraction, hours)]
        assert len(found) <= 1
        availability.append(dict(model=model, climate=climate, density=density, extraction=extraction,
            hours_worker_year=hours, available=bool(found), scenario=found[0]['scenario'] if found else None))
    pairs = []
    for a, b in itertools.combinations(cases, 2):
        if (a['model'], a['climate']) != (b['model'], b['climate']):
            continue
        changed = [f for f in FACTORS if a[f] != b[f]]
        if len(changed) != 1:
            continue
        factor = changed[0]
        if (factor == 'density' and a[factor] == 'central') or (factor != 'density' and a[factor] > b[factor]):
            a, b = b, a
        pairs.append(dict(model=a['model'], climate=a['climate'], factor=factor,
            from_scenario=a['scenario'], to_scenario=b['scenario'],
            from_value=a[factor], to_value=b[factor],
            **{k + '_delta': b[k] - a[k] for k in OUTCOMES}))
    ranks = []
    for model, climate, outcome in itertools.product(['candidate', 'control'], ['raw', 'corrected'], OUTCOMES):
        local = []
        for factor in FACTORS:
            rows = [p for p in pairs if (p['model'], p['climate'], p['factor']) == (model, climate, factor)]
            largest = max(rows, key=lambda p: abs(p[outcome + '_delta']))
            values = [abs(p[outcome + '_delta']) for p in rows]
            local.append(dict(model=model, climate=climate, outcome=outcome, factor=factor,
                max_absolute_delta=max(values), median_absolute_delta=statistics.median(values),
                pairs=len(rows), max_from=largest['from_scenario'], max_to=largest['to_scenario'],
                signed_max_delta=largest[outcome + '_delta']))
        for row in local:
            row['rank'] = 1 + sum(r['max_absolute_delta'] > row['max_absolute_delta'] for r in local)
        ranks.extend(sorted(local, key=lambda r: (r['rank'], r['factor'])))
    assert len(cases) == 32 and len(pairs) == 48 and len(ranks) == 60
    assert len(availability) == 48 and sum(a['available'] for a in availability) == 32
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in [('cases.csv', cases), ('contrasts.csv', pairs), ('rankings.csv', ranks)]:
        table(out / name, rows)
    write(out / 'availability.json', availability)
    write(out / 'results.json', dict(status='completed_existing_annual_one_input_sensitivity_not_empirical_uncertainty',
        sources_sha256=sources, protected_sha256=protected,
        files_sha256={n: sha(out / n) for n in ['cases.csv', 'contrasts.csv', 'rankings.csv', 'availability.json']},
        cases=len(cases), contrasts=len(pairs), ranking_rows=len(ranks), missing_combinations=16,
        primary_model='candidate', secondary_model='control', climate_paired=False,
        model_solver_calls=0, new_fit=False, new_validation_claim=False, main_atlas_changed=False, adopt=False))
    print(f'{len(cases)} archived cases, {len(pairs)} one-input contrasts; no model runs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
