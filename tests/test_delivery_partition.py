import numpy as np
import pytest

from harvest.event_food_stocks import periodic_event_food_year
from polity.delivery_partition import partition_trip_cargo,lagged_return_times
from polity.worker_calendar import pack_worker_calendar


def run(**changes):
    args=dict(departures=np.array([250000.,10000.]),counts=np.array([3,1]),owner=np.array([0,1]),origin=np.array([0,1]),serial=np.array([1,0]),site=np.array([0,1]),provider_count=2)
    args.update(changes);return partition_trip_cargo(**args)


def test_incomplete_deliveries_preserve_every_missing_identity_and_partial_load():
    r=run();np.testing.assert_array_equal(r.packed_cargo,[120000.,10000.]);np.testing.assert_array_equal(r.missing_origin,[0,0]);np.testing.assert_array_equal(r.missing_serial,[0,2]);np.testing.assert_array_equal(r.missing_cargo,[120000.,10000.])
    assert r.packed_cargo.sum()+r.missing_cargo.sum()==260000


def test_all_missing_and_all_packed_are_explicit_not_dropped_providers():
    empty=np.array([],dtype='i8');r=run(origin=empty,serial=empty,site=empty)
    assert len(r.missing_origin)==4 and r.missing_cargo.sum()==260000 and not len(r.packed_cargo)
    r=run(origin=np.array([0,0,0,1]),serial=np.array([0,1,2,0]),site=np.array([0,0,0,1]));assert not len(r.missing_origin)


def test_duplicate_wrong_owner_bad_serial_and_inconsistent_counts_fail_closed():
    for changes in [dict(origin=np.array([0,0]),serial=np.array([1,1]),site=np.array([0,0])),dict(site=np.array([1,1])),dict(serial=np.array([3,0])),dict(counts=np.array([2,1])),dict(counts=np.array([3.,1.]))]:
        with pytest.raises(ValueError):run(**changes)


def test_original_lag_wrap_and_retention_once_with_unfilled_jobs():
    times=lagged_return_times(np.array([7.,14.]),11);np.testing.assert_allclose(times,[1.,2.])
    np.testing.assert_allclose(lagged_return_times(np.array([7.]),0),[365/12+1.])
    r=run();retained=r.packed_cargo*.95;assert retained.sum()==123500 and (r.packed_cargo.sum()+r.missing_cargo.sum())*.95==247000
    with pytest.raises(ValueError):lagged_return_times(np.array([365*7/12]),0)


def test_omission_remains_food_shortage_with_capacity_and_simultaneous_events():
    full=periodic_event_food_year([0.,0.],[50.,50.],demand_rate=10.,capacity=100.,year_days=10.,loss_fraction_year=0.)
    partial=periodic_event_food_year([0.],[50.],demand_rate=10.,capacity=100.,year_days=10.,loss_fraction_year=0.)
    assert full.unmet==0 and partial.unmet==50 and partial.periodic_residual==0


def test_calendar_omission_preserves_service_and_actual_work_charges():
    empty=np.array([],dtype='i8')
    r=pack_worker_calendar(workers=1,duty_cap_hours=10.,calendar_hours=20.,home_service_hours=4.,collection_origin=np.array([0]),collection_count=np.array([2]),collection_duration=np.array([6.]),
        visit_actor=empty,visit_target=empty,visit_duration=np.array([]),crew=1)
    assert r.service_packed and not r.collection_complete and r.worker_work_hours.sum()==10 and r.collection_unpacked_counts.tolist()==[1]
    partition=partition_trip_cargo(np.array([240000.]),np.array([2]),np.array([0]),r.collection_origin,r.collection_serial,np.array([0]),provider_count=1)
    assert partition.packed_cargo.sum()==partition.missing_cargo.sum()==120000


def test_partition_inputs_are_preserved():
    cargo=np.array([250000.,10000.]);counts=np.array([3,1]);a=cargo.copy();b=counts.copy();run(departures=cargo,counts=counts)
    np.testing.assert_array_equal(cargo,a);np.testing.assert_array_equal(counts,b)
