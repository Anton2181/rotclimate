from dataclasses import fields

import numpy as np
import pytest

from harvest.event_food_stocks import event_food_year,periodic_event_food_year
from harvest.event_food_trace import trace_event_food_year


def test_boundary_pulse_belongs_to_next_bin_without_moving_food():
    r=periodic_event_food_year([5.],[10.],demand_rate=1.,capacity=20.,year_days=10.,loss_fraction_year=0.)
    trace=trace_event_food_year([5.],[10.],demand_rate=1.,capacity=20.,initial_stock=r.initial_stock,year_days=10.,loss_fraction_year=0.,bins=2)
    np.testing.assert_allclose(trace['arrivals'],[0.,10.]);np.testing.assert_allclose(trace['stock_path'],[5.,0.,5.]);assert trace['unmet'].sum()==0


def test_trace_annual_channels_match_continuous_event_inventory():
    rng=np.random.default_rng(39810)
    for _ in range(40):
        times=np.sort(rng.uniform(0,365,30));cargo=rng.uniform(0,100,30);rate=float(rng.uniform(0,5));cap=float(rng.uniform(0,200));initial=cap*.3
        year=event_food_year(times,cargo,demand_rate=rate,capacity=cap,initial_stock=initial)
        trace=trace_event_food_year(times,cargo,demand_rate=rate,capacity=cap,initial_stock=initial)
        for name in ('needed','consumed','unmet','spoiled','overflow','shortfall_days'):assert trace[name].sum()==pytest.approx(getattr(year,name),rel=1e-12,abs=1e-8)
        assert trace['arrivals'].sum()==pytest.approx(year.harvested,rel=1e-12)
        assert trace['stock_path'][-1]==pytest.approx(year.final_stock,rel=1e-12,abs=1e-8)
        assert trace['peak_stock'].max()==pytest.approx(year.peak_stock,rel=1e-12)


def test_retained_supplies_and_inputs_are_preserved_without_another_loss():
    cargo=np.array([95.,95.]);old=cargo.copy();trace=trace_event_food_year([0.,180.],cargo,demand_rate=0.,capacity=1000.,initial_stock=0.,loss_fraction_year=0.)
    assert trace['arrivals'].sum()==190 and trace['stock_path'][-1]==190;np.testing.assert_array_equal(cargo,old)


def test_invalid_stock_and_display_bins_are_rejected():
    for changes in [dict(initial_stock=-1.),dict(bins=0),dict(bins=True)]:
        args=dict(times=[],supplies=[],demand_rate=1.,capacity=10.,initial_stock=0.);args.update(changes)
        with pytest.raises(ValueError):trace_event_food_year(**args)
