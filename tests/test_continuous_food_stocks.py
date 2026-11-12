from dataclasses import fields
from math import exp,log

import numpy as np
import pytest

from harvest.continuous_food_stocks import continuous_food_year,periodic_continuous_food_year
from harvest.event_food_stocks import periodic_event_food_year
from harvest.food_stocks import periodic_food_year


def test_closed_form_constant_meals_and_storage_decay():
    r=continuous_food_year(np.zeros(2),np.full(2,10.),100.,initial_stock=100.,loss_fraction_year=.1,step_days=5.)
    h=-log(.9)/10;expected=(100+2/h)*exp(-h*10)-2/h
    assert r.final_stock==pytest.approx(expected) and r.unmet==0 and r.consumed==20
    assert abs(r.ledger_residual)<1e-12


def test_immediate_capacity_and_periodicity_are_separate_from_sufficiency():
    old=periodic_food_year(np.array([10.]),np.array([10.]),0.,step_days=10.)
    new=periodic_continuous_food_year(np.array([10.]),np.array([10.]),0.,step_days=10.)
    assert old.unmet==0 and new.unmet==10 and new.overflow==10 and new.periodic_converged


def test_minimum_zero_loss_reserve_and_zero_demand():
    r=periodic_continuous_food_year(np.array([0.,10.]),np.array([5.,5.]),20.,step_days=5.)
    assert r.initial_stock==pytest.approx(5.,abs=1e-7) and r.unmet<1e-7 and r.peak_stock==pytest.approx(10.,abs=1e-7)
    empty=periodic_continuous_food_year(np.zeros(2),np.zeros(2),20.,step_days=5.)
    assert empty.initial_stock==empty.final_stock==empty.unmet==0


def test_vectorized_uniform_meals_match_every_scalar_event_field():
    rng=np.random.default_rng(74823);supply=rng.uniform(0,30,(12,40));rate=rng.uniform(0,3,40);capacity=rng.uniform(0,100,40)
    need=np.broadcast_to(rate*365/12,supply.shape)
    result=periodic_continuous_food_year(supply,need,capacity,loss_fraction_year=.05,step_days=365/12,record=True)
    for site in range(40):
        scalar=periodic_event_food_year(np.arange(12)*365/12,supply[:,site],demand_rate=rate[site],capacity=capacity[site])
        for field in fields(scalar):
            np.testing.assert_allclose(getattr(result,field.name)[site],getattr(scalar,field.name),rtol=1e-10,atol=1e-8)
    assert result.stock_path.shape==(13,40) and result.unmet_path.shape==(12,40)


def test_varying_rates_durations_and_mixed_zero_loss_cases():
    supply=np.array([[0.,100.],[20.,0.]]);need=np.array([[2.,0.],[8.,0.]]);before=supply.copy()
    result=periodic_continuous_food_year(supply,need,np.array([20.,10.]),loss_fraction_year=np.array([0.,.1]),step_days=np.array([2.,8.]))
    assert result.unmet[0]<1e-7 and result.unmet[1]==0 and result.overflow[1]>0
    np.testing.assert_allclose(result.initial_stock,[12.,9.],atol=1e-7)
    assert result.overflow[1]==pytest.approx(99.) and result.spoiled[1]==pytest.approx(1.)
    np.testing.assert_allclose(result.consumed+result.unmet,result.needed,atol=1e-10)
    np.testing.assert_allclose(result.ledger_residual,0.,atol=1e-8);np.testing.assert_array_equal(supply,before)


def test_interior_periodic_reserve_without_spill_or_shortage():
    supply=np.full(12,15.1);need=np.full(12,15.);rate=180/365
    vector=periodic_continuous_food_year(supply,need,90.,loss_fraction_year=.05,step_days=365/12)
    scalar=periodic_event_food_year(np.arange(12)*365/12,supply,demand_rate=rate,capacity=90.)
    assert 0<vector.initial_stock<vector.peak_stock<90 and vector.overflow==vector.unmet==0
    assert vector.initial_stock==pytest.approx(scalar.initial_stock,rel=1e-10)
    assert abs(vector.periodic_residual)<1e-10


def test_invalid_inputs_do_not_manufacture_food():
    for changes in [dict(capacity=-1),dict(loss_fraction_year=1),dict(step_days=0),dict(initial_stock=11),dict(capacity=1e308,supply=np.array([1e308]))]:
        args=dict(supply=np.array([1.]),need=np.array([1.]),capacity=10.);args.update(changes)
        with pytest.raises(ValueError):continuous_food_year(**args)
