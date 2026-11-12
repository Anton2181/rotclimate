"""Independent scalar mixed-job replay,worker intervals and both delivery gates."""
import bisect
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_joint_order_20261112'
BASE = ROOT / 'output/network_visit_calendar_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def scalar_schedule(workers, services, origins, counts, durations, actors, targets, visit_cost, crew):
    service_ok = services == 0 if not workers else services / workers <= 50.
    each = services / workers if service_ok and workers else 0.
    work = [each] * workers; end = work.copy(); idle = [0.] * workers
    collection = []; missing = dict(zip(origins.tolist(), counts.tolist()))
    scheduled = np.zeros(len(actors), bool); members = np.full((len(actors), crew), -1, 'i8'); starts = np.zeros(len(actors)); finishes = np.zeros(len(actors))
    # Sorted job groups and sorted worker lists implement the declared scalar
    # rule independently of the production heap/NumPy allocator.
    jobs = [(-float(duration), 0, int(origin), 0, j) for j, (origin, duration) in enumerate(zip(origins, durations))]
    jobs += [(-float(cost) / crew, 1, int(a), int(t), j) for j, (a, t, cost) in enumerate(zip(actors, targets, visit_cost))]
    if service_ok:
        for negative, kind, _, _, j in sorted(jobs):
            duration = -negative
            available = sorted((end[w], w) for w in range(workers) if work[w] + duration <= 50. and end[w] + duration <= 7 * 365 / 12)
            if kind == 0:
                for serial in range(int(counts[j])):
                    if not available: break
                    start, worker = available.pop(0); finish = start + duration
                    collection.append((int(origins[j]), serial, worker, start, finish)); missing[int(origins[j])] -= 1
                    work[worker] += duration; end[worker] = finish
                    if work[worker] + duration <= 50. and finish + duration <= 7 * 365 / 12: bisect.insort(available, (finish, worker))
            elif len(available) >= crew:
                chosen = [w for _, w in available[:crew]]; start = max(end[w] for w in chosen); finish = start + duration
                scheduled[j] = True; members[j] = chosen; starts[j] = start; finishes[j] = finish
                for w in chosen: idle[w] += start - end[w]; work[w] += duration; end[w] = finish
    complete = bool(service_ok and not any(missing.values()))
    return dict(collection=collection, missing=[missing[int(o)] for o in origins], scheduled=scheduled, qualified=scheduled & complete,
        members=members, starts=starts, finishes=finishes, work=work, end=end, idle=idle, service_ok=service_ok, complete=complete, service_each=each)


def verify_summary(row, monthly, f, x, previous, fields):
    # Derive the twelve-bin flag from individual bins,never from published
    # summary totals. Inactive providers cannot pass on empty obligations.
    complete = np.array([m['complete'] for m in monthly], bool); annual = np.array([bool(f['active'][s]) and all(complete[:, s]) for s in range(len(x['nodes']))])
    scheduled = np.array([m['scheduled'] for m in monthly]); qualified = np.array([m['qualified'] for m in monthly])
    missing = np.array([m['missing'] for m in monthly]); hours = np.array([m['visit_hours'] for m in monthly]); relevant = np.array([m['relevant'] for m in monthly])
    expected = dict(complete=complete, annual=annual, scheduled=scheduled, qualified=qualified, missing=missing, visit_hours=hours, relevant=relevant)
    for name, values in expected.items(): np.testing.assert_array_equal(fields[row['policy'] + '__' + row['key'] + '__' + name], values)
    values = dict(original_requested_visits=previous['requested_visits'], original_planned_visits=previous['completed_visits'],
        physically_scheduled_visits=int(scheduled.sum()), bin_qualified_visits=int(qualified.sum()),
        scheduled_with_mandatory_gaps=int((scheduled - qualified).sum()), not_scheduled_visits=int(previous['completed_visits'] - scheduled.sum()),
        twelve_bin_gated_visits=int(sum(int(qualified[:, s].sum()) for s in np.flatnonzero(annual))), twelve_bin_mandatory_providers=int(annual.sum()),
        active_providers=int(f['active'].sum()), unpacked_collector_trips=int(missing.sum()), required_collector_trips=int(f['origin_trips'].sum()),
        mandatory_failed_provider_bins=int((relevant & ~complete).sum()), relevant_provider_bins=int(relevant.sum()), physically_scheduled_visit_hours=float(hours.sum()))
    for name, value in values.items(): assert row[name] == value, (row['policy'], row['key'], name)
    for name, values in [('scheduled_by_bin', scheduled.sum(axis=1)), ('bin_qualified_by_bin', qualified.sum(axis=1)), ('twelve_bin_gated_by_bin', qualified[:, annual].sum(axis=1))]: np.testing.assert_array_equal(row[name], values)
    assert row['original_planned_visits'] == row['bin_qualified_visits'] + row['scheduled_with_mandatory_gaps'] + row['not_scheduled_visits']
    for a in row['actors']:
        i = a['actor_index']; owned = x['actor'] == i
        assert a['inventory_present'] == previous['actors'][i]['inventory_present'] and a['original_planned_visits'] == previous['actors'][i]['completed_visits']
        for name, value in [('physically_scheduled', scheduled[:, owned].sum()), ('bin_qualified', qualified[:, owned].sum()),
            ('twelve_bin_gated', qualified[:, owned & annual].sum()), ('active_providers', (owned & f['active']).sum()), ('twelve_bin_mandatory_providers', (owned & annual).sum())]: assert a[name] == int(value)


