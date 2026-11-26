from types import SimpleNamespace

import numpy as np
import pytest

from scripts.padding_sensitivity import check_footprint, copy_checked, footprint, require_closed_campaign
from scripts.local_benchmark_protocol import file_hash


def case(offset=0):
    rr, cc = np.indices((7 + 2 * offset, 9 + 2 * offset))
    y, x = rr - offset, cc - offset
    inmap = (y >= 2) & (y <= 4) & (x >= 3) & (x <= 5)
    terrain = (y * 10 + x).astype(float)
    grid = SimpleNamespace(inmap=inmap, land=np.ones_like(inmap), lat=30 - y * .5,
                           land_frac=np.ones_like(terrain), elev=terrain, elev_max=terrain + 2)
    obs = np.stack([terrain + m for m in range(12)])
    return SimpleNamespace(grid=grid, lon=60 + x * .5, obs_T=obs, obs_P=obs * 2)


def test_integer_padding_retains_all_scored_cells_without_interpolation():
    base = footprint(case())
    actual = check_footprint(base, case(2), 2)
    np.testing.assert_array_equal(actual['rows'], base['rows'] + 2)
    assert len(actual['rows']) == 9


@pytest.mark.parametrize('change', ['observation', 'terrain', 'extra_cell', 'missing_cell', 'coordinates'])
def test_changed_scored_footprint_is_rejected(change):
    expanded = case(2)
    if change == 'observation':
        expanded.obs_P[0, 4, 5] += 1
    elif change == 'terrain':
        expanded.grid.elev[4, 5] += 1
    elif change == 'extra_cell':
        expanded.grid.inmap[3, 5] = True
    elif change == 'missing_cell':
        expanded.grid.land[4, 5] = False
    else:
        expanded.lon[4, 5] += .001
    with pytest.raises(AssertionError):
        check_footprint(footprint(case()), expanded, 2)


@pytest.mark.parametrize('stage,running', [('evaluating_development', True), ('evaluating_development', False),
    ('base_failed_investigate_before_remaining_budget', False), ('all_gates_passed_ready_for_review', True), ('closed_fine_gate_failed', True)])
def test_padding_integrations_cannot_overlap_active_or_nonterminal_campaign(stage, running):
    with pytest.raises(RuntimeError, match='preparation only'):
        require_closed_campaign({'stage':stage}, running)


@pytest.mark.parametrize('stage', ['closed_development_gate_failed', 'closed_fine_gate_failed',
                                 'closed_sealed_gate_failed', 'all_gates_passed_ready_for_review'])
def test_terminal_campaign_without_supervisor_permits_fixed_study(stage):
    require_closed_campaign({'stage':stage}, False)


def test_private_input_copy_does_not_share_writable_storage(tmp_path):
    source, destination = tmp_path / 'shared.npz', tmp_path / 'private' / 'input.npz'
    source.write_bytes(b'qualified original')
    copy_checked(source, destination, file_hash(source))
    destination.write_bytes(b'new private derived data')
    assert source.read_bytes() == b'qualified original'


def test_symlink_private_input_is_rejected(tmp_path):
    source, destination = tmp_path / 'shared.npz', tmp_path / 'private.npz'
    source.write_bytes(b'original')
    destination.symlink_to(source)
    with pytest.raises(ValueError, match='symlinks'):
        copy_checked(source, destination, file_hash(source))
