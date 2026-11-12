"""Independent sorted-list calendar replay and explicit worker-interval audit."""
import bisect
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_calendar_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def main():
    result = json.loads((OUT / 'results.json').read_text()); old = dict(np.load(PARENT / 'fields.npz'))
    parent = json.loads((PARENT / 'results.json').read_text()); parent_review = json.loads((PARENT / 'review.json').read_text())
    assert parent_review['status'] == 'passed' and parent_review['results_sha256'] == sha(PARENT / 'results.json')
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for path, digest in result['files_sha256'].items(): assert sha(OUT / path) == digest, path
    assert len(result['collection_rows']) == 4 and len(result['visit_rows']) == 8 and len(result['files_sha256']) == 144
    checked_trips = checked_visits = checked_worker_bins = 0; visited = []; totals = {}; collection_totals = {}
    for mode in ('raw', 'corrected'):
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz'))
        for name in ('owner', 'local_index', 'nodes'): np.testing.assert_array_equal(paths[name], x[name])
        n = len(x['nodes']); origins_by_site = [np.flatnonzero(paths['owner'] == site) for site in range(n)]
        for hours in (600, 300):
            parent_key = f'{mode}_h{hours}_load120000_all_open'; f = dict(np.load(SEEDED / parent_key / 'fields.npz'))
            workers = np.floor(f['staff']).astype('i8'); offsets = np.r_[0, np.cumsum(workers)]
            ct = dict(packed_trips=0, unpacked_trips=0, mandatory_failed_provider_bins=0, relevant_provider_bins=0, packed_collection_hours=0., unpacked_collection_hours=0., service_unpacked_hours=0.)
            for crew in (1, 4):
                key = f'{mode}_h{hours}_crew{crew}'
                totals[key] = dict(packed_visits=0, blocked_by_mandatory_collection=0, greedy_crew_unpacked_visits=0, packed_visit_hours=0., worker_calendar_idle_hours=0., max_worker_duty_hours=0., max_worker_calendar_end=0., packed_by_bin=[], actors=np.zeros((len(old[mode + '__demand']), 3), 'i8'))
            for month in range(12):
                c = dict(np.load(OUT / parent_key / f'collection_{month:02d}.npz')); col_count = np.bincount(c['collection_site'], minlength=n)
                col_offset = np.r_[0, np.cumsum(col_count)]; np.testing.assert_array_equal(c['provider_packed_counts'], col_count)
                np.testing.assert_array_equal(c['collection_site'], np.repeat(np.arange(n), col_count)); np.testing.assert_array_equal(c['worker_counts'], workers)
                np.testing.assert_array_equal(c['required_trip_counts'], f['origin_trips'][month].astype('i8'))
                services = f['work_secondary_hours'][1:, month].sum(axis=0); np.testing.assert_array_equal(c['home_service_hours'], services)
                visits = {}; visit_offsets = {}
                for crew in (1, 4):
                    key = f'{mode}_h{hours}_crew{crew}'; v = dict(np.load(OUT / key / f'visits_{month:02d}.npz')); visits[crew] = v
                    np.testing.assert_array_equal(v['worker_offsets'], offsets)
                    a, t = np.where(old[key + '__served'][month]); sources = old[key + '__provider_for_target'][month, a, t]
                    expected_jobs = sorted(zip(sources.tolist(), a.tolist(), t.tolist()))
                    assert list(zip(v['site'].tolist(), v['actor'].tolist(), v['target_index'].tolist())) == expected_jobs
                    assert len(expected_jobs) == len(set(expected_jobs))
                    np.testing.assert_array_equal(v['required_crew_hours'], old[key + '__chosen_cost_hours'][month, v['actor'], v['target_index']])
                    counts = np.bincount(v['site'], minlength=n); visit_offsets[crew] = np.r_[0, np.cumsum(counts)]
                    np.testing.assert_array_equal(v['provider_planned'], counts)
                unfilled = np.zeros(len(paths['owner']), 'i8'); required_hours = np.zeros(n)
                for site in range(n):
                    w = int(workers[site]); service = float(services[site]); service_ok = service == 0 if not w else service / w <= min(50., 7 * 365 / 12)
                    each = service / w if service_ok and w else 0.; work = [each] * w; ends = work.copy(); intervals = [[] for _ in range(w)]
                    for worker in range(w): intervals[worker].append((0., each))
                    origins = origins_by_site[site]; origins = origins[f['origin_trips'][month, origins] > 0]
                    duration = {int(o): float(7 * (paths['outward_days'][month, o] + paths['inward_days'][month, o]) + .25) for o in origins}
                    for o in origins:
                        assert paths['access'][month, o] and np.isfinite(duration[int(o)]) and duration[int(o)] > 0
                        required_hours[site] += int(f['origin_trips'][month, o]) * duration[int(o)]
                    expected_col = []; available = [(each, worker) for worker in range(w)]
                    for origin in sorted(origins.tolist(), key=lambda o: (-duration[o], o)):
                        count = int(f['origin_trips'][month, origin]); packed = 0
                        if service_ok:
                            for serial in range(count):
                                if not available or available[0][0] + duration[origin] > min(50., 7 * 365 / 12): break
                                start, worker = available.pop(0); finish = start + duration[origin]
                                expected_col.append((origin, serial, worker, start, finish)); work[worker] += duration[origin]; ends[worker] = finish
                                intervals[worker].append((start, finish)); bisect.insort(available, (finish, worker)); packed += 1
                        unfilled[origin] = count - packed
                    lo, hi = col_offset[site:site + 2]
                    for j, name in enumerate(('collection_origin', 'collection_serial', 'collection_worker', 'collection_start', 'collection_end')):
                        np.testing.assert_array_equal(c[name][lo:hi], [row[j] for row in expected_col])
                    collection_ok = bool(service_ok and not unfilled[origins].any())
                    assert bool(c['service_packed'][site]) == service_ok and bool(c['collection_complete'][site]) == collection_ok
                    checked_trips += len(expected_col)
                    for crew, v in visits.items():
                        key = f'{mode}_h{hours}_crew{crew}'; lo, hi = visit_offsets[crew][site:site + 2]; indexes = list(range(int(lo), int(hi)))
                        busy = [list(rows) for rows in intervals]; duty = work.copy(); end = ends.copy(); idle = [0.] * w
                        packed = np.zeros(len(indexes), bool); blocked = np.full(len(indexes), not collection_ok, bool)
                        members = np.full((len(indexes), crew), -1, 'i8'); starts = np.zeros(len(indexes)); finishes = np.zeros(len(indexes))
                        if collection_ok:
                            for j in sorted(range(len(indexes)), key=lambda j: (-float(v['required_crew_hours'][indexes[j]]) / crew, int(v['actor'][indexes[j]]), int(v['target_index'][indexes[j]]))):
                                i = indexes[j]; duration_visit = float(v['required_crew_hours'][i]) / crew
                                eligible = sorted((end[worker], worker) for worker in range(w) if duty[worker] + duration_visit <= 50. and end[worker] + duration_visit <= 7 * 365 / 12)
                                if len(eligible) < crew: continue
                                chosen = [worker for _, worker in eligible[:crew]]; start = max(end[worker] for worker in chosen); finish = start + duration_visit
                                packed[j] = True; members[j] = chosen; starts[j] = start; finishes[j] = finish
                                for worker in chosen:
                                    idle[worker] += start - end[worker]; duty[worker] += duration_visit; end[worker] = finish; busy[worker].append((start, finish))
                        for name, value in [('packed', packed), ('blocked_collection', blocked), ('greedy_unpacked', ~packed & ~blocked), ('crew_workers', members), ('start', starts), ('end', finishes)]: np.testing.assert_array_equal(v[name][lo:hi], value)
                        ws = slice(offsets[site], offsets[site + 1])
                        for name, value in [('worker_work_hours', duty), ('worker_calendar_end', end), ('worker_idle_hours', idle)]: np.testing.assert_array_equal(v[name][ws], value)
                        for worker, rows in enumerate(busy):
                            last = 0.; total_work = 0.
                            for start, finish in sorted(rows):
                                assert start >= last and finish >= start and finish <= 7 * 365 / 12
                                total_work += finish - start; last = finish
                            assert duty[worker] <= 50.
                            np.testing.assert_allclose(total_work, duty[worker], rtol=1e-11, atol=1e-9)
                        np.testing.assert_allclose(end, np.array(duty) + idle, atol=1e-9)
                        assert (packed.astype('u1') + blocked + (~packed & ~blocked)).sum() == len(indexes)
                        actual = float(v['required_crew_hours'][lo:hi][packed].sum()); assert actual <= old[key + '__used_hours'][month, site] + 1e-7
                        assert sum(duty) <= workers[site] * 50 + 1e-7 and sum(duty) <= f['work_gross_hours'][month, site] + 1e-7
                        for name, value in [('provider_packed', int(packed.sum())), ('provider_blocked_collection', int(blocked.sum())), ('provider_greedy_unpacked', int((~packed & ~blocked).sum()))]: assert v[name][site] == value
                        assert v['provider_visit_hours'][site] == actual
                        checked_visits += len(indexes); checked_worker_bins += w
                np.testing.assert_array_equal(c['unpacked_trip_counts'], unfilled); np.testing.assert_allclose(c['provider_required_hours'], required_hours, rtol=1e-11, atol=1e-7)
                np.testing.assert_allclose(required_hours, f['work_required_collection_hours'][month], rtol=1e-11, atol=1e-7)
                packed_hours = np.bincount(c['collection_site'], weights=c['collection_end'] - c['collection_start'], minlength=n)
                np.testing.assert_array_equal(c['provider_packed_hours'], packed_hours)
                relevant = (workers > 0) | (required_hours > 0) | (services > 0); np.testing.assert_array_equal(c['relevant_provider'], relevant)
                duration_all = np.zeros(len(paths['owner'])); pos = f['origin_trips'][month] > 0
                duration_all[pos] = 7 * (paths['outward_days'][month, pos] + paths['inward_days'][month, pos]) + .25
                for field, value in [('packed_trips', int(col_count.sum())), ('unpacked_trips', int(unfilled.sum())), ('mandatory_failed_provider_bins', int((relevant & ~c['collection_complete']).sum())),
                    ('relevant_provider_bins', int(relevant.sum())), ('packed_collection_hours', float(packed_hours.sum())), ('unpacked_collection_hours', float((unfilled * duration_all).sum())), ('service_unpacked_hours', float(services[~c['service_packed']].sum()))]: ct[field] += value
                for crew, v in visits.items():
                    key = f'{mode}_h{hours}_crew{crew}'; acc = totals[key]
                    for name, field in [('packed_visits', 'packed'), ('blocked_by_mandatory_collection', 'blocked_collection'), ('greedy_crew_unpacked_visits', 'greedy_unpacked')]: acc[name] += int(v[field].sum())
                    acc['packed_visit_hours'] += float(v['provider_visit_hours'].sum()); acc['worker_calendar_idle_hours'] += sum(float(v['worker_idle_hours'][offsets[s]:offsets[s + 1]].sum()) for s in range(n))
                    acc['max_worker_duty_hours'] = max(acc['max_worker_duty_hours'], float(v['worker_work_hours'].max(initial=0.)))
                    acc['max_worker_calendar_end'] = max(acc['max_worker_calendar_end'], float(v['worker_calendar_end'].max(initial=0.))); acc['packed_by_bin'].append(int(v['packed'].sum()))
                    for a in range(len(acc['actors'])):
                        for j, field in enumerate(('packed', 'blocked_collection', 'greedy_unpacked')): acc['actors'][a, j] += int(v[field][v['actor'] == a].sum())
                print(parent_key, 'independent calendar/worker/whole-job review', month + 1, flush=True)
            collection_totals[parent_key] = ct
    for row in result['collection_rows']:
        for name, value in collection_totals[row['parent_key']].items(): assert row[name] == value, (row['parent_key'], name)
        assert row['required_trips'] == row['packed_trips'] + row['unpacked_trips']
    for row in result['visit_rows']:
        acc = totals[row['key']]
        for name, value in acc.items():
            if name != 'actors': np.testing.assert_array_equal(row[name], value)
        for actor in row['actors']:
            np.testing.assert_array_equal([actor[k] for k in ('packed', 'blocked_collection', 'greedy_unpacked')], acc['actors'][actor['actor_index']])
        previous = next(r for r in parent['rows'] if r['key'] == row['key'])
        assert row['original_planned_visits'] == previous['completed_visits'] and row['requested_visits'] == previous['requested_visits']
        assert row['original_planned_visits'] == row['packed_visits'] + row['blocked_by_mandatory_collection'] + row['greedy_crew_unpacked_visits']; visited.append(row['key'])
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(Path(__file__)), cases=visited,
        checked_collection_trips=checked_trips, checked_planned_visits=checked_visits, checked_worker_bins=checked_worker_bins,
        independent_sorted_list_replay=True, explicit_nonoverlap_and_duty_caps=True, distinct_synchronized_crews=True,
        collection_failures_block_visits=True, source_provider_jobs_and_monthly_ledgers=True, original_maps_unchanged=True,
        limits='Constructive supplied calendars and greedy shortfalls only;not impossibility,observed staffing,complete service-job rosters,daily provisioning or authority.'))


if __name__ == '__main__': main()
