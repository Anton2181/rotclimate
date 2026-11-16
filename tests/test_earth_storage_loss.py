from dataclasses import asdict

import numpy as np
import pytest

from polity.earth_fixed_food import fixed_request_food
from polity.earth_storage_loss import KCAL, commercial_capacity, fixed_storage_food, inventory


def inputs(grain=3., rural=1., blocked=False):
    return (np.array([[grain]]) * KCAL, np.array([[6]]), np.array([rural]), np.array([.5]),
            np.full((4, 1), -1 if blocked else 0, int), np.full((4, 1), 0. if blocked else .8),
            np.zeros((4, 1, 1)))


def test_five_percent_baseline_identity_all_food_fields():
    args = inputs(); baseline = fixed_request_food(*args, marketed_share=.5)
    actual = fixed_storage_food(*args, marketed_share=.5, reference_market=baseline['marketed'].sum(0), commercial_days=365, loss=.05)
    for key, value in baseline.items():
        if hasattr(value, 'stock_path'):
            for field, array in asdict(value).items():
                np.testing.assert_array_equal(asdict(actual[key])[field], array)
        else:
            np.testing.assert_array_equal(actual[key], value)


@pytest.mark.parametrize('month', range(12))
def test_balanced_zero_loss_selects_smallest_repeating_stock(month):
    harvest = np.zeros((12, 1)); harvest[month] = 12
    year = inventory(harvest, np.ones_like(harvest), np.array([24.]), 0.)
    assert year.initial_stock[0] == pytest.approx(month, abs=1.2e-9)
    assert year.unmet[0] <= 1.2e-9 and year.spoiled[0] == 0
    assert year.stock_path.min() <= 1.2e-9 and year.periodic_converged.all()


def test_balanced_uniform_grain_needs_no_inherited_stock():
    year = inventory(np.ones((12, 1)), np.ones((12, 1)), np.array([24.]), 0.)
    assert year.initial_stock[0] == year.final_stock[0] == 0


def test_balanced_noninteger_grain_does_not_select_arbitrary_large_reserves():
    from harvest.food_stocks import food_year
    rng = np.random.default_rng(17); n = 1000
    harvest = np.zeros((12, n)); amount = rng.uniform(1e6, 1e10, n)
    month = rng.integers(0, 12, n); harvest[month, np.arange(n)] = amount
    need = np.broadcast_to(amount / 12, harvest.shape)
    empty = food_year(harvest, need, amount, record=True, step_days=365/12)
    year = inventory(harvest, need, amount, 0.)
    assert np.all(abs(year.initial_stock - empty.final_stock) <= 1e-10 * amount)
    assert year.periodic_converged.all()


def test_reference_capacity_exact_and_independent_of_new_marketing():
    reference = np.array([0., 123456.789])
    np.testing.assert_array_equal(commercial_capacity(reference, 365), reference)
    np.testing.assert_array_equal(commercial_capacity(reference, 90), reference * 90 / 365)
    with pytest.raises(ValueError): commercial_capacity(reference, 180)


def test_newly_eligible_origin_keeps_zero_commercial_capacity():
    args = inputs(grain=1.01)
    baseline = fixed_request_food(*args, marketed_share=.5)
    assert baseline['marketed'].sum() == 0 and baseline['rural_food'].unmet[0] > 0
    new = fixed_storage_food(*args, marketed_share=.5, reference_market=np.zeros(1), commercial_days=365, loss=0.)
    assert new['rural_food'].unmet[0] <= 1e-4 and new['marketed'].sum() > 0
    assert np.all(new['export_food'].stock_path == 0)
    # Immediate harvest-month dispatch remains possible with no carried stock.
    assert new['departures'].sum() <= new['marketed'].sum() / 12 + 1e-6


def test_zero_loss_blocked_routes_do_not_deliver_food():
    new = fixed_storage_food(*inputs(blocked=True), marketed_share=.5, reference_market=np.array([KCAL]), commercial_days=90, loss=0.)
    assert new['marketed'].sum() > 0
    assert new['departures'].sum() == new['town_food'].consumed.sum() == 0


def test_zero_supply_cannot_borrow_stock():
    year = inventory(np.zeros((12, 1)), np.ones((12, 1)), np.array([24.]), 0.)
    assert year.initial_stock[0] == 0 and year.unmet[0] == 12
