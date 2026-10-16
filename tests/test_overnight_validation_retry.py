from dataclasses import asdict
import json

import pytest

from scripts import retry_overnight_validation as retry


def saved_failure(tmp_path):
    source = tmp_path / 'original'
    source.mkdir()
    p = retry.night.Params.from_json('calibration/round20_retrograde_local_shortlist.json')
    code = 'original-source'
    j = retry.night.job('fresh_anchor_s402', p.replace(beyond_seed=402),
                        2 * p.steps_per_year, source, code)
    failure = dict(name=j['name'], status='failed', input_id=j['input_id'],
                   error='Temperature/wind failed at seasonal step 11')
    (source / 'experiment.json').write_text(json.dumps(dict(anchor=asdict(p), source_id=code)))
    (source / 'summary.json').write_text(json.dumps(dict(stage='complete', runs={j['name']: failure})))
    return source, p


def test_plan_preserves_physics_and_strict_checks_and_never_starts_simulation(tmp_path, monkeypatch):
    source, p = saved_failure(tmp_path)
    monkeypatch.setattr(retry.night, 'worker', lambda *args: pytest.fail('Plan started a simulation'))
    plan = retry.retry_plan(source)
    q = retry.night.Params(**plan['params'])
    before = json.loads(json.dumps(asdict(p.replace(beyond_seed=402))))
    after = json.loads(json.dumps(asdict(q)))
    assert {k for k,v in after.items() if v != before[k]} == {'t_iters'}
    assert q.t_iters == p.t_iters * 2
    assert plan['warmup_steps'] == 50
    assert retry.main(['--source', str(source), '--out', str(tmp_path/'unused')]) == 0
    assert not (tmp_path/'unused').exists()


def test_mismatched_failure_or_unfinished_batch_is_rejected(tmp_path):
    source, _ = saved_failure(tmp_path)
    path = source/'summary.json'
    summary = json.loads(path.read_text())
    summary['runs']['fresh_anchor_s402']['input_id'] = 'wrong-physics'
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='does not match'):
        retry.retry_plan(source)
    summary['stage'] = 'resolution'
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='finish'):
        retry.retry_plan(source)


def test_changed_model_and_original_output_are_protected(tmp_path, monkeypatch):
    source, _ = saved_failure(tmp_path)
    plan = retry.retry_plan(source)
    monkeypatch.setattr(retry.night, 'worker', lambda *args: pytest.fail('Invalid input reached worker'))
    monkeypatch.setattr(retry.night, 'source_id', lambda: 'changed-source')
    with pytest.raises(ValueError, match='sources changed'):
        retry.run_retry(plan, tmp_path/'new')
    assert not (tmp_path/'new').exists()
    with pytest.raises(ValueError, match='separate output'):
        retry.run_retry(plan, source)


def test_failed_retry_is_saved_without_a_climate_score(tmp_path, monkeypatch):
    source, _ = saved_failure(tmp_path)
    plan = retry.retry_plan(source)
    monkeypatch.setattr(retry.night, 'source_id', lambda: plan['source_id'])
    monkeypatch.setattr(retry.night, 'cached', lambda j: None)
    def fail(j):
        assert j['spinup'] == 50 and j['params']['t_iters'] == 384
        return dict(status='failed', name=j['name'], input_id=j['input_id'], error='Still unconverged')
    monkeypatch.setattr(retry.night, 'worker', fail)
    out = tmp_path/'new'
    result = retry.run_retry(plan, out)
    assert result['status'] == 'failed' and 'row' not in result
    report = json.loads((out/'comparison.json').read_text())
    assert report['status'] == 'failed' and 'row' not in report['retry']
    assert 'No usable climate score' in (out/'summary.md').read_text()


def test_matching_success_reuses_fields_without_repeating_the_simulation(tmp_path, monkeypatch):
    source, _ = saved_failure(tmp_path)
    plan = retry.retry_plan(source)
    monkeypatch.setattr(retry.night, 'source_id', lambda: plan['source_id'])
    answer = dict(status='ok', row=dict(accuracy=.5, zone_recall={'cold_dry': .6},
                                        mediterranean={'dry_share': .03}))
    monkeypatch.setattr(retry.night, 'cached', lambda j: answer)
    monkeypatch.setattr(retry.night, 'worker', lambda j: pytest.fail('Cached run was repeated'))
    out = tmp_path/'new'
    assert retry.run_retry(plan, out)['status'] == 'ok'
    assert json.loads((out/'comparison.json').read_text())['retry'] == answer
