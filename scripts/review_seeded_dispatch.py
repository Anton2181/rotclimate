"""Independent seeded-search physical ledgers and staff-threshold certificates."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from review_settlement_feedback import inventory, cycle, repeating_initial, production, harvest_series

OUT = ROOT / 'output/settlement_dispatch_seeded_20261112'
COARSE = ROOT / 'output/settlement_dispatch_20261112'
PARENT = ROOT / 'output/settlement_feedback_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'
PLAN = ROOT / 'calibration/settlement_dispatch_seeded_20261112/plan.json'


def close(a, b):
    np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-3)


def independent_threshold(x, paths, hours, load, opened, upper):
    """Rebuild the known activation candidate without any feedback solver."""
    local = x['local_index']; owner = x['owner']; n = len(x['nodes']); pop = x['people'][local]
    target = np.where(upper >= 150., 150., 0.)
    budget = np.bincount(owner, weights=pop * .075, minlength=n)
    moved = pop * .075 * np.divide(target, budget, out=np.zeros(n), where=budget > 0)[owner]
    rural = pop - moved
    produced, _, _, _ = production(x['potential_kcal'][local], x['listed_hours'][local], x['reaping_hours'][local], rural, hours)
    supply = harvest_series(produced, x['boundaries'][local]); need = np.broadcast_to(rural * 2500 * 365 / 12, supply.shape)
    capacity = need.sum(axis=0); initial = repeating_initial(supply, need, capacity)
    year = inventory(supply, need, capacity, initial); good = year['unmet'] <= 1e-8 * np.maximum(1., capacity)
    stock = initial.copy(); overflow = []
    for harvest, demand in zip(supply, need):
        rest = np.maximum(stock + harvest - demand, 0.); overflow.append(np.maximum(rest - capacity, 0.) * good)
        stock = np.minimum(rest, capacity) * np.exp(np.log1p(-.05) / 12)
    collected = np.stack(overflow) * .1; annual = collected.sum(axis=0)
    total = np.bincount(owner, weights=annual, minlength=n)
    share = np.divide(annual, total[owner], out=np.zeros_like(annual), where=total[owner] > 0)
    freight = np.bincount(owner, weights=x['potential_kcal'][local], minlength=n)
    departure_need = np.minimum(freight[owner][None, :] * share, annual / 12) * x['access']
    initial = repeating_initial(collected, departure_need, annual)
    export = inventory(collected, departure_need, annual, initial)
    base = (departure_need - export['unmet_path']) * opened[:, None]
    active = x['affiliated'] & (target >= 150) & (x['civilian_request'] >= 50)
    gross = np.where(active, 100., 0.)[None, :] * opened[:, None] * 50.
    trip_cost = (paths['outward_days'] + paths['inward_days']) * 7 + .25
    def aggregate(a): return np.stack([np.bincount(owner, weights=v, minlength=n) for v in a])
    def feasible(scale):
        departure = base * scale[owner][None, :]
        trips = np.where(departure > 0, np.maximum(1., np.ceil(departure / load)), 0.)
        return np.all(aggregate(trips * trip_cost) <= gross, axis=0)
    full = feasible(np.ones(n)) & active
    lo = np.where(full, 1., 0.); hi = np.where(active, 1., 0.); refine = ~full & active
    for _ in range(40):
        mid = (lo + hi) / 2; fits = feasible(np.where(refine, mid, lo))
        lo = np.where(refine & fits, mid, lo); hi = np.where(refine & ~fits, mid, hi)
    arrivals = .95 * np.roll(aggregate(base * lo[owner][None, :]), 1, axis=0)
    town_need = np.broadcast_to(target * 2500 * 365 / 12, arrivals.shape); town_capacity = target * 2500 * 90
    initial = repeating_initial(arrivals, town_need, town_capacity)
    town = inventory(arrivals, town_need, town_capacity, initial)
    sources = np.bincount(owner, weights=~good, minlength=n) == 0
    return (upper >= 150.) & sources & (town['unmet'] <= 1e-10 * np.maximum(1., town['needed']))


def check(folder):
    r = json.loads((folder / 'results.json').read_text()); f = dict(np.load(folder / 'fields.npz'))
    for p, digest in {**r['sources'], **r['producers']}.items():
        assert sha(ROOT / p) == digest, p
    assert r['plan_sha256'] == sha(PLAN) and r['fields_sha256'] == sha(folder / 'fields.npz')
    x = dict(np.load(PARENT / f'{r["climate"]}_inputs.npz')); paths = dict(np.load(WORK / f'{r["climate"]}_paths.npz'))
    old = dict(np.load(PARENT / f'{r["climate"]}_h{r["hours_worker_year"]}_f0.075/fields.npz'))
    local = x['local_index']; owner = x['owner']; n = len(x['nodes']); population = x['people'][local]
    budget = np.bincount(owner, weights=population * .075, minlength=n); close(f['budget'], budget)
    moved = population * .075 * np.divide(f['total'], budget, out=np.zeros(n), where=budget > 0)[owner]
    close(f['moved'], moved); close(f['rural'], population - moved)
    close(np.bincount(owner, weights=moved, minlength=n), f['total'])
    assert np.all(f['rural'] >= 0) and np.all(f['total'] <= budget + 1e-7)
    assert np.all(f['civilian'] <= x['civilian_request'] + 1e-7)
    active = x['affiliated'] & (f['total'] >= 150) & (x['civilian_request'] >= 50)
    np.testing.assert_array_equal(active, f['active']); close(f['staff'], np.where(active, 100., 0.))
    close(f['civilian'] + f['staff'], f['total'])
    produced, retained, annual, peak = production(x['potential_kcal'][local], x['listed_hours'][local],
        x['reaping_hours'][local], f['rural'], r['hours_worker_year'])
    for name, value in [('produced_kcal', produced), ('retained', retained), ('annual_hours_available', annual),
                        ('reaping_hours_available', peak), ('annual_hours_used', produced * x['listed_hours'][local] / 1e6),
                        ('reaping_hours_used', produced * x['reaping_hours'][local] / 1e6)]:
        close(f[name], value)
    assert np.all(f['annual_hours_used'] <= annual + 1e-7) and np.all(f['reaping_hours_used'] <= peak + 1e-7)
    supply = harvest_series(produced, x['boundaries'][local])
    rural_need = np.broadcast_to(f['rural'] * 2500 * 365 / 12, supply.shape); capacity = rural_need.sum(axis=0)
    rural = inventory(supply, rural_need, capacity, f['rural_initial_stock'])
    for name, value in rural.items():
        if name != 'unmet_path': close(f['rural_' + name], value)
    cycle(rural)
    source_good = rural['unmet'] <= 1e-8 * np.maximum(1., rural_need.sum(axis=0))
    stock = f['rural_initial_stock'].copy(); overflows = []
    for harvest, need in zip(supply, rural_need):
        rest = np.maximum(stock + harvest - need, 0.); overflows.append(np.maximum(rest - capacity, 0.) * source_good)
        stock = np.minimum(rest, capacity) * np.exp(np.log1p(-.05) / 12)
    collected = np.stack(overflows) * .1; export_capacity = collected.sum(axis=0)
    total_export = np.bincount(owner, weights=export_capacity, minlength=n)
    share = np.divide(export_capacity, total_export[owner], out=np.zeros_like(export_capacity), where=total_export[owner] > 0)
    freight = np.bincount(owner, weights=x['potential_kcal'][local], minlength=n)
    reference_need = np.minimum(freight[owner][None, :] * share, export_capacity / 12) * x['access']
    initial = repeating_initial(collected, reference_need, export_capacity)
    reference = inventory(collected, reference_need, export_capacity, initial)
    close(f['reference_origin_departures'], reference_need - reference['unmet_path'])
    opened = np.ones(12, bool)
    if r['availability'] != 'all_open': opened[6:9] = False
    origin = f['reference_origin_departures'] * opened[:, None] * f['dispatch_scale'][owner][None, :]
    close(f['origin_departures'], origin)
    assert np.all(f['dispatch_scale'] >= 0) and np.all(f['dispatch_scale'] <= f['maximum_dispatch_scale'])
    assert np.all(f['maximum_dispatch_scale'] <= 1) and np.all(f['origin_departures'] <= reference_need + 1e-3)
    assert not np.any(f['origin_departures'][~x['access']] > 0) and not np.any(f['origin_departures'][:, ~source_good] > 1e-3)
    export = inventory(collected, f['origin_departures'], export_capacity, f['export_initial_stock'])
    for name, value in export.items():
        if name != 'unmet_path': close(f['export_' + name], value)
    cycle(export); assert np.all(export['unmet'] <= 1e-8 * np.maximum(1., collected.sum(axis=0)))
    def aggregate(values):
        return np.stack([np.bincount(owner, weights=v, minlength=n) for v in values])
    arrivals = np.roll(aggregate(origin), 1, axis=0) * .95; close(f['arrivals'], arrivals)
    need = np.broadcast_to(f['total'] * 2500 * 365 / 12, arrivals.shape); town_capacity = f['total'] * 2500 * 90
    town = inventory(arrivals, need, town_capacity, f['town_initial_stock'])
    for name, value in town.items():
        if name != 'unmet_path': close(f['town_' + name], value)
    cycle(town); assert np.all(town['unmet'] <= 1e-8 * np.maximum(1., town['needed']))
    positive = f['total'] > 0
    site_source_good = np.bincount(owner, weights=~source_good, minlength=n) == 0
    np.testing.assert_array_equal(f['source_supported'], site_source_good); assert site_source_good[positive].all()
    trip_cost = (paths['outward_days'] + paths['inward_days']) * 7 + .25
    def hours(departures):
        trips = np.where(departures > 0, np.maximum(1., np.ceil(departures / r['load_kcal'])), 0.)
        return trips, aggregate(trips * trip_cost)
    trips, collection = hours(origin); np.testing.assert_array_equal(f['origin_trips'], trips)
    gross = f['staff'][None, :] * opened[:, None] * 50.
    close(f['work_gross_hours'], gross); close(f['work_required_collection_hours'], collection)
    assert np.all(collection <= gross)
    _, maximum_hours = hours(f['reference_origin_departures'] * opened[:, None] * f['maximum_dispatch_scale'][owner][None, :])
    assert np.all(maximum_hours <= gross)
    assert np.all(f['dispatch_scale_upper'] - f['maximum_dispatch_scale'] <= 2 ** -40 + 1e-14)
    _, upper_hours = hours(f['reference_origin_departures'] * opened[:, None] * f['dispatch_scale_upper'][owner][None, :])
    bracketed = positive & (f['maximum_dispatch_scale'] < 1.)
    assert np.all(np.any(upper_hours > gross, axis=0)[bracketed])
    assert np.all(f['dispatch_scale'] - f['food_scalar_lower'] <= 2 ** -40 + 1e-14)
    demands = np.stack([np.broadcast_to(f['staff'], (12, n)), np.broadcast_to(f['total'] / 12, (12, n)),
                        np.broadcast_to(f['total'] / 12, (12, n))])
    cost = np.array([14., 1., 2.])[:, None, None]
    qualified = site_source_good & np.all(collection <= gross, axis=0)
    np.testing.assert_array_equal(f['work_qualified'], qualified)
    spare = (gross - collection) * qualified[None, :]; requested_hours = (demands * cost).sum(axis=0)
    fraction = np.minimum(1., np.divide(spare, requested_hours, out=np.ones_like(spare), where=requested_hours > 0))
    fraction *= qualified[None, :]
    served = demands * fraction[None, :, :]; unreachable = demands * (~qualified)[None, None, :]
    close(f['work_secondary_served'], served); close(f['work_secondary_unreachable'], unreachable)
    close(f['work_secondary_capacity_unmet'], np.maximum(demands - served - unreachable, 0.))
    close(f['work_secondary_hours'], served * cost)
    close(f['work_unused_hours'], gross - collection - (served * cost).sum(axis=0))
    assert qualified[positive].all() and not f['work_collection_unmet_hours'].any()
    for name in ('outside_index', 'outside_people', 'outside_produced', 'outside_unmet', 'outside_retained', 'old_total', 'old_active'):
        original = old[name.removeprefix('old_')] if name.startswith('old_') else old[name]
        np.testing.assert_array_equal(f[name], original)
    population_residual = float(x['people'].sum() - f['outside_people'].sum() - f['rural'].sum() - f['total'].sum())
    assert abs(population_residual) < 1e-8 * max(1., x['people'].sum()); close(r['population_residual'], population_residual)
    coarse = dict(np.load(COARSE / r['key'] / 'fields.npz'))
    for name in ('scan_feasible', 'scan_source_supported', 'scan_destination_unmet'):
        np.testing.assert_array_equal(f[name][::2], coarse[name])
    assert r['effective_model'] == 'ThresholdSeededDispatchFeedback'
    eligible = f['upper'] >= 150.
    threshold_good = independent_threshold(x, paths, r['hours_worker_year'], r['load_kcal'], opened, f['upper'])
    np.testing.assert_array_equal(f['threshold_feasible'], threshold_good)
    seeded = threshold_good & (150. > f['preseed_total'])
    np.testing.assert_array_equal(f['threshold_seeded'], seeded)
    assert r['seeded_sites'] == int(seeded.sum())
    close(r['preseed_town_people'], f['preseed_total'].sum())
    assert r['preseed_active_sources'] == int(f['preseed_active'].sum())
    for j in range(n):
        selected = np.flatnonzero(f['scan_feasible'][:, j] & (np.arange(65) > 0))
        if len(selected):
            last = selected[-1] / 64
            assert f['upper'][j] * last - 1e-6 <= f['preseed_total'][j] <= f['upper'][j] * min(1, last + 1 / 64) + 1e-6
        else: assert f['preseed_total'][j] == 0
        if seeded[j]:
            assert eligible[j] and f['total'][j] >= 150.
            next_grid = f['upper'][j] * min(1., (np.floor(150. / f['upper'][j] * 64) + 1) / 64)
            assert f['total'][j] <= next_grid + 1e-6
        else:
            close(f['total'][j], f['preseed_total'][j])
    close(f['total'], f['upper'] * f['selected_fraction'])
    if positive.any(): assert r['source_gate']['status'] == 'passed'
    else: assert r['source_gate']['status'] == 'no_positive_allocations'
    checks = [('town_people', f['total'].sum()), ('civilian_people', f['civilian'].sum()), ('staff_people', f['staff'].sum()),
        ('active_sources', f['active'].sum()), ('positive_sites', positive.sum()), ('collection_hours', collection.sum()),
        ('gross_staff_hours', gross.sum()), ('secondary_hours', (served * cost).sum()),
        ('unused_staff_hours', f['work_unused_hours'].sum()), ('departed_kcal', origin.sum()),
        ('reference_departed_kcal', f['reference_origin_departures'].sum()), ('destination_unused_kcal', town['overflow'].sum())]
    for name, value in checks: close(r[name], value)
    # Independently repeat the old-resident dispatch control from its archived
    # origin shipments; no resident/dispatch solver imported by this reviewer.
    original_base = old['origin_departures'] * opened[:, None]
    old_gross = old['staff'][None, :] * opened[:, None] * 50.
    _, original_hours = hours(original_base)
    full = np.all(original_hours <= old_gross, axis=0) & (old['total'] > 0) & (old['staff'] > 0)
    lo = np.where(full, 1., 0.); hi = np.where(old['staff'] > 0, 1., 0.)
    refine = ~full & (hi > 0) & (old['total'] > 0)
    for _ in range(40):
        mid = (lo + hi) / 2
        _, used = hours(original_base * np.where(refine, mid, lo)[owner][None, :])
        feasible = np.all(used <= old_gross, axis=0)
        lo = np.where(refine & feasible, mid, lo); hi = np.where(refine & ~feasible, mid, hi)
    control_arrivals = np.roll(aggregate(original_base * lo[owner][None, :]), 1, axis=0) * .95
    control_need = np.broadcast_to(old['total'] * 2500 * 365 / 12, control_arrivals.shape)
    control_capacity = old['total'] * 2500 * 90
    control_initial = repeating_initial(control_arrivals, control_need, control_capacity)
    control = inventory(control_arrivals, control_need, control_capacity, control_initial)
    control_feasible = old['source_supported'] & (control['unmet'] <= 1e-10 * np.maximum(1., control['needed']))
    np.testing.assert_array_equal(f['old_total_joint_feasible'], control_feasible)
    close(r['old_resident_town_people_passing_joint_dispatch'], old['total'][control_feasible].sum())
    assert r['old_resident_sites_passing_joint_dispatch'] == int(((old['total'] > 0) & control_feasible).sum())
    stock_change = sum(float((year['final_stock'] - year['initial_stock']).sum()) for year in (rural, export, town))
    unused = float(rural['overflow'].sum() - export['harvested'].sum() + export['overflow'].sum())
    residual = float(rural['harvested'].sum() - rural['consumed'].sum() - rural['spoiled'].sum() - unused
        - export['spoiled'].sum() - origin.sum() * .05 - town['consumed'].sum() - town['spoiled'].sum() - town['overflow'].sum() - stock_change)
    assert abs(residual) < 1e-7 * max(1., rural['harvested'].sum())
    # Independent recurrence and sum order subtract trillion-kcal ledgers.
    # Bound that comparison by floating-point roundoff of the actual terms,
    # retaining the original (separate) joint-balance acceptance criterion.
    residual_comparison_bound = 64 * np.finfo(float).eps * sum(abs(float(v)) for v in (
        rural['harvested'].sum(), rural['consumed'].sum(), rural['spoiled'].sum(), unused,
        export['spoiled'].sum(), origin.sum() * .05, town['consumed'].sum(), town['spoiled'].sum(),
        town['overflow'].sum(), stock_change))
    assert abs(r['grain_residual_kcal'] - residual) <= max(1e-7, residual_comparison_bound)
    # Check that the candidate retained all original population/owner inputs;
    # geographic patrol endpoints remain outside this numerical certificate.
    assert not r['adopt'] and not r['actual_patrol_footprint_qualified'] and r['all_positive_food_and_collection_qualified']
    write(folder / 'review.json', dict(status='passed', results_sha256=sha(folder / 'results.json'),
        fields_sha256=sha(folder / 'fields.npz'), reviewer_sha256=sha(Path(__file__)),
        inventory_reviewer_sha256=sha(ROOT / 'scripts/review_settlement_feedback.py'),
        positive_sites_checked=int(positive.sum()), origin_bins_checked=int(origin.size), provider_bins_checked=int(collection.size),
        direct_inventory_people_trip_and_duty_checks=True, same_source_food_gate_verified=True,
        original_outside_people_and_inputs_preserved=True, all_positive_catchments_source_supported=True,
        all_positive_collection_work_supported=True, global_optimum_or_empirical_adoption_claimed=False))
    print(r['key'], 'independent people/food/trip/monthly-work review passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--case', type=Path)
    args = parser.parse_args()
    if args.case: check(args.case)
    else:
        for folder in sorted(OUT.iterdir()):
            if folder.is_dir() and (folder / 'results.json').exists(): check(folder)
