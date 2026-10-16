import copy
from dataclasses import asdict
import json
import sys

import numpy as np
import pytest

from scripts import tune_mediterranean as tuning
from scripts.validate_mediterranean import finalists


def row(dry=.1, cold=.68, hot=.57, accuracy=.49, cs=.4):
    return dict(accuracy=accuracy, zone_recall=dict(cold_dry=cold, hot_dry=hot),
                mediterranean=dict(dry_share=dry, cs_share=cs))


def detail(params):
    return dict(params=asdict(params), accuracy=.49, zones={
        'med': dict(correct=.4, koppen_share={'BSh': .1, 'Csa': .4}),
        'cold_dry': dict(correct=.68), 'hot_dry': dict(correct=.57)},
        moisture_transport=None, solver=dict(unconverged_solves=0),
        temperature_convergence=dict(unconverged_steps=0, final_update_max_c=[.04]),
        moisture_convergence=dict(enabled=True, unconverged_steps=0), validation_code_id='current')


def test_local_probes_change_one_physical_parameter_and_keep_strict_numerics():
    base = finalists()['strong_seasonal']
    expected = dict(drier_exchange='eddy_rate', stronger_seasons='eddy_seasonality',
                    slightly_narrower='storm_width')
    for name, p in tuning.candidates(base).items():
        changed = {k for k, v in asdict(p).items() if v != asdict(base)[k]}
        assert changed == {expected[name]}
        assert p.moisture_require_convergence and p.solver_require_convergence and p.t_require_convergence


def test_a_better_overall_score_cannot_hide_dry_zone_damage():
    assert 'cold_dry' in tuning.guard_failures(row(dry=.01, cold=.65, accuracy=.60), row())[0]
    assert 'hot_dry' in tuning.guard_failures(row(dry=.01, hot=.53, accuracy=.60), row())[0]
    assert tuning.guard_failures(row(dry=.09, cold=.66, hot=.54, accuracy=.48, cs=.38), row()) == []


def test_no_dry_increase_and_no_loss_of_mediterranean_seasonality():
    assert any('dry area grew' in f for f in tuning.guard_failures(row(dry=.101), row()))
    assert any('Cs area fell' in f for f in tuning.guard_failures(row(dry=.01, cs=.35), row()))


def test_incomplete_or_unchanged_candidates_are_never_selected():
    anchors = {seed: row() for seed in tuning.SEEDS}
    trials = dict(incomplete=dict(status='passed', worlds={1: row(dry=0.)}),
                  unchanged=dict(status='passed', worlds=copy.deepcopy(anchors)))
    assert tuning.decision(anchors, trials)['suggested_candidate'] is None
    trials['improved'] = dict(status='passed', worlds={seed: row(dry=.04) for seed in tuning.SEEDS})
    decision = tuning.decision(anchors, trials)
    assert decision['suggested_candidate'] == 'improved' and decision['mediterranean_goal_met']


def test_rejection_skips_remaining_worlds_and_saves_each_result(monkeypatch):
    base = finalists()['strong_seasonal']
    anchors = {seed: row() for seed in tuning.SEEDS}
    calls, saves = [], []
    monkeypatch.setattr(tuning, 'dry_patch_changes', lambda a, b: {})
    def evaluate(name, seed, p):
        calls.append((name, seed))
        bad = name == 'drier_exchange' or name == 'stronger_seasons' and seed == 302
        return row(dry=.04, cold=.60 if bad else .68), None
    trials = tuning.local_search(base, anchors, {seed: None for seed in tuning.SEEDS},
                                evaluate, lambda trials: saves.append(copy.deepcopy(trials)))
    assert len(calls) == len(saves) == 6
    assert ('drier_exchange', 302) not in calls
    assert ('stronger_seasons', 301) not in calls
    assert trials['slightly_narrower']['status'] == 'passed'
    assert tuning.decision(anchors, trials)['suggested_candidate'] == 'slightly_narrower'


def test_cache_requires_source_fingerprint_and_matching_field_parameters(tmp_path):
    params = finalists()['strong_seasonal']
    path, fields = tmp_path/'run.json', tmp_path/'fields.npz'
    path.write_text(json.dumps(detail(params)))
    np.savez(fields, params_json=json.dumps(asdict(params)))
    assert tuning.load_cached(path, fields, params, 'current') is not None
    assert tuning.load_cached(path, fields, params, 'different') is None
    np.savez(fields, params_json=json.dumps(asdict(params.replace(beyond_seed=999))))
    assert tuning.load_cached(path, fields, params, 'current') is None


@pytest.mark.parametrize('failure', ['temperature', 'linear', 'moisture', 'unchecked_moisture'])
def test_unconverged_or_unchecked_runs_cannot_enter_the_search(failure):
    d = detail(finalists()['strong_seasonal'])
    if failure == 'temperature':
        d['temperature_convergence']['unconverged_steps'] = 1
    elif failure == 'linear':
        d['solver']['unconverged_solves'] = 1
    elif failure == 'moisture':
        d['moisture_convergence']['unconverged_steps'] = 1
    else:
        d['moisture_convergence']['enabled'] = False
    with pytest.raises(RuntimeError, match='convergence check failed'):
        tuning.checked_summary(d)


def test_default_is_read_only_and_never_calls_simulation(monkeypatch, tmp_path):
    params = finalists()['strong_seasonal']
    out = tmp_path/'must-not-exist'
    monkeypatch.setattr(sys, 'argv', ['tune_mediterranean.py', '--out', str(out)])
    monkeypatch.setattr(tuning, 'load_cached', lambda *args: detail(params))
    def forbidden(*args):
        pytest.fail('Plan must never run a simulation')
    monkeypatch.setattr(tuning, 'run_or_reuse', forbidden)
    tuning.main()
    assert not out.exists()
