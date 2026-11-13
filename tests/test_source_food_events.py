from dataclasses import asdict
from math import sqrt
import pytest
from harvest.source_food_events import source_food_year,periodic_source_food_year


def run(**changes):
    args=dict(harvest_times=[0.],harvest_cargo=[1500.],pickup_times=[0.],pickup_cargo=[80.],pickup_ids=[7],demand_rate=0.,rural_capacity=1000.,export_capacity=500.,loss_fraction_year=0.)
    args.update(changes);return source_food_year(**args)


def test_rural_priority_quota_and_raw_pickup_retention_absent():
    y=run();assert y.rural.final_stock==1000. and y.rural.overflow==500.
    assert y.export.quota_input==50. and y.pickup_withdrawn==(50.,) and y.pickup_unfilled==(30.,)
    assert y.uncollected==450. and y.total_ledger_residual==0.


def test_export_clipping_never_returns_grain_to_rural_or_creates_cargo():
    y=run(export_capacity=10.);assert y.pickup_withdrawn==(10.,) and y.export.overflow==40.
    assert y.uncollected==490. and y.rural.final_stock==1000. and y.total_ledger_residual==0.


def test_independent_export_decay_before_and_after_pickup():
    y=run(harvest_cargo=[1000.],rural_capacity=0.,export_capacity=100.,pickup_times=[182.5],pickup_cargo=[50.],loss_fraction_year=.05)
    assert y.pickup_withdrawn==(50.,)
    assert y.export.final_stock==pytest.approx(95.-50.*sqrt(.95))
    assert y.export.spoiled==pytest.approx(100.-50.-y.export.final_stock)


def test_same_time_harvest_precedes_pickups_ordered_by_unique_id():
    y=run(pickup_times=[0.,0.],pickup_cargo=[40.,40.],pickup_ids=[9,2])
    assert y.pickup_withdrawn==(10.,40.) and y.pickup_unfilled==(30.,0.)
    z=run(pickup_times=[0.,0.],pickup_cargo=[40.,40.],pickup_ids=[2,9])
    assert dict(zip(y.pickup_ids,y.pickup_withdrawn))==dict(zip(z.pickup_ids,z.pickup_withdrawn))


def test_harvest_aggregation_and_input_order_preserve_accounts():
    a=run(harvest_times=[0.,0.],harvest_cargo=[500.,1000.]);b=run()
    assert asdict(a)==asdict(b)


def test_pickups_cannot_take_rural_stock_before_overflow():
    y=run(harvest_cargo=[900.]);assert y.export.quota_input==0. and y.pickup_withdrawn==(0.,)
    assert y.rural.final_stock==900. and y.uncollected==0.


def test_zero_quota_keeps_all_overflow_uncollected():
    y=run(quota_fraction=0.);assert y.export.withdrawn==0. and y.uncollected==500.


def test_periodic_empty_source_has_no_free_stock_loan():
    y=periodic_source_food_year([],[],[100.],[50.],[0],demand_rate=1.,rural_capacity=365.,export_capacity=100.)
    assert y.rural.initial_stock==0. and y.export.initial_stock==0.
    assert y.rural.unmet==365. and y.pickup_unfilled==(50.,)


def test_minimum_periodic_export_reserve_with_balanced_pulses():
    args=dict(harvest_times=[100.],harvest_cargo=[200.],pickup_cargo=[20.],pickup_ids=[0],demand_rate=0.,rural_capacity=0.,export_capacity=100.,loss_fraction_year=0.)
    early=periodic_source_food_year(pickup_times=[0.],**args);late=periodic_source_food_year(pickup_times=[200.],**args)
    assert early.export.initial_stock==early.export.final_stock==20.
    assert late.export.initial_stock==late.export.final_stock==0.
    assert early.export.unfilled==late.export.unfilled==0.


def test_periodic_saturated_surplus_is_real_overflow_not_a_loan():
    y=periodic_source_food_year([0.],[1000.],[],[],[],demand_rate=0.,rural_capacity=0.,export_capacity=100.,loss_fraction_year=0.)
    assert y.export.initial_stock==y.export.final_stock==100.
    assert y.export.overflow==100. and y.uncollected==1000. and y.total_ledger_residual==0.


def test_rural_food_failure_stays_visible_even_when_exports_fill_requests():
    y=run(harvest_cargo=[1000.],demand_rate=1.,rural_capacity=365.,pickup_cargo=[50.],loss_fraction_year=.05)
    assert y.rural.unmet>0. and y.export.unfilled==0.
    assert abs(y.total_ledger_residual)<1e-8


@pytest.mark.parametrize('changes',[
    dict(pickup_ids=[1,1],pickup_times=[0.,1.],pickup_cargo=[1.,1.]),dict(pickup_ids=[True]),
    dict(pickup_times=[365.]),dict(pickup_times=[float('nan')]),dict(pickup_cargo=[-1.]),
    dict(export_capacity=-1.),dict(quota_fraction=1.1),dict(initial_export_stock=501.),
    dict(harvest_cargo=[float('inf')]),dict(loss_fraction_year=1.),
])
def test_invalid_source_or_pickup_inputs_rejected(changes):
    with pytest.raises(ValueError):run(**changes)
