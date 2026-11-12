"""Run the declared collection-work/dispatch/resident feedback on exact parents."""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import fields as dataclass_fields
import itertools
import json
from pathlib import Path
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from build_settlement_feedback import audit_positive, inventory_fields
from polity.settlement_feedback import FeedbackInputs
from polity.settlement_dispatch import DispatchFeedback
from polity.monthly_work import allocate_monthly_work

OUT = ROOT / 'output/settlement_dispatch_20261112'
PLAN = ROOT / 'calibration/settlement_dispatch_20261112/plan.json'
PARENT = ROOT / 'output/settlement_feedback_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'


def case_key(mode, hours, load, profile):
    return f'{mode}_h{hours}_load{int(load)}_{profile}'


def run(mode, hours, load, profile, out=OUT):
    start = time.monotonic(); key = case_key(mode, hours, load, profile); folder = out / key
    folder.mkdir(parents=True, exist_ok=True)
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit exact joint dispatch declaration before outputs')
    old_folder = PARENT / f'{mode}_h{hours}_f0.075'
    old_result = json.loads((old_folder / 'results.json').read_text()); old_review = json.loads((old_folder / 'review.json').read_text())
    if old_review['status'] != 'passed' or old_review['results_sha256'] != sha(old_folder / 'results.json'):
        raise ValueError('Original food/source review missing or stale')
    if old_result['fields_sha256'] != sha(old_folder / 'fields.npz'):
        raise ValueError('Changed original food fields')
    paths_receipt = json.loads((WORK / f'{mode}_paths.json').read_text())
    for path, digest in paths_receipt['sources'].items():
        if sha(ROOT / path) != digest:
            raise ValueError('Changed original collection source: ' + path)
    if paths_receipt['paths_sha256'] != sha(WORK / f'{mode}_paths.npz'):
        raise ValueError('Changed checked collection paths')
    work_review = json.loads((WORK / 'review.json').read_text())
    if work_review['status'] != 'passed' or work_review['results_sha256'] != sha(WORK / 'results.json'):
        raise ValueError('Independent fixed-plan collection review required')
    sources = {str(p.relative_to(ROOT)): sha(p) for p in [PLAN, PARENT / f'{mode}_inputs.npz',
        old_folder / 'results.json', old_folder / 'review.json', old_folder / 'fields.npz',
        WORK / f'{mode}_paths.json', WORK / f'{mode}_paths.npz', WORK / 'results.json', WORK / 'review.json']}
    producer_paths = [Path(__file__), ROOT / 'polity/settlement_dispatch.py', ROOT / 'polity/settlement_feedback.py',
        ROOT / 'polity/monthly_work.py', ROOT / 'polity/service_capacity.py', ROOT / 'polity/settlement_residents.py',
        ROOT / 'polity/settlement_support.py', ROOT / 'harvest/field_support.py', ROOT / 'harvest/food_stocks.py',
        ROOT / 'scripts/build_settlement_feedback.py']
    producers = {str(p.relative_to(ROOT)): sha(p) for p in producer_paths}
    x = dict(np.load(PARENT / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz'))
    old_fields = dict(np.load(old_folder / 'fields.npz')); local = x['local_index']; owner = x['owner']; n = len(x['nodes'])
    inputs = FeedbackInputs(x['people'][local], owner, x['potential_kcal'][local], x['boundaries'][local],
        x['listed_hours'][local], x['reaping_hours'][local], x['access'], x['civilian_request'], x['affiliated'],
        np.bincount(owner, weights=x['potential_kcal'][local], minlength=n))
    opened = np.ones(12, bool)
    if profile == 'bins6_7_8_closed':
        opened[6:9] = False
    m = DispatchFeedback(inputs, outward_days=paths['outward_days'], inward_days=paths['inward_days'],
        load_kcal=load, monthly_open=opened, transfer_fraction=.075, hours_worker_year=hours)
    old_control = m.evaluate(old_fields['total'])
    print(key, 'solving joint resident/dispatch feedback', flush=True)
    result = m.solve(); source_gate = audit_positive(m, result)
    demand = np.stack([np.broadcast_to(result['staff'], (12, n)), np.broadcast_to(result['total'] / 12, (12, n)),
                       np.broadcast_to(result['total'] / 12, (12, n))])
    work = allocate_monthly_work(result['plan'], result['collection_hours'], demand,
        hours_per_staff_month=m.hour_envelope, source_supported=result['source_supported'],
        hours_per_request=np.array([14., 1., 2.])[:, None, None])
    if np.any((result['total'] > 0) & ~work.qualified):
        raise ValueError('Final positive resident case failed food/monthly collection qualification')
    rural, export, town = result['rural_food'].year, result['flow']['export_year'], result['town_food']
    stock_change = float((rural.final_stock - rural.initial_stock).sum() + (export.final_stock - export.initial_stock).sum()
                         + (town.final_stock - town.initial_stock).sum())
    unused = float(rural.overflow.sum() - export.harvested.sum() + export.overflow.sum())
    grain_residual = float(rural.harvested.sum() - rural.consumed.sum() - rural.spoiled.sum() - unused - export.spoiled.sum()
        - result['flow']['transport_loss'] - town.consumed.sum() - town.spoiled.sum() - town.overflow.sum() - stock_change)
    if abs(grain_residual) > 1e-7 * max(1., rural.harvested.sum()):
        raise ValueError('Joint grain ledger failed')
    fields = dict(total=result['total'], civilian=result['civil'], staff=result['staff'], active=result['active'],
        rural=result['rural'], moved=result['moved'], budget=m.budget, upper=m.upper,
        selected_fraction=result['selected_fraction'], refined_upper_fraction=result['refined_upper_fraction'],
        source_supported=result['source_supported'], source_deficit_origins=result['source_deficit_origins'],
        produced_kcal=result['work'].produced_kcal, retained=result['work'].retained,
        annual_hours_used=result['work'].annual_hours_used, reaping_hours_used=result['work'].reaping_hours_used,
        annual_hours_available=result['work'].annual_hours_available, reaping_hours_available=result['work'].reaping_hours_available,
        origin_departures=result['flow']['origin_departures'], arrivals=result['flow']['arrivals'],
        reference_origin_departures=result['reference_origin_departures'], origin_trips=result['origin_trips'],
        maximum_dispatch_scale=result['maximum_dispatch_scale'], dispatch_scale_upper=result['dispatch_scale_upper'],
        dispatch_scale=result['dispatch_scale'], food_scalar_lower=result['food_scalar_lower'],
        scan_feasible=np.stack([s['feasible'] for s in result['scan']]),
        scan_source_supported=np.stack([s['source_supported'] for s in result['scan']]),
        scan_destination_unmet=np.stack([s['destination_unmet'] for s in result['scan']]),
        old_total=old_fields['total'], old_active=old_fields['active'], old_total_joint_feasible=old_control['feasible'],
        **{name: old_fields[name] for name in ('outside_index', 'outside_people', 'outside_produced', 'outside_unmet', 'outside_retained')},
        **inventory_fields('rural_', rural), **inventory_fields('export_', export), **inventory_fields('town_', town))
    for f in dataclass_fields(work):
        fields['work_' + f.name] = getattr(work, f.name)
    np.savez_compressed(folder / 'fields.npz', **fields)
    fixed = next(r for r in json.loads((WORK / 'results.json').read_text())['rows']
        if r['parent'] == f'{mode}_h{hours}_f0.075' and r['load_kcal'] == load and r['availability'] == profile)
    people_error = float(x['people'].sum() - old_fields['outside_people'].sum() - result['rural'].sum() - result['total'].sum())
    summary = dict(status='joint_work_dispatch_resident_scenario', adopt=False, key=key, climate=mode,
        hours_worker_year=hours, transfer_fraction=.075, load_kcal=load, availability=profile,
        plan_sha256=sha(PLAN), sources=sources, producers=producers, fields_sha256=sha(folder / 'fields.npz'),
        original_town_people=float(old_fields['total'].sum()), original_active_sources=int(old_fields['active'].sum()),
        fixed_plan_qualified_town_people=fixed['conditional_qualified_town_people'], fixed_plan_qualified_sources=fixed['qualified_active_sites'],
        old_resident_town_people_passing_joint_dispatch=float(old_fields['total'][old_control['feasible']].sum()),
        old_resident_sites_passing_joint_dispatch=int(((old_fields['total'] > 0) & old_control['feasible']).sum()),
        town_people=float(result['total'].sum()), civilian_people=float(result['civil'].sum()), staff_people=float(result['staff'].sum()),
        active_sources=int(result['active'].sum()), viable_communities=int(result['plan'].community_viable.sum()),
        positive_sites=int((result['total'] > 0).sum()), rural_people=float(result['rural'].sum() + old_fields['outside_people'].sum()),
        origin_people=float(x['people'].sum()), population_residual=people_error, grain_residual_kcal=grain_residual,
        source_gate=source_gate, local_rural_unmet_kcal=float(rural.unmet.sum()),
        local_rural_deficit_origins=int((rural.unmet > 1e-8 * np.maximum(1., rural.needed)).sum()),
        outside_rural_unmet_kcal=float(old_fields['outside_unmet'].sum()),
        local_production_retained=float(rural.harvested.sum() / max(1., inputs.potential_kcal.sum())),
        collection_hours=float(result['collection_hours'].sum()), gross_staff_hours=float(work.gross_hours.sum()),
        secondary_hours=float(work.secondary_hours.sum()), unused_staff_hours=float(work.unused_hours.sum()),
        collection_unmet_hours=float(work.collection_unmet_hours.sum()), departed_kcal=float(result['flow']['origin_departures'].sum()),
        reference_departed_kcal=float(result['reference_origin_departures'].sum()), destination_unused_kcal=float(town.overflow.sum()),
        all_positive_food_and_collection_qualified=True, actual_patrol_footprint_qualified=False,
        original_model_packets_changed=False, search=result['search_scope'],
        limits='Supplied partial-cereal/staff/load scenarios;uniform catchment dispatch family and examined resident search,not global schedule optimization,empirical sizes or authority.')
    for p, digest in {**sources, **producers}.items():
        if sha(ROOT / p) != digest:
            raise ValueError('Original input changed during run: ' + p)
    write(folder / 'results.json', summary)
    print(key, 'complete:', round(summary['town_people']), 'town people;', summary['active_sources'],
          'sources;', round(time.monotonic() - start, 1), 'seconds', flush=True)
    return summary


def task(args):
    return run(*args)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true'); parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--mode', choices=('raw', 'corrected')); parser.add_argument('--hours', type=int, choices=(600, 300))
    parser.add_argument('--load', type=int, choices=(60000, 120000)); parser.add_argument('--availability', choices=('all_open', 'bins6_7_8_closed'))
    parser.add_argument('--out', type=Path, default=OUT); a = parser.parse_args()
    if a.all:
        jobs = [(*c, a.out) for c in itertools.product(('raw', 'corrected'), (600, 300), (60000, 120000), ('all_open', 'bins6_7_8_closed'))]
        with ProcessPoolExecutor(max_workers=a.jobs) as executor:
            list(executor.map(task, jobs))
    else:
        if any(v is None for v in (a.mode, a.hours, a.load, a.availability)):
            parser.error('Use --all or supply all four case options')
        run(a.mode, a.hours, a.load, a.availability, a.out)
