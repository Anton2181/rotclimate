import json
from types import SimpleNamespace

import pytest

from scripts import run_climate_followups as followups


def action(stage='evaluating_development', **overrides):
    arguments = dict(campaign_live=True, benchmark_live=True, padding_live=False,
                     study_complete=False, review_complete=False, interrupted_attempt=False)
    arguments.update(overrides)
    return followups.next_action(stage, **arguments)


@pytest.mark.parametrize('stage', ['evaluating_development', 'finalist_frozen', 'fine_resolution_gate',
    'single_sealed_AA_pair', 'base_failed_investigate_before_remaining_budget'])
def test_nonterminal_campaign_never_starts_padding(stage):
    assert action(stage) == 'wait_for_campaign'
    assert action(stage, campaign_live=False, benchmark_live=False) == 'campaign_needs_recovery'


@pytest.mark.parametrize('stage', ['closed_development_gate_failed', 'closed_fine_gate_failed',
    'closed_sealed_gate_failed', 'all_gates_passed_ready_for_review'])
def test_terminal_campaign_requires_supervisor_and_workers_to_exit(stage):
    assert action(stage) == 'wait_for_campaign'
    assert action(stage, campaign_live=False) == 'wait_for_campaign'
    assert action(stage, campaign_live=False, benchmark_live=False) == 'run_padding'


def test_live_padding_attempt_is_waited_on_not_repeated_or_declared_interrupted():
    assert action(padding_live=True, interrupted_attempt=True) == 'wait_for_padding'


def test_interrupted_padding_needs_review_instead_of_automatic_retry():
    assert action(interrupted_attempt=True, campaign_live=False, benchmark_live=False) == 'interrupted_padding_needs_review'


def test_completed_study_moves_to_review_then_agent_without_further_integrations():
    assert action(study_complete=True) == 'review_padding'
    assert action(study_complete=True, review_complete=True) == 'finished_for_agent_review'
    assert action(review_complete=True) == 'review_without_results_needs_review'


def test_zombie_supervisor_is_not_mistaken_for_live_progress(tmp_path):
    zombie, worker = tmp_path / '1877', tmp_path / '6609'
    for folder, state, script in [(zombie, 'Z', 'run_w18c_campaign.py'), (worker, 'S', 'benchmark_local.py')]:
        folder.mkdir()
        (folder / 'stat').write_text(f'{folder.name} (python) {state} 1 1 1')
        (folder / 'cmdline').write_bytes(b'python\0-u\0/workspace/scripts/' + script.encode() + b'\0')
    scripts = followups.live_scripts(tmp_path)
    assert 'run_w18c_campaign.py' not in scripts and 'benchmark_local.py' in scripts


def test_failed_child_is_called_once_and_failure_is_persisted(monkeypatch, tmp_path):
    monkeypatch.setattr(followups, 'OUT', tmp_path)
    calls = []
    def failing_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1)
    assert not followups.execute_once('run_padding', {'stage':'closed_fine_gate_failed'}, run=failing_run)
    assert len(calls) == 1 and calls[0][-1] == '--run'
    assert json.loads((tmp_path / 'status.json').read_text())['stage'] == 'padding_command_failed'


def test_success_exit_without_output_stops_instead_of_repeating_the_study(monkeypatch, tmp_path):
    monkeypatch.setattr(followups, 'OUT', tmp_path)
    monkeypatch.setattr(followups, 'PADDING', tmp_path / 'missing_study')
    calls = []
    def empty_success(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=0)
    assert not followups.execute_once('run_padding', {'stage':'closed_fine_gate_failed'}, run=empty_success)
    assert len(calls) == 1
    record = json.loads((tmp_path / 'status.json').read_text())
    assert record['stage'] == 'padding_command_failed' and record['returncode'] == 0


def test_check_only_does_not_create_queue_or_execute_children(monkeypatch, tmp_path):
    target = tmp_path / 'absent_queue'
    monkeypatch.setattr(followups, 'OUT', target)
    monkeypatch.setattr(followups, 'observe', lambda:('wait_for_campaign', {'stage':'evaluating_development', 'completed':16}))
    monkeypatch.setattr(followups.sys, 'argv', ['run_climate_followups.py', '--check-only'])
    def forbidden(*args, **kwargs):
        raise AssertionError('No child may run during a dry check')
    monkeypatch.setattr(followups, 'execute_once', forbidden)
    followups.main()
    assert not target.exists()


def test_dependency_drift_refuses_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(followups, 'ROOT', tmp_path)
    path = tmp_path / 'runner.py'
    path.write_text('changed')
    with pytest.raises(ValueError, match='dependency changed'):
        followups.check_dependencies({'sources_sha256':{'runner.py':'old_digest'}})
    with pytest.raises(ValueError, match='dependency changed'):
        followups.check_dependencies({'sources_sha256':{'missing.py':'old_digest'}})
