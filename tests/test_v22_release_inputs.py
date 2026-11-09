"""A relabelled r43 model must not satisfy an r44 release preflight."""
import hashlib
import json
import numpy as np
import pytest
from scripts.check_v22_release_inputs import verify_correction


def fixture(folder, protocol_hash, actual_hash):
    folder.mkdir()
    np.savez_compressed(folder / 'correction.npz', meta=np.array(json.dumps(dict(physics_params_sha256=actual_hash))))
    digest = hashlib.sha256((folder / 'correction.npz').read_bytes()).hexdigest()
    (folder / 'protocol.json').write_text(json.dumps(dict(meta=dict(physics_params_sha256=protocol_hash), files={'correction.npz': digest})))


def test_model_and_protocol_must_both_match_adopted_physics(tmp_path):
    physics = tmp_path / 'r44.json'; physics.write_text('{"storm_plateau":0.5}')
    digest = hashlib.sha256(physics.read_bytes()).hexdigest()
    folder = tmp_path / 'correct'; fixture(folder, digest, digest)
    assert verify_correction(folder, physics)
    wrong = tmp_path / 'wrong'; fixture(wrong, 'r43-hash', 'r43-hash')
    with pytest.raises(ValueError, match='protocol belongs'): verify_correction(wrong, physics)
    relabelled = tmp_path / 'relabelled'; fixture(relabelled, digest, 'r43-hash')
    with pytest.raises(ValueError, match='model belongs'): verify_correction(relabelled, physics)
    (folder / 'correction.npz').write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed correction artifact'): verify_correction(folder, physics)
