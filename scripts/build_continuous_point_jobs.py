"""Fund NEW point jobs only from the NEW continuous-parent reserved patrol slice."""
import argparse
from dataclasses import fields as dataclass_fields
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'
PLAN=ROOT/'calibration/continuous_food_visit_calendars_20261112/plan.json'
PARENT=ROOT/'output/settlement_feedback_20261112'
PATHS=ROOT/'output/network_duty_visits_20261112'
from polity.network_visits import VisitAllocation, allocate_reserved_visits
from settlement_locations_earth import sha, write

SEEDED = ROOT / 'output/settlement_continuous_destination_20261112'


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit duty declaration first')
    producers = {str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__), ROOT / 'polity/network_visits.py', PLAN)}
    sources = {}; fields = {}; rows = []; targets_by_mode = {}; metadata = {}
    protected=dict(json.loads((ROOT/'output/continuous_collection_calendar_20261112/results.json').read_text())['unchanged_atlas_sha256'])
    # The new optional family extends these UI files;all earlier data,images and defaults stay exact.
    ui_before={name:protected.pop(name) for name in ('atlases/earth_fit/index.html','atlases/earth_fit/settled-reach.js','atlases/earth_fit/evidence.js')}
    for mode in ('raw', 'corrected'):
        prep = json.loads((PATHS / f'{mode}_paths.json').read_text())
        if prep['paths_sha256'] != sha(PATHS / f'{mode}_paths.npz'): raise ValueError('Changed recorded walking paths')
        for p, digest in prep['sources'].items():
            if sha(ROOT / p) != digest: raise ValueError('Changed duty path source: ' + p)
        paths = dict(np.load(PATHS / f'{mode}_paths.npz')); x = dict(np.load(PARENT / f'{mode}_inputs.npz'))
        for p in (PATHS / f'{mode}_paths.json', PATHS / f'{mode}_paths.npz', PARENT / f'{mode}_inputs.npz'):
            sources[str(p.relative_to(ROOT))] = sha(p)
        targets_by_mode[mode] = paths['target_nodes']; metadata[mode] = dict(target_points=len(paths['target_nodes']),
            actual_block_edge_km=prep['actual_block_edge_km'], scope='one conditional point task per actor/retained-target/bin;not whole-block territory')
        demand = paths['target_reference_masks'] > 0; n = len(x['nodes'])
        fields[mode + '__demand'] = demand
        # A pair belongs to exactly one source and one month; target indexes
        # remain stable across farm/crew scenarios and never become absences.
        pairs = []
        for month in range(12):
            selected = np.flatnonzero(paths['keys'][:, 0] == month)
            ids = np.concatenate([np.arange(paths['offsets'][i], paths['offsets'][i + 1]) for i in selected])
            provider = np.repeat(paths['keys'][selected, 1], np.diff(paths['offsets'])[selected])
            pairs.append((provider.astype(np.int64), paths['target_index'][ids].astype(np.int64),
                          7 * (paths['outward_days'][ids] + paths['inward_days'][ids]) + 1))
        for hours in (600, 300):
            parent_key = f'{mode}_h{hours}_load120000_all_open'; folder = SEEDED / parent_key
            result = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
            if review['status'] != 'passed' or review['results_sha256'] != sha(folder / 'results.json'):
                raise ValueError('Current physical food/collection certificate required')
            if review['reviewer_sha256'] != sha(ROOT / 'scripts/review_continuous_destination.py'):
                raise ValueError('Parent physical reviewer changed')
            for path, digest in {**result['sources'], **result['producers']}.items():
                if sha(ROOT / path) != digest: raise ValueError('Changed physical parent input/code: ' + path)
            if not review['all_positive_collection_work_supported'] or result['source_gate']['status'] != 'passed':
                raise ValueError('Unsupported parent cohort cannot supply duty hours')
            f = dict(np.load(folder / 'fields.npz'))
            if sha(folder / 'fields.npz') != result['fields_sha256']: raise ValueError('Changed parent population/work fields')
            for p in (folder / 'results.json', folder / 'review.json', folder / 'fields.npz'):
                sources[str(p.relative_to(ROOT))] = sha(p)
            for crew in (1, 4):
                key = f'{mode}_h{hours}_crew{crew}'; bins = []; zero_controls = []
                for month, (provider, target, cost) in enumerate(pairs):
                    budget = f['work_secondary_hours'][0, month]
                    visit = allocate_reserved_visits(provider, target, cost, provider_actor=x['actor'], supported_staff=f['staff'],
                        active=f['active'], reserved_hours=budget, demand=demand, crew=crew)
                    zero = allocate_reserved_visits(provider, target, cost, provider_actor=x['actor'], supported_staff=f['staff'],
                        active=f['active'], reserved_hours=np.zeros(n), demand=demand, crew=crew)
                    if zero.served.any() or zero.used_hours.any() or not np.array_equal(zero.route_unreachable, visit.route_unreachable):
                        raise ValueError('Zero-work control changed routes or created a free point visit')
                    bins.append(visit); zero_controls.append(zero.provider_work_unavailable)
                for field in dataclass_fields(VisitAllocation):
                    fields[key + '__' + field.name] = np.stack([getattr(v, field.name) for v in bins])
                fields[key + '__reserved_hours'] = f['work_secondary_hours'][0].copy()
                fields[key + '__zero_budget_work_unavailable'] = np.stack(zero_controls)
                served = fields[key + '__served']; used = fields[key + '__used_hours']
                collection = f['work_fundable_collection_hours']; services = f['work_secondary_hours'][1:].sum(axis=0)
                total_used = collection + services + used
                if np.any(total_used > f['work_gross_hours'] + 1e-8): raise ValueError('Actual visits reused collection/service staff hours')
                actual_unused = f['work_gross_hours'] - total_used
                np.testing.assert_allclose(actual_unused, f['work_unused_hours'] + fields[key + '__unused_hours'], rtol=1e-11, atol=1e-7)
                fields[key + '__whole_provider_unused_hours'] = actual_unused
                requested = int(demand.sum() * 12); actor_rows = []
                for actor in range(len(demand)):
                    count = int(demand[actor].sum() * 12); done = int(served[:, actor].sum())
                    actor_rows.append(dict(actor_index=actor, inventory_present=bool((x['actor'] == actor).any()),
                        requested_visits=count, completed_visits=done, completed_fraction=done / count if count else None,
                        route_unreachable=int(fields[key + '__route_unreachable'][:, actor].sum()),
                        provider_work_unavailable=int(fields[key + '__provider_work_unavailable'][:, actor].sum()),
                        capacity_unmet=int(fields[key + '__capacity_unmet'][:, actor].sum())))
                rows.append(dict(key=key, climate=mode, hours_worker_year=hours, crew=crew, parent_key=parent_key,
                    target_points=len(paths['target_nodes']), requested_visits=requested, completed_visits=int(served.sum()),
                    completed_fraction=float(served.sum() / requested) if requested else None,
                    route_unreachable=int(fields[key + '__route_unreachable'].sum()),
                    provider_work_unavailable=int(fields[key + '__provider_work_unavailable'].sum()),
                    capacity_unmet=int(fields[key + '__capacity_unmet'].sum()),
                    unfunded_walking_potential_visits=int(requested - fields[key + '__route_unreachable'].sum()),
                    reserved_patrol_hours=float(fields[key + '__reserved_hours'].sum()), visit_hours_used=float(used.sum()),
                    unused_patrol_hours=float(fields[key + '__unused_hours'].sum()), zero_budget_visits=0, actors=actor_rows,
                    whole_provider_maximum_excess=float(np.maximum(total_used - f['work_gross_hours'], 0.).max()),
                    visits_are_points_not_held_blocks=True, no_new_people_food_staff_or_transport=True))
                print(key, 'completed', rows[-1]['completed_visits'], '/', requested, 'point visits;',
                    round(rows[-1]['visit_hours_used']), 'reserved crew-hours used', flush=True)
    np.testing.assert_array_equal(targets_by_mode['raw'], targets_by_mode['corrected'])
    if len(rows) != 8: raise ValueError('Incomplete predeclared duty scenario set')
    for path, digest in {**sources, **producers, **protected}.items():
        if sha(ROOT / path) != digest: raise ValueError('Input or old map changed: ' + path)
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'funded_fields.npz', **fields)
    write(out / 'funded_results.json', dict(status='new_continuous_parent_hour_funded_point_jobs', adopt=False,
        producers=producers, sources=sources, unchanged_map_sha256=protected, fields_sha256=sha(out / 'funded_fields.npz'),
        target_metadata=metadata, rows=rows, ui_integration_snapshot_before=ui_before, original_population_food_staff_and_nonpatrol_work_unchanged=True,
        limits='Supplied target/crew/frequency/foot-only/ration and greedy-allocation scenarios. Monthly staff-hour checks,not complete individual rosters,daily provisioning,observed visits,whole-block occupation or sovereignty.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
