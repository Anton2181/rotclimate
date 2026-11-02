import subprocess
from scripts.finish_atlas_snapshot import allowed, publication_paths, stage


PLAN = dict(report='reports/R43_20261103.md', corrections='calibration/earth_correction_r43_20261103',
            correction_output='output/earth_correction_r43_20261103', output='output/atlas_r43')


def test_publication_excludes_snapshot_backups_checkpoints_and_unrelated_work():
    assert allowed('atlases/earth_fit/data/atlas.bin', PLAN)
    assert allowed('output/atlas_r43/snapshot.json', PLAN)
    for name in ['user.txt', 'reports/R42_20261101.md', 'output/atlas_r43/snapshot/data/raw.npz',
                 'output/atlas_r43/previous_atlases/earth_fit_r42/index.html',
                 'output/atlas_r43/atlases.zip', 'output/atlas_r43/publication_status.json', '../atlases/earth_fit/data/a.bin']:
        assert not allowed(name, PLAN)


def test_already_staged_deletions_are_committed_and_unrelated_user_edits_stay_staged(tmp_path):
    def git(*args): return subprocess.check_output(['git', *args], cwd=tmp_path, text=True)
    git('init', '-q'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.org')
    folder = tmp_path / 'atlases/earth_fit'; folder.mkdir(parents=True)
    (folder / 'old.txt').write_text('old'); (tmp_path / 'user.txt').write_text('old')
    git('add', '.'); git('commit', '-qm', 'base')
    (folder / 'old.txt').unlink(); git('add', '-u')
    (folder / 'new.txt').write_text('new')
    (tmp_path / 'user.txt').write_text('user edit'); git('add', 'user.txt')
    hidden = tmp_path / 'output/atlas_r43/snapshot/data'; hidden.mkdir(parents=True)
    (hidden / 'raw.json').write_text('{}')
    names = publication_paths(tmp_path, PLAN)
    assert 'atlases/earth_fit/old.txt' in names
    assert not any('/snapshot/' in n for n in names)
    stage(tmp_path, names)
    git('commit', '--only', '-qm', 'release', '--', *names)
    assert git('show', 'HEAD:user.txt') == 'old'
    assert git('diff', '--cached', '--name-only').strip() == 'user.txt'
    assert git('ls-tree', '-r', '--name-only', 'HEAD').splitlines() == ['atlases/earth_fit/new.txt', 'user.txt']
