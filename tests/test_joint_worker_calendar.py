import numpy as np
import pytest

from polity.joint_worker_calendar import pack_joint_worker_calendar
from polity.worker_calendar import pack_worker_calendar


def arguments(**changes):
    args = dict(workers=2, duty_cap_hours=10., calendar_hours=30., home_service_hours=0.,
        collection_origin=np.array([0]), collection_count=np.array([2]), collection_duration=np.array([3.]),
        visit_actor=np.array([0]), visit_target=np.array([0]), visit_duration=np.array([8.]), crew=1)
    args.update(changes); return args


def test_joint_order_recovers_collection_first_fragmentation():
    args = arguments(); old = pack_worker_calendar(**args); joint = pack_joint_worker_calendar(**args)
    assert old.collection_complete and not old.visit_packed[0]
    assert joint.collection_complete and joint.visit_bin_qualified[0]
    np.testing.assert_array_equal(joint.worker_work_hours, [8, 6])


def test_scheduled_visit_is_not_qualified_when_collection_later_fails():
    args = arguments(collection_duration=np.array([6.]))
    assert 2 * 6 + 8 <= 2 * 10
    r = pack_joint_worker_calendar(**args)
    assert r.visit_scheduled[0] and not r.visit_bin_qualified[0] and not r.collection_complete
    assert r.collection_unpacked_counts[0] == 1
    np.testing.assert_array_equal(r.worker_work_hours, [8, 6])
    assert r.visit_start[0] == 0 and r.visit_end[0] == 8


def test_equal_duration_collection_precedes_visit():
    r = pack_joint_worker_calendar(**arguments(workers=1, duty_cap_hours=6., collection_count=np.array([1]),
        collection_duration=np.array([6.]), visit_duration=np.array([6.])))
    assert r.collection_complete and not r.visit_scheduled.any()


def test_crew_idle_does_not_consume_work_and_later_collector_checks_real_cap():
    r = pack_joint_worker_calendar(**arguments(collection_origin=np.array([0, 1]), collection_count=np.array([1, 1]),
        collection_duration=np.array([6., 3.]), visit_duration=np.array([4.]), crew=2))
    np.testing.assert_array_equal(r.visit_crew, [[1, 0]])
    np.testing.assert_array_equal(r.worker_work_hours, [10, 7])
    np.testing.assert_array_equal(r.worker_calendar_end, [10, 13])
    np.testing.assert_array_equal(r.worker_idle_hours, [0, 6])
    np.testing.assert_array_equal(r.collection_worker, [0, 1])
    assert r.collection_complete and r.visit_bin_qualified[0]


def test_calendar_and_supported_crew_limits():
    r = pack_joint_worker_calendar(**arguments(calendar_hours=5.))
    assert not r.visit_scheduled.any() and r.collection_complete
    assert not pack_joint_worker_calendar(**arguments(workers=1, crew=2, visit_duration=np.array([2.]))).visit_scheduled.any()


def test_services_and_zero_workers_do_not_create_free_work():
    r = pack_joint_worker_calendar(**arguments(home_service_hours=21.))
    assert not r.service_packed and r.service_unpacked_hours == 21.
    assert not r.visit_scheduled.any() and r.collection_unpacked_counts[0] == 2
    r = pack_joint_worker_calendar(**arguments(workers=0)); assert not r.collection_complete and not r.visit_scheduled.any()
    r = pack_joint_worker_calendar(**arguments(duty_cap_hours=0.)); assert not r.visit_scheduled.any()


def test_empty_jobs_are_supported_without_mutation():
    args = arguments(collection_origin=np.array([], 'i8'), collection_count=np.array([], 'i8'), collection_duration=np.array([]),
        visit_actor=np.array([], 'i8'), visit_target=np.array([], 'i8'), visit_duration=np.array([]))
    r = pack_joint_worker_calendar(**args); assert r.collection_complete and r.service_packed and not r.worker_work_hours.any()
    original = arguments(); saved = {k: v.copy() for k, v in original.items() if isinstance(v, np.ndarray)}
    pack_joint_worker_calendar(**original)
    for k, v in saved.items(): np.testing.assert_array_equal(original[k], v)


def test_origin_target_and_worker_ties_are_deterministic():
    r = pack_joint_worker_calendar(**arguments(collection_origin=np.array([9, 3]), collection_count=np.array([1, 1]),
        collection_duration=np.array([4., 4.]), visit_actor=np.array([], 'i8'), visit_target=np.array([], 'i8'), visit_duration=np.array([])))
    np.testing.assert_array_equal(r.collection_origin, [3, 9]); np.testing.assert_array_equal(r.collection_worker, [0, 1])
    r = pack_joint_worker_calendar(**arguments(collection_count=np.array([0]), visit_actor=np.array([1, 0]),
        visit_target=np.array([2, 9]), visit_duration=np.array([8., 8.])))
    np.testing.assert_array_equal(r.visit_crew, [[1], [0]])


def test_invalid_or_overflow_jobs_are_rejected():
    for changes in [dict(workers=1.5), dict(crew=True), dict(collection_count=np.array([2**31])),
                    dict(collection_duration=np.array([0.])), dict(visit_duration=np.array([np.inf]))]:
        with pytest.raises(ValueError): pack_joint_worker_calendar(**arguments(**changes))
    with pytest.raises(ValueError):
        pack_joint_worker_calendar(**arguments(visit_actor=np.array([0, 0]), visit_target=np.array([1, 1]), visit_duration=np.array([2., 3.])))
