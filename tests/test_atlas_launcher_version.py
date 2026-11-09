import hashlib
import json
import subprocess

from scripts.serve_atlases import checkout_version, release_version


def test_release_label_requires_matching_metadata_for_all_three_atlases(tmp_path):
    hashes = {}
    for name in ('free_fit', 'earth_fit', 'whittaker_fit'):
        data = tmp_path / 'atlases' / name / 'data'; data.mkdir(parents=True)
        (data / 'atlas.json').write_bytes(b'{}')
        hashes[name] = hashlib.sha256(b'{}').hexdigest()
    manifest = tmp_path / 'atlases/release.json'
    hub = tmp_path / 'atlases/index.html'; hub.write_bytes(b'current\nhub')
    release = dict(earth_physics='r42', metadata_sha256=hashes, hub_sha256=hashlib.sha256(hub.read_bytes()).hexdigest())
    manifest.write_text(json.dumps(release))
    label, stamp = release_version(tmp_path)
    assert 'r42' in label and len(stamp) == 12
    release.update(active_atlases=['earth_fit'], retired_atlases=['free_fit', 'whittaker_fit'])
    manifest.write_text(json.dumps(release))
    assert release_version(tmp_path)[1] is not None
    release['retired_atlases'].append('earth_fit')
    manifest.write_text(json.dumps(release))
    assert release_version(tmp_path)[1] is None
    release['retired_atlases'].pop()
    manifest.write_text(json.dumps(release))
    hub.write_bytes(b'current\r\nhub')
    assert release_version(tmp_path)[1] is not None
    hub.write_bytes(b'old hub')
    assert release_version(tmp_path)[1] is None
    hub.write_bytes(b'current\nhub')
    (data / 'atlas.json').write_bytes(b'{"old":true}')
    label, stamp = release_version(tmp_path)
    assert 'unverified' in label and stamp is None
    hashes.pop('earth_fit')
    manifest.write_text(json.dumps(dict(earth_physics='r42', metadata_sha256=hashes)))
    assert release_version(tmp_path)[1] is None


def test_legacy_or_malformed_label_does_not_prevent_local_serving(tmp_path):
    assert release_version(tmp_path)[1] is None
    (tmp_path / 'atlases').mkdir(); (tmp_path / 'atlases/release.json').write_text('invalid')
    assert release_version(tmp_path)[1] is None


def test_portable_folder_does_not_report_its_parent_git_checkout(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    subprocess.run(['git', '-C', str(tmp_path), 'checkout', '-qb', 'old-branch'], check=True)
    portable = tmp_path / 'portable'; portable.mkdir()
    assert checkout_version(portable) is None
