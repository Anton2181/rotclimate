import json
from pathlib import Path
from types import SimpleNamespace

from scripts import run_padding_parallel as driver


def test_failed_parallel_child_stops_without_retry(monkeypatch, tmp_path):
    monkeypatch.setattr(driver, 'OUT', tmp_path)
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(returncode=1)
    assert not driver.run_phase('integrating', ['declared-worker'], tmp_path / 'results.json', run=fail)
    assert len(calls) == 1
    assert json.loads((tmp_path / 'driver_failure.json').read_text())['automatic_retry'] is False


def test_missing_child_output_is_not_treated_as_completed_science(monkeypatch, tmp_path):
    monkeypatch.setattr(driver, 'OUT', tmp_path)
    assert not driver.run_phase('reviewing', ['review-worker'], tmp_path / 'review.json',
                                run=lambda *args, **kwargs:SimpleNamespace(returncode=0))
    assert not json.loads((tmp_path / 'driver_failure.json').read_text())['expected_output_present']


def test_amendment_preserves_the_entire_scientific_design():
    root = Path(__file__).resolve().parents[1]
    original = json.loads((root / 'calibration/padding_sensitivity_20261126/plan.json').read_text())
    amended = json.loads((root / 'calibration/padding_sensitivity_parallel_20261127/plan.json').read_text())
    for key in ['model_sources_sha256', 'regions', 'cell_km', 'pads_km', 'pad_cell_offsets',
                'maximum_integrations', 'model_overrides', 'controls', 'failure_policy', 'metrics', 'interpretation']:
        assert amended[key] == original[key], key
    assert all(amended['cache_seed_sha256'][name] == digest for name, digest in original['cache_seed_sha256'].items())
    assert all(amended['inputs_sha256'][name] == digest for name, digest in original['inputs_sha256'].items())
    assert original['maximum_integrations'] == amended['maximum_integrations'] == 9
