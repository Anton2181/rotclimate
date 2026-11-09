import hashlib
import json
import pytest
from scripts.publish_settlement_integration import field_support_artifact


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ancestor(root, name='labour'):
    folder = root / name; folder.mkdir()
    grid = folder / 'field_support.npz'; grid.write_bytes(b'recorded work grid')
    review = folder / 'review.json'
    review.write_text(json.dumps({'artifacts_sha256': {grid.name: sha(grid)}}))
    return grid, review


def test_local_grid_is_registered_and_verified(tmp_path):
    grid, parent = ancestor(tmp_path)
    review = json.loads(parent.read_text())
    assert field_support_artifact(grid.parent, review, {}, root=tmp_path) == grid
    grid.write_bytes(b'changed')
    with pytest.raises(ValueError, match='local'):
        field_support_artifact(grid.parent, review, {}, root=tmp_path)


def test_fertility_release_retains_hashed_ancestor_grid(tmp_path):
    grid, parent = ancestor(tmp_path)
    review = {'artifacts_sha256': {}, 'inputs_sha256': {str(parent.relative_to(tmp_path)): sha(parent)}}
    assert field_support_artifact(tmp_path/'fertility', review, {'labour_specification': {'hours': 600}}, root=tmp_path) == grid


@pytest.mark.parametrize('changed', ['review', 'grid'])
def test_changed_ancestor_cannot_supply_a_download(tmp_path, changed):
    grid, parent = ancestor(tmp_path)
    review = {'artifacts_sha256': {}, 'inputs_sha256': {str(parent.relative_to(tmp_path)): sha(parent)}}
    (parent if changed == 'review' else grid).write_bytes(b'changed')
    with pytest.raises(ValueError, match='Changed'):
        field_support_artifact(tmp_path/'fertility', review, {'labour_specification': {'hours': 600}}, root=tmp_path)


def test_missing_or_ambiguous_work_provenance_is_rejected(tmp_path):
    review = {'artifacts_sha256': {}, 'inputs_sha256': {}}
    model = {'labour_specification': {'hours': 600}}
    with pytest.raises(ValueError, match='exactly one'):
        field_support_artifact(tmp_path/'fertility', review, model, root=tmp_path)
    for name in ['first', 'second']:
        _, parent = ancestor(tmp_path, name)
        review['inputs_sha256'][str(parent.relative_to(tmp_path))] = sha(parent)
    with pytest.raises(ValueError, match='exactly one'):
        field_support_artifact(tmp_path/'fertility', review, model, root=tmp_path)


def test_base_release_without_work_scenarios_has_no_work_download(tmp_path):
    assert field_support_artifact(tmp_path, {}, {}, root=tmp_path) is None
