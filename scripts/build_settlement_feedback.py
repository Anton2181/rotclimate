"""Run the declared cell-resident/work/food feedback on current atlas inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, PLAN, DATA
from settlement_locations_earth import sha, write
from polity.settlement_feedback import FeedbackInputs, CerealFeedback
from polity.settlement_residents import allocate_residents, audit_origin_food, ResidentAllocation
from polity.settlement_support import SettlementPlan
from harvest.field_support import field_support, fixed_rural_food
from harvest.food_stocks import periodic_food_year


def case_name(mode, hours, fraction):
    return f'{mode}_h{hours}_f{fraction:g}'


def inventory_fields(prefix, year):
    return {prefix + k: getattr(year, k) for k in ('initial_stock', 'final_stock', 'harvested', 'needed',
        'consumed', 'unmet', 'spoiled', 'overflow', 'ledger_residual')}


def audit_positive(m, final):
    """Apply the preceding source-food gate to every positive catchment.

    Unsupported rural origins elsewhere remain visible in the whole-world
    ledger. They are not silently included in a successful all-people claim.
    """
    sites = np.flatnonzero(final['total'] > 0)
    if not len(sites):
        return dict(status='no_positive_allocations', positive_sites=0)
    lookup = np.full(len(m.budget), -1, int); lookup[sites] = np.arange(len(sites))
    origins = lookup[m.x.owner] >= 0; owner = lookup[m.x.owner[origins]]
    total = final['total'][sites]; need = np.broadcast_to(total * m.kcal_day * m.year_days / 12, (12, len(sites)))
    arrivals = final['flow']['arrivals'][:, sites]
    dest = periodic_food_year(arrivals, need, total * m.kcal_day * m.destination_store_days,
        loss_fraction_year=m.loss_fraction_year, step_days=m.year_days / 12, record=True)
    plan = SettlementPlan(final['plan'].food_ceiling_people[sites], final['civil'][sites],
        final['staff'][sites], total, final['active'][sites], final['civil'][sites] >= m.minimum_community, dest)
    allocation = ResidentAllocation(plan, m.x.people[origins], final['rural'][origins], final['moved'][origins],
        m.budget[sites], owner, arrivals, m.kcal_day, m.year_days, m.destination_store_days, m.loss_fraction_year)
    capacity = final['rural_food'].year.needed * m.rural_store_days / m.year_days + final['flow']['export_capacity']
    result = audit_origin_food(allocation, final['rural_food'].harvest[:, origins],
        final['flow']['origin_departures'][:, origins], origin_capacity_kcal=capacity[origins],
        retention=m.collection_options['retention'], delay_bins=m.collection_options['delay_bins'],
        loss_fraction_year=m.loss_fraction_year)
    return dict(status='passed', positive_sites=len(sites), source_origins=int(origins.sum()),
        joint_residual_kcal=result['joint_residual_kcal'],
        scope='Additional pooled-store feasibility gate on positive catchments; detailed two-store ledger separately retained.')


def run(mode, hours, fraction, out=OUT):
    key = case_name(mode, hours, fraction); destination = out / key; destination.mkdir(parents=True, exist_ok=True)
    # The source declaration precedes ALL new feedback outputs.
    committed = subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT)
    if committed != PLAN.read_bytes():
        raise ValueError('Commit the exact feedback declaration first')
    plan = json.loads(PLAN.read_text())
    if dict(hours_worker_year=hours, transfer_fraction=fraction) not in plan['scenarios'] or mode not in plan['climate_modes']:
        raise ValueError('Scenario outside the declared experiment')
    prep = json.loads((OUT / f'{mode}_preparation.json').read_text()); path = OUT / f'{mode}_inputs.npz'
    if sha(path) != prep['inputs_sha256'] or prep['plan_sha256'] != sha(PLAN):
        raise ValueError('Prepared inputs or protocol changed')
    for name, digest in prep['sources'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Prepared input source changed: ' + name)
    x = dict(np.load(path)); local = x['local_index']; ids = x['owner']; n = len(x['nodes'])
    freight = np.bincount(ids, weights=x['potential_kcal'][local], minlength=n)
    inputs = FeedbackInputs(x['people'][local], ids, x['potential_kcal'][local], x['boundaries'][local],
        x['listed_hours'][local], x['reaping_hours'][local], x['access'], x['civilian_request'],
        x['affiliated'], freight)
    m = CerealFeedback(inputs, transfer_fraction=fraction, hours_worker_year=hours)
    zero = m.evaluate(np.zeros(n))
    frozen = allocate_residents(zero['flow']['arrivals'], inputs.people, ids, inputs.civilian_request,
        inputs.affiliated, transfer_fraction=fraction)
    print(key, 'solving coupled cell feedback', flush=True)
    result = m.solve()
    source_gate = audit_positive(m, result)
    # Land outside the local collection partition is retained, with its original
    # population, meals and workers. It never vanishes from the grain ledger.
    outside = np.flatnonzero(x['land'].ravel() & ~np.isin(np.arange(len(x['people'])), local))
    need = x['people'][outside] * 2500 * 365
    outside_work = field_support(x['potential_kcal'][outside], x['listed_hours'][outside], x['reaping_hours'][outside],
        rural_need_kcal=need, hours_worker_year=hours)
    outside_food = fixed_rural_food(outside_work.produced_kcal, x['boundaries'][outside], need)
    rr, export, town = result['rural_food'].year, result['flow']['export_year'], result['town_food']
    stock_change = float((rr.final_stock - rr.initial_stock).sum() + (export.final_stock - export.initial_stock).sum()
                         + (town.final_stock - town.initial_stock).sum())
    unused = float(rr.overflow.sum() - export.harvested.sum() + export.overflow.sum())
    grain_residual = float(rr.harvested.sum() - rr.consumed.sum() - rr.spoiled.sum() - unused - export.spoiled.sum()
        - result['flow']['transport_loss'] - town.consumed.sum() - town.spoiled.sum() - town.overflow.sum() - stock_change)
    if abs(grain_residual) > 1e-7 * max(1, rr.harvested.sum()):
        raise ValueError('Coupled source/export/destination grain ledger does not close')
    fields = dict(total=result['total'], civilian=result['civil'], staff=result['staff'], active=result['active'],
        rural=result['rural'], moved=result['moved'], budget=m.budget, upper=m.upper,
        selected_fraction=result['selected_fraction'], refined_upper_fraction=result['refined_upper_fraction'],
        source_supported=result['source_supported'], source_deficit_origins=result['source_deficit_origins'],
        produced_kcal=result['work'].produced_kcal, retained=result['work'].retained,
        annual_hours_used=result['work'].annual_hours_used, reaping_hours_used=result['work'].reaping_hours_used,
        annual_hours_available=result['work'].annual_hours_available, reaping_hours_available=result['work'].reaping_hours_available,
        origin_departures=result['flow']['origin_departures'], arrivals=result['flow']['arrivals'],
        outside_index=outside, outside_people=x['people'][outside], outside_produced=outside_work.produced_kcal,
        outside_unmet=outside_food.year.unmet, outside_retained=outside_work.retained,
        frozen_total=frozen.settlement.total_people, frozen_active=frozen.settlement.institutional_active,
        scan_feasible=np.stack([s['feasible'] for s in result['scan']]),
        scan_source_supported=np.stack([s['source_supported'] for s in result['scan']]),
        scan_destination_unmet=np.stack([s['destination_unmet'] for s in result['scan']]),
        **inventory_fields('rural_', rr), **inventory_fields('export_', export), **inventory_fields('town_', town))
    np.savez_compressed(destination / 'fields.npz', **fields)
    people_error = float(x['people'].sum() - outside_food.year.needed.sum() / (2500 * 365)
                         - result['rural'].sum() - result['total'].sum())
    if abs(people_error) > 1e-8 * max(1, x['people'].sum()):
        raise ValueError('Full-world rural/town population partition failed')
    positive = result['total'] > 0
    summary = dict(status='cell_population_work_food_feedback_scenario', adopt=False, key=key, climate=mode,
        hours_worker_year=hours, transfer_fraction=fraction, plan_sha256=sha(PLAN),
        inputs_sha256=sha(path), preparation_sha256=sha(OUT / f'{mode}_preparation.json'),
        fields_sha256=sha(destination / 'fields.npz'),
        producers={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'polity/settlement_feedback.py',
            ROOT / 'polity/settlement_residents.py', ROOT / 'harvest/field_support.py', ROOT / 'harvest/food_stocks.py',
            ROOT / 'polity/settlement_support.py']},
        origin_people=float(x['people'].sum()), local_origin_people=float(inputs.people.sum()),
        town_people=float(result['total'].sum()), civilian_people=float(result['civil'].sum()),
        staff_people=float(result['staff'].sum()), active_sources=int(result['active'].sum()),
        viable_communities=int(result['plan'].community_viable.sum()), positive_sites=int(positive.sum()),
        frozen_reference_town_people=float(frozen.settlement.total_people.sum()),
        frozen_reference_sources=int(frozen.settlement.institutional_active.sum()),
        rural_people=float(result['rural'].sum() + x['people'][outside].sum()), population_residual=people_error,
        local_rural_unmet_kcal=float(rr.unmet.sum()), outside_rural_unmet_kcal=float(outside_food.year.unmet.sum()),
        local_rural_deficit_origins=int(np.sum(rr.unmet > 1e-8 * np.maximum(rr.needed, 1))),
        outside_rural_deficit_origins=int(np.sum(outside_food.year.unmet > 1e-8 * np.maximum(outside_food.year.needed, 1))),
        source_gate=source_gate, grain_residual_kcal=grain_residual,
        local_produced_kcal=float(rr.harvested.sum()), outside_produced_kcal=float(outside_food.year.harvested.sum()),
        local_reference_production_kcal=float(inputs.potential_kcal.sum()),
        local_production_retained=float(rr.harvested.sum() / max(1, inputs.potential_kcal.sum())),
        maximum_annual_hours_excess=float(np.maximum(result['work'].annual_hours_used - result['work'].annual_hours_available, 0).max()),
        maximum_reaping_hours_excess=float(np.maximum(result['work'].reaping_hours_used - result['work'].reaping_hours_available, 0).max()),
        destination_food_unmet_kcal=float(town.unmet.sum()), positive_sites_source_supported=bool(result['source_supported'][positive].all()),
        all_world_rural_food_supported=bool(not np.any(outside_food.year.unmet > 1e-8 * np.maximum(outside_food.year.needed, 1))
            and not np.any(rr.unmet > 1e-8 * np.maximum(rr.needed, 1))),
        search=result['search_scope'], partial_cereal_only=True, empirical_resident_size_fit=False,
        production_atlas_changed=False, reach_recomputed=False,
        limits='Same local people/grain origins; unlike earlier wide trade catchments. Rural deficits remain explicit and block positive allocations in affected catchments. Scenario work/shares, incomplete diet/household work; no historical adoption.')
    write(destination / 'results.json', summary)
    print(key, 'town', round(summary['town_people']), 'staffed', summary['active_sources'],
          'source gate', source_gate['status'], 'rural deficit cells', summary['local_rural_deficit_origins'], flush=True)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    p.add_argument('--hours', type=int, required=True); p.add_argument('--fraction', type=float, default=.075)
    p.add_argument('--out', type=Path, default=OUT); a = p.parse_args(); run(a.mode, a.hours, a.fraction, a.out)
