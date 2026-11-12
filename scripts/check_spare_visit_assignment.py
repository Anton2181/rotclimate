"""Quantify a feasible improvement from spare same-actor patrol providers."""
import argparse
from dataclasses import fields as dataclass_fields
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.spare_visits import SpareVisits, add_spare_visits

OUT = ROOT / 'output/network_visit_spare_assignment_20261112'
PLAN = ROOT / 'calibration/network_visit_spare_assignment_20261112/plan.json'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit spare-provider declaration before diagnostic outputs')
    parent = json.loads((PARENT / 'results.json').read_text()); review = json.loads((PARENT / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(PARENT / 'results.json')
    assert review['reviewer_sha256'] == sha(ROOT / 'scripts/review_network_duty_visits.py')
    assert parent['fields_sha256'] == sha(PARENT / 'fields.npz')
    for path, digest in {**parent['sources'], **parent['producers'], **parent['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    sources = {}; producers = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'polity/spare_visits.py', PLAN)}
    for p in (PARENT / 'results.json', PARENT / 'fields.npz', PARENT / 'review.json'):
        sources[str(p.relative_to(ROOT))] = sha(p)
    protected = dict(parent['unchanged_map_sha256'])
    protected['atlases/earth_fit/data/network_duty_visits.json'] = sha(ROOT / 'atlases/earth_fit/data/network_duty_visits.json')
    for p in (ROOT / 'atlases/earth_fit/data/network_visits').rglob('*'):
        if p.is_file(): protected[str(p.relative_to(ROOT))] = sha(p)
    original = dict(np.load(PARENT / 'fields.npz')); arrays = {}; rows = []
    for mode in ('raw', 'corrected'):
        x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); paths = dict(np.load(PARENT / f'{mode}_paths.npz'))
        for p in (INPUTS / f'{mode}_inputs.npz', PARENT / f'{mode}_paths.npz'):
            sources[str(p.relative_to(ROOT))] = sha(p)
        for old in (r for r in parent['rows'] if r['climate'] == mode):
            key = old['key']; physical = dict(np.load(SEEDED / old['parent_key'] / 'fields.npz'))
            sources[str((SEEDED / old['parent_key'] / 'fields.npz').relative_to(ROOT))] = sha(SEEDED / old['parent_key'] / 'fields.npz')
            bins = []
            for month in range(12):
                selected = np.flatnonzero(paths['keys'][:, 0] == month)
                ids = np.concatenate([np.arange(paths['offsets'][i], paths['offsets'][i + 1]) for i in selected])
                provider = np.repeat(paths['keys'][selected, 1], np.diff(paths['offsets'])[selected])
                target = paths['target_index'][ids]; cost = 7 * (paths['outward_days'][ids] + paths['inward_days'][ids]) + 1
                pending = original[key + '__capacity_unmet'][month]
                kwargs = dict(provider_actor=x['actor'], supported_staff=physical['staff'], active=physical['active'], pending=pending, crew=old['crew'])
                extra = add_spare_visits(provider, target, cost, spare_hours=original[key + '__unused_hours'][month], **kwargs)
                zero = add_spare_visits(provider, target, cost, spare_hours=np.zeros(len(x['nodes'])), **kwargs)
                assert not zero.added.any() and not zero.used_hours.any()
                assert not (extra.added & original[key + '__served'][month]).any() and np.all(~extra.added | pending)
                bins.append(extra)
            for field in dataclass_fields(SpareVisits): arrays[key + '__' + field.name] = np.stack([getattr(v, field.name) for v in bins])
            final_used = original[key + '__used_hours'] + arrays[key + '__used_hours']
            arrays[key + '__final_patrol_used_hours'] = final_used
            full_unused = physical['work_gross_hours'] - physical['work_fundable_collection_hours'] - physical['work_secondary_hours'][1:].sum(axis=0) - final_used
            assert np.all(full_unused >= -1e-8)
            np.testing.assert_allclose(full_unused, physical['work_unused_hours'] + arrays[key + '__unused_hours'], atol=1e-7)
            arrays[key + '__whole_provider_unused_hours'] = full_unused
            extra = arrays[key + '__added']; added = int(extra.sum()); actors = []
            for a in old['actors']:
                count = int(extra[:, a['actor_index']].sum())
                actors.append(dict(actor_index=a['actor_index'], requested_visits=a['requested_visits'], original_completed=a['completed_visits'],
                    added_visits=count, final_completed=a['completed_visits'] + count, remaining_capacity_unmet=a['capacity_unmet'] - count))
            rows.append(dict(key=key, climate=mode, hours_worker_year=old['hours_worker_year'], crew=old['crew'],
                requested_visits=old['requested_visits'], original_completed=old['completed_visits'], added_visits=added,
                final_completed=old['completed_visits'] + added, original_capacity_unmet=old['capacity_unmet'],
                remaining_capacity_unmet=old['capacity_unmet'] - added, route_unreachable=old['route_unreachable'],
                provider_work_unavailable=old['provider_work_unavailable'], added_by_bin=extra.sum(axis=(1, 2)).astype(int).tolist(),
                added_crew_hours=float(arrays[key + '__used_hours'].sum()), spare_patrol_hours_before=float(original[key + '__unused_hours'].sum()),
                spare_patrol_hours_after=float(arrays[key + '__unused_hours'].sum()), zero_spare_budget_visits=0, actors=actors,
                original_completed_tasks_and_providers_unchanged=True, constructive_lower_bound_not_global_optimum=True))
            print(key, '+', added, 'feasible visits;', rows[-1]['remaining_capacity_unmet'], 'capacity tasks remain', flush=True)
    assert len(rows) == 8
    for path, digest in {**sources, **producers, **protected}.items(): assert sha(ROOT / path) == digest, path
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', **arrays)
    write(out / 'results.json', dict(status='constructive_spare_provider_assignment_diagnostic', adopt=False, producers=producers, sources=sources,
        fields_sha256=sha(out / 'fields.npz'), unchanged_map_sha256=protected, rows=rows,
        limits='Feasible additional whole point tasks only;not global optimality,unavoidable residual deficits,observed visits,territory,individual rosters or empirical authority.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
