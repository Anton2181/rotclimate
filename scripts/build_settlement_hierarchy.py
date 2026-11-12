"""Run the declared market-hierarchy scenarios on the current coupled inputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from build_settlement_feedback import audit_positive, case_name, inventory_fields
from prepare_settlement_feedback import OUT as BASE
from settlement_locations_earth import sha, write
from harvest.field_support import field_support, fixed_rural_food
from polity.settlement_feedback import FeedbackInputs
from polity.settlement_hierarchy import MarketHierarchy, band_state, market_forest, year_round_links
from polity.settlement_size_shape import shape_metrics

PLAN = ROOT / 'calibration/settlement_hierarchy_20261112/plan.json'
SHAPE = ROOT / 'output/settlement_size_shape_20261112/results.json'
OUT = ROOT / 'output/settlement_hierarchy_20261112'
TAILS = {'all_places': 1.0, 'largest_50_percent': .5, 'largest_25_percent': .25}
PRODUCERS = ['scripts/build_settlement_hierarchy.py', 'polity/settlement_hierarchy.py', 'polity/settlement_feedback.py',
    'polity/settlement_residents.py', 'polity/settlement_support.py', 'polity/settlement_size_shape.py',
    'harvest/field_support.py', 'harvest/food_stocks.py']


def key_of(mode, share):
    return f'{mode}_share{round(share * 100)}'


def load(mode):
    prep = json.loads((BASE / f'{mode}_preparation.json').read_text()); path = BASE / f'{mode}_inputs.npz'
    if sha(path) != prep['inputs_sha256']:
        raise ValueError('Prepared coupled inputs changed')
    receipt = json.loads((BASE / f'{mode}_footprints.json').read_text()); footprints = BASE / f'{mode}_footprints.npz'
    if receipt['status'] != 'passed' or sha(footprints) != receipt['footprints_sha256']:
        raise ValueError('Reviewed source footprints changed')
    x = dict(np.load(path)); f = dict(np.load(footprints))
    if not np.array_equal(f['nodes'], x['nodes']):
        raise ValueError('Footprints and coupled inputs use different town nodes')
    return x, f, dict(inputs_sha256=sha(path), footprints_sha256=sha(footprints))


def model(x, parent, depth, share, hours, fraction, leg_retention=None):
    local = x['local_index']; ids = x['owner']; n = len(x['nodes'])
    freight = np.bincount(ids, weights=x['potential_kcal'][local], minlength=n)
    inputs = FeedbackInputs(x['people'][local], ids, x['potential_kcal'][local], x['boundaries'][local],
        x['listed_hours'][local], x['reaping_hours'][local], x['access'], x['civilian_request'], x['affiliated'], freight)
    return MarketHierarchy(inputs, parent, depth, forward_share=share, leg_retention=leg_retention,
        transfer_fraction=fraction, hours_worker_year=hours)


def run(mode, share, out=OUT):
    plan = json.loads(PLAN.read_text())['scenarios']
    if mode not in plan['climate_modes'] or share not in plan['forward_share']:
        raise ValueError('Scenario outside the declared test')
    x, f, hashes = load(mode)
    links = year_round_links(f['keys'], f['offsets'], f['covered'], f['landnodes'], x['nodes'])
    return solve_case(mode, share, x, links, key_of(mode, share), PLAN, out, hashes,
        link_rule='inside the cached two-day two-way footprint in all 12 bins, same actor')


def solve_case(mode, share, x, links, key, plan_path, out, hashes, *, link_rule, leg_days=None, extra_producers=()):
    """One declared scenario. leg_days[a, b] gives the slowest child-to-parent days when legs are distance scaled."""
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(plan_path.relative_to(ROOT))], cwd=ROOT) != plan_path.read_bytes():
        raise ValueError('Commit the hierarchy declaration first')
    plan = json.loads(plan_path.read_text())['scenarios']
    hours, fraction = plan['hours_worker_year'], plan['transfer_fraction']; n = len(x['nodes'])
    base_fields = BASE / case_name(mode, hours, fraction) / 'fields.npz'
    base_result = json.loads((BASE / case_name(mode, hours, fraction) / 'results.json').read_text())
    if sha(base_fields) != base_result['fields_sha256']:
        raise ValueError('Published base scenario changed')
    base = dict(np.load(base_fields))
    probe = model(x, np.full(n, -1), np.zeros(n, int), 0., hours, fraction)
    parent, depth = market_forest(probe.budget, x['actor'], links)
    days = np.zeros(n); retention = None
    if leg_days is not None:
        child = np.flatnonzero(parent >= 0); days[child] = np.maximum(1., leg_days[child, parent[child]])
        retention = np.where(parent >= 0, .95 ** days, 1.)
    # Declared regression: no forwarding must reproduce the published base scenario exactly.
    zero = model(x, parent, depth, 0., hours, fraction); solved = zero.solve(); same = zero.distribute(solved)
    if not (np.array_equal(same['residents'], base['total']) and np.array_equal(same['staff'], base['staff'])
            and np.array_equal(same['grain'], base['arrivals']) and np.array_equal(same['active'], base['active'])):
        raise ValueError('Zero forwarding does not reproduce the published base scenario')
    m = model(x, parent, depth, share, hours, fraction, retention)
    print(key, 'solving', flush=True)
    result = m.solve(); town = m.distribute(result); source_gate = audit_positive(m, result)
    local = x['local_index']
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
    own = np.where(parent >= 0, (1 - share) * town['draw'], town['draw'])
    destination = out / key; destination.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(destination / 'fields.npz', total=total, civilian=town['civil'], staff=town['staff'],
        active=town['active'], draw=town['draw'], own_catchment_residents=own, forwarded_in_residents=total - own,
        passed_people=town['passed_people'], parent=parent, depth=depth, children=children, links=np.packbits(links),
        leg_days=days, leg_retention=m.leg_retention, chain_retention=m.chain,
        arrivals=town['grain'], local_arrivals=result['flow']['arrivals'], sent_grain=town['sent_grain'],
        leg_loss=town['leg_loss'], rural=result['rural'], moved=result['moved'], budget=m.budget, upper=m.upper,
        selected_fraction=result['selected_fraction'], source_supported=result['source_supported'],
        source_deficit_origins=result['source_deficit_origins'], origin_departures=result['flow']['origin_departures'],
        base_total=base['total'], base_active=base['active'], frozen_total=base['frozen_total'],
        frozen_active=base['frozen_active'], **inventory_fields('rural_', rr), **inventory_fields('export_', export),
        **inventory_fields('town_', pooled))
    shape = json.loads(SHAPE.read_text()); band = shape['reference_band']; verdict = {}; metrics = {}
    for label, tail in TAILS.items():
        metrics[label] = shape_metrics(total, tail); verdict[label] = {}
        for name in ('gini', 'log10_sd'):
            low, high = band[label][name]
            verdict[label][name] = dict(value=metrics[label][name], reference_band=[low, high],
                state=band_state(metrics[label][name], low, high))
    states = {v['state'] for t in verdict.values() for v in t.values()}
    largest = [dict(site=int(j), residents=float(total[j]), own_catchment=float(own[j]), forwarded_in=float(total[j] - own[j]),
        children=int(children[j]), depth=int(depth[j])) for j in np.argsort(-total)[:10]]
    legs = days[parent >= 0]
    summary = dict(status='market_hierarchy_mechanism_scenario', adopt=False, key=key, climate=mode,
        hours_worker_year=hours, transfer_fraction=fraction, forward_share=share, link_rule=link_rule,
        plan_sha256=sha(plan_path), **hashes,
        base_fields_sha256=sha(base_fields), shape_results_sha256=sha(SHAPE), fields_sha256=sha(destination / 'fields.npz'),
        producers={p: sha(ROOT / p) for p in [*PRODUCERS, *extra_producers]},
        legs=dict(distance_scaled=leg_days is not None, count=int(len(legs)),
            days_median=float(np.median(legs)) if leg_days is not None and len(legs) else None,
            days_max=float(legs.max()) if leg_days is not None and len(legs) else None,
            retention_min=float(m.leg_retention[parent >= 0].min()) if len(legs) else None,
            chain_retention_min=float(m.chain.min())),
        zero_forwarding_reproduces_published_base=True,
        forest=dict(towns=n, linked_pairs_year_round=int(links.sum()), asymmetric_links=int((links != links.T).sum()),
            towns_with_parent=int((parent >= 0).sum()), roots_with_children=int(((parent < 0) & (children > 0)).sum()),
            isolated_towns=int(((parent < 0) & (children == 0)).sum()), without_actor=int((x['actor'] < 0).sum()),
            maximum_depth=int(depth.max()), maximum_children=int(children.max()),
            depth_counts={str(d): int((depth == d).sum()) for d in range(int(depth.max()) + 1)}),
        town_people=float(total.sum()), base_town_people=float(base['total'].sum()),
        civilian_people=float(town['civil'].sum()), staff_people=float(town['staff'].sum()),
        active_sources=int(town['active'].sum()), base_active_sources=int(base['active'].sum()),
        cohorts_lost=int((base['active'] & ~town['active']).sum()), cohorts_gained=int((~base['active'] & town['active']).sum()),
        viable_communities=int(town['community_viable'].sum()), base_viable_communities=int((base['civilian'] >= 50).sum()),
        positive_sites=int((total > 0).sum()), people_passed_up=float(town['passed_people'].sum()),
        grain_lost_on_forwarding_legs_kcal=float(town['leg_loss'].sum()),
        grain_sent_on_forwarding_legs_kcal=float(town['sent_grain'].sum()),
        local_collection_loss_kcal=float(result['flow']['transport_loss']),
        rural_people=float(result['rural'].sum() + x['people'][outside].sum()), population_residual=people_error,
        grain_residual_kcal=grain_residual, destination_food_unmet_kcal=float(pooled.unmet.sum()),
        local_rural_unmet_kcal=float(rr.unmet.sum()), outside_rural_unmet_kcal=float(outside_food.year.unmet.sum()),
        local_rural_deficit_origins=int(np.sum(rr.unmet > 1e-8 * np.maximum(rr.needed, 1))),
        local_production_retained=float(rr.harvested.sum() / max(1, m.x.potential_kcal.sum())),
        source_gate=source_gate, shape_metrics=metrics, base_shape_metrics={t: shape_metrics(base['total'], v) for t, v in TAILS.items()},
        shape_verdict=verdict, shape_supported=states == {'within_reference_band'},
        largest_towns=largest, search=result['search_scope'], partial_cereal_only=True,
        empirical_resident_size_fit=False, production_atlas_changed=False,
        limits='Declared share and year-round same-actor links; forwarding-leg loss as declared. Relative shape only; no absolute size, date, location or sovereignty claim.')
    write(destination / 'results.json', summary)
    print(summary['key'], 'residents', round(summary['town_people']), 'largest', round(largest[0]['residents']),
          'gini', round(metrics['all_places']['gini'], 3), 'cohorts', summary['active_sources'], summary['forest'], flush=True)
    return summary


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    p.add_argument('--share', type=float, required=True); p.add_argument('--out', type=Path, default=OUT)
    a = p.parse_args(); run(a.mode, a.share, a.out)
