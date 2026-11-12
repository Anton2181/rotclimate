import numpy as np
import pytest

from polity.spare_visits import add_spare_visits


def run(p=(0, 0, 1), t=(0, 1, 1), cost=(3., 4., 5.), **changes):
    args = dict(provider_actor=np.array([0, 0]), supported_staff=np.array([4., 4.]), active=np.ones(2, bool),
                spare_hours=np.array([0., 5.]), pending=np.array([[False, True]]), crew=1)
    args.update(changes)
    return add_spare_visits(np.array(p, dtype='i8'), np.array(t, dtype='i8'), np.array(cost), **args)


def test_recovers_only_pending_from_spare_provider():
    r = run(); np.testing.assert_array_equal(r.added, [[False, True]])
    assert r.provider_for_added[0, 0] == -1 and r.provider_for_added[0, 1] == 1
    np.testing.assert_array_equal(r.used_hours, [0, 5])


def test_no_hours_no_free_tasks_and_wrong_actor_no_transfer():
    assert not run(spare_hours=np.zeros(2)).added.any()
    r = run(provider_actor=np.array([0, 1]), pending=np.array([[False, True], [False, False]]))
    assert not r.added.any() and r.used_hours.sum() == 0


def test_crew_is_supported_and_multiplies_route_cost():
    assert not run(crew=4, spare_hours=np.array([0., 19.])).added.any()
    assert not run(crew=4, supported_staff=np.array([4., 3.]), spare_hours=np.array([0., 20.])).added.any()
    r = run(crew=4, spare_hours=np.array([0., 20.])); assert r.used_hours[1] == 20


def test_orders_tasks_by_cheapest_route_then_actor_target_and_preserves_inputs():
    pending = np.ones((1, 2), bool); budget = np.array([5., 0.])
    r = run(p=(0, 0, 1), t=(0, 1, 1), cost=(5., 3., 3.), pending=pending, spare_hours=budget)
    np.testing.assert_array_equal(r.added, [[False, True]])
    assert r.provider_for_added[0, 1] == 0
    np.testing.assert_array_equal(pending, [[True, True]]); np.testing.assert_array_equal(budget, [5, 0])


def test_deterministic_provider_tie_and_independent_actor_budgets():
    r = run(p=(1, 0), t=(1, 1), cost=(5., 5.), spare_hours=np.array([5., 5.]))
    assert r.provider_for_added[0, 1] == 0
    r = run(p=(0, 1), t=(1, 1), cost=(5., 5.), provider_actor=np.array([0, 1]), pending=np.ones((2, 2), bool), spare_hours=np.array([5., 5.]))
    np.testing.assert_array_equal(r.used_hours, [5, 5]); assert r.added.sum() == 2


def test_no_fractional_or_overflow_tasks_and_duplicate_route_rejected():
    assert not run(spare_hours=np.array([0., 4.999999])).added.any()
    with pytest.raises(ValueError, match='Duplicate'): run(p=(0, 0), t=(1, 1), cost=(1., 2.))
    with pytest.raises(ValueError, match='numerical range'): run(cost=(1e308, 1e308, 1e308), crew=4)
    with pytest.raises(ValueError): run(crew=True)
