import json
import pytest

from scripts.correction_training_receipt import artifacts, matches, record, relative_name


def test_complete_training_is_reused_only_for_identical_inputs_and_artifacts(tmp_path):
    model = tmp_path / 'model.npz'; model.write_bytes(b'actual model payload')
    identity = {'physics': 'r42', 'source_hash': 'original'}
    receipt = record(identity, [model], tmp_path)
    assert matches(receipt, identity, tmp_path)
    assert not matches(receipt, {**identity, 'source_hash': 'changed'}, tmp_path)
    model.write_bytes(b'changed model payload')
    assert not matches(receipt, identity, tmp_path)


def test_missing_artifacts_or_incomplete_receipts_are_never_reused(tmp_path):
    model = tmp_path / 'model.npz'; model.write_bytes(b'weights')
    receipt = record({'physics': 'r42'}, [model], tmp_path)
    assert not matches({**receipt, 'status': 'running'}, receipt['inputs'], tmp_path)
    model.unlink()
    assert not matches(receipt, receipt['inputs'], tmp_path)


def test_completion_requires_the_heldout_models_named_in_the_training_protocol(tmp_path):
    cal = tmp_path / 'cal'; folder = cal / 'temperature'; folder.mkdir(parents=True)
    (folder / 'protocol.json').write_text(json.dumps({'files': {'folds/withheld.npz': 'missing'}}))
    with pytest.raises(ValueError, match='Missing or changed trained'):
        artifacts(tmp_path / 'out', cal, 'r42')


def test_linked_inputs_keep_the_snapshot_path_and_are_checked_by_content(tmp_path):
    root = tmp_path / 'snapshot'; root.mkdir()
    shared = tmp_path / 'observations.zip'; shared.write_bytes(b'original observations')
    alias = root / 'observations.zip'; alias.symlink_to(shared)
    assert relative_name(alias, root) == 'observations.zip'
    receipt = record({'physics': 'r43'}, [alias], root)
    assert matches(receipt, receipt['inputs'], root)
    shared.write_bytes(b'changed observations')
    assert not matches(receipt, receipt['inputs'], root)
    with pytest.raises(ValueError): relative_name(shared, root)
