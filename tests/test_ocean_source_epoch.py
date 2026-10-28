"""An ocean source transition cannot conceal other code or data changes."""
import hashlib
from copy import deepcopy
import pytest
from scripts import ocean_source_epoch as epoch_tools
from scripts.ocean_profile_pilot import ocean_certificate_failures


@pytest.fixture
def source_epoch(tmp_path, monkeypatch):
    monkeypatch.setattr(epoch_tools, 'ROOT', tmp_path)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    files = {}
    for name in epoch_tools.CORE:
        target = tmp_path / name; target.parent.mkdir(exist_ok=True)
        target.write_bytes(b'after')
        files[name] = dict(before_sha256=sha(b'before'), after_sha256=sha(b'after'))
    data = tmp_path / 'observed.txt'; data.write_bytes(b'fixed observation')
    old = {n: v['before_sha256'] for n, v in files.items()}
    old['observed.txt'] = sha(data.read_bytes())
    epoch = dict(before_commit='old', after_commit='new', files=files)
    monkeypatch.setattr(epoch_tools.subprocess, 'check_output',
                        lambda args, **kwargs: b'before' if args[2].startswith('old:') else b'after')
    return epoch, old, tmp_path


def test_both_committed_versions_and_running_version_are_verified(source_epoch):
    epoch, old, root = source_epoch
    epoch_tools.validate_epoch(epoch)
    current = epoch_tools.current_sources(old, epoch)
    assert current['observed.txt'] == old['observed.txt']
    assert all(current[n] == row['after_sha256'] for n, row in epoch['files'].items())
    (root / 'rotclimate/model.py').write_bytes(b'undeclared edit')
    with pytest.raises(ValueError, match='Running ocean core'):
        epoch_tools.validate_epoch(epoch)


def test_source_transition_does_not_allow_observation_changes(source_epoch):
    epoch, old, root = source_epoch
    (root / 'observed.txt').write_bytes(b'changed observation')
    with pytest.raises(ValueError, match='Undeclared changed source/input'):
        epoch_tools.current_sources(old, epoch)


def test_unexpected_historical_version_cannot_be_relabelled(source_epoch):
    epoch, old, _ = source_epoch
    old['rotclimate/config.py'] = 'wrong old hash'
    with pytest.raises(ValueError, match='Unexpected historical core version'):
        epoch_tools.current_sources(old, epoch)


def test_uncommitted_before_bytes_are_rejected(source_epoch):
    epoch, _, _ = source_epoch
    epoch['files']['rotclimate/model.py']['before_sha256'] = 'invented old hash'
    with pytest.raises(ValueError, match='Declared Git source bytes differ'):
        epoch_tools.validate_epoch(epoch)


def test_every_seasonal_ocean_certificate_is_required_and_humidity_bounded():
    step = dict(ocean_target_scheme='hydrostatic-rh', ocean_rh_taper=.5,
                ocean_target_thermal_profile='environmental', ocean_target_lapse_k_km=6.,
                ocean_target_cells=3, minimum_ocean_surface_rh=.75, maximum_ocean_surface_rh=.75,
                minimum_ocean_target_water_mm=10., maximum_ocean_target_water_mm=20.)
    row = dict(status='passed', params=dict(moisture_reservoirs=True, moisture_ocean_hydrostatic=True,
        moisture_ocean_rh_taper=.5, ocean_rh=.75, ocean_rh_warm=0., year_days=365., steps_per_year=13),
        numerics={'moisture_reservoirs': {'steps': [dict(step) for _ in range(21)]}})
    assert not ocean_certificate_failures(row)
    broken = deepcopy(row); broken['numerics']['moisture_reservoirs']['steps'].pop()
    assert 'Missing primer/scored ocean certificates' in ocean_certificate_failures(broken)
    broken = deepcopy(row); broken['numerics']['moisture_reservoirs']['steps'][0]['maximum_ocean_surface_rh'] = 1.01
    assert 'Ocean target bounds failed' in ocean_certificate_failures(broken)
