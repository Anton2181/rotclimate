"""Frozen duration-first packing of the same collector and crew visit jobs.

Scheduled visits retain their intervals and work even if collection later
fails. Bin qualification is a separate gate;greedy failure is not impossibility.
"""
from dataclasses import dataclass
import heapq

import numpy as np


@dataclass
class JointWorkerCalendar:
    collection_origin: np.ndarray
    collection_serial: np.ndarray
    collection_worker: np.ndarray
    collection_start: np.ndarray
    collection_end: np.ndarray
    collection_unpacked_counts: np.ndarray
    visit_scheduled: np.ndarray
    visit_bin_qualified: np.ndarray
    visit_crew: np.ndarray
    visit_start: np.ndarray
    visit_end: np.ndarray
    worker_work_hours: np.ndarray
    worker_calendar_end: np.ndarray
    worker_idle_hours: np.ndarray
    service_packed: bool
    collection_complete: bool
    service_packed_hours: float
    service_unpacked_hours: float


def pack_joint_worker_calendar(*, workers, duty_cap_hours, calendar_hours, home_service_hours,
                               collection_origin, collection_count, collection_duration,
                               visit_actor, visit_target, visit_duration, crew):
    if isinstance(workers, bool) or not isinstance(workers, (int, np.integer)) or not 0 <= workers <= 2 ** 31 - 1:
        raise ValueError('Nonnegative representable integer worker count required')
    if isinstance(crew, bool) or not isinstance(crew, (int, np.integer)) or not 1 <= crew <= 2 ** 31 - 1:
        raise ValueError('Positive representable integer crew required')
    if not np.isfinite([duty_cap_hours, calendar_hours, home_service_hours]).all() or min(duty_cap_hours, calendar_hours, home_service_hours) < 0:
        raise ValueError('Finite nonnegative work,calendar and service hours required')
    origins, counts = np.asarray(collection_origin), np.asarray(collection_count)
    durations = np.asarray(collection_duration, float); actors, targets = np.asarray(visit_actor), np.asarray(visit_target)
    visits = np.asarray(visit_duration, float)
    if origins.ndim != 1 or origins.dtype.kind not in 'iu' or counts.shape != origins.shape or counts.dtype.kind not in 'iu' or durations.shape != origins.shape:
        raise ValueError('Aligned integer collection origin/count and duration arrays required')
    if np.any(origins < 0) or len(np.unique(origins)) != len(origins) or np.any(counts < 0) or sum(map(int, counts)) > 2 ** 31 - 1:
        raise ValueError('Unique origins and representable nonnegative whole trip counts required')
    if actors.ndim != 1 or actors.dtype.kind not in 'iu' or targets.shape != actors.shape or targets.dtype.kind not in 'iu' or visits.shape != actors.shape:
        raise ValueError('Aligned integer visit actor/target and duration arrays required')
    if np.any(actors < 0) or np.any(targets < 0) or len(set(zip(actors.tolist(), targets.tolist()))) != len(actors):
        raise ValueError('Unique known actor/target visit jobs required')
    if any(not np.isfinite(a).all() or np.any(a <= 0) for a in (durations, visits)):
        raise ValueError('Positive finite whole-job durations required')
    with np.errstate(over='ignore'):
        required_collection = durations @ counts; required_visits = visits.sum() * crew
        work_budget = float(workers) * duty_cap_hours
    if not np.isfinite([required_collection, required_visits, work_budget]).all(): raise ValueError('Job work exceeds numerical range')
    n = int(workers)
    service_ok = home_service_hours == 0 if not n else home_service_hours / n <= min(duty_cap_hours, calendar_hours)
    each = home_service_hours / n if service_ok and n else 0.
    work = np.full(n, each); end = work.copy(); idle = np.zeros(n)
    origin_rows = []; serial_rows = []; worker_rows = []; start_rows = []; end_rows = []
    unfilled = counts.astype('i8').copy(); scheduled = np.zeros(len(visits), bool)
    members = np.full((len(visits), int(crew)), -1, 'i8'); starts = np.zeros(len(visits)); finishes = np.zeros(len(visits))
    # Identical-origin jobs stay a single sorted group;serials within the group
    # are attempted in order. Collection wins equal-duration cross-type ties.
    jobs = [(-float(durations[j]), 0, int(origins[j]), 0, j) for j in range(len(origins)) if counts[j] > 0]
    jobs += [(-float(visits[j]), 1, int(actors[j]), int(targets[j]), j) for j in range(len(visits))]
    if service_ok:
        for negative_duration, kind, _, _, j in sorted(jobs):
            duration = -negative_duration
            eligible = np.flatnonzero((work + duration <= duty_cap_hours) & (end + duration <= calendar_hours))
            if kind == 0:
                available = [(float(end[w]), int(w)) for w in eligible]; heapq.heapify(available)
                for serial in range(int(counts[j])):
                    if not available: break
                    start, worker = heapq.heappop(available); finish = start + duration
                    origin_rows.append(int(origins[j])); serial_rows.append(serial); worker_rows.append(worker); start_rows.append(start); end_rows.append(finish)
                    work[worker] += duration; end[worker] = finish; unfilled[j] -= 1
                    if work[worker] + duration <= duty_cap_hours and finish + duration <= calendar_hours:
                        heapq.heappush(available, (finish, worker))
            elif len(eligible) >= crew:
                chosen = eligible[np.lexsort((eligible, end[eligible]))][:crew]
                start = float(end[chosen].max()); finish = start + duration
                if finish > calendar_hours: raise RuntimeError('Crew synchronization exceeded calendar')
                idle[chosen] += start - end[chosen]; work[chosen] += duration; end[chosen] = finish
                scheduled[j] = True; members[j] = chosen; starts[j] = start; finishes[j] = finish
    complete = bool(service_ok and not unfilled.any())
    if np.any(work > duty_cap_hours) or np.any(end > calendar_hours): raise RuntimeError('Worker calendar or work cap reused')
    np.testing.assert_allclose(end, work + idle, rtol=1e-12, atol=1e-9)
    return JointWorkerCalendar(np.asarray(origin_rows, 'i8'), np.asarray(serial_rows, 'i8'), np.asarray(worker_rows, 'i8'),
        np.asarray(start_rows), np.asarray(end_rows), unfilled, scheduled, scheduled & complete, members, starts, finishes,
        work, end, idle, bool(service_ok), complete, float(home_service_hours if service_ok else 0.), float(0. if service_ok else home_service_hours))
