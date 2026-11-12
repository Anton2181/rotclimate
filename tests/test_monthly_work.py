from copy import deepcopy
import numpy as np
import pytest
from polity.monthly_work import collection_trip_work, allocate_monthly_work
from polity.settlement_support import allocate_settlement


def plan():
    return allocate_settlement(np.full((12, 1), 300 * 30.), [200.], [True],
        institutional_request=100, minimum_community=50, kcal_day=1,
        year_days=360, store_days=360, loss_fraction_year=0)


def test_full_collectors_and_fractional_last_load_use_integer_roundtrips():
    food = np.zeros((12, 2)); food[0] = [61, 1e-300]
    out = np.ones_like(food); back = out * 2
    trips, hours = collection_trip_work(food, out, back, np.ones_like(food, bool), load_kcal=60)
    np.testing.assert_array_equal(trips[0], [2, 1])
    np.testing.assert_allclose(hours[0], [42.5, 21.25])
    assert not hours[1:].any()
    with pytest.raises(ValueError, match='access'):
        collection_trip_work(food, out, back, np.zeros_like(food, bool), load_kcal=60)


def test_one_closed_month_is_not_rescued_by_spare_annual_work():
    p = plan(); work = np.ones((12, 1)); hours = np.ones((12, 1)); hours[6] = 0
    result = allocate_monthly_work(p, work, np.ones((3, 12, 1)), hours_per_staff_month=hours,
        source_supported=[True], hours_per_request=1)
    assert result.collection_unmet_hours[6, 0] == 1
    assert not result.qualified[0] and not result.secondary_served.any()
    assert result.secondary_unreachable.sum() == 36
    assert result.unused_hours.sum() > 1000


def test_collection_and_all_secondary_costs_share_the_same_pool():
    p = plan(); before = deepcopy(p)
    demand = np.full((2, 12, 1), 10.)
    result = allocate_monthly_work(p, np.full((12, 1), 5.), demand,
        hours_per_staff_month=.2, source_supported=[True], hours_per_request=np.array([1., 2.])[:, None, None])
    np.testing.assert_allclose(result.gross_hours, 20)
    np.testing.assert_allclose(result.secondary_served, 5)
    np.testing.assert_allclose(result.secondary_hours.sum(axis=0), 15)
    np.testing.assert_allclose(result.invalid_reused_budget_hours, 25)
    np.testing.assert_allclose(result.unused_hours, 0)
    np.testing.assert_array_equal(p.total_people, before.total_people)
    np.testing.assert_array_equal(p.food_year.consumed, before.food_year.consumed)


def test_zero_staff_or_failed_source_food_gate_cannot_fund_duties():
    p = plan(); p.institutional_active[:] = False
    p.civilian_people += p.institutional_people; p.institutional_people[:] = 0
    result = allocate_monthly_work(p, np.ones((12, 1)), np.ones((1, 12, 1)),
        hours_per_staff_month=50., source_supported=[True], hours_per_request=1)
    assert not result.gross_hours.any() and not result.qualified.any()
    result = allocate_monthly_work(plan(), np.zeros((12, 1)), np.ones((1, 12, 1)),
        hours_per_staff_month=50., source_supported=[False], hours_per_request=1)
    assert not result.qualified.any() and not result.secondary_served.any()


def test_zero_shipments_need_no_trips_on_unreachable_paths():
    food = np.zeros((12, 1))
    trips, hours = collection_trip_work(food, np.full_like(food, np.inf), np.full_like(food, np.inf),
                                       np.zeros_like(food, bool), load_kcal=60)
    assert not trips.any() and not hours.any()


def test_unsupported_food_and_numeric_overflow_are_refused():
    p = plan(); p.food_year.unmet[0] = 100000
    with pytest.raises(ValueError, match='Repeating food'):
        allocate_monthly_work(p, np.zeros((12, 1)), np.zeros((1, 12, 1)),
            hours_per_staff_month=50., source_supported=[True], hours_per_request=1)
    with pytest.raises(ValueError, match='numerical range'):
        collection_trip_work(np.full((12, 1), 1e300), np.ones((12, 1)), np.ones((12, 1)),
                             np.ones((12, 1), bool), load_kcal=1e-300)
