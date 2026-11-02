from scripts.correction_training_receipt import matches, record


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
