import copy
import math

import numpy as np
import pytest

from scripts.review_padding_sensitivity import assert_control, compare_states, make_comparisons, summarize_state, validate_state


def packet(offset=0):
    shape = (12, 2)
    return dict(T=np.full(shape, 15.), P=np.full(shape, 365 / 12), E=np.ones(shape),
        W=np.full(shape, 4.), u=np.full(shape, 2.), v=np.full(shape, -1.),
        obs_T=np.full(shape, 15.), obs_P=np.full(shape, 365 / 12),
        rows=np.array([2, 3]) + offset, cols=np.array([4, 5]) + offset,
        lat=np.array([20., 19.5]), lon=np.array([40., 40.5]), days=(np.arange(12) + .5) * 365 / 12,
        step_gain=np.full(shape, .01), step_sinkd=np.full(shape, .02),
        step_W=np.full(shape, 4.), step_P=np.ones(shape))


def test_exact_climate_and_trace_integrals_have_known_units():
    summary = summarize_state(packet())
    assert summary['temperature_mae_C'] == summary['rain_loss'] == 0
    assert summary['annual_rain_mm'] == pytest.approx(365)
    assert summary['annual_import_mm'] == pytest.approx(14.6)
    assert summary['annual_drying_mm'] == pytest.approx(-29.2)


def test_constant_field_changes_match_monthly_and_annual_analytic_values():
    base, other = packet(), packet(2)
    other['T'] += 2
    other['P'] += 3
    other['step_P'] += 3 / (365 / 12)
    changes = compare_states(base, other, 2)['fields']
    assert changes['T']['rms_monthly_change'] == pytest.approx(2)
    assert changes['P']['rms_monthly_change'] == pytest.approx(3)
    assert changes['P']['mean_signed_annual_change'] == pytest.approx(36)
    assert changes['P']['max_absolute_annual_change'] == pytest.approx(36)
    expected_loss = .5 * (math.log(451 / 415) + 36 / 485)
    assert summarize_state(other)['rain_loss'] == pytest.approx(expected_loss)


def test_seasonal_cancellation_does_not_hide_monthly_padding_response():
    base, other = packet(), packet(2)
    perturbation = np.array([1., -1.] * 6)[:, None]
    other['T'] += perturbation * 2
    other['P'] += perturbation * 3
    other['step_P'] += perturbation * 3 / (365 / 12)
    changes = compare_states(base, other, 2)['fields']
    assert changes['T']['mean_signed_annual_change'] == pytest.approx(0)
    assert changes['T']['rms_monthly_change'] == pytest.approx(2)
    assert changes['P']['mean_signed_annual_change'] == pytest.approx(0, abs=1e-12)
    assert changes['P']['rms_monthly_change'] == pytest.approx(3)


def test_import_uses_instantaneous_covariance_not_product_of_time_means():
    state = packet()
    state['step_gain'][:] = np.array([0., 2.] * 6)[:, None]
    state['step_W'][:] = np.array([2., 0.] * 6)[:, None]
    state['W'][:] = state['step_W']
    assert state['step_gain'].mean() * state['step_W'].mean() == 1
    assert summarize_state(state)['annual_import_mm'] == 0


@pytest.mark.parametrize('change', ['cell', 'observation', 'calendar', 'coordinate'])
def test_unmatched_locations_observations_or_days_are_rejected(change):
    base, other = packet(), packet(2)
    if change == 'cell':
        other['cols'][0] += 1
    elif change == 'observation':
        other['obs_P'][0, 0] += 1
    elif change == 'calendar':
        other['days'][0] += 1
    else:
        other['lon'][0] += .01
    with pytest.raises(AssertionError):
        compare_states(base, other, 2)


@pytest.mark.parametrize('change', ['negative_rain', 'nonfinite', 'phase_mismatch'])
def test_invalid_or_inconsistent_saved_state_is_rejected(change):
    state = packet()
    if change == 'negative_rain':
        state['P'][0, 0] = -1
    elif change == 'nonfinite':
        state['step_gain'][0, 0] = np.nan
    else:
        state['step_P'][0, 0] += 1
    with pytest.raises(ValueError):
        validate_state(state)


def test_failed_middle_padding_is_missing_instead_of_zero_filled_or_averaged():
    states = {('region', 1100.):packet(), ('region', 4012.):packet(52)}
    pairs, missing = make_comparisons(['region'], [1100., 2220., 4012.], states, 56.)
    assert len(pairs) == 1 and len(missing) == 2
    assert (pairs[0]['from_pad_km'], pairs[0]['to_pad_km']) == (1100., 4012.)
    assert all(2220. in (p['from_pad_km'], p['to_pad_km']) for p in missing)


def test_fractional_cell_padding_is_not_compared_as_matching_geography():
    with pytest.raises(ValueError, match='integer-cell'):
        make_comparisons(['region'], [1100., 2200.], {('region', 1100.):packet(), ('region', 2200.):copy.deepcopy(packet())}, 56.)


def test_control_reproduction_is_checked_against_archived_arrays(tmp_path):
    state = packet()
    path = tmp_path / 'output/ppe_20261126/ref58/r58_dev31/cells/north_india.npz'
    path.parent.mkdir(parents=True)
    np.savez(path, Ts=state['T'].astype(np.float32), Ps=state['P'].astype(np.float32))
    assert_control('north_india', state, tmp_path)
    state['T'][0, 0] += .01
    with pytest.raises(AssertionError):
        assert_control('north_india', state, tmp_path)


def test_somali_control_also_checks_evaporation_water_and_wind(tmp_path):
    state = packet()
    path = tmp_path / 'output/somalia_mechanism_20261126/s_2n_43e/control/fields.npz'
    path.parent.mkdir(parents=True)
    fields = {name:value[:, None, :] for name, value in state.items() if name in ['T', 'P', 'E', 'W', 'u', 'v']}
    np.savez(path, mask=np.ones((1, 2), bool), **fields)
    assert_control('s_2n_43e', state, tmp_path)
    state['u'][0, 0] += .01
    with pytest.raises(AssertionError):
        assert_control('s_2n_43e', state, tmp_path)
