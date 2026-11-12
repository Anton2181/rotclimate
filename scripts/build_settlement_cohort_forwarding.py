"""Run the declared cohort-protected forwarding cases on the published market links."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_settlement_feedback import audit_positive, case_name, inventory_fields
from build_settlement_hierarchy import SHAPE, TAILS, load
from build_settlement_market_range import OUT as MARKET, key_of as market_key
from prepare_settlement_feedback import OUT as BASE
from settlement_locations_earth import sha, write
from harvest.field_support import field_support, fixed_rural_food
from polity.settlement_cohort_forwarding import CohortProtectedHierarchy
from polity.settlement_feedback import FeedbackInputs
from polity.settlement_hierarchy import band_state, market_forest
from polity.settlement_size_shape import shape_metrics

PLAN = ROOT / 'calibration/settlement_cohort_forwarding_20261112/plan.json'
OUT = ROOT / 'output/settlement_cohort_forwarding_20261112'
PRODUCERS = ['scripts/build_settlement_cohort_forwarding.py', 'polity/settlement_cohort_forwarding.py', 'polity/settlement_hierarchy.py',
    'polity/settlement_feedback.py', 'polity/settlement_residents.py', 'polity/settlement_support.py', 'polity/settlement_size_shape.py',
    'harvest/field_support.py', 'harvest/food_stocks.py']


def key_of(mode, days, rule):
    return f'{mode}_range{days}_share50_{rule}'


def run(mode, days, rule, out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the cohort-forwarding declaration first')
    plan = json.loads(PLAN.read_text())['scenarios']; share = plan['forward_share'][0]
    hours, fraction = plan['hours_worker_year'], plan['transfer_fraction']
    if mode not in plan['climate_modes'] or days not in plan['range_days_each_way'] or rule not in plan['rules']:
        raise ValueError('Scenario outside the declared test')
    x, _, hashes = load(mode); n = len(x['nodes'])
    receipt = json.loads((MARKET / f'{mode}_travel.json').read_text()); travel = MARKET / f'{mode}_travel.npz'
    if sha(travel) != receipt['travel_sha256']:
        raise ValueError('Reviewed travel matrix changed')
    published_folder = MARKET / market_key(mode, days, share); published_result = json.loads((published_folder / 'results.json').read_text())
    if sha(published_folder / 'fields.npz') != published_result['fields_sha256']:
        raise ValueError('Published flat-share case changed')
    published = dict(np.load(published_folder / 'fields.npz'))
    base = dict(np.load(BASE / case_name(mode, hours, fraction) / 'fields.npz'))
    slowest = np.load(travel)['days'].astype(float).max(0)
    links = (slowest <= days) & (slowest.T <= days); np.fill_diagonal(links, False)
    local = x['local_index']; ids = x['owner']
    freight = np.bincount(ids, weights=x['potential_kcal'][local], minlength=n)
    inputs = FeedbackInputs(x['people'][local], ids, x['potential_kcal'][local], x['boundaries'][local],
        x['listed_hours'][local], x['reaping_hours'][local], x['access'], x['civilian_request'], x['affiliated'], freight)
    budget = np.bincount(ids, weights=inputs.people * fraction, minlength=n)
    parent, depth = market_forest(budget, x['actor'], links)
    if not np.array_equal(parent, published['parent']):
        raise ValueError('Forest differs from the published case')
    leg_days = np.zeros(n); child = np.flatnonzero(parent >= 0); leg_days[child] = np.maximum(1., slowest[child, parent[child]])
    retention = np.where(parent >= 0, .95 ** leg_days, 1.)

    def model(chosen_rule, floor=None):
        return CohortProtectedHierarchy(inputs, parent, depth, rule=chosen_rule, floor=floor, forward_share=share,
            leg_retention=retention, transfer_fraction=fraction, hours_worker_year=hours)
    m = model(rule); print(key_of(mode, days, rule), 'solving', flush=True)
    result = m.solve()
    # Declared regressions: same draws as the published case, and a zero floor reproduces it exactly.
    if not np.array_equal(result['total'], published['draw']):
        raise ValueError('Catchment draws differ from the published flat-share case')
    flat = model(rule, floor=0.).distribute(result)
    if not (np.array_equal(flat['residents'], published['total']) and np.array_equal(flat['grain'], published['arrivals'])
            and np.array_equal(flat['active'], published['active'])):
        raise ValueError('A zero floor does not reproduce the published flat-share case')
    town = m.distribute(result); source_gate = audit_positive(m, result)
    outside = np.flatnonzero(x['land'].ravel() & ~np.isin(np.arange(len(x['people'])), local))
    need = x['people'][outside] * 2500 * 365
    outside_work = field_support(x['potential_kcal'][outside], x['listed_hours'][outside], x['reaping_hours'][outside],
        rural_need_kcal=need, hours_worker_year=hours)
    outside_food = fixed_rural_food(outside_work.produced_kcal, x['boundaries'][outside], need)
    rr, export, pooled = result['rural_food'].year, result['flow']['export_year'], town['town_food']
    stock_change = float((rr.final_stock - rr.initial_stock).sum() + (export.final_stock - export.initial_stock).sum()
                         + (pooled.final_stock - pooled.initial_stock).sum())
    unused = float(rr.overflow.sum() - export.harvested.sum() + export.overflow.sum())
    grain_residual = float(rr.harvested.sum() - rr.consumed.sum() - rr.spoiled.sum() - unused - export.spoiled.sum()
        - result['flow']['transport_loss'] - town['leg_loss'].sum() - pooled.consumed.sum() - pooled.spoiled.sum()
        - pooled.overflow.sum() - stock_change)
    if abs(grain_residual) > 1e-7 * max(1, rr.harvested.sum()):
        raise ValueError('Source, export, forwarding and town grain ledger does not close')
    people_error = float(x['people'].sum() - x['people'][outside].sum() - result['rural'].sum() - town['residents'].sum())
    if abs(people_error) > 1e-8 * max(1, x['people'].sum()):
        raise ValueError('Whole-world rural and town population partition failed')
    total = town['residents']; children = np.bincount(parent[parent >= 0], minlength=n)
    held = total + town['passed_people']; own = town['draw'] * (1 - town['passed_fraction'])
    at_floor = m.capable & (parent >= 0) & (town['passed_people'] > 0) & np.isclose(total, m.floor)
    destination = out / key_of(mode, days, rule); destination.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination / 'fields.npz', total=total, civilian=town['civil'], staff=town['staff'], active=town['active'],
        draw=town['draw'], held_before_passing=held, own_catchment_residents=own, forwarded_in_residents=total - own,
        passed_people=town['passed_people'], passed_fraction=town['passed_fraction'], capable=m.capable, at_floor=at_floor,
        parent=parent, depth=depth, children=children, links=np.packbits(links), leg_days=leg_days, leg_retention=m.leg_retention,
        chain_retention=m.chain, arrivals=town['grain'], local_arrivals=result['flow']['arrivals'], sent_grain=town['sent_grain'],
        leg_loss=town['leg_loss'], rural=result['rural'], moved=result['moved'], budget=m.budget, upper=m.upper,
        selected_fraction=result['selected_fraction'], source_supported=result['source_supported'],
        source_deficit_origins=result['source_deficit_origins'], origin_departures=result['flow']['origin_departures'],
        base_total=base['total'], base_active=base['active'], flat_total=published['total'], flat_active=published['active'],
        **inventory_fields('rural_', rr), **inventory_fields('export_', export), **inventory_fields('town_', pooled))
    band = json.loads(SHAPE.read_text())['reference_band']; verdict = {}; metrics = {}
    for label, tail in TAILS.items():
        metrics[label] = shape_metrics(total, tail); verdict[label] = {}
        for name in ('gini', 'log10_sd'):
            low, high = band[label][name]
            verdict[label][name] = dict(value=metrics[label][name], reference_band=[low, high], state=band_state(metrics[label][name], low, high))
    states = [v['state'] for t in verdict.values() for v in t.values()]
    largest = [dict(site=int(j), residents=float(total[j]), own_catchment=float(own[j]), forwarded_in=float(total[j] - own[j]),
        children=int(children[j]), depth=int(depth[j])) for j in np.argsort(-total)[:10]]
    legs = leg_days[parent >= 0]
    summary = dict(status='cohort_protected_forwarding_scenario', adopt=False, key=key_of(mode, days, rule), climate=mode,
        hours_worker_year=hours, transfer_fraction=fraction, forward_share=share, range_days_each_way=days, rule=rule, floor_people=m.floor,
        link_rule=f'at most {days} days each way in all 12 bins on the seasonal transport graph, same actor',
        plan_sha256=sha(PLAN), **hashes, travel_sha256=receipt['travel_sha256'],
        base_fields_sha256=sha(BASE / case_name(mode, hours, fraction) / 'fields.npz'),
        flat_share_fields_sha256=published_result['fields_sha256'], shape_results_sha256=sha(SHAPE),
        fields_sha256=sha(destination / 'fields.npz'), producers={p: sha(ROOT / p) for p in PRODUCERS},
        draws_equal_published_flat_share_case=True, zero_floor_reproduces_published_flat_share_case=True,
        legs=dict(distance_scaled=True, count=int(len(legs)), days_median=float(np.median(legs)), days_max=float(legs.max()),
            retention_min=float(m.leg_retention[parent >= 0].min()), chain_retention_min=float(m.chain.min())),
        forest=dict(towns=n, linked_pairs_year_round=int(links.sum()), towns_with_parent=int((parent >= 0).sum()),
            roots_with_children=int(((parent < 0) & (children > 0)).sum()), isolated_towns=int(((parent < 0) & (children == 0)).sum()),
            without_actor=int((x['actor'] < 0).sum()), maximum_depth=int(depth.max()), maximum_children=int(children.max())),
        cohort_capable_towns=int(m.capable.sum()), capable_towns_holding_floor_before_passing=int((m.capable & (parent >= 0) & (held >= m.floor)).sum()),
        towns_left_exactly_at_floor=int(at_floor.sum()), towns_passing_people=int((town['passed_people'] > 0).sum()),
        town_people=float(total.sum()), base_town_people=float(base['total'].sum()), flat_share_town_people=float(published['total'].sum()),
        civilian_people=float(town['civil'].sum()), staff_people=float(town['staff'].sum()),
        active_sources=int(town['active'].sum()), base_active_sources=int(base['active'].sum()), flat_share_active_sources=int(published['active'].sum()),
        cohorts_lost_against_base=int((base['active'] & ~town['active']).sum()), cohorts_gained_against_base=int((~base['active'] & town['active']).sum()),
        cohorts_kept_that_flat_share_lost=int((town['active'] & ~published['active']).sum()),
        viable_communities=int(town['community_viable'].sum()), base_viable_communities=int((base['civilian'] >= 50).sum()),
        positive_sites=int((total > 0).sum()), people_passed_up=float(town['passed_people'].sum()),
        flat_share_people_passed_up=float(published['passed_people'].sum()),
        grain_lost_on_forwarding_legs_kcal=float(town['leg_loss'].sum()), grain_sent_on_forwarding_legs_kcal=float(town['sent_grain'].sum()),
        local_collection_loss_kcal=float(result['flow']['transport_loss']),
        rural_people=float(result['rural'].sum() + x['people'][outside].sum()), population_residual=people_error,
        grain_residual_kcal=grain_residual, destination_food_unmet_kcal=float(pooled.unmet.sum()),
        local_rural_unmet_kcal=float(rr.unmet.sum()), outside_rural_unmet_kcal=float(outside_food.year.unmet.sum()),
        local_rural_deficit_origins=int(np.sum(rr.unmet > 1e-8 * np.maximum(rr.needed, 1))),
        local_production_retained=float(rr.harvested.sum() / max(1, inputs.potential_kcal.sum())),
        source_gate=source_gate, shape_metrics=metrics, flat_share_shape_metrics={t: shape_metrics(published['total'], v) for t, v in TAILS.items()},
        base_shape_metrics={t: shape_metrics(base['total'], v) for t, v in TAILS.items()},
        shape_verdict=verdict, shape_checks_within_band=sum(s == 'within_reference_band' for s in states),
        shape_supported=set(states) == {'within_reference_band'}, largest_towns=largest, search=result['search_scope'],
        partial_cereal_only=True, empirical_resident_size_fit=False, production_atlas_changed=False,
        limits='Declared floor, share, range and rule on same-actor year-round links. Relative shape only; no absolute size, date, location or sovereignty claim.')
    write(destination / 'results.json', summary)
    print(summary['key'], 'residents', round(summary['town_people']), 'largest', round(largest[0]['residents']), 'gini', round(metrics['all_places']['gini'], 3),
          'checks', summary['shape_checks_within_band'], 'cohorts', summary['active_sources'], 'base', summary['base_active_sources'],
          'flat', summary['flat_share_active_sources'], 'passed', round(summary['people_passed_up']), flush=True)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    p.add_argument('--days', type=int, required=True); p.add_argument('--rule', choices=('excess', 'capped'), required=True)
    p.add_argument('--out', type=Path, default=OUT); a = p.parse_args(); run(a.mode, a.days, a.rule, a.out)
