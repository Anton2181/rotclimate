"""Seal the reviewed reduction and unchanged scientific/publication inputs."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/annual_assumption_impact_20261117'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    assert not (OUT / 'qualification.json').exists()
    read = lambda p: json.loads(p.read_text())
    r = read(OUT / 'results.json'); review = read(OUT / 'review.json'); p = read(OUT / 'presentation.json')
    assert review['status'] == 'passed_exhaustive_archived_scalar_availability_pairing_and_ranking_review'
    assert review['results_sha256'] == p['results_sha256'] == sha(OUT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_annual_assumption_impact.py')
    assert p['review_sha256'] == sha(OUT / 'review.json')
    assert p['renderer_sha256'] == sha(ROOT / 'scripts/render_annual_assumption_impact.py')
    assert p['figure_sha256'] == sha(OUT / 'assumption_impacts.png')
    for n, h in {**r['sources_sha256'], **r['protected_sha256']}.items():
        assert sha(ROOT / n) == h, n
    for n, h in r['files_sha256'].items():
        assert sha(OUT / n) == h, n
    for n in ['results.json', *r['files_sha256']]:
        assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    with (OUT / 'rankings.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert len(p['plotted_values']) == 18
    expected = {(r['climate'], r['outcome'], r['factor']): float(r['max_absolute_delta'])
                for r in rows if r['model'] == 'candidate' and r['outcome'] in
                ['residents', 'coverage_percentage_points', 'rural_shortfall_person_years']}
    actual = {(v['climate'], v['outcome'], v['factor']): v['absolute_delta'] for v in p['plotted_values']}
    assert actual == expected
    # No outcome-unit pooling and no reliance on climate/cohort cross-pairs.
    for metric in {r['outcome'] for r in rows}:
        orders = [[(r['factor'], r['rank']) for r in rows if (r['model'], r['climate'], r['outcome']) == (m, c, metric)]
                  for m in ['candidate', 'control'] for c in ['raw', 'corrected']]
        assert all(order == orders[0] for order in orders)
    sources = dict(r['sources_sha256'])
    next_plan = 'calibration/roman_benchmark_20261117/karanis_density_feasibility.json'
    notes = ['reports/GREEK_WALLS_20261114.md', 'reports/FARM_LABOUR_20261103.md',
             'research_notes/farm_labour_20261103.json', 'reports/SETTLEMENT_HOUSING_DIAGNOSTIC_20261112.md',
             'reports/WAREHOUSE_WORK_READINESS_20261117.md', 'reports/ROMAN_BENCHMARK_20261117.md',
             'reports/LEVANT_SPATIAL_DIAGNOSTIC_20261117.md', 'reports/ANNUAL_ASSUMPTION_IMPACT_20261117.md',
             'scripts/review_annual_assumption_impact.py', 'scripts/render_annual_assumption_impact.py',
             'scripts/seal_annual_assumption_impact.py', next_plan]
    sources.update({n: sha(ROOT / n) for n in notes})
    files = ['results.json', 'review.json', 'presentation.json', 'assumption_impacts.png', *r['files_sha256']]
    result = dict(status='passed_existing_annual_matched_sensitivity_not_empirical_uncertainty',
        sources_sha256=sources, protected_sha256=r['protected_sha256'],
        files_sha256={n: sha(OUT / n) for n in sorted(set(files))},
        cases=32, contrasts=48, missing_combinations=16, ranking_rows=60, plotted_values_reviewed=18,
        fresh_exports_byte_exact=True, figure_visually_inspected=True, control_factor_orders_agree=True,
        empirical_uncertainty_qualified=False, period_density_qualified=False, seasonal_food_work_qualified=False,
        model_solver_calls=0, new_fit=False, new_validation_claim=False, main_atlas_changed=False, adopt=False,
        next_plan=next_plan)
    (OUT / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Sealed matched sensitivities; population density and agricultural budget prioritized')


if __name__ == '__main__':
    main()
