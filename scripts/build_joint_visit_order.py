"""Compare fixed mixed-duration packing with immutable collection-first calendars."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from build_visit_calendars import append, save_packet
from polity.joint_worker_calendar import pack_joint_worker_calendar

OUT = ROOT / 'output/network_visit_joint_order_20261112'
PLAN = ROOT / 'calibration/network_visit_joint_order_20261112/plan.json'
BASE = ROOT / 'output/network_visit_calendar_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def summarize(policy, previous, x, f, monthly):
    complete = np.stack([m['complete'] for m in monthly]); scheduled = np.stack([m['scheduled'] for m in monthly])
    qualified = np.stack([m['qualified'] for m in monthly]); annual = f['active'] & complete.all(axis=0)
    missing = np.stack([m['missing'] for m in monthly]); relevant = np.stack([m['relevant'] for m in monthly])
    used = np.stack([m['visit_hours'] for m in monthly]); actors = []
    for old in previous['actors']:
        actor = old['actor_index']; selected = x['actor'] == actor
        actors.append(dict(actor_index=actor, inventory_present=old['inventory_present'], original_planned_visits=old['completed_visits'],
            physically_scheduled=int(scheduled[:, selected].sum()), bin_qualified=int(qualified[:, selected].sum()),
            twelve_bin_gated=int(qualified[:, selected & annual].sum()), active_providers=int((selected & f['active']).sum()),
            twelve_bin_mandatory_providers=int((selected & annual).sum())))
    row = dict(policy=policy, key=previous['key'], climate=previous['climate'], hours_worker_year=previous['hours_worker_year'], crew=previous['crew'],
        original_requested_visits=previous['requested_visits'], original_planned_visits=previous['completed_visits'],
        physically_scheduled_visits=int(scheduled.sum()), bin_qualified_visits=int(qualified.sum()),
        scheduled_with_mandatory_gaps=int(scheduled.sum() - qualified.sum()), not_scheduled_visits=int(previous['completed_visits'] - scheduled.sum()),
        twelve_bin_gated_visits=int(qualified[:, annual].sum()), twelve_bin_mandatory_providers=int(annual.sum()), active_providers=int(f['active'].sum()),
        unpacked_collector_trips=int(missing.sum()), required_collector_trips=int(f['origin_trips'].sum()),
        mandatory_failed_provider_bins=int((relevant & ~complete).sum()), relevant_provider_bins=int(relevant.sum()),
        physically_scheduled_visit_hours=float(used.sum()), scheduled_by_bin=scheduled.sum(axis=1).astype(int).tolist(),
        bin_qualified_by_bin=qualified.sum(axis=1).astype(int).tolist(), twelve_bin_gated_by_bin=qualified[:, annual].sum(axis=1).astype(int).tolist(), actors=actors)
    assert row['original_planned_visits'] == row['bin_qualified_visits'] + row['scheduled_with_mandatory_gaps'] + row['not_scheduled_visits']
    arrays = dict(complete=complete, scheduled=scheduled, qualified=qualified, annual=annual, missing=missing, visit_hours=used, relevant=relevant)
    return row, arrays


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes(): raise ValueError('Commit joint-order declaration first')
    baseline = json.loads((BASE / 'results.json').read_text()); review = json.loads((BASE / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(BASE / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_visit_calendars.py')
    sources = {**baseline['sources'], **baseline['producers']}
    for p in (BASE / 'results.json', BASE / 'review.json', BASE / 'replay.json'): sources[str(p.relative_to(ROOT))] = sha(p)
    preserved = {str((BASE / name).relative_to(ROOT)): digest for name, digest in json.loads((BASE / 'replay.json').read_text())['byte_exact_files'].items()}
    sources.update(preserved)
    for path, digest in {**sources, **baseline['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    producers = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'polity/joint_worker_calendar.py', PLAN)}
    original = dict(np.load(PARENT / 'fields.npz')); parent = json.loads((PARENT / 'results.json').read_text())
    out.mkdir(parents=True, exist_ok=True); files = {}; rows = []; gates = {}
    for previous in parent['rows']:
        key = previous['key']; mode = previous['climate']; crew = previous['crew']; parent_key = previous['parent_key']
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz')); f = dict(np.load(SEEDED / parent_key / 'fields.npz'))
        for name in ('owner', 'local_index', 'nodes'): np.testing.assert_array_equal(paths[name], x[name])
        n = len(x['nodes']); workers = np.floor(f['staff']).astype('i8'); offsets = np.r_[0, np.cumsum(workers)]
        origin_groups = [np.flatnonzero(paths['owner'] == site) for site in range(n)]
        old_monthly = []; joint_monthly = []
        for month in range(12):
            old_c = dict(np.load(BASE / parent_key / f'collection_{month:02d}.npz')); old_v = dict(np.load(BASE / key / f'visits_{month:02d}.npz'))
            old_monthly.append(dict(complete=old_c['collection_complete'] & old_c['service_packed'], scheduled=old_v['provider_packed'], qualified=old_v['provider_packed'],
                missing=np.bincount(paths['owner'], weights=old_c['unpacked_trip_counts'], minlength=n).astype('i8'),
                visit_hours=old_v['provider_visit_hours'], relevant=old_c['relevant_provider']))
            aa, tt = np.where(original[key + '__served'][month]); owners = original[key + '__provider_for_target'][month, aa, tt]
            costs = original[key + '__chosen_cost_hours'][month, aa, tt]; order = np.argsort(owners, kind='stable')
            planned = np.bincount(owners, minlength=n); boundaries = np.r_[0, np.cumsum(planned)]
            trips = f['origin_trips'][month]; assert np.all(trips == np.floor(trips)) and np.all(trips <= 2 ** 31 - 1)
            duration = np.zeros(len(trips)); positive = trips > 0; assert paths['access'][month, positive].all()
            duration[positive] = 7 * (paths['outward_days'][month, positive] + paths['inward_days'][month, positive]) + .25
            required = np.bincount(paths['owner'], weights=trips * duration, minlength=n)
            np.testing.assert_allclose(required, f['work_required_collection_hours'][month], rtol=1e-11, atol=1e-7)
            services = f['work_secondary_hours'][1:, month].sum(axis=0); parts = {}; unfilled = np.zeros(len(trips), 'i8')
            service_ok = np.zeros(n, bool); complete = np.zeros(n, bool); scheduled_counts = np.zeros(n, 'i8'); qualified_counts = np.zeros(n, 'i8'); used = np.zeros(n)
            for site in range(n):
                origins = origin_groups[site]; origins = origins[trips[origins] > 0]
                ids = order[boundaries[site]:boundaries[site + 1]]; actors, targets, visit_cost = aa[ids], tt[ids], costs[ids]
                assert (actors == x['actor'][site]).all()
                schedule = pack_joint_worker_calendar(workers=int(workers[site]), duty_cap_hours=50., calendar_hours=7 * 365 / 12, home_service_hours=float(services[site]),
                    collection_origin=origins, collection_count=trips[origins].astype('i8'), collection_duration=duration[origins],
                    visit_actor=actors, visit_target=targets, visit_duration=visit_cost / crew, crew=crew)
                for name in ('collection_origin', 'collection_serial', 'collection_worker', 'collection_start', 'collection_end'):
                    append(parts, name, getattr(schedule, name))
                append(parts, 'collection_site', np.full(len(schedule.collection_origin), site, 'i8'))
                for name, value in [('visit_site', np.full(len(ids), site, 'i8')), ('visit_actor', actors), ('visit_target', targets), ('visit_required_crew_hours', visit_cost),
                    ('visit_scheduled', schedule.visit_scheduled), ('visit_bin_qualified', schedule.visit_bin_qualified), ('visit_crew', schedule.visit_crew),
                    ('visit_start', schedule.visit_start), ('visit_end', schedule.visit_end), ('worker_work_hours', schedule.worker_work_hours),
                    ('worker_calendar_end', schedule.worker_calendar_end), ('worker_idle_hours', schedule.worker_idle_hours)]: append(parts, name, value)
                unfilled[origins] = schedule.collection_unpacked_counts; service_ok[site] = schedule.service_packed; complete[site] = schedule.collection_complete
                scheduled_counts[site] = int(schedule.visit_scheduled.sum()); qualified_counts[site] = int(schedule.visit_bin_qualified.sum())
                used[site] = float(visit_cost[schedule.visit_scheduled].sum())
                col_work = float(np.sum((trips[origins] - schedule.collection_unpacked_counts) * duration[origins]))
                np.testing.assert_allclose(schedule.worker_work_hours.sum(), schedule.service_packed_hours + col_work + used[site], rtol=1e-11, atol=1e-7)
                assert used[site] <= original[key + '__used_hours'][month, site] + 1e-7
                assert col_work <= f['work_fundable_collection_hours'][month, site] + 1e-7
                assert schedule.worker_work_hours.sum() <= f['work_gross_hours'][month, site] + 1e-7
            missing = np.bincount(paths['owner'], weights=unfilled, minlength=n).astype('i8'); relevant = (workers > 0) | (required > 0) | (services > 0)
            packet = out / key / f'calendar_{month:02d}.npz'
            files[str(packet.relative_to(out))] = save_packet(packet, parts, dict(worker_counts=workers, worker_offsets=offsets, home_service_hours=services, service_packed=service_ok,
                collection_complete=complete, required_trip_counts=trips.astype('i8'), collection_unpacked_counts=unfilled,
                provider_required_collection_hours=required, provider_missing_trips=missing, provider_planned_visits=planned,
                provider_scheduled_visits=scheduled_counts, provider_bin_qualified_visits=qualified_counts, provider_scheduled_visit_hours=used, relevant_provider=relevant))
            joint_monthly.append(dict(complete=complete & service_ok, scheduled=scheduled_counts, qualified=qualified_counts, missing=missing, visit_hours=used, relevant=relevant))
        for policy, monthly in [('collection_first', old_monthly), ('joint_duration_first', joint_monthly)]:
            row, arrays = summarize(policy, previous, x, f, monthly); rows.append(row)
            for name, values in arrays.items(): gates[f'{policy}__{key}__{name}'] = values
        print(key, 'bin-qualified', rows[-2]['bin_qualified_visits'], '->', rows[-1]['bin_qualified_visits'],
            ';twelve-bin-gated', rows[-2]['twelve_bin_gated_visits'], '->', rows[-1]['twelve_bin_gated_visits'], flush=True)
    assert len(rows) == 16 and len(files) == 96
    for path, digest in {**sources, **producers, **baseline['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    np.savez_compressed(out / 'qualification_fields.npz', **gates)
    write(out / 'results.json', dict(status='fixed_joint_order_and_necessary_delivery_gate_comparison', adopt=False, rows=rows, sources=sources, producers=producers,
        files_sha256=files, qualification_fields_sha256=sha(out / 'qualification_fields.npz'), unchanged_map_sha256=baseline['unchanged_map_sha256'], unchanged_baseline_sha256=preserved,
        annual_gate_is_necessary_delivery_schedule_only=True,
        limits='All original jobs/providers/caps retained. Physical scheduling,bin mandatory-work completion and twelve-bin provider gate are distinct. Neither policy proves optimality,impossibility,daily provisioning,within-bin grain timing,observed staffing,full annual food validation or authority.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT); main(parser.parse_args().out)
