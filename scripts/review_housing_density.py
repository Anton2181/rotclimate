"""Independent scalar review of every blocked housing prediction and metric."""
import csv
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_housing_diagnostic_20261112'


def close(actual, expected):
    if not math.isclose(actual, expected, rel_tol=2e-11, abs_tol=2e-11):
        raise ValueError(f'Independent scalar difference: {actual} != {expected}')


def features(r, model):
    if model == 'constant':
        return []
    values = [math.log(float(r['site_area_ha']))]
    if model == 'area_coverage':
        values.append(math.log(float(r['sample_area_ha']) / float(r['site_area_ha'])))
    return values


def scalar_fit(rows, model):
    """Explicit centered normal equations, no numpy, lstsq or producer import."""
    x = [features(r, model) for r in rows]
    y = [math.log(int(r['properties'])) - math.log(float(r['sample_area_ha'])) for r in rows]
    mean_y = statistics.mean(y)
    width = len(x[0])
    if not width:
        return [mean_y]
    means = [statistics.mean(v[j] for v in x) for j in range(width)]
    centered = [[v - m for v, m in zip(row, means)] for row in x]
    sums = [[math.fsum(v[i] * v[j] for v in centered) for j in range(width)] for i in range(width)]
    cov = [math.fsum(v[j] * (value - mean_y) for v, value in zip(centered, y)) for j in range(width)]
    if width == 1:
        slopes = [cov[0] / sums[0][0]]
    else:
        a, b, d = sums[0][0], sums[0][1], sums[1][1]
        determinant = a * d - b * b
        if determinant <= 0:
            raise ValueError('Scalar design singular')
        slopes = [(cov[0] * d - cov[1] * b) / determinant,
                  (cov[1] * a - cov[0] * b) / determinant]
    return [mean_y - math.fsum(v * m for v, m in zip(slopes, means))] + slopes


