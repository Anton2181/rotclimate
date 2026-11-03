import numpy as np
import pytest

from harvest.calendar_stocks import calendar_stock_bounds, two_pulse_capacity
from harvest.crop_sequences import CropCatalogue, CropWindow, optimize_sequences
from harvest.food_stocks import minimum_zero_loss_capacity, periodic_food_year


def test_two_pulse_formula_matches_the_independent_cyclic_food_ledger():
    rng=np.random.default_rng(905)
    for steps in [12,73,365]:
        for _ in range(40):
            a,b=(int(v) for v in rng.integers(0,12,2));share=rng.uniform(0,1)
            harvest=np.zeros(steps);need=np.full(steps,365./steps)
            index=lambda boundary:int(np.floor(boundary*steps/12+.5))%steps
            harvest[index(a)]+=365*share;harvest[index(b)]+=365*(1-share)
            expected=minimum_zero_loss_capacity(harvest,need)
            actual=two_pulse_capacity(a,b,share,year_steps=steps)
            np.testing.assert_allclose(actual,expected,atol=1e-9)
            r=periodic_food_year(harvest,need,actual,step_days=365./steps)
            assert r.unmet<1e-7


def test_all_equally_good_sequences_contribute_to_reserve_range():
    c=CropCatalogue((CropWindow('a',0,3),CropWindow('b',3,3),CropWindow('b',6,3)),np.array([10.,8.,8.]))
    r=optimize_sequences(c,True)
    assert r.optimal_count==2
    stocks=calendar_stock_bounds(c,r,True)
    assert stocks.annual_schedules==2
    assert stocks.maximum_days>stocks.minimum_days
    np.testing.assert_allclose(stocks.minimum_days,two_pulse_capacity(3,9,10/14))
    np.testing.assert_allclose(stocks.maximum_days,two_pulse_capacity(3,6,10/14))


def test_single_harvest_and_unknown_perennial_timing_are_distinct():
    c=CropCatalogue((CropWindow('a',0,3),),np.array([[10.,10.,0.]]))
    r=optimize_sequences(c,False,perennial_energy=[20.,10.,0.])
    stocks=calendar_stock_bounds(c,r,False,perennial_energy=[20.,10.,0.])
    assert np.isnan(stocks.minimum_days[0]) and stocks.perennial_timing_unknown[0]
    assert stocks.minimum_days[1]==stocks.maximum_days[1]==360
    assert stocks.perennial_timing_unknown[1] and stocks.annual_schedules[1]==1
    assert np.isnan(stocks.minimum_days[2]) and not stocks.perennial_timing_unknown[2]


def test_storage_policy_must_reproduce_the_supplied_optimal_schedules():
    c=CropCatalogue((CropWindow('a',0,3),CropWindow('b',3,3)),np.array([10.,8.]))
    r=optimize_sequences(c,True)
    with pytest.raises(ValueError):calendar_stock_bounds(c,r,True,turnaround=1)


@pytest.mark.parametrize('kwargs',[{'year_steps':5},{'year_steps':73.},{'year_days':0}])
def test_invalid_clocks_are_rejected(kwargs):
    with pytest.raises(ValueError):two_pulse_capacity(0,6,.5,**kwargs)
