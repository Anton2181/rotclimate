from copy import deepcopy
import numpy as np
import pytest
from polity.network_visits import land_block_targets, allocate_reserved_visits


def allocate(provider, target, costs, *, budgets=(4., 10.), crew=1, demand=None, actors=(0, 0), staff=(4., 4.), active=(True, True)):
    return allocate_reserved_visits(np.asarray(provider, int), np.asarray(target, int), costs,
        provider_actor=np.array(actors), supported_staff=staff, active=np.array(active), reserved_hours=budgets,
        demand=np.ones((1, 3), bool) if demand is None else demand, crew=crew)


def test_target_geometry_keeps_every_nonempty_block_and_uses_grid_tie_not_population():
    land = np.ones((4, 4), bool); land[1, 1] = False
    r = land_block_targets(land, land * 4., cell_km=2., block_cells=3)
    np.testing.assert_array_equal(r['nodes'], [1, 7, 13, 15])
    assert r['land_cells'].sum() == land.sum() and r['represented_area_km2'].sum() == 60.
    assert r['block_edge_km'] == 6.


def test_one_actor_target_selects_one_provider_and_never_reuses_a_second_budget():
    r = allocate([0, 1, 0, 1], [0, 0, 1, 1], [2., 3., 3., 4.])
    np.testing.assert_array_equal(r.provider_for_target, [[0, 0, -1]])
    np.testing.assert_array_equal(r.served, [[True, False, False]])
    np.testing.assert_allclose(r.used_hours, [2., 0.]); np.testing.assert_allclose(r.unused_hours, [2., 10.])
    assert r.capacity_unmet[0, 1] and r.route_unreachable[0, 2]


def test_unfunded_provider_is_separate_from_absent_route_and_crew_does_not_become_fractional():
    r = allocate([0, 0], [0, 1], [2., 3.], budgets=(3., 0.), crew=4)
    assert not r.served.any() and r.provider_work_unavailable[0, :2].all() and r.route_unreachable[0, 2]
    r = allocate([0, 1], [0, 0], [2., 3.], budgets=(1., 4.))
    assert r.provider_for_target[0, 0] == 1 and r.served[0, 0]


def test_different_actor_requests_can_visit_same_point_but_never_share_staff_hours():
    r = allocate([0, 1], [0, 0], [2., 2.], budgets=(2., 0.), demand=np.ones((2, 1), bool), actors=(0, 1))
    assert r.served[0, 0] and not r.served[1, 0]
    assert r.provider_work_unavailable[1, 0]


def test_zero_tiny_budget_and_unknown_provider_cannot_create_free_visits():
    r = allocate([0, 1], [0, 1], [1., 1.], budgets=(0., 1e-300), actors=(0, -1))
    assert not r.served.any() and not r.used_hours.any()
    assert r.provider_work_unavailable[0, 0] and r.route_unreachable[0, 1]


def test_duplicate_pairs_and_nonfinite_work_do_not_double_fund_tasks():
    with pytest.raises(ValueError, match='Repeated'): allocate([0, 0], [0, 0], [1., 1.])
    with pytest.raises(ValueError, match='numerical range'): allocate([0], [0], [1e308], crew=4)
    with pytest.raises(ValueError, match='positive|Positive'): allocate([0], [0], [0.])


def test_provider_indices_break_cost_ties_and_inputs_are_not_mutated():
    p, t = np.array([1, 0]), np.array([0, 0]); demand = np.ones((1, 3), bool)
    before = deepcopy((p, t, demand)); r = allocate(p, t, [2., 2.], demand=demand)
    assert r.provider_for_target[0, 0] == 0
    for value, original in zip((p, t, demand), before): np.testing.assert_array_equal(value, original)