def main():
    result = json.loads((OUT / 'results.json').read_text())
    plan = json.loads((ROOT / 'calibration/settlement_housing_diagnostic_20261112/plan.json').read_text())
    assert result['adopt'] is False and result['prospective_transfer'] is False
    assert result['AD150_size_fit_eligible'] == 0 and not result['catalogue_join_certified']
    for path, digest in {**result['sources_sha256'], **result['unchanged_sha256']}.items():
        assert sha(ROOT / path) == digest, path
    with (ROOT / plan['sources']['table']).open() as f:
        raw = list(csv.DictReader(f))
    source = {r['city_key']: r for r in raw}
    assert len(raw) == len(source) == len(result['source_rows']) == 50
    prepared = json.loads((ROOT / plan['sources']['prepared']).read_text())
    gates = {r['city_key']: r for r in prepared['rows']}
    for r in result['source_rows']:
        original = source[r['city_key']]
        for key in ('ancient_name', 'province', 'footnote'):
            assert r[key] == original[key]
        for key in ('site_area_ha', 'sample_area_ha', 'properties'):
            close(r[key], float(original[key]))
        close(r['sample_fraction'], float(original['sample_area_ha']) / float(original['site_area_ha']))
        assert r['AD150_blockers'] == gates[r['city_key']]['AD150_blockers']
        assert r['AD150_size_fit_eligible'] is False
    predictions_checked = coefficients_checked = folds_checked = household_checks = 0
    unscored = []
    assert len(result['cohorts']) == len(plan['cohorts'])
    for cohort, spec in zip(result['cohorts'], plan['cohorts']):
        assert cohort['id'] == spec['id']
        selected = [r for r in raw if float(r['sample_area_ha']) / float(r['site_area_ha']) >= spec['minimum_sample_fraction']]
        assert cohort['city_keys'] == [r['city_key'] for r in selected]
        groups = sorted({r['province'] for r in selected})
        assert cohort['cities'] == len(selected) and cohort['provinces'] == len(groups)
        too_small = len(groups) < 3 or any(sum(r['province'] != g for r in selected) < 10 for g in groups)
        if too_small:
            assert cohort['status'] == 'unscored' and 'reason' in cohort and 'models' not in cohort
            unscored.append(cohort['id'])
            continue
        assert [m['id'] for m in cohort['models']] == ['constant', 'area', 'area_coverage']
        baseline = {}
        for model in cohort['models']:
            name = model['id']; predictions = {p['city_key']: p for p in model['predictions']}
            assert len(predictions) == len(model['predictions']) == len(selected)
            assert set(predictions) == {r['city_key'] for r in selected}
            independent_errors = []; by_group = {}; all_coefficients = []
            assert [f['province'] for f in model['folds']] == groups
            for group, fold in zip(groups, model['folds']):
                train = [r for r in selected if r['province'] != group]
                test = [r for r in selected if r['province'] == group]
                assert fold['training_keys'] == [r['city_key'] for r in train]
                assert fold['test_keys'] == [r['city_key'] for r in test]
                coefs = scalar_fit(train, name); all_coefficients.append(coefs)
                assert len(fold['coefficients']) == len(coefs)
                for actual, expected in zip(fold['coefficients'], coefs):
                    close(actual, expected); coefficients_checked += 1
                errors = []
                for r in test:
                    expected = coefs[0] + math.fsum(c * v for c, v in zip(coefs[1:], features(r, name)))
                    observed = math.log(int(r['properties'])) - math.log(float(r['sample_area_ha']))
                    p = predictions[r['city_key']]
                    assert p['province'] == group
                    close(p['observed_log_property_density'], observed)
                    close(p['predicted_log_property_density'], expected)
                    close(p['log_error'], expected - observed)
                    close(p['conditional_predicted_people_at5'], math.exp(expected) * float(r['site_area_ha']) * 5)
                    errors.append(expected - observed); predictions_checked += 1
                    for household in (3, 5, 7):
                        shifted_coefficients = [coefs[0] + math.log(household)] + coefs[1:]
                        shifted = shifted_coefficients[0] + math.fsum(c * v for c, v in zip(shifted_coefficients[1:], features(r, name)))
                        close(shifted - (observed + math.log(household)), expected - observed)
                        household_checks += 1
                mae = statistics.mean(map(abs, errors)); by_group[group] = mae
                close(fold['mean_absolute_log_error'], mae)
                independent_errors.extend(errors); folds_checked += 1
            expected_metrics = dict(mean_absolute_log_error=statistics.mean(map(abs, independent_errors)),
                root_mean_square_log_error=math.sqrt(statistics.mean(e * e for e in independent_errors)),
                median_multiplicative_error=math.exp(statistics.median(map(abs, independent_errors))),
                equal_province_mean_absolute_log_error=statistics.mean(by_group.values()))
            assert set(model['metrics']) == set(expected_metrics)
            for key, expected in expected_metrics.items():
                close(model['metrics'][key], expected)
            descriptive = scalar_fit(selected, name)
            for actual, expected in zip(model['descriptive_all_city_coefficients'], descriptive):
                close(actual, expected)
            for j in range(len(descriptive)):
                close(model['fold_coefficient_min'][j], min(c[j] for c in all_coefficients))
                close(model['fold_coefficient_max'][j], max(c[j] for c in all_coefficients))
            if name == 'constant':
                baseline = by_group
            assert [d['province'] for d in model['province_error_difference_vs_constant']] == groups
            for d in model['province_error_difference_vs_constant']:
                close(d['mean_absolute_log_error_difference'], by_group[d['province']] - baseline[d['province']])
            assert 0 <= model['maximum_household_log_error_difference'] < 1e-12
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'),
        reviewer_sha256=sha(Path(__file__)), scalar_normal_equations=True, no_producer_import=True,
        source_rows_checked=50, held_province_predictions_checked=predictions_checked,
        training_coefficients_checked=coefficients_checked, held_province_folds_checked=folds_checked,
        household_unit_checks=household_checks, unscored_cohorts=unscored,
        prior_phase_gates_and_atlas_model_bytes_unchanged=True,
        scope='Independent numerical/source/group review; not independent archaeological or prospective validation.'))
    print('Scalar review passed:', predictions_checked, 'predictions;', folds_checked, 'folds;', household_checks, 'household checks')


if __name__ == '__main__':
    main()
