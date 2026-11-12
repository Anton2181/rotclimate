import numpy as np
import pytest

from polity.worker_calendar import pack_worker_calendar


def run(**changes):
    args = dict(workers=2, duty_cap_hours=10., calendar_hours=30., home_service_hours=0., collection_origin=np.array([0]),
        collection_count=np.array([1]), collection_duration=np.array([3.]), visit_actor=np.array([0]),
        visit_target=np.array([0]), visit_duration=np.array([4.]), crew=2)
    args.update(changes); return pack_worker_calendar(**args)


def test_synchronized_crew_consumes_work_once_and_idle_only_calendar():
    r = run(); assert r.collection_complete and r.visit_packed[0]
    np.testing.assert_array_equal(r.visit_crew, [[1, 0]])
    np.testing.assert_array_equal(r.worker_work_hours, [7, 4])
    np.testing.assert_array_equal(r.worker_calendar_end, [7, 7]); np.testing.assert_array_equal(r.worker_idle_hours, [0, 3])
    assert r.visit_start[0] == 3 and r.visit_end[0] == 7


def test_fluid_hours_pass_but_whole_collection_jobs_do_not_pack():
    r = run(collection_count=np.array([3]), collection_duration=np.array([6.]))
    assert 3 * 6 <= 2 * 10
    assert not r.collection_complete and r.collection_unpacked_counts[0] == 1
    assert r.visit_blocked_by_collection[0] and not r.visit_packed[0]
    np.testing.assert_array_equal(r.collection_worker, [0, 1])


def test_home_services_displace_jobs_and_mandatory_failure_explicit():
    r = run(home_service_hours=14.)
    assert r.service_packed and r.collection_complete and not r.visit_packed[0]
    r = run(home_service_hours=21.)
    assert not r.service_packed and not r.collection_complete and r.service_unpacked_hours == 21
    assert not r.collection_origin.size and r.visit_blocked_by_collection.all()


def test_calendar_limits_and_distinct_supported_workers():
    r = run(calendar_hours=6.)
    assert r.collection_complete and not r.visit_packed[0]
    assert not run(workers=1).visit_packed[0]
    with pytest.raises(ValueError): run(workers=1.5)


def test_zero_workers_jobs_and_work_caps():
    r = run(workers=0); assert not r.collection_complete and r.visit_blocked_by_collection.all()
    r = run(duty_cap_hours=0.); assert r.collection_unpacked_counts[0] == 1
    r = run(collection_count=np.array([0]), visit_duration=np.array([], float), visit_actor=np.array([], 'i8'), visit_target=np.array([], 'i8'))
    assert r.collection_complete and not r.visit_packed.size and not r.worker_work_hours.any()


def test_lpt_order_ties_and_inputs_preserved():
    counts = np.array([1, 1]); origins = np.array([9, 3]); durations = np.array([4., 4.])
    r = run(collection_origin=origins, collection_count=counts, collection_duration=durations)
    np.testing.assert_array_equal(r.collection_origin, [3, 9]); np.testing.assert_array_equal(r.collection_worker, [0, 1])
    np.testing.assert_array_equal(counts, [1, 1]); np.testing.assert_array_equal(origins, [9, 3])


def test_overflow_duplicate_and_nonpositive_jobs_rejected():
    with pytest.raises(ValueError): run(collection_duration=np.array([np.inf]))
    with pytest.raises(ValueError): run(collection_count=np.array([2**31]))
    with pytest.raises(ValueError): run(collection_duration=np.array([0.]))
    with pytest.raises(ValueError): run(visit_actor=np.array([0, 0]), visit_target=np.array([1, 1]), visit_duration=np.array([2., 3.]))
