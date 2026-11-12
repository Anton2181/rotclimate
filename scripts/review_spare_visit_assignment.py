"""Independent scalar spare-provider assignment and physical-hour review."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/network_visit_spare_assignment_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def independent(month, p, x, physical, pending, budget, crew):
    candidates = {}
    for i in np.flatnonzero(p['keys'][:, 0] == month):
        source = int(p['keys'][i, 1]); actor = int(x['actor'][source])
        if actor < 0 or not physical['active'][source] or physical['staff'][source] < crew: continue
        for j in range(int(p['offsets'][i]), int(p['offsets'][i + 1])):
            target = int(p['target_index'][j])
            if pending[actor, target]:
                cost = float(crew * (7 * (p['outward_days'][j] + p['inward_days'][j]) + 1))
                candidates.setdefault((actor, target), {})[source] = cost
    work = np.zeros(len(x['nodes'])); chosen = np.full(pending.shape, -1, 'i8'); cost = np.zeros(pending.shape)
    task_order = sorted(candidates, key=lambda k: (min(candidates[k].values()), k[0], k[1]))
    for actor, target in task_order:
        possible = [(h, source) for source, h in candidates[actor, target].items() if work[source] + h <= budget[source]]
        if possible:
            h, source = min(possible); chosen[actor, target] = source; cost[actor, target] = h; work[source] += h
    return dict(added=chosen >= 0, provider_for_added=chosen, cost_for_added=cost, used_hours=work, unused_hours=budget - work)


def main():
    result = json.loads((OUT / 'results.json').read_text()); saved = dict(np.load(OUT / 'fields.npz'))
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    assert sha(OUT / 'fields.npz') == result['fields_sha256']
    parent = json.loads((PARENT / 'results.json').read_text()); parent_review = json.loads((PARENT / 'review.json').read_text())
    assert parent_review['status'] == 'passed' and parent_review['results_sha256'] == sha(PARENT / 'results.json')
    old = dict(np.load(PARENT / 'fields.npz')); reviewed = []
    for mode in ('raw', 'corrected'):
        p = dict(np.load(PARENT / f'{mode}_paths.npz')); x = dict(np.load(INPUTS / f'{mode}_inputs.npz'))
        for row in (r for r in result['rows'] if r['climate'] == mode):
            key = row['key']; original = next(r for r in parent['rows'] if r['key'] == key)
            physical = dict(np.load(SEEDED / original['parent_key'] / 'fields.npz'))
            for month in range(12):
                pending = old[key + '__capacity_unmet'][month]; budget = old[key + '__unused_hours'][month]
                expected = independent(month, p, x, physical, pending, budget, row['crew'])
                for name, values in expected.items(): np.testing.assert_array_equal(saved[key + '__' + name][month], values)
                added = expected['added']; served = old[key + '__served'][month]
                assert np.all(~added | pending) and not np.any(added & served)
                # The unchanged parent is the complete earlier assignment;
                # additions touch only formerly unserved tasks and their hours.
                partition = (served | added).astype('u1') + old[key + '__route_unreachable'][month] + old[key + '__provider_work_unavailable'][month] + (pending & ~added)
                np.testing.assert_array_equal(partition, old[mode + '__demand'].astype('u1'))
                final_work = old[key + '__used_hours'][month] + expected['used_hours']
                np.testing.assert_array_equal(saved[key + '__final_patrol_used_hours'][month], final_work)
                assert np.all(final_work <= old[key + '__reserved_hours'][month] + 1e-8)
                full_unused = physical['work_gross_hours'][month] - physical['work_fundable_collection_hours'][month] - physical['work_secondary_hours'][1:, month].sum(axis=0) - final_work
                assert np.all(full_unused >= -1e-8)
                np.testing.assert_array_equal(saved[key + '__whole_provider_unused_hours'][month], full_unused)
                np.testing.assert_allclose(full_unused, physical['work_unused_hours'][month] + expected['unused_hours'], atol=1e-7)
                # Positive route/duty costs cannot consume a zero spare budget.
                assert not np.any(expected['cost_for_added'][added] <= 0)
            added = int(saved[key + '__added'].sum())
            assert row['original_completed'] == original['completed_visits'] and row['added_visits'] == added
            assert row['final_completed'] == row['original_completed'] + added
            assert row['remaining_capacity_unmet'] == original['capacity_unmet'] - added
            for field in ('requested_visits', 'route_unreachable', 'provider_work_unavailable'): assert row[field] == original[field]
            np.testing.assert_array_equal(row['added_by_bin'], saved[key + '__added'].sum(axis=(1, 2)))
            for name, field in [('added_crew_hours', 'used_hours'), ('spare_patrol_hours_after', 'unused_hours')]: assert row[name] == float(saved[key + '__' + field].sum())
            assert row['spare_patrol_hours_before'] == float(old[key + '__unused_hours'].sum()) and row['zero_spare_budget_visits'] == 0
            for a in row['actors']:
                i = a['actor_index']; previous = original['actors'][i]; count = int(saved[key + '__added'][:, i].sum())
                assert a['requested_visits'] == previous['requested_visits'] and a['original_completed'] == previous['completed_visits']
                assert a['added_visits'] == count and a['final_completed'] == a['original_completed'] + count
                assert a['remaining_capacity_unmet'] == previous['capacity_unmet'] - count
            reviewed.append(key); print('Independent spare-provider/route-cost/request/ledger checks passed:', key, flush=True)
    assert len(reviewed) == 8
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), fields_sha256=sha(OUT / 'fields.npz'),
        reviewer_sha256=sha(Path(__file__)), cases=reviewed, independent_scalar_reproduction=True, no_duplicate_or_relocated_original_visit=True,
        added_only_original_capacity_unmet=True, valid_parent_provider_specific_costs=True, all_actor_bin_partitions=True,
        only_remaining_patrol_slice_used=True, collection_and_services_unchanged=True, zero_spare_budget_control=True, all_original_maps_unchanged=True,
        limits='Constructive feasible gain only;not global optimum,irreducible remaining deficits,complete daily rosters,observed visits or authority.'))


if __name__ == '__main__': main()
