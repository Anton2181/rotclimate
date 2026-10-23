import copy
import json
from pathlib import Path

import pytest

from scripts.rainfall_metrics import loss
from scripts.review_rainfall_fit import assess


def cases():
    base = {p.stem.removeprefix('baseline_'):json.loads(p.read_text()) for p in
            Path('output/climate_physics_20261023/rainfall_baseline/cases').glob('baseline_*.json')}
    assert len(base) == 19
    candidate = copy.deepcopy(base)
    for row in candidate.values():
        for key in ['monthly_mae_mm', 'annual_log_rmse']:
            row['climate']['rain'][key] *= .9
            row['rainfall'][key] *= .9
        row['rainfall']['loss'] = loss(row['climate'])
        row['rainfall']['annual_mae_mm'] *= .9
    return base, candidate


def policy():
    return json.loads(Path('calibration/climate_physics_20261023/rainfall_policy.json').read_text())


def test_actual_no_change_control_cannot_be_selected_as_a_gain():
    base, _ = cases(); p = policy()
    decision = assess(base, base, p['training'], p)
    assert not decision['eligible_for_new_geographic_validation']
    assert 'Mean monthly MAE did not improve' in decision['failures']


def test_rainfall_gain_can_pass_without_improving_temperature():
    base, candidate = cases(); p = policy()
    for row in candidate.values(): row['climate']['temperature']['rmse_C'] += .1
    decision = assess(base, candidate, p['training'], p)
    assert decision['eligible_for_new_geographic_validation']
    assert decision['relative_rainfall_loss_gain'] == pytest.approx(.1)


def test_global_gain_cannot_hide_a_severe_regional_rainfall_regression():
    base, candidate = cases(); p = policy()
    row = candidate['new_zealand']
    row['rainfall']['monthly_mae_mm'] = row['climate']['rain']['monthly_mae_mm'] = 100
    row['rainfall']['loss'] = loss(row['climate'])
    decision = assess(base, candidate, p['training'], p)
    assert not decision['eligible_for_new_geographic_validation']
    assert 'new_zealand: monthly rainfall errors regressed beyond protection' in decision['failures']


def test_changed_geography_and_false_diagnostics_are_rejected():
    base, candidate = cases(); p = policy()
    candidate['california']['rainfall']['wet_scored_cells'] -= 1
    with pytest.raises(ValueError, match='Scored geography changed'):
        assess(base, candidate, p['training'], p)
    candidate['california']['rainfall']['wet_scored_cells'] += 1
    candidate['california']['rainfall']['loss'] = 0
    with pytest.raises(ValueError, match='diagnostics disagree'):
        assess(base, candidate, p['training'], p)


def test_rainfall_gain_cannot_hide_failed_numerics_or_temperature_damage():
    base, candidate = cases(); p = policy()
    candidate['california']['numerics']['all_checks_passed'] = False
    for row in candidate.values(): row['climate']['temperature']['rmse_C'] += .2
    decision = assess(base, candidate, p['training'], p)
    assert not decision['eligible_for_new_geographic_validation']
    assert 'california: failed numerical or execution checks' in decision['failures']
    assert 'temperature_rmse_C regressed beyond protection' in decision['failures']
