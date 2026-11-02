from pathlib import Path
import subprocess

import pytest

from scripts import finalize_r42_atlas as publisher
from scripts.finalize_r42_atlas import allowed, commit_artifacts


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True)


def test_release_commit_retains_unrelated_staged_work_and_includes_deletions(tmp_path, monkeypatch):
    git(tmp_path, 'init', '-q'); git(tmp_path, 'config', 'user.email', 'test@example.org'); git(tmp_path, 'config', 'user.name', 'Test')
    atlas = tmp_path / 'atlases/earth_fit'; atlas.mkdir(parents=True)
    old = atlas / 'old.json'; old.write_text('obsolete')
    unrelated = tmp_path / 'user.txt'; unrelated.write_text('original')
    git(tmp_path, 'add', '.'); git(tmp_path, 'commit', '-qm', 'base')
    old.unlink(); new = atlas / 'params.json'; new.write_text('r42')
    git(tmp_path, 'add', '-u', '--', 'atlases/earth_fit/old.json')
    monkeypatch.setattr(publisher, 'ROOT', tmp_path)
    assert 'atlases/earth_fit/old.json' in publisher.publication_paths()
    unrelated.write_text('user edit'); git(tmp_path, 'add', 'user.txt')
    commit_artifacts(tmp_path, ['atlases/earth_fit/old.json', 'atlases/earth_fit/params.json'])
    assert git(tmp_path, 'show', 'HEAD:user.txt') == 'original'
    assert git(tmp_path, 'diff', '--cached', '--name-only').strip() == 'user.txt'
    assert git(tmp_path, 'ls-tree', '--name-only', 'HEAD', 'atlases/earth_fit/old.json') == ''
    assert git(tmp_path, 'show', 'HEAD:atlases/earth_fit/params.json') == 'r42'


@pytest.mark.parametrize('name', ['user.txt', 'output/atlas_r42/previous_atlases/private.json',
                                  'output/atlas_r42/candidate.pkl', 'output/atlas_r42/final_qa/automation_status.json',
                                  'atlases/earth_fit/../../user.txt', '/tmp/atlas.json'])
def test_publication_scope_excludes_user_work_backups_and_live_status(name):
    assert not allowed(name)
