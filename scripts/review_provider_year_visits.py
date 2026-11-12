"""Independently select whole provider-years from recorded tasks and work ledgers."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_year_complete_20261112'
PLAN = ROOT / 'calibration/network_visit_year_complete_20261112/plan.json'
JOINT = ROOT / 'output/network_visit_joint_order_20261112'
BASE = ROOT / 'output/network_visit_calendar_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def physical_certificate(folder, reviewer):
    result = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(folder / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts' / reviewer)
    return result


def main():
    r = json.loads((OUT / 'results.json').read_text()); saved = dict(np.load(OUT / 'fields.npz'))
    for path, digest in {**r['sources'], **r['producers'], **r['unchanged_schedule_sha256'], **r['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    assert sha(OUT / 'fields.npz') == r['fields_sha256'] and len(r['rows']) == 8
    physical_certificate(JOINT, 'review_joint_visit_order.py'); physical_certificate(BASE, 'review_visit_calendars.py')
    original = dict(np.load(PARENT / 'fields.npz')); parent = json.loads((PARENT / 'results.json').read_text()); targets = {}
    for mode in ('raw', 'corrected'): targets[mode] = np.load(PARENT / f'{mode}_paths.npz')['target_nodes']
    np.testing.assert_array_equal(targets['raw'], targets['corrected'])
    reviewed = []; worker_blocks = 0
    for row in r['rows']:
        key, mode, crew, parent_key = (row[n] for n in ('key', 'climate', 'crew', 'parent_key'))
        previous = next(v for v in parent['rows'] if v['key'] == key); x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); folder = SEEDED / parent_key
        physical = physical_certificate(folder, 'review_seeded_dispatch.py'); assert physical['source_gate']['status'] == 'passed'
        f = dict(np.load(folder / 'fields.npz')); n = len(x['nodes']); tasks = [[set() for _ in range(n)] for _ in range(3)]
        complete = [[], []]; packets = []
        for month in range(12):
            c = dict(np.load(BASE / parent_key / f'collection_{month:02d}.npz')); v = dict(np.load(BASE / key / f'visits_{month:02d}.npz')); j = dict(np.load(JOINT / key / f'calendar_{month:02d}.npz'))
            packets.append((c, v, j)); complete[0].append(c['collection_complete'] & c['service_packed']); complete[1].append(j['collection_complete'] & j['service_packed'])
            for source, a, t in zip(v['site'][v['packed']].tolist(), v['actor'][v['packed']].tolist(), v['target_index'][v['packed']].tolist()):
                assert x['actor'][source] == a; tasks[0][source].add((month, a, t))
            for source, a, t in zip(j['visit_site'][j['visit_scheduled']].tolist(), j['visit_actor'][j['visit_scheduled']].tolist(), j['visit_target'][j['visit_scheduled']].tolist()):
                assert x['actor'][source] == a; tasks[1][source].add((month, a, t))
            for a, t in zip(*np.where(original[key + '__served'][month])):
                source = int(original[key + '__provider_for_target'][month, a, t]); tasks[2][source].add((month, int(a), int(t)))
        complete = np.asarray(complete); policies = np.zeros(n, 'i1'); annual = np.zeros(n, bool); base_count = np.zeros(n, 'i8'); selected_count = np.zeros(n, 'i8'); rejected = np.zeros(n, bool)
        qualified = np.zeros_like(original[key + '__served']); baseline = np.zeros_like(qualified); counts = np.zeros((12, n), 'i8')
        for site in range(n):
            baseline_ok = bool(f['active'][site]) and all(complete[0, :, site]); joint_ok = bool(f['active'][site]) and all(complete[1, :, site])
            assert tasks[0][site] <= tasks[2][site] and tasks[1][site] <= tasks[2][site]
            lost = tasks[0][site] - tasks[1][site]; extra = tasks[1][site] - tasks[0][site]
            choice = 0
            if baseline_ok:
                rejected[site] = joint_ok and bool(lost)
                if joint_ok and not lost and extra: choice = 1
            elif joint_ok: choice = 1
            policies[site] = choice; annual[site] = joint_ok if choice else baseline_ok
            before = tasks[0][site] if baseline_ok else set(); after = tasks[choice][site] if annual[site] else set()
            assert before <= after and after <= tasks[2][site]
            base_count[site] = len(before); selected_count[site] = len(after)
            for month, a, t in before: baseline[month, a, t] = True
            for month, a, t in after:
                assert not qualified[month, a, t] and original[key + '__provider_for_target'][month, a, t] == site
                qualified[month, a, t] = True; counts[month, site] += 1
        for name, values in [('policy', policies), ('mandatory_complete', annual), ('baseline_task_counts', base_count), ('selected_task_counts', selected_count),
            ('added_task_counts', selected_count - base_count), ('joint_rejected_lost_tasks', rejected), ('served', qualified), ('baseline_served', baseline),
            ('calendar_unqualified', original[key + '__served'] & ~qualified), ('original_funded', original[key + '__served']), ('provider_completed_visits', counts)]: np.testing.assert_array_equal(saved[key + '__' + name], values)
        assert np.all(~baseline | qualified) and np.all(~qualified | original[key + '__served']) and f['source_supported'][annual].all()
        partition = qualified.astype('u1') + saved[key + '__calendar_unqualified']
        for name in ('route_unreachable', 'provider_work_unavailable', 'capacity_unmet'):
            np.testing.assert_array_equal(saved[key + '__' + name], original[key + '__' + name]); partition += original[key + '__' + name]
            assert row[name] == previous[name]
        np.testing.assert_array_equal(partition, np.broadcast_to(original[mode + '__demand'], qualified.shape))
        np.testing.assert_array_equal(saved[mode + '__demand'], original[mode + '__demand'])
        for month, (c, v, j) in enumerate(packets):
            for site, policy in enumerate(policies):
                source = j if policy else v; lo, hi = source['worker_offsets'][site:site + 2]
                work = source['worker_work_hours'][lo:hi]; end = source['worker_calendar_end'][lo:hi]
                assert hi - lo == int(np.floor(f['staff'][site])) and np.all(work <= 50.) and np.all(end <= 7 * 365 / 12)
                actual = sum(float(h) for h in work); max_work = max(work, default=0.); max_end = max(end, default=0.)
                np.testing.assert_allclose(actual, saved[key + '__provider_work_hours'][month, site], rtol=1e-12, atol=1e-7)
                assert saved[key + '__provider_max_worker_hours'][month, site] == max_work and saved[key + '__provider_max_calendar_end'][month, site] == max_end
                if policy:
                    col_hours = sum(float(b - a) for a, b in zip(j['collection_start'][j['collection_site'] == site], j['collection_end'][j['collection_site'] == site]))
                    visit_hours = float(j['provider_scheduled_visit_hours'][site]); visits = int(j['provider_scheduled_visits'][site]); missing = int(j['provider_missing_trips'][site])
                    bin_ok = bool(j['collection_complete'][site] and j['service_packed'][site])
                else:
                    col_hours = float(c['provider_packed_hours'][site]); visit_hours = float(v['provider_visit_hours'][site]); visits = int(v['provider_packed'][site])
                    missing = int(c['unpacked_trip_counts'][x['owner'] == site].sum()); bin_ok = bool(c['collection_complete'][site] and c['service_packed'][site])
                for name, value in [('collection_hours', col_hours), ('visit_hours', visit_hours), ('physical_visits', visits), ('missing_trips', missing), ('bin_complete', bin_ok)]:
                    np.testing.assert_allclose(saved[key + '__provider_' + name][month, site], value, rtol=1e-12, atol=1e-7)
                if annual[site]:
                    assert bin_ok and missing == 0
                    np.testing.assert_allclose(col_hours, f['work_required_collection_hours'][month, site], rtol=1e-11, atol=1e-7)
                assert actual <= f['work_gross_hours'][month, site] + 1e-7 and visit_hours <= original[key + '__reserved_hours'][month, site] + 1e-7
                worker_blocks += 1
            np.testing.assert_array_equal(saved[key + '__provider_reserved_patrol_hours'][month], original[key + '__reserved_hours'][month])
            np.testing.assert_allclose(saved[key + '__provider_unused_patrol_hours'][month], original[key + '__reserved_hours'][month] - saved[key + '__provider_visit_hours'][month], atol=1e-7)
            np.testing.assert_allclose(saved[key + '__provider_unused_staff_hours'][month], f['work_gross_hours'][month] - saved[key + '__provider_work_hours'][month], atol=1e-7)
        values = dict(requested_visits=previous['requested_visits'], original_funded_visits=previous['completed_visits'], baseline_twelve_bin_visits=int(baseline.sum()),
            qualified_visits=int(qualified.sum()), added_visits=int(qualified.sum() - baseline.sum()), calendar_unqualified=int((original[key + '__served'] & ~qualified).sum()),
            baseline_twelve_bin_providers=int((f['active'] & complete[0].all(axis=0)).sum()), qualified_providers=int(annual.sum()), joint_policy_providers=int(policies.sum()),
            joint_rejected_lost_task_providers=int(rejected.sum()), parent_active_providers=int(f['active'].sum()),
            physically_scheduled_visits=int(saved[key + '__provider_physical_visits'].sum()), physically_scheduled_visit_hours=float(saved[key + '__provider_visit_hours'].sum()))
        for name, value in values.items(): assert row[name] == value, (key, name)
        assert row['baseline_tasks_lost'] == 0 and row['all_twelve_mandatory_bins_completed_for_qualified']
        for a in row['actors']:
            i = a['actor_index']; owned = x['actor'] == i; previous_actor = previous['actors'][i]
            assert a['inventory_present'] == previous_actor['inventory_present'] and a['requested_visits'] == previous_actor['requested_visits'] and a['original_funded_visits'] == previous_actor['completed_visits']
            for name, value in [('baseline_twelve_bin_visits', baseline[:, i].sum()), ('qualified_visits', qualified[:, i].sum()),
                ('calendar_unqualified', (original[key + '__served'][:, i] & ~qualified[:, i]).sum()), ('qualified_providers', (owned & annual).sum()), ('active_parent_providers', (owned & f['active']).sum())]: assert a[name] == int(value)
        reviewed.append(key); print('Independent whole-year selection,task inclusion and source ledgers passed:', key, flush=True)
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), fields_sha256=sha(OUT / 'fields.npz'), reviewer_sha256=sha(Path(__file__)), cases=reviewed,
        independently_replayed_provider_year_rule=True, source_physical_certificates_current=True, complete_worker_source_blocks_checked=worker_blocks,
        baseline_task_identity_inclusion=True, original_funded_task_subset=True, one_policy_all_twelve_bins=True, selected_physical_work_charged=True,
        all_actor_request_partitions=True, climate_target_ids_exact=True, original_maps_and_schedules_unchanged=True,
        limits='Necessary delivery-scheduling gate only;not daily provisioning,within-bin timing,full annual food validation,observed roles,optimality or authority.'))


if __name__ == '__main__': main()
