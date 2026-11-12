import numpy as np
import pytest

from polity.network_visits import land_block_targets
from polity.visit_target_grid import phased_land_targets


def test_clipped_shifted_tiles_cover_each_land_cell_and_area_once():
    land = np.ones((7, 8), bool); land[1:5, 2] = False; area = np.arange(56).reshape(7, 8) / 3
    for block in (2, 3, 5):
        for phase in range(block):
            r = phased_land_targets(land, area, cell_km=2, block_cells=block, row_phase=phase, column_phase=phase)
            assert r['land_cells'].sum() == land.sum()
            np.testing.assert_allclose(r['represented_area_km2'].sum(), area[land].sum())
            assert len(np.unique(r['nodes'])) == len(r['nodes']) and land.ravel()[r['nodes']].all()


def test_zero_phase_exactly_matches_original_geometry():
    land = np.array([[1, 0, 1, 1], [1, 1, 1, 0], [0, 0, 1, 1], [1, 1, 0, 1]], bool)
    area = np.arange(16).reshape(4, 4).astype('f4')
    for block in (2, 3, 5):
        old = land_block_targets(land, area, cell_km=3, block_cells=block)
        new = phased_land_targets(land, area, cell_km=3, block_cells=block)
        for name in old: np.testing.assert_array_equal(old[name], new[name])


def test_lowest_global_node_tie_and_clipped_phase_edge():
    r = phased_land_targets(np.ones((4, 4), bool), np.ones((4, 4)), cell_km=1, block_cells=3, row_phase=1, column_phase=1)
    np.testing.assert_array_equal(r['nodes'], [0, 2, 8, 10])
    np.testing.assert_array_equal(r['land_cells'], [4, 4, 4, 4])
    assert r['block_edge_km'] == 3


def test_rejects_invalid_grid_and_does_not_mutate_inputs():
    land = np.ones((3, 3), bool); area = np.ones((3, 3))
    for args in [dict(block_cells=0), dict(block_cells=3, row_phase=3), dict(block_cells=3, column_phase=-1), dict(block_cells=True)]:
        with pytest.raises(ValueError): phased_land_targets(land, area, cell_km=1, **args)
    assert land.all() and (area == 1).all()
