"""Construct supplied integer-worker calendars for existing collection/visit plans."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.worker_calendar import pack_worker_calendar

OUT = ROOT / 'output/network_visit_calendar_20261112'
PLAN = ROOT / 'calibration/network_visit_calendar_20261112/plan.json'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'
COLLECTION = ('collection_origin', 'collection_serial', 'collection_worker', 'collection_start', 'collection_end')


def append(parts, name, value): parts.setdefault(name, []).append(np.asarray(value))


def save_packet(path, parts, arrays):
    path.parent.mkdir(parents=True, exist_ok=True)
    packet = {name: np.concatenate(values) for name, values in parts.items()}
    np.savez_compressed(path, **packet, **arrays)
    return sha(path)


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes(): raise ValueError('Commit worker-calendar declaration first')
    parent = json.loads((PARENT / 'results.json').read_text()); review = json.loads((PARENT / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(PARENT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_network_duty_visits.py')
    for path, digest in {**parent['sources'], **parent['producers'], **parent['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    sources = {}; producers = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'polity/worker_calendar.py', PLAN)}
    for p in (PARENT / 'results.json', PARENT / 'review.json', PARENT / 'fields.npz'): sources[str(p.relative_to(ROOT))] = sha(p)
    protected = dict(parent['unchanged_map_sha256']); protected['atlases/earth_fit/data/network_duty_visits.json'] = sha(ROOT / 'atlases/earth_fit/data/network_duty_visits.json')
    for p in (ROOT / 'atlases/earth_fit/data/network_visits').rglob('*'):
        if p.is_file(): protected[str(p.relative_to(ROOT))] = sha(p)
    old = dict(np.load(PARENT / 'fields.npz')); files = {}; collection_rows = []; visit_rows = []
    for mode in ('raw', 'corrected'):
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz'))
        receipt = json.loads((WORK / f'{mode}_paths.json').read_text())
        assert receipt['paths_sha256'] == sha(WORK / f'{mode}_paths.npz')
        for path, digest in receipt['sources'].items(): assert sha(ROOT / path) == digest, path
        for name in ('nodes', 'local_index', 'owner'): np.testing.assert_array_equal(paths[name], x[name])
        for p in (INPUTS / f'{mode}_inputs.npz', WORK / f'{mode}_paths.npz', WORK / f'{mode}_paths.json'): sources[str(p.relative_to(ROOT))] = sha(p)
        n = len(x['nodes']); provider_origins = [np.flatnonzero(paths['owner'] == site) for site in range(n)]
        for hours in (600, 300):
            parent_key = f'{mode}_h{hours}_load120000_all_open'; folder = SEEDED / parent_key
            r = json.loads((folder / 'results.json').read_text()); f = dict(np.load(folder / 'fields.npz'))
            assert r['fields_sha256'] == sha(folder / 'fields.npz')
            for path, digest in {**r['sources'], **r['producers']}.items(): assert sha(ROOT / path) == digest, path
            for p in (folder / 'fields.npz', folder / 'results.json'): sources[str(p.relative_to(ROOT))] = sha(p)
            workers = np.floor(f['staff']).astype('i8'); offsets = np.r_[0, np.cumsum(workers)]
            trips = f['origin_trips']; assert np.isfinite(trips).all() and np.all(trips == np.floor(trips)) and np.all(trips <= 2 ** 31 - 1)
            assert np.all(f['work_gross_hours'] >= workers[None, :] * 50 - 1e-8)
            col_summary = dict(parent_key=parent_key, climate=mode, hours_worker_year=hours, required_trips=int(trips.sum()), packed_trips=0,
                unpacked_trips=0, mandatory_failed_provider_bins=0, relevant_provider_bins=0, fractional_support_hours_removed=float((f['work_gross_hours'] - workers[None, :] * 50).sum()),
                packed_collection_hours=0., unpacked_collection_hours=0., service_unpacked_hours=0.)
            summaries = {}
            for crew in (1, 4):
                key = f'{mode}_h{hours}_crew{crew}'; previous = next(v for v in parent['rows'] if v['key'] == key)
                summaries[crew] = dict(key=key, parent_key=parent_key, climate=mode, hours_worker_year=hours, crew=crew,
                    requested_visits=previous['requested_visits'], original_planned_visits=previous['completed_visits'], packed_visits=0,
                    blocked_by_mandatory_collection=0, greedy_crew_unpacked_visits=0, packed_visit_hours=0., worker_calendar_idle_hours=0.,
                    max_worker_duty_hours=0., max_worker_calendar_end=0., packed_by_bin=[], actors=[dict(actor_index=i, packed=0, blocked_collection=0, greedy_unpacked=0) for i in range(len(old[mode + '__demand']))])
            for month in range(12):
                required_hours = np.zeros(n); durations = np.zeros(len(paths['owner'])); positive = trips[month] > 0
                assert paths['access'][month, positive].all()
                durations[positive] = 7 * (paths['outward_days'][month, positive] + paths['inward_days'][month, positive]) + .25
                np.add.at(required_hours, paths['owner'][positive], trips[month, positive] * durations[positive])
                np.testing.assert_allclose(required_hours, f['work_required_collection_hours'][month], rtol=1e-11, atol=1e-7)
                services = f['work_secondary_hours'][1:, month].sum(axis=0); base_calendars = []; collection_parts = {}
                collection_unfilled = np.zeros(len(paths['owner']), 'i8'); service_ok = np.zeros(n, bool); collection_ok = np.zeros(n, bool)
                for crew in (1, 4):
                    key = f'{mode}_h{hours}_crew{crew}'; served = old[key + '__served'][month]; aa, tt = np.where(served)
                    providers = old[key + '__provider_for_target'][month, aa, tt]; costs = old[key + '__chosen_cost_hours'][month, aa, tt]
                    order = np.argsort(providers, kind='stable'); counts = np.bincount(providers, minlength=n); boundaries = np.r_[0, np.cumsum(counts)]
                    visit_parts = {}; provider_packed = np.zeros(n, 'i8'); provider_blocked = np.zeros(n, 'i8'); provider_greedy = np.zeros(n, 'i8'); provider_used = np.zeros(n)
                    for site in range(n):
                        origins = provider_origins[site]; origins = origins[trips[month, origins] > 0]
                        indexes = order[boundaries[site]:boundaries[site + 1]]; actors, targets = aa[indexes], tt[indexes]; job_cost = costs[indexes]
                        assert (actors == x['actor'][site]).all()
                        schedule = pack_worker_calendar(workers=int(workers[site]), duty_cap_hours=50., calendar_hours=7 * 365 / 12,
                            home_service_hours=float(services[site]), collection_origin=origins, collection_count=trips[month, origins].astype('i8'),
                            collection_duration=durations[origins], visit_actor=actors, visit_target=targets, visit_duration=job_cost / crew, crew=crew)
                        if crew == 1:
                            base_calendars.append(schedule)
                            for name in COLLECTION: append(collection_parts, name, getattr(schedule, name))
                            append(collection_parts, 'collection_site', np.full(len(schedule.collection_origin), site, 'i8'))
                            collection_unfilled[origins] = schedule.collection_unpacked_counts; service_ok[site] = schedule.service_packed; collection_ok[site] = schedule.collection_complete
                        else:
                            baseline = base_calendars[site]
                            for name in (*COLLECTION, 'collection_unpacked_counts'): np.testing.assert_array_equal(getattr(schedule, name), getattr(baseline, name))
                            assert schedule.service_packed == baseline.service_packed and schedule.collection_complete == baseline.collection_complete
                        packed, blocked = schedule.visit_packed, schedule.visit_blocked_by_collection; greedy = ~packed & ~blocked
                        for name, value in [('site', np.full(len(indexes), site, 'i8')), ('actor', actors), ('target_index', targets), ('packed', packed),
                            ('blocked_collection', blocked), ('greedy_unpacked', greedy), ('crew_workers', schedule.visit_crew), ('start', schedule.visit_start), ('end', schedule.visit_end), ('required_crew_hours', job_cost),
                            ('worker_work_hours', schedule.worker_work_hours), ('worker_calendar_end', schedule.worker_calendar_end), ('worker_idle_hours', schedule.worker_idle_hours)]: append(visit_parts, name, value)
                        provider_packed[site] = int(packed.sum()); provider_blocked[site] = int(blocked.sum()); provider_greedy[site] = int(greedy.sum()); provider_used[site] = float(job_cost[packed].sum())
                        np.testing.assert_allclose(schedule.worker_work_hours.sum(), schedule.service_packed_hours + np.sum(trips[month, origins] * durations[origins]) - np.sum(schedule.collection_unpacked_counts * durations[origins]) + provider_used[site], rtol=1e-11, atol=1e-7)
                        assert provider_used[site] <= old[key + '__used_hours'][month, site] + 1e-7
                    packet = out / key / f'visits_{month:02d}.npz'
                    files[str(packet.relative_to(out))] = save_packet(packet, visit_parts, dict(worker_offsets=offsets, provider_planned=counts,
                        provider_packed=provider_packed, provider_blocked_collection=provider_blocked, provider_greedy_unpacked=provider_greedy, provider_visit_hours=provider_used))
                    summary = summaries[crew]; summary['packed_visits'] += int(provider_packed.sum()); summary['blocked_by_mandatory_collection'] += int(provider_blocked.sum())
                    summary['greedy_crew_unpacked_visits'] += int(provider_greedy.sum()); summary['packed_visit_hours'] += float(provider_used.sum())
                    summary['worker_calendar_idle_hours'] += sum(float(v.sum()) for v in visit_parts['worker_idle_hours']); summary['packed_by_bin'].append(int(provider_packed.sum()))
                    summary['max_worker_duty_hours'] = max(summary['max_worker_duty_hours'], max((float(v.max()) for v in visit_parts['worker_work_hours'] if len(v)), default=0.))
                    summary['max_worker_calendar_end'] = max(summary['max_worker_calendar_end'], max((float(v.max()) for v in visit_parts['worker_calendar_end'] if len(v)), default=0.))
                    actor_all = np.concatenate(visit_parts['actor'])
                    for a in summary['actors']:
                        selected = actor_all == a['actor_index']
                        for name, field in [('packed', 'packed'), ('blocked_collection', 'blocked_collection'), ('greedy_unpacked', 'greedy_unpacked')]: a[name] += int(np.concatenate(visit_parts[field])[selected].sum())
                packed_counts = np.bincount(np.concatenate(collection_parts['collection_site']), minlength=n)
                packed_hours = np.bincount(np.concatenate(collection_parts['collection_site']), weights=np.concatenate(collection_parts['collection_end']) - np.concatenate(collection_parts['collection_start']), minlength=n)
                relevant = (workers > 0) | (required_hours > 0) | (services > 0)
                packet = out / parent_key / f'collection_{month:02d}.npz'
                files[str(packet.relative_to(out))] = save_packet(packet, collection_parts, dict(worker_counts=workers, home_service_hours=services,
                    service_packed=service_ok, collection_complete=collection_ok, required_trip_counts=trips[month].astype('i8'),
                    unpacked_trip_counts=collection_unfilled, provider_packed_counts=packed_counts, provider_packed_hours=packed_hours,
                    provider_required_hours=required_hours, relevant_provider=relevant))
                col_summary['packed_trips'] += int(packed_counts.sum()); col_summary['unpacked_trips'] += int(collection_unfilled.sum())
                col_summary['mandatory_failed_provider_bins'] += int((relevant & ~collection_ok).sum()); col_summary['relevant_provider_bins'] += int(relevant.sum())
                col_summary['packed_collection_hours'] += float(packed_hours.sum()); col_summary['unpacked_collection_hours'] += float(np.sum(collection_unfilled * durations))
                col_summary['service_unpacked_hours'] += float(services[~service_ok].sum())
                print(parent_key, 'calendar month', month + 1, ':', int(collection_unfilled.sum()), 'collector trips unpacked;',
                    summaries[1]['packed_by_bin'][-1], '/', summaries[4]['packed_by_bin'][-1], 'crew1/4 visits packed', flush=True)
            assert col_summary['required_trips'] == col_summary['packed_trips'] + col_summary['unpacked_trips']; collection_rows.append(col_summary)
            for summary in summaries.values():
                assert summary['original_planned_visits'] == summary['packed_visits'] + summary['blocked_by_mandatory_collection'] + summary['greedy_crew_unpacked_visits']
                visit_rows.append(summary)
    assert len(collection_rows) == 4 and len(visit_rows) == 8 and len(files) == 144
    for path, digest in {**sources, **producers, **protected}.items(): assert sha(ROOT / path) == digest, path
    write(out / 'results.json', dict(status='constructive_worker_calendar_packing_diagnostic', adopt=False, collection_rows=collection_rows, visit_rows=visit_rows,
        sources=sources, producers=producers, files_sha256=files, unchanged_map_sha256=protected,
        limits='Supplied full-month worker availability,divisible home services and greedy nonpreemptive packing;failure is not impossibility. No daily provisioning,observed staff functions,empirical authority or map/default replacement.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT); main(parser.parse_args().out)
