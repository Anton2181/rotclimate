"""Signed ascent, nonlinear clipping, and paired forcing controls."""
from dataclasses import replace
import numpy as np
import pytest
from scripts import audit_v10_storm_ascent as audit
from tests.test_v10_split_column import five_fixture


def test_equal_storm_increment_can_have_different_positive_ascent_response():
    uniform = audit.ascent_statistics(np.array([1., 1.]), np.array([2., 0.]))
    descending = audit.ascent_statistics(np.array([-2., -2.]), np.array([-1., -3.]))
    assert uniform['storm_positive_component_pa_s'] == descending['storm_positive_component_pa_s'] == .5
    assert uniform['actual_positive_only_pa_s'] == 1.
    assert descending['actual_positive_only_pa_s'] == 0.
    assert uniform['storm_signed_pa_s'] == 0.


def test_signed_positive_only_and_reversal_fraction_are_distinct():
    row = audit.ascent_statistics(np.array([-2., 1., -1.]), np.array([1., -1., -2.]))
    assert row['storm_reverses_descent_fraction'] == pytest.approx(1/3)
    assert row['actual_signed_pa_s'] == pytest.approx(-2/3)
    assert row['actual_positive_only_pa_s'] == pytest.approx(1/3)
    assert row['storm_positive_component_pa_s'] == 1.


@pytest.mark.parametrize('background,actual', [([], []), ([0.], [0., 1.]), ([np.nan], [0.])])
def test_refuses_unpaired_or_nonfinite_samples(background, actual):
    with pytest.raises(ValueError, match='paired finite'):
        audit.ascent_statistics(np.array(background), np.array(actual))


def test_storm_increment_is_paired_under_both_backgrounds_on_uneven_mass():
    case, profile, setting, geometry, air, circulation = five_fixture()
    setting = replace(setting, storm_rate_month=1.)
    m = audit.run.model
    storms = m.nested_events(case.domain, setting, 41, profile.storm_domain_width_m)
    time_s = storms[0].day*audit.DAY
    increments = []
    for mode in ('uniform', 'spatial'):
        quiet = m.flow_at(case.domain, profile, setting, [], time_s, geometry, circulation[3], wind_mode=mode, circulation=circulation)
        full = m.flow_at(case.domain, profile, setting, storms, time_s, geometry, circulation[3], wind_mode=mode, circulation=circulation)
        increments.append(full.vertical-quiet.vertical)
    assert np.max(abs(increments[0])) > 1e-10
    np.testing.assert_allclose(increments[0], increments[1], atol=1e-12, rtol=0)
