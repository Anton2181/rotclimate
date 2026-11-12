"""Protect geographic holdout, missing targets and density-unit invariants."""
from copy import deepcopy
import numpy as np
import pytest
from polity.housing_diagnostic import fit_predict, province_folds


def observations():
    return [dict(city_key=str(i), province='ABC'[i % 3], site_area_ha=float(i + 5),
                 sample_area_ha=float((i % 4 + 1) / 10), properties=i + 2) for i in range(18)]


@pytest.mark.parametrize('model', ['constant', 'area', 'area_coverage'])
def test_held_out_properties_are_never_used_to_fit_or_predict(model):
    rows = observations(); training, test = rows[:12], deepcopy(rows[12:])
    coefficients, prediction = fit_predict(training, test, model)
    for r in test:
        del r['properties']
    other_coefficients, other_prediction = fit_predict(training, test, model)
    np.testing.assert_array_equal(other_coefficients, coefficients)
    np.testing.assert_array_equal(other_prediction, prediction)


def test_province_blocking_excludes_every_held_out_city_and_refuses_small_cohorts():
    rows = observations(); folds = province_folds(rows)
    assert sorted(i for _, _, test in folds for i in test) == list(range(len(rows)))
    for province, train, test in folds:
        assert {rows[i]['province'] for i in test} == {province}
        assert province not in {rows[i]['province'] for i in train}
        assert set(train).isdisjoint(test)
    with pytest.raises(ValueError, match='training cities'):
        province_folds(rows[:12])


def test_rank_deficient_coverage_does_not_silently_produce_a_fit():
    rows = observations()
    for r in rows:
        r['sample_area_ha'] = r['site_area_ha'] / 10
    with pytest.raises(ValueError, match='Rank-deficient'):
        fit_predict(rows, rows, 'area_coverage')


def test_household_scenarios_change_units_and_never_create_additional_targets():
    rows = observations()
    _, base = fit_predict(rows[:12], rows[12:], 'area_coverage')
    _, shifted = fit_predict(rows[:12], rows[12:], 'area_coverage', household=5)
    np.testing.assert_allclose(shifted, base + np.log(5), rtol=0, atol=1e-12)
    assert len(base) == len(rows[12:])
