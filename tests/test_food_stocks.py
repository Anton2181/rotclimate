import numpy as np
import pytest

from harvest.food_stocks import food_year, periodic_food_year, minimum_zero_loss_capacity


def test_same_annual_food_needs_storage_if_harvest_is_seasonal():
    steady = np.ones(365)
    pulse = np.zeros(365); pulse[0] = 365.
    assert minimum_zero_loss_capacity(steady, steady) == 0
    assert minimum_zero_loss_capacity(pulse, steady) == 364
    no_store = periodic_food_year(pulse, steady, 0)
    enough = periodic_food_year(pulse, steady, 364)
    assert no_store.unmet == 364 and no_store.shortfall_days == 364
    assert enough.unmet < 1e-7 and enough.periodic_converged
    assert enough.peak_stock == 364 and abs(enough.ledger_residual) < 1e-9


def test_late_harvest_repeating_reserve_is_accounted_not_created():
    pulse = np.zeros(365); pulse[182] = 365.
    result = periodic_food_year(pulse, np.ones(365), 364, record=True)
    np.testing.assert_allclose(result.initial_stock, 182, atol=1e-7)
    np.testing.assert_allclose(result.final_stock, result.initial_stock, atol=1e-7)
    assert result.unmet < 1e-7
    np.testing.assert_allclose(result.stock_path[1:], result.stock_path[:-1] + pulse - 1, atol=1e-7)


def test_repeating_year_cannot_live_forever_on_an_enormous_inherited_store():
    result = periodic_food_year(np.zeros(4), np.ones(4), 1e12)
    assert result.initial_stock == result.final_stock == 0
    assert result.unmet == 4 and result.periodic_converged
    assert np.isinf(minimum_zero_loss_capacity(np.zeros(4), np.ones(4)))


def test_spoilage_uses_actual_time_and_closes_the_food_ledger():
    result = food_year(np.zeros(4), np.zeros(4), 100, initial_stock=100,
                       loss_fraction_year=.1, step_days=[90,91,92,92])
    np.testing.assert_allclose(result.final_stock, 90, atol=1e-12)
    np.testing.assert_allclose(result.spoiled, 10, atol=1e-12)
    assert result.unmet == 0 and abs(result.ledger_residual) < 1e-12


def test_meals_use_harvest_before_the_storage_cap_and_overflow_is_explicit():
    result = food_year([10.], [3.], 2., loss_fraction_year=.5)
    assert result.consumed == 3 and result.overflow == 5
    assert result.spoiled == 1 and result.final_stock == 1
    assert result.ledger_residual == 0


def test_vector_cells_match_separate_runs_and_inputs_are_unchanged():
    rng = np.random.default_rng(4)
    harvest = rng.uniform(0,4,(12,3)); need = rng.uniform(.5,2,(12,3))
    original = harvest.copy(); caps = np.array([1.,4.,8.]); losses = np.array([0.,.05,.2])
    result = periodic_food_year(harvest, need, caps, loss_fraction_year=losses, step_days=30)
    for j in range(3):
        single = periodic_food_year(harvest[:,j], need[:,j], caps[j], loss_fraction_year=losses[j], step_days=30)
        np.testing.assert_allclose(result.unmet[j], single.unmet, atol=1e-7)
        np.testing.assert_allclose(result.initial_stock[j], single.initial_stock, atol=1e-7)
    np.testing.assert_array_equal(harvest, original)


def test_analytic_capacity_is_feasible_and_any_smaller_integer_capacity_fails():
    rng = np.random.default_rng(32)
    for _ in range(24):
        harvest = rng.integers(0,5,8).astype(float); need = np.ones(8)*2
        capacity = float(minimum_zero_loss_capacity(harvest, need))
        if not np.isfinite(capacity):
            assert harvest.sum() < need.sum(); continue
        assert periodic_food_year(harvest, need, capacity).unmet < 1e-7
        if capacity > 0:
            assert periodic_food_year(harvest, need, capacity-1).unmet > .9


def test_storage_capacity_and_spoilage_have_the_expected_food_security_order():
    harvest = np.zeros(12); harvest[[2,8]] = 10
    need = np.ones(12)
    low = periodic_food_year(harvest, need, 2, loss_fraction_year=.1)
    high = periodic_food_year(harvest, need, 6, loss_fraction_year=.1)
    worse_loss = periodic_food_year(harvest, need, 6, loss_fraction_year=.5)
    assert high.unmet <= low.unmet and worse_loss.unmet >= high.unmet


def test_analytic_capacity_rejects_overflowing_annual_totals():
    with pytest.raises(ValueError): minimum_zero_loss_capacity([1e308,1e308],[1,1])


def test_ledger_tolerates_roundoff_at_a_large_explicit_reserve():
    result = food_year([0.], [0.], 1e12, initial_stock=1e12, loss_fraction_year=1e-20)
    assert result.spoiled > 0 and result.unmet == 0


@pytest.mark.parametrize('harvest,need,capacity,options', [
    ([],[],0,{}), ([np.nan],[1],0,{}), ([1],[-1],0,{}),
    ([1],[1],-1,{}), ([1],[1],1,dict(loss_fraction_year=1)),
    ([1],[1],1,dict(step_days=0)), ([1],[1],1,dict(initial_stock=2)),
    ([1e308,1e308],[1,1],1,{}), ([1,1],[1,1],1,dict(step_days=1e308)),
])
def test_invalid_budget_inputs_are_rejected(harvest, need, capacity, options):
    with pytest.raises(ValueError): food_year(harvest,need,capacity,**options)
