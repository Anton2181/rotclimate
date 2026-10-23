from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import earth_calibrate as E
from scripts.rainfall_metrics import local_metrics, loss
from scripts.benchmark_rainfall import summarize
from rotclimate.config import Params


def test_regional_total_cannot_hide_swapped_wet_and_dry_locations():
    obs = np.array([[10., 100.]] * 12)
    exact = local_metrics(obs, obs, np.ones(2, bool))
    swapped = local_metrics(obs[:, ::-1], obs, np.ones(2, bool))
    assert exact['loss'] == exact['annual_mae_mm'] == 0
    assert exact['annual_within_25pct'] == 1
    assert swapped['annual_bias_mm'] == 0
    assert swapped['annual_mae_mm'] == 1080
    assert swapped['loss'] > 0
    assert swapped['annual_within_50pct'] == 0


def test_wrong_rainy_season_is_penalized_even_with_exact_annual_rain():
    obs = np.array([[100.]] * 6 + [[0.]] * 6)
    result = local_metrics(np.roll(obs, 6, axis=0), obs, np.ones(1, bool))
    assert result['annual_log_rmse'] == result['annual_mae_mm'] == 0
    assert result['seasonality_total_variation'] == 1
    assert result['monthly_mae_mm'] == 100
    assert result['loss'] > 0


def test_dry_cells_and_zero_simulated_rain_are_finite_and_honest():
    dry = np.zeros((12, 2))
    m = np.ones(2, bool)
    out = local_metrics(dry, dry, m)
    assert out['loss'] == 0
    assert out['annual_within_25pct'] is None
    assert out['seasonality_total_variation'] is None
    out = local_metrics(dry, np.ones((12, 2))*10, m)
    assert out['seasonality_total_variation'] == 1
    assert out['annual_within_50pct'] == 0
    assert np.isfinite(out['loss'])


def test_invalid_land_is_rejected_but_unscored_ocean_is_ignored():
    obs = np.ones((12, 2))*10
    sim = obs.copy(); sim[:, 1] = np.nan
    assert local_metrics(sim, obs, np.array([True, False]))['loss'] == 0
    with pytest.raises(ValueError, match='Invalid rainfall'):
        local_metrics(sim, obs, np.ones(2, bool))
    with pytest.raises(ValueError, match='No scored'):
        local_metrics(obs, obs, np.zeros(2, bool))
    with pytest.raises(ValueError, match='twelve-month'):
        local_metrics(obs[:11], obs[:11], np.ones(2, bool))
    sim[:, 1] = -1
    with pytest.raises(ValueError, match='Invalid rainfall'):
        local_metrics(sim, obs, np.ones(2, bool))


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -1])
def test_archived_loss_rejects_invalid_errors(value):
    with pytest.raises(ValueError):
        loss(dict(rain=dict(annual_log_rmse=value, monthly_mae_mm=10, obs_mean_annual_mm=100)))


def test_earth_rainfall_objective_does_not_reward_temperature(monkeypatch):
    p = Params()
    region = dict(climate_distance=.01, rain=dict(annual_log_rmse=1., monthly_mae_mm=10., obs_mean_annual_mm=120.))
    monkeypatch.setattr(E, '_OBJECTIVE', 'rainfall')
    monkeypatch.setattr(E, 'SPACE', E.SPACES['storm_water'])
    monkeypatch.setattr(E, '_CASES', {})
    monkeypatch.setattr(E.earth, 'region_case', lambda *a, **kw:None)
    monkeypatch.setattr(E.earth, 'run_case', lambda *a, **kw:SimpleNamespace(numerics=dict(all_checks_passed=True)))
    monkeypatch.setattr(E.earth, 'compare', lambda *a:region)
    monkeypatch.setattr(E, 'rainfall_compare', lambda *a:dict(loss=.75))
    monkeypatch.setattr(E.earth, 'station_table', lambda *a:{})
    result = E.evaluate((E.encode(p), asdict(p), ['test'], 56))
    assert result['cost'] == .75
    assert result['cost'] != region['climate_distance']
    assert result['observed_numerics']['test']['all_checks_passed']


def test_failed_numerical_certificate_cannot_be_a_rainfall_gain(monkeypatch):
    p = Params()
    monkeypatch.setattr(E, '_OBJECTIVE', 'rainfall')
    monkeypatch.setattr(E, 'SPACE', E.SPACES['storm_water'])
    monkeypatch.setattr(E, '_CASES', {})
    monkeypatch.setattr(E.earth, 'region_case', lambda *a, **kw:None)
    monkeypatch.setattr(E.earth, 'run_case', lambda *a, **kw:SimpleNamespace(numerics=dict(all_checks_passed=False)))
    result = E.evaluate((E.encode(p), asdict(p), ['test'], 56))
    assert result['cost'] == 99
    assert 'Observed numerical checks failed' in result['error']


def test_failed_or_incomplete_benchmark_is_never_averaged_as_success():
    row = dict(fit='baseline', region='one', status='passed', rainfall={})
    incomplete = summarize([row], ['baseline'], ['one', 'two'])['baseline']
    assert incomplete['complete'] is False
    assert 'equal_region_mean' not in incomplete
    failed = summarize([dict(row, status='failed')], ['baseline'], ['one'])['baseline']
    assert failed['complete'] is False
    assert 'equal_region_mean' not in failed


def test_pooled_location_percentages_and_equal_region_means_are_distinct():
    a = local_metrics(np.ones((12, 1))*10, np.ones((12, 1))*10, np.ones(1, bool))
    b = local_metrics(np.ones((12, 9))*30, np.ones((12, 9))*10, np.ones(9, bool))
    rows = [dict(fit='baseline', region=r, status='passed', rainfall=m) for r,m in [('one',a),('two',b)]]
    result = summarize(rows, ['baseline'], ['one', 'two'])['baseline']
    assert result['complete']
    assert result['equal_region_mean']['annual_within_25pct'] == .5
    assert result['pooled_annual_within_25pct'] == .1
    assert result['pooled_wet_cells'] == 10
