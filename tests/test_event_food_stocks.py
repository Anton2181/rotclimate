from dataclasses import asdict
from math import exp, log

import numpy as np
import pytest

from harvest.event_food_stocks import event_food_year, periodic_event_food_year
from harvest.food_stocks import periodic_food_year
from polity.delivery_events import trip_delivery_events


def test_closed_form_decay_and_meals_before_depletion():
    r = event_food_year([], [], demand_rate=2., capacity=100., initial_stock=100., year_days=10., loss_fraction_year=.1)
    h = -log(.9) / 10
    expected = (100 + 2 / h) * exp(-10*h) - 2 / h
    assert r.final_stock == pytest.approx(expected)
    assert r.consumed == 20 and r.unmet == 0 and abs(r.ledger_residual) < 1e-12


def test_closed_form_depletion_and_empty_duration():
    r = event_food_year([], [], demand_rate=2., capacity=10., initial_stock=4., year_days=10., loss_fraction_year=.1)
    h = -log(.9) / 10; fed = log(1 + h*4/2)/h
    assert r.shortfall_days == pytest.approx(10-fed)
    assert r.unmet == pytest.approx(2*(10-fed)) and r.final_stock == 0
    assert r.consumed + r.unmet == pytest.approx(r.needed)


def test_minimum_periodic_reserve_with_zero_loss():
    r = periodic_event_food_year([5.], [10.], demand_rate=1., capacity=20., year_days=10., loss_fraction_year=0.)
    assert r.initial_stock == r.final_stock == 5 and r.peak_stock == 10 and r.unmet == 0
    lower = event_food_year([5.], [10.], demand_rate=1., capacity=20., initial_stock=4.9, year_days=10., loss_fraction_year=0.)
    assert lower.unmet > 0 and lower.periodic_residual > 0


def test_periodic_shortage_does_not_mean_sufficient_food():
    r = periodic_event_food_year([0.], [1.], demand_rate=1., capacity=10., year_days=10.)
    assert abs(r.periodic_residual) < 1e-12 and r.unmet > 9 and r.shortfall_days > 9


def test_zero_demand_zero_capacity_and_meal_capacity_convention():
    assert periodic_event_food_year([], [], demand_rate=0., capacity=10., loss_fraction_year=0.).initial_stock == 0
    r = periodic_event_food_year([0.], [10.], demand_rate=0., capacity=5., year_days=10., loss_fraction_year=0.)
    assert r.initial_stock == 5 and r.overflow == 10 and r.unmet == 0
    old = periodic_food_year(np.array([10.]), np.array([10.]), 0., step_days=10.)
    new = periodic_event_food_year([0.], [10.], demand_rate=1., capacity=0., year_days=10., loss_fraction_year=0.)
    assert old.unmet == 0 and new.unmet == 10 and new.overflow == 10


def test_simultaneous_split_pulses_overflow_and_input_preservation():
    t = np.array([2., 2., 0.]); q = np.array([100., 5., 20.]); before = q.copy()
    a = periodic_event_food_year(t, q, demand_rate=1., capacity=30., year_days=10.)
    b = periodic_event_food_year([0., 2.], [20., 105.], demand_rate=1., capacity=30., year_days=10.)
    assert asdict(a) == asdict(b) and a.overflow > 0; np.testing.assert_array_equal(q, before)


def test_random_fixed_points_against_scalar_bisection():
    rng = np.random.default_rng(9823)
    for _ in range(80):
        times = np.sort(rng.uniform(0, 10, 12)); cargo = rng.uniform(0, 10, 12)
        params = dict(demand_rate=float(rng.uniform(0, 10)), capacity=float(rng.uniform(0, 100)), year_days=10., loss_fraction_year=.2)
        lo, hi = 0., params['capacity']
        for _ in range(65):
            mid = (lo+hi)/2
            if event_food_year(times, cargo, initial_stock=mid, **params).final_stock > mid: lo = mid
            else: hi = mid
        result = periodic_event_food_year(times, cargo, **params)
        assert result.initial_stock == pytest.approx(hi, abs=1e-10)
        assert abs(result.ledger_residual) < 1e-10


def shipment(month=11, **changes):
    args = dict(departures=np.array([250000.]), trips=np.array([3]), owners=np.array([0]), qualified=np.array([True]),
        origin=np.array([0, 0, 0]), serial=np.array([0, 1, 2]), site=np.array([0, 0, 0]), end_hours=np.array([7., 14., 21.]), month=month)
    args.update(changes); return trip_delivery_events(**args)


def test_delivery_lag_wrap_retention_once_and_final_partial_load():
    times, cargo = shipment(); np.testing.assert_allclose(times, [1., 2., 3.]); np.testing.assert_allclose(cargo, np.array([120000.,120000.,10000.])*.95)
    times, _ = shipment(month=0); np.testing.assert_allclose(times, 365/12+np.array([1.,2.,3.]))


def test_duplicate_missing_cargo_owner_and_clock_fail_closed():
    for changes in [dict(serial=np.array([0, 0, 2])), dict(trips=np.array([4])), dict(departures=np.array([240000.])),
                    dict(site=np.array([1,1,1])), dict(end_hours=np.array([7.,14.,365*7/12]))]:
        with pytest.raises(ValueError): shipment(**changes)


def test_invalid_events_and_nonfinite_annual_energy():
    for times, supplies, changes in [([365.],[1.],{}), ([0.],[-1.],{}), ([0.],[1.],dict(capacity=-1)),
                                   ([0.],[1e308],dict(capacity=1e308)), ([0.],[],{})]:
        args = dict(demand_rate=1., capacity=10.);args.update(changes)
        with pytest.raises(ValueError): periodic_event_food_year(times, supplies, **args)
