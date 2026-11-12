"""Select one checked calendar per provider/year and preserve baseline point tasks."""
import argparse
from dataclasses import fields as dataclass_fields
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.provider_year_schedule import select_provider_years

OUT = ROOT / 'output/network_visit_year_complete_20261112'
PLAN = ROOT / 'calibration/network_visit_year_complete_20261112/plan.json'
JOINT = ROOT / 'output/network_visit_joint_order_20261112'
BASE = ROOT / 'output/network_visit_calendar_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def worker_ledgers(packet, n):
    provider = np.repeat(np.arange(n), np.diff(packet['worker_offsets']))
    work = np.bincount(provider, weights=packet['worker_work_hours'], minlength=n)
    max_work = np.zeros(n); max_end = np.zeros(n)
    np.maximum.at(max_work, provider, packet['worker_work_hours']); np.maximum.at(max_end, provider, packet['worker_calendar_end'])
    return work, max_work, max_end


def task_sets(site, actor, target, included, month, collections):
    for source, a, t in zip(site[included].tolist(), actor[included].tolist(), target[included].tolist()):
        identity = month, int(a), int(t)
        if identity in collections[source]: raise ValueError('Duplicate recorded provider task')
        collections[source].add(identity)


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes(): raise ValueError('Commit provider-year declaration first')
    joint = json.loads((JOINT / 'results.json').read_text()); checked = json.loads((JOINT / 'review.json').read_text())
    assert checked['status'] == 'passed' and checked['results_sha256'] == sha(JOINT / 'results.json')
    assert checked['reviewer_sha256'] == sha(ROOT / 'scripts/review_joint_visit_order.py')
    sources = {**joint['sources'], **joint['producers']}
    for p in (JOINT / 'results.json', JOINT / 'review.json', JOINT / 'qualification_fields.npz'): sources[str(p.relative_to(ROOT))] = sha(p)
    for name, digest in joint['files_sha256'].items(): sources[str((JOINT / name).relative_to(ROOT))] = digest
    preserved = dict(joint['unchanged_baseline_sha256'])
    preserved.update({str((JOINT / name).relative_to(ROOT)): digest for name, digest in json.loads((JOINT / 'replay.json').read_text())['byte_exact_files'].items()})
    for path, digest in {**sources, **preserved, **joint['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    producers = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'polity/provider_year_schedule.py', PLAN)}
    original = dict(np.load(PARENT / 'fields.npz')); parent = json.loads((PARENT / 'results.json').read_text())
    reference = dict(np.load(JOINT / 'qualification_fields.npz')); arrays = {}; rows = []; targets_by_mode = {}
    for mode in ('raw', 'corrected'):
        p = PARENT / f'{mode}_paths.npz'; targets_by_mode[mode] = np.load(p)['target_nodes']; sources[str(p.relative_to(ROOT))] = sha(p)
    np.testing.assert_array_equal(targets_by_mode['raw'], targets_by_mode['corrected'])
    for previous in parent['rows']:
        key, mode, crew, parent_key = (previous[n] for n in ('key', 'climate', 'crew', 'parent_key'))
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); folder = SEEDED / parent_key; f = dict(np.load(folder / 'fields.npz'))
        physical = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
        assert review['status'] == 'passed' and review['results_sha256'] == sha(folder / 'results.json')
        assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_seeded_dispatch.py') and review['all_positive_collection_work_supported']
        assert physical['source_gate']['status'] == 'passed' and physical['fields_sha256'] == sha(folder / 'fields.npz')
        for path, digest in {**physical['sources'], **physical['producers']}.items(): assert sha(ROOT / path) == digest, path
        sources[str((folder / 'review.json').relative_to(ROOT))] = sha(folder / 'review.json')
        n = len(x['nodes']); baseline_tasks = [set() for _ in range(n)]; joint_tasks = [set() for _ in range(n)]; funded = [set() for _ in range(n)]
        base_complete = []; joint_complete = []; base_ledgers = []; joint_ledgers = []
        for month in range(12):
            c = dict(np.load(BASE / parent_key / f'collection_{month:02d}.npz')); v = dict(np.load(BASE / key / f'visits_{month:02d}.npz'))
            j = dict(np.load(JOINT / key / f'calendar_{month:02d}.npz'))
            task_sets(v['site'], v['actor'], v['target_index'], v['packed'], month, baseline_tasks)
            task_sets(j['visit_site'], j['visit_actor'], j['visit_target'], j['visit_scheduled'], month, joint_tasks)
            aa, tt = np.where(original[key + '__served'][month]); owners = original[key + '__provider_for_target'][month, aa, tt]
            task_sets(owners, aa, tt, np.ones(len(aa), bool), month, funded)
            base_complete.append(c['collection_complete'] & c['service_packed']); joint_complete.append(j['collection_complete'] & j['service_packed'])
            base_work, base_max, base_end = worker_ledgers(v, n); joint_work, joint_max, joint_end = worker_ledgers(j, n)
            joint_col = np.bincount(j['collection_site'], weights=j['collection_end'] - j['collection_start'], minlength=n)
            # Original source-owner positions are the same for both policies.
            owner = x['owner']; base_missing = np.bincount(owner, weights=c['unpacked_trip_counts'], minlength=n).astype('i8')
            base_ledgers.append(dict(work_hours=base_work, max_worker_hours=base_max, max_calendar_end=base_end,
                collection_hours=c['provider_packed_hours'], visit_hours=v['provider_visit_hours'], physical_visits=v['provider_packed'], missing_trips=base_missing))
            joint_ledgers.append(dict(work_hours=joint_work, max_worker_hours=joint_max, max_calendar_end=joint_end,
                collection_hours=joint_col, visit_hours=j['provider_scheduled_visit_hours'], physical_visits=j['provider_scheduled_visits'], missing_trips=j['provider_missing_trips']))
        base_complete, joint_complete = np.stack(base_complete), np.stack(joint_complete)
        for policy, flags in [('collection_first', base_complete), ('joint_duration_first', joint_complete)]:
            np.testing.assert_array_equal(flags, reference[f'{policy}__{key}__complete'])
        selection = select_provider_years(active=f['active'], baseline_complete=base_complete, joint_complete=joint_complete,
            baseline_tasks=baseline_tasks, joint_tasks=joint_tasks, funded_tasks=funded)
        for field in dataclass_fields(selection):
            if field.name != 'qualified_tasks': arrays[key + '__' + field.name] = getattr(selection, field.name)
        served = np.zeros_like(original[key + '__served']); baseline = np.zeros_like(served); completed = np.zeros((12, n), 'i8')
        baseline_year = f['active'] & base_complete.all(axis=0)
        for site in range(n):
            if baseline_year[site]:
                for month, a, t in baseline_tasks[site]: baseline[month, a, t] = True
            for month, a, t in selection.qualified_tasks[site]:
                assert original[key + '__served'][month, a, t] and original[key + '__provider_for_target'][month, a, t] == site
                served[month, a, t] = True; completed[month, site] += 1
        assert np.all(~baseline | served) and np.all(~served | original[key + '__served'])
        calendar_unqualified = original[key + '__served'] & ~served
        arrays[key + '__served'] = served; arrays[key + '__baseline_served'] = baseline; arrays[key + '__calendar_unqualified'] = calendar_unqualified
        arrays[key + '__original_funded'] = original[key + '__served']
        arrays[mode + '__demand'] = original[mode + '__demand']
        partition = served.astype('u1') + calendar_unqualified
        for name in ('route_unreachable', 'provider_work_unavailable', 'capacity_unmet'):
            arrays[key + '__' + name] = original[key + '__' + name]; partition += original[key + '__' + name]
        np.testing.assert_array_equal(partition, np.broadcast_to(original[mode + '__demand'], served.shape).astype('u1'))
        arrays[key + '__provider_completed_visits'] = completed
        selected_bins = np.where(selection.policy[None, :] == 1, joint_complete, base_complete)
        arrays[key + '__provider_bin_complete'] = selected_bins
        np.testing.assert_array_equal(selection.mandatory_complete, f['active'] & selected_bins.all(axis=0))
        assert f['source_supported'][selection.mandatory_complete].all()
        for name in base_ledgers[0]:
            base_values = np.stack([v[name] for v in base_ledgers]); joint_values = np.stack([v[name] for v in joint_ledgers])
            arrays[key + '__provider_' + name] = np.where(selection.policy[None, :] == 1, joint_values, base_values)
        work = arrays[key + '__provider_work_hours']; visit_work = arrays[key + '__provider_visit_hours']; budget = original[key + '__reserved_hours']
        assert np.all(work <= f['work_gross_hours'] + 1e-7) and np.all(visit_work <= budget + 1e-7)
        assert np.all(arrays[key + '__provider_max_worker_hours'] <= 50.) and np.all(arrays[key + '__provider_max_calendar_end'] <= 7 * 365 / 12)
        assert not arrays[key + '__provider_missing_trips'][:, selection.mandatory_complete].any()
        np.testing.assert_allclose(arrays[key + '__provider_collection_hours'][:, selection.mandatory_complete],
            f['work_required_collection_hours'][:, selection.mandatory_complete], rtol=1e-11, atol=1e-7)
        arrays[key + '__provider_reserved_patrol_hours'] = budget
        arrays[key + '__provider_unused_patrol_hours'] = budget - visit_work
        arrays[key + '__provider_unused_staff_hours'] = f['work_gross_hours'] - work
        actors = []
        for old in previous['actors']:
            a = old['actor_index']; owned = x['actor'] == a
            actors.append(dict(actor_index=a, inventory_present=old['inventory_present'], requested_visits=old['requested_visits'],
                original_funded_visits=old['completed_visits'], baseline_twelve_bin_visits=int(baseline[:, a].sum()), qualified_visits=int(served[:, a].sum()),
                calendar_unqualified=int(calendar_unqualified[:, a].sum()), qualified_providers=int((owned & selection.mandatory_complete).sum()),
                active_parent_providers=int((owned & f['active']).sum())))
        rows.append(dict(key=key, climate=mode, hours_worker_year=previous['hours_worker_year'], crew=crew, parent_key=parent_key,
            requested_visits=previous['requested_visits'], original_funded_visits=previous['completed_visits'],
            baseline_twelve_bin_visits=int(baseline.sum()), qualified_visits=int(served.sum()), added_visits=int(served.sum() - baseline.sum()),
            calendar_unqualified=int(calendar_unqualified.sum()), route_unreachable=previous['route_unreachable'],
            provider_work_unavailable=previous['provider_work_unavailable'], capacity_unmet=previous['capacity_unmet'],
            baseline_twelve_bin_providers=int(baseline_year.sum()), qualified_providers=int(selection.mandatory_complete.sum()),
            joint_policy_providers=int(selection.policy.sum()), joint_rejected_lost_task_providers=int(selection.joint_rejected_lost_tasks.sum()),
            parent_active_providers=int(f['active'].sum()), physically_scheduled_visits=int(arrays[key + '__provider_physical_visits'].sum()),
            physically_scheduled_visit_hours=float(visit_work.sum()), baseline_tasks_lost=0, all_twelve_mandatory_bins_completed_for_qualified=True, actors=actors))
        assert rows[-1]['added_visits'] >= 0 and rows[-1]['qualified_visits'] <= rows[-1]['original_funded_visits']
        print(key, 'baseline', rows[-1]['baseline_twelve_bin_visits'], '->', rows[-1]['qualified_visits'],
            'qualified point visits;', rows[-1]['joint_policy_providers'], 'whole provider-years use joint order', flush=True)
    assert len(rows) == 8
    for path, digest in {**sources, **producers, **preserved, **joint['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', **arrays)
    write(out / 'results.json', dict(status='coherent_provider_year_point_visits', adopt=False, rows=rows, sources=sources, producers=producers,
        fields_sha256=sha(out / 'fields.npz'), unchanged_schedule_sha256=preserved, unchanged_map_sha256=joint['unchanged_map_sha256'],
        necessary_delivery_gate_only=True, baseline_gated_task_inclusion=True, original_funded_task_subset=True,
        limits='One complete calendar per provider/year;selected physical work stays charged even when unqualified. Necessary delivery-scheduling gate,not daily provisioning,within-bin timing,complete annual food validation,observed roles,optimality or authority.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT); main(parser.parse_args().out)
