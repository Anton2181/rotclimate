"""Check collection and pooled secondary duties on unchanged coupled food plans."""
import argparse
from dataclasses import fields as dataclass_fields
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_monthly_work import OUT, PLAN
from settlement_locations_earth import sha, write
from harvest.food_stocks import periodic_food_year
from polity.settlement_support import SettlementPlan, permanent_food_ceiling
from polity.monthly_work import collection_trip_work, allocate_monthly_work

PARENT = ROOT / 'output/settlement_feedback_20261112'


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit monthly work protocol first')
    sources = {str(PLAN.relative_to(ROOT)): sha(PLAN)}
    source_paths = [Path(__file__), ROOT / 'polity/monthly_work.py', ROOT / 'polity/service_capacity.py',
                    ROOT / 'polity/settlement_support.py', ROOT / 'harvest/food_stocks.py']
    for p in source_paths:
        sources[str(p.relative_to(ROOT))] = sha(p)
    protected = json.loads((PARENT / 'atlas_publication.json').read_text())['original_packets_sha256']
    rows = []; fields = {}; food_checks = []
    for climate in ('raw', 'corrected'):
        path_receipt = json.loads((OUT / f'{climate}_paths.json').read_text())
        if sha(OUT / f'{climate}_paths.npz') != path_receipt['paths_sha256']:
            raise ValueError('Changed checked collection paths')
        for p, digest in path_receipt['sources'].items():
            if sha(ROOT / p) != digest:
                raise ValueError('Changed path parent: ' + p)
        paths = dict(np.load(OUT / f'{climate}_paths.npz'))
        x = dict(np.load(PARENT / f'{climate}_inputs.npz')); owner = x['owner']; n = len(x['nodes'])
        for p in (OUT / f'{climate}_paths.npz', OUT / f'{climate}_paths.json'):
            sources[str(p.relative_to(ROOT))] = sha(p)
        for hours in (600, 300):
            key = f'{climate}_h{hours}_f0.075'; parent = PARENT / key
            result = json.loads((parent / 'results.json').read_text()); review = json.loads((parent / 'review.json').read_text())
            if review['status'] != 'passed' or review['results_sha256'] != sha(parent / 'results.json'):
                raise ValueError('Current independent source-food review required')
            if not review['all_positive_catchments_source_supported'] or result['source_gate']['status'] != 'passed':
                raise ValueError('Original positive catchments lack source-food support')
            if result['fields_sha256'] != sha(parent / 'fields.npz'):
                raise ValueError('Changed coupled food fields')
            z = dict(np.load(parent / 'fields.npz'))
            for p in (parent / 'results.json', parent / 'fields.npz', parent / 'review.json'):
                sources[str(p.relative_to(ROOT))] = sha(p)
            total, staff = z['total'], z['staff']
            need = np.broadcast_to(total * 2500 * 365 / 12, (12, n))
            food = periodic_food_year(z['arrivals'], need, total * 2500 * 90,
                loss_fraction_year=.05, step_days=365 / 12, record=True)
            for name in ('needed', 'consumed', 'unmet', 'spoiled', 'overflow', 'initial_stock', 'final_stock'):
                np.testing.assert_allclose(getattr(food, name), z['town_' + name], rtol=1e-11, atol=1e-5)
            ceiling = permanent_food_ceiling(z['arrivals'])
            plan = SettlementPlan(ceiling, z['civilian'], staff, total, z['active'], z['civilian'] >= 50, food)
            food_checks.append(dict(key=key, people=float(total.sum()), staff=float(staff.sum()),
                source_food_review_passed=True, destination_food_replayed=True))
            demand = np.stack([np.broadcast_to(staff, (12, n)), np.broadcast_to(total / 12, (12, n)),
                               np.broadcast_to(total / 12, (12, n))])
            costs = np.array([14., 1., 2.])[:, None, None]
            fields[key + '__requested'] = demand
            for load in (60000., 120000.):
                trips, origin_hours = collection_trip_work(z['origin_departures'], paths['outward_days'],
                    paths['inward_days'], paths['access'], load_kcal=load,
                    walking_hours_day=path_receipt['walking_hours_day'], handling_hours=.25)
                collection = np.stack([np.bincount(owner, weights=h, minlength=n) for h in origin_hours])
                trip_key = f'{key}_load{int(load)}'
                fields[trip_key + '__trips'] = trips
                fields[trip_key + '__origin_hours'] = origin_hours
                for availability in ('all_open', 'bins6_7_8_closed'):
                    envelope = np.full((12, 1), 50.)
                    if availability != 'all_open':
                        envelope[6:9] = 0
                    work = allocate_monthly_work(plan, collection, demand, hours_per_staff_month=envelope,
                        source_supported=z['source_supported'], hours_per_request=costs)
                    tag = f'{trip_key}_{availability}'
                    for f in dataclass_fields(work):
                        fields[tag + '__' + f.name] = getattr(work, f.name)
                    positive = total > 0; qualified = work.qualified
                    naive_excess = np.maximum(work.fundable_collection_hours + work.invalid_reused_budget_hours - work.gross_hours, 0.)
                    actor_rows = [dict(actor_index=int(actor), original_town_people=float(total[x['actor'] == actor].sum()),
                        qualified_town_people=float(total[(x['actor'] == actor) & qualified].sum()),
                        qualified_active_sites=int((z['active'] & qualified & (x['actor'] == actor)).sum()))
                        for actor in sorted(set(x['actor'].tolist()))]
                    rows.append(dict(key=tag, parent=key, climate=climate, field_worker_hours=hours,
                        load_kcal=load, availability=availability, original_town_people=float(total.sum()),
                        original_active_sites=int(z['active'].sum()), positive_sites=int(positive.sum()),
                        qualified_positive_sites=int((positive & qualified).sum()),
                        qualified_active_sites=int((z['active'] & qualified).sum()),
                        conditional_qualified_town_people=float(total[qualified].sum()),
                        collection_deficit_sites=int((positive & np.any(work.collection_unmet_hours > 0, axis=0)).sum()),
                        positive_sites_without_staff=int((positive & (staff == 0)).sum()),
                        required_collection_hours=float(collection.sum()), collection_unmet_hours=float(work.collection_unmet_hours.sum()),
                        gross_hours=float(work.gross_hours.sum()), fundable_collection_hours=float(work.fundable_collection_hours.sum()),
                        secondary_hours=float(work.secondary_hours.sum()), unused_hours=float(work.unused_hours.sum()),
                        secondary_requested=demand.sum(axis=(1, 2)).tolist(),
                        secondary_served=work.secondary_served.sum(axis=(1, 2)).tolist(),
                        secondary_unreachable=work.secondary_unreachable.sum(axis=(1, 2)).tolist(),
                        secondary_capacity_unmet=work.secondary_capacity_unmet.sum(axis=(1, 2)).tolist(),
                        invalid_independent_budget_excess_hours=float(naive_excess.sum()),
                        invalid_independent_budget_excess_site_bins=int((naive_excess > 1e-7).sum()), actors=actor_rows))
            print(key, 'four monthly-work cases checked', flush=True)
    if len(rows) != 16:
        raise ValueError('Incomplete declared monthly scenarios')
    for path, digest in {**sources, **protected}.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Original input changed: ' + path)
    out.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out / 'fields.npz', **fields)
    write(out / 'results.json', dict(status='fixed_food_plan_monthly_work_diagnostic', adopt=False,
        sources_sha256=sources, unchanged_atlas_sha256=protected, fields_sha256=sha(out / 'fields.npz'),
        original_food_checks=food_checks, rows=rows, requests=['patrol_sessions', 'service_A', 'service_B'],
        people_food_staff_reallocated=False, actual_patrol_reach_recomputed=False,
        limits='Supplied staff-only collection/load/work/request scenarios. Refused fixed plans keep deficits visible;no reduced shipments with old food claims,no new equilibrium,census,authority or adoption.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