def main():
    r = json.loads((OUT / 'results.json').read_text()); fields = dict(np.load(OUT / 'qualification_fields.npz'))
    for path, digest in {**r['sources'], **r['producers'], **r['unchanged_map_sha256'], **r['unchanged_baseline_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in r['files_sha256'].items(): assert sha(OUT / name) == digest
    assert sha(OUT / 'qualification_fields.npz') == r['qualification_fields_sha256'] and len(r['rows']) == 16 and len(r['files_sha256']) == 96
    parent = json.loads((PARENT / 'results.json').read_text()); original = dict(np.load(PARENT / 'fields.npz'))
    checked_trips = checked_visits = checked_workers = 0; cases = []
    for previous in parent['rows']:
        key, mode, crew, parent_key = (previous[n] for n in ('key', 'climate', 'crew', 'parent_key'))
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz')); f = dict(np.load(SEEDED / parent_key / 'fields.npz'))
        for name in ('nodes', 'local_index', 'owner'): np.testing.assert_array_equal(paths[name], x[name])
        n = len(x['nodes']); workers = np.floor(f['staff']).astype('i8'); offsets = np.r_[0, np.cumsum(workers)]
        groups = [np.flatnonzero(paths['owner'] == s) for s in range(n)]; baseline_months = []; mixed_months = []
        for month in range(12):
            p = dict(np.load(OUT / key / f'calendar_{month:02d}.npz')); old_c = dict(np.load(BASE / parent_key / f'collection_{month:02d}.npz')); old_v = dict(np.load(BASE / key / f'visits_{month:02d}.npz'))
            np.testing.assert_array_equal(p['worker_counts'], workers); np.testing.assert_array_equal(p['worker_offsets'], offsets)
            np.testing.assert_array_equal(p['required_trip_counts'], f['origin_trips'][month].astype('i8'))
            services = f['work_secondary_hours'][1:, month].sum(axis=0); np.testing.assert_array_equal(p['home_service_hours'], services)
            aa, tt = np.where(original[key + '__served'][month]); providers = original[key + '__provider_for_target'][month, aa, tt]
            expected_jobs = sorted(zip(providers.tolist(), aa.tolist(), tt.tolist()))
            assert list(zip(p['visit_site'].tolist(), p['visit_actor'].tolist(), p['visit_target'].tolist())) == expected_jobs
            assert len(expected_jobs) == len(set(expected_jobs))
            np.testing.assert_array_equal(p['visit_required_crew_hours'], original[key + '__chosen_cost_hours'][month, p['visit_actor'], p['visit_target']])
            col_counts = np.bincount(p['collection_site'], minlength=n); col_offsets = np.r_[0, np.cumsum(col_counts)]
            np.testing.assert_array_equal(p['collection_site'], np.repeat(np.arange(n), col_counts))
            visit_counts = np.bincount(p['visit_site'], minlength=n); visit_offsets = np.r_[0, np.cumsum(visit_counts)]
            np.testing.assert_array_equal(p['provider_planned_visits'], visit_counts)
            missing_all = np.zeros(len(paths['owner']), 'i8'); required = np.zeros(n); scheduled_counts = np.zeros(n, 'i8'); qualified_counts = np.zeros(n, 'i8'); used = np.zeros(n)
            complete = np.zeros(n, bool); service_ok = np.zeros(n, bool)
            for site in range(n):
                origins = groups[site]; origins = origins[f['origin_trips'][month, origins] > 0]; counts = f['origin_trips'][month, origins].astype('i8')
                assert paths['access'][month, origins].all()
                durations = 7 * (paths['outward_days'][month, origins] + paths['inward_days'][month, origins]) + .25
                required[site] = float(np.sum(counts * durations)); lo, hi = visit_offsets[site:site + 2]; cl, ch = col_offsets[site:site + 2]
                e = scalar_schedule(int(workers[site]), float(services[site]), origins, counts, durations, p['visit_actor'][lo:hi], p['visit_target'][lo:hi], p['visit_required_crew_hours'][lo:hi], crew)
                for j, name in enumerate(('collection_origin', 'collection_serial', 'collection_worker', 'collection_start', 'collection_end')): np.testing.assert_array_equal(p[name][cl:ch], [v[j] for v in e['collection']])
                for name, expected in [('visit_scheduled', 'scheduled'), ('visit_bin_qualified', 'qualified'), ('visit_crew', 'members'), ('visit_start', 'starts'), ('visit_end', 'finishes')]: np.testing.assert_array_equal(p[name][lo:hi], e[expected])
                ws = slice(offsets[site], offsets[site + 1])
                for name, expected in [('worker_work_hours', 'work'), ('worker_calendar_end', 'end'), ('worker_idle_hours', 'idle')]: np.testing.assert_array_equal(p[name][ws], e[expected])
                missing_all[origins] = e['missing']; complete[site] = e['complete']; service_ok[site] = e['service_ok']
                assert p['collection_complete'][site] == e['complete'] and p['service_packed'][site] == e['service_ok']
                intervals = [[(0., e['service_each'])] for _ in range(int(workers[site]))]
                for i in range(int(cl), int(ch)):
                    worker = int(p['collection_worker'][i]); assert 0 <= worker < workers[site]
                    intervals[worker].append((float(p['collection_start'][i]), float(p['collection_end'][i])))
                for i in range(int(lo), int(hi)):
                    if not p['visit_scheduled'][i]:
                        assert (p['visit_crew'][i] == -1).all() and p['visit_start'][i] == p['visit_end'][i] == 0; continue
                    members = p['visit_crew'][i].tolist(); assert len(set(members)) == crew and all(0 <= w < workers[site] for w in members)
                    assert int(p['visit_actor'][i]) == int(x['actor'][site])
                    np.testing.assert_allclose(p['visit_end'][i] - p['visit_start'][i], p['visit_required_crew_hours'][i] / crew, atol=1e-12)
                    for w in members: intervals[w].append((float(p['visit_start'][i]), float(p['visit_end'][i])))
                for w, spans in enumerate(intervals):
                    last = 0.; work = 0.
                    for start, finish in sorted(spans): assert start >= last and finish >= start and finish <= 7 * 365 / 12; last = finish; work += finish - start
                    assert e['work'][w] <= 50.
                    np.testing.assert_allclose(work, e['work'][w], rtol=1e-11, atol=1e-9)
                np.testing.assert_allclose(e['end'], np.array(e['work']) + e['idle'], atol=1e-9)
                scheduled_counts[site] = int(e['scheduled'].sum()); qualified_counts[site] = int(e['qualified'].sum())
                used[site] = float(p['visit_required_crew_hours'][lo:hi][e['scheduled']].sum())
                col_hours = float(np.sum((counts - np.asarray(e['missing'])) * durations))
                np.testing.assert_allclose(sum(e['work']), (services[site] if e['service_ok'] else 0.) + col_hours + used[site], rtol=1e-11, atol=1e-7)
                assert used[site] <= original[key + '__used_hours'][month, site] + 1e-7
                assert col_hours <= f['work_fundable_collection_hours'][month, site] + 1e-7 and sum(e['work']) <= f['work_gross_hours'][month, site] + 1e-7
                checked_trips += len(e['collection']); checked_visits += int(hi - lo); checked_workers += int(workers[site])
            np.testing.assert_array_equal(p['collection_unpacked_counts'], missing_all)
            np.testing.assert_allclose(p['provider_required_collection_hours'], required, rtol=1e-11, atol=1e-7)
            np.testing.assert_allclose(required, f['work_required_collection_hours'][month], rtol=1e-11, atol=1e-7)
            missing = np.bincount(paths['owner'], weights=missing_all, minlength=n).astype('i8'); relevant = (workers > 0) | (required > 0) | (services > 0)
            for name, values in [('provider_missing_trips', missing), ('provider_scheduled_visits', scheduled_counts), ('provider_bin_qualified_visits', qualified_counts), ('provider_scheduled_visit_hours', used), ('relevant_provider', relevant)]: np.testing.assert_array_equal(p[name], values)
            mixed_months.append(dict(complete=complete & service_ok, scheduled=scheduled_counts, qualified=qualified_counts, missing=missing, visit_hours=used, relevant=relevant))
            old_counts = np.bincount(old_v['site'][old_v['packed']], minlength=n); np.testing.assert_array_equal(old_counts, old_v['provider_packed'])
            old_missing = np.bincount(paths['owner'], weights=old_c['unpacked_trip_counts'], minlength=n).astype('i8')
            baseline_months.append(dict(complete=old_c['collection_complete'] & old_c['service_packed'], scheduled=old_counts, qualified=old_counts,
                missing=old_missing, visit_hours=old_v['provider_visit_hours'], relevant=old_c['relevant_provider']))
            print(key, 'independent joint intervals/crew/budget check', month + 1, flush=True)
        for policy, monthly in [('collection_first', baseline_months), ('joint_duration_first', mixed_months)]:
            row = next(row for row in r['rows'] if row['key'] == key and row['policy'] == policy)
            verify_summary(row, monthly, f, x, previous, fields); cases.append((policy, key))
    assert len(cases) == 16
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(Path(__file__)), cases=cases,
        checked_collector_trips=checked_trips, checked_original_visits=checked_visits, checked_worker_bins=checked_workers,
        independent_sorted_list_joint_replay=True, physical_work_retained_when_collection_fails=True, explicit_interval_nonoverlap_and_crews=True,
        original_provider_jobs_and_monthly_channels=True, both_twelve_bin_gates_recomputed=True, all_actor_bin_summaries=True, original_maps_and_schedules_unchanged=True,
        limits='Both annual flags are necessary provider delivery-scheduling gates only;not daily food,within-bin timing,optimality,impossibility,observed staffing or authority.'))


if __name__ == '__main__': main()
