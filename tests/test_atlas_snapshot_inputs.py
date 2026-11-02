from scripts.run_atlas_snapshot import link_missing


def test_snapshot_keeps_pinned_inputs_and_links_only_missing_cache_files(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    (source / 'settings.json').write_text('new settings')
    (source / 'cache').mkdir(); (source / 'cache/raw.npz').write_bytes(b'large raw data')
    dest = tmp_path / 'snapshot'; dest.mkdir(); (dest / 'settings.json').write_text('pinned settings')
    link_missing(source, dest)
    assert (dest / 'settings.json').read_text() == 'pinned settings'
    assert not (dest / 'settings.json').is_symlink()
    assert (dest / 'cache/raw.npz').is_symlink()
    (dest / 'cache/new_result.npz').write_bytes(b'new cache')
    assert not (source / 'cache/new_result.npz').exists()
