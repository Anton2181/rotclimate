"""Status provenance must accept a frozen finalist without changing its plan."""
import importlib.util
import json
from pathlib import Path

import pytest


def supervisor():
    path = Path(__file__).resolve().parents[1] / 'scripts/run_w18c_campaign.py'
    spec = importlib.util.spec_from_file_location('w18c_status_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_identical_finalist_plan_hash_can_be_recorded(tmp_path):
    s = supervisor()
    digest = s.file_hash(s.PLAN)
    s.state(tmp_path, 'finalist_frozen', name='w1_005', plan_sha256=digest)
    record = json.loads((tmp_path / 'campaign_status.json').read_text())
    assert record['plan_sha256'] == digest
    assert record['stage'] == 'finalist_frozen' and record['name'] == 'w1_005'
    assert record['supervisor_sha256'] == s.file_hash(Path(s.__file__))


def test_conflicting_plan_provenance_preserves_existing_status(tmp_path):
    s = supervisor()
    previous = '{"stage":"search_closed_predicted_gain_below_0.005"}\n'
    (tmp_path / 'campaign_status.json').write_text(previous)
    with pytest.raises(AssertionError, match='Conflicting status provenance'):
        s.state(tmp_path, 'finalist_frozen', plan_sha256='different-plan')
    assert (tmp_path / 'campaign_status.json').read_text() == previous
