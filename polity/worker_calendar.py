"""Constructive whole-trip/crew schedules under supplied worker availability.

Greedy failure is not a proof that no schedule exists. Divisible home services
and full-month availability are scenario assumptions,not observed staff roles.
"""
from dataclasses import dataclass
import heapq
import numpy as np


@dataclass
class WorkerCalendar:
    collection_origin: np.ndarray
    collection_serial: np.ndarray
    collection_worker: np.ndarray
    collection_start: np.ndarray
    collection_end: np.ndarray
    collection_unpacked_counts: np.ndarray
    visit_packed: np.ndarray
    visit_blocked_by_collection: np.ndarray
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


def pack_worker_calendar(*, workers, duty_cap_hours, calendar_hours, home_service_hours,
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
    with np.errstate(over='ignore'): total_collection = durations @ counts; total_visit = visits.sum() * crew
    if not np.isfinite([total_collection, total_visit, float(workers) * duty_cap_hours]).all():
        raise ValueError('Job work exceeds numerical range')
    n = int(workers); service_ok = home_service_hours == 0 if n == 0 else home_service_hours / n <= min(duty_cap_hours, calendar_hours)
    service_each = home_service_hours / n if service_ok and n else 0.
    work = np.full(n, service_each); end = work.copy(); idle = np.zeros(n)
    origin_rows = []; serial_rows = []; worker_rows = []; start_rows = []; end_rows = []; unfilled = counts.astype('i8').copy()
    packed = np.zeros(len(visits), bool); blocked = np.zeros(len(visits), bool)
    members = np.full((len(visits), int(crew)), -1, 'i8'); starts = np.zeros(len(visits)); finishes = np.zeros(len(visits))
    if service_ok:
        available = [(float(service_each), worker) for worker in range(n)]
        heapq.heapify(available)
        for j in np.lexsort((origins, -durations)):
            duration = float(durations[j])
            for serial in range(int(counts[j])):
                # Before crew visits every worker has end == work:no idle gaps.
                # The earliest worker therefore tests both common caps for all.
                if not available or available[0][0] + duration > min(duty_cap_hours, calendar_hours): break
                start, worker = heapq.heappop(available); finish = start + duration
                origin_rows.append(int(origins[j])); serial_rows.append(serial); worker_rows.append(worker); start_rows.append(start); end_rows.append(finish)
                work[worker] += duration; end[worker] = finish; unfilled[j] -= 1
                heapq.heappush(available, (finish, worker))
    collection_ok = bool(service_ok and not unfilled.any())
    if not collection_ok: blocked[:] = True
    else:
        for j in np.lexsort((targets, actors, -visits)):
            duration = float(visits[j]); eligible = np.flatnonzero((work + duration <= duty_cap_hours) & (end + duration <= calendar_hours))
            if len(eligible) < crew: continue
            chosen = eligible[np.lexsort((eligible, end[eligible]))][:crew]; start = float(end[chosen].max()); finish = start + duration
            if finish > calendar_hours: raise RuntimeError('Crew synchronization exceeded calendar')
            idle[chosen] += start - end[chosen]; work[chosen] += duration; end[chosen] = finish
            packed[j] = True; members[j] = chosen; starts[j] = start; finishes[j] = finish
    if np.any(work > duty_cap_hours) or np.any(end > calendar_hours): raise RuntimeError('Worker calendar or work cap reused')
    np.testing.assert_allclose(end, work + idle, rtol=1e-12, atol=1e-9)
    return WorkerCalendar(np.asarray(origin_rows, 'i8'), np.asarray(serial_rows, 'i8'), np.asarray(worker_rows, 'i8'),
        np.asarray(start_rows), np.asarray(end_rows), unfilled, packed, blocked, members, starts, finishes,
        work, end, idle, bool(service_ok), collection_ok, float(home_service_hours if service_ok else 0.), float(0. if service_ok else home_service_hours))
