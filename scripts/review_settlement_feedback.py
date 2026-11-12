"""Independently certify cell population, work, inventories and shipments.

Direct monthly recurrence does not import the feedback or food/work solvers.
It certifies saved final allocations, not a global optimum of the search.
"""
import argparse
import gzip
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, DATA, PLAN
from settlement_locations_earth import sha, write
from population.export import decode_harvest

OUTSIDE_CACHE = {}


def close(a, b):
    np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-3)


def inventory(supply, need, capacity, initial):
    """Direct FAO-style meal/overflow/decay ledger from a supplied cycle state."""
    stock = np.array(initial, float, copy=True); first = stock.copy()
    consumed = np.zeros_like(stock); unmet = consumed.copy(); spoiled = consumed.copy(); spilled = consumed.copy()
    missing = []
    for harvest, demand in zip(supply, need):
        available = stock + harvest
        eaten = np.minimum(available, demand); deficit = demand - eaten
        rest = available - eaten; extra = np.maximum(rest - capacity, 0.)
        kept = np.minimum(rest, capacity); stock = kept * np.exp(np.log1p(-.05) / 12)
        consumed += eaten; unmet += deficit; spoiled += kept - stock; spilled += extra; missing.append(deficit)
    return dict(initial_stock=first, final_stock=stock, harvested=supply.sum(0), needed=need.sum(0),
        consumed=consumed, unmet=unmet, spoiled=spoiled, overflow=spilled,
        ledger_residual=first + supply.sum(0) - consumed - spoiled - spilled - stock,
        unmet_path=np.stack(missing))


def cycle(year):
    # Match the pre-existing FoodYear convergence criterion, which scales
    # with annual throughput, not a possibly tiny boundary stock.
    scale = np.maximum(1., np.maximum(year['harvested'], year['needed']))
    assert np.all(np.abs(year['final_stock'] - year['initial_stock']) <=
                  (1e-10 + 128 * np.finfo(float).eps) * scale)


def repeating_initial(supply, need, capacity):
    low = np.zeros_like(capacity); high = np.array(capacity, float, copy=True)
    empty = inventory(supply, need, capacity, low)['final_stock'] == 0
    for _ in range(60):
        mid = (low + high) / 2
        end = inventory(supply, need, capacity, mid)['final_stock']
        low = np.where(end > mid, mid, low); high = np.where(end <= mid, mid, high)
    return np.where(empty, 0., high)


def production(potential, listed, reaping, people, hours):
    annual = people * .4 * hours
    peak = people * .4 * min(hours, 8 * 30)
    year_ratio = np.divide(annual, potential * listed / 1e6, out=np.ones_like(potential), where=potential * listed > 0)
    peak_ratio = np.divide(peak, potential * reaping / 1e6, out=np.ones_like(potential), where=potential * reaping > 0)
    retained = np.minimum(1, np.minimum(year_ratio, peak_ratio)); retained[potential == 0] = 0
    return potential * retained, retained, annual, peak


def harvest_series(energy, boundaries):
    first = np.array([next((m for m in range(12) if int(mask) & (1 << m)), 0) for mask in boundaries])
    result = np.zeros((12, len(energy))); result[first, np.arange(len(energy))] = energy
    return result


def check_case(folder, x):
    r = json.loads((folder / 'results.json').read_text()); f = dict(np.load(folder / 'fields.npz'))
    for p, digest in r['producers'].items():
        assert sha(ROOT / p) == digest, p
    assert r['fields_sha256'] == sha(folder / 'fields.npz') and r['plan_sha256'] == sha(PLAN)
    assert r['inputs_sha256'] == sha(OUT / f'{r["climate"]}_inputs.npz')
    assert r['preparation_sha256'] == sha(OUT / f'{r["climate"]}_preparation.json')
    local = x['local_index']; ids = x['owner']; n = len(x['nodes']); pop = x['people'][local]
    budget = np.bincount(ids, weights=pop * r['transfer_fraction'], minlength=n)
    close(f['budget'], budget)
    can_staff = x['affiliated'] & (x['civilian_request'] >= 50) & (budget >= 150)
    close(f['upper'], np.minimum(budget, x['civilian_request'] + np.where(can_staff, 100., 0.)))
    moved = pop * r['transfer_fraction'] * np.divide(f['total'], budget, out=np.zeros(n), where=budget > 0)[ids]
    close(f['moved'], moved); close(f['rural'], pop - moved)
    close(np.bincount(ids, weights=moved, minlength=n), f['total'])
    assert np.all(f['rural'] >= 0) and np.all(f['total'] <= budget + 1e-7)
    assert np.all(f['civilian'] <= x['civilian_request'] + 1e-7)
    active = x['affiliated'] & (f['total'] >= 150) & (x['civilian_request'] >= 50)
    np.testing.assert_array_equal(active, f['active']); close(f['staff'], np.where(active, 100., 0.))
    close(f['civilian'] + f['staff'], f['total'])
    produced, retained, annual, peak = production(x['potential_kcal'][local], x['listed_hours'][local],
        x['reaping_hours'][local], f['rural'], r['hours_worker_year'])
    close(f['produced_kcal'], produced); close(f['retained'], retained)
    close(f['annual_hours_used'], produced * x['listed_hours'][local] / 1e6)
    close(f['reaping_hours_used'], produced * x['reaping_hours'][local] / 1e6)
    close(f['annual_hours_available'], annual); close(f['reaping_hours_available'], peak)
    assert np.all(f['annual_hours_used'] <= annual + 1e-7)
    assert np.all(f['reaping_hours_used'] <= peak + 1e-7)
    supply = harvest_series(produced, x['boundaries'][local]); rural_need = np.broadcast_to(f['rural'] * 2500 * 365 / 12, supply.shape)
    rural_capacity = rural_need.sum(0)
    rural = inventory(supply, rural_need, rural_capacity, f['rural_initial_stock'])
    for k, v in rural.items():
        if k != 'unmet_path':
            close(v, f['rural_' + k])
    cycle(rural)
    good = f['rural_unmet'] <= 1e-8 * np.maximum(1, rural_need.sum(0))
    # Reconstruct each month's overflow directly; use the independently
    # replayed beginning stocks rather than the producer's exportable helper.
    stock = f['rural_initial_stock'].copy(); overflows = []
    for harvest, demand in zip(supply, rural_need):
        rest = np.maximum(stock + harvest - demand, 0)
        overflows.append(np.maximum(rest - rural_capacity, 0) * good)
        stock = np.minimum(rest, rural_capacity) * np.exp(np.log1p(-.05) / 12)
    collected = np.stack(overflows) * .1; annual_export = collected.sum(0)
    total_export = np.bincount(ids, weights=annual_export, minlength=n)
    shares = np.divide(annual_export, total_export[ids], out=np.zeros_like(annual_export), where=total_export[ids] > 0)
    freight = np.bincount(ids, weights=x['potential_kcal'][local], minlength=n)
    export_need = np.minimum(freight[ids][None, :] * shares, annual_export / 12) * x['access']
    export = inventory(collected, export_need, annual_export, f['export_initial_stock'])
    for k, v in export.items():
        if k != 'unmet_path':
            close(v, f['export_' + k])
    cycle(export)
    departures = export_need - export['unmet_path']; close(departures, f['origin_departures'])
    assert not np.any(f['origin_departures'][:, ~good] > 1e-7)
    assert not np.any(f['origin_departures'][~x['access']] > 1e-7)
    site_departures = np.stack([np.bincount(ids, weights=d, minlength=n) for d in departures])
    arrivals = np.roll(site_departures, 1, axis=0) * .95; close(arrivals, f['arrivals'])
    need = np.broadcast_to(f['total'] * 2500 * 365 / 12, arrivals.shape)
    town = inventory(arrivals, need, f['total'] * 2500 * 90, f['town_initial_stock'])
    for k, v in town.items():
        if k != 'unmet_path':
            close(v, f['town_' + k])
    cycle(town)
    positive = f['total'] > 0
    source_good = np.bincount(ids, weights=~good, minlength=n) == 0
    np.testing.assert_array_equal(f['source_deficit_origins'], np.bincount(ids, weights=~good, minlength=n).astype(int))
    np.testing.assert_array_equal(source_good, f['source_supported'])
    assert np.all(source_good[positive]) and np.all(f['town_unmet'] <= 1e-8 * np.maximum(f['town_needed'], 1))
    for j in range(n):
        selected = np.flatnonzero(f['scan_feasible'][:, j] & (np.arange(33) > 0))
        if len(selected):
            last = selected[-1] / 32
            assert last - 1e-12 <= f['selected_fraction'][j] <= min(1, last + 1 / 32) + 1e-12
        else:
            assert f['selected_fraction'][j] == 0
    close(f['total'], f['upper'] * f['selected_fraction'])
    outside = np.flatnonzero(x['land'].ravel() & ~np.isin(np.arange(len(x['people'])), local))
    np.testing.assert_array_equal(outside, f['outside_index']); close(x['people'][outside], f['outside_people'])
    outside_produced, outside_retained, _, _ = production(x['potential_kcal'][outside], x['listed_hours'][outside],
        x['reaping_hours'][outside], x['people'][outside], r['hours_worker_year'])
    close(outside_produced, f['outside_produced']); close(outside_retained, f['outside_retained'])
    cache_key = (r['inputs_sha256'], r['hours_worker_year'])
    if cache_key not in OUTSIDE_CACHE:
        outside_supply = harvest_series(outside_produced, x['boundaries'][outside])
        outside_need = np.broadcast_to(x['people'][outside] * 2500 * 365 / 12, outside_supply.shape)
        initial = repeating_initial(outside_supply, outside_need, outside_need.sum(0))
        outside_food = inventory(outside_supply, outside_need, outside_need.sum(0), initial)
        throughput = np.maximum(1., np.maximum(outside_supply.sum(0), outside_need.sum(0)))
        OUTSIDE_CACHE[cache_key] = (outside_food, throughput)
    outside_food, throughput = OUTSIDE_CACHE[cache_key]
    # This replay finds the limiting cycle more precisely than the producer.
    # Its initial bracket is1e-10 of annual throughput wide, and unmet food is
    # 1-Lipschitz in initial stock. Certify that original numerical bound.
    outside_error = np.abs(outside_food['unmet'] - f['outside_unmet'])
    assert np.all(outside_error <= (1e-10 + 128 * np.finfo(float).eps) * throughput)
    stock_change = sum(float((v['final_stock'] - v['initial_stock']).sum()) for v in (rural, export, town))
    unused = rural['overflow'].sum() - export['harvested'].sum() + export['overflow'].sum()
    balance = float(rural['harvested'].sum() - rural['consumed'].sum() - rural['spoiled'].sum() - unused
        - export['spoiled'].sum() - site_departures.sum() * .05 - town['consumed'].sum()
        - town['spoiled'].sum() - town['overflow'].sum() - stock_change)
    assert abs(balance) < 1e-9 * max(1, supply.sum())
    population_balance = float(x['people'].sum() - f['outside_people'].sum() - f['rural'].sum() - f['total'].sum())
    assert abs(population_balance) < 1e-7
    close(r['town_people'], f['total'].sum()); close(r['staff_people'], f['staff'].sum())
    assert r['active_sources'] == int(active.sum()) and r['positive_sites'] == int(positive.sum())
    assert r['source_gate']['status'] == 'passed' and r['source_gate']['positive_sites'] == int(positive.sum())
    assert not r['adopt'] and not r['empirical_resident_size_fit'] and not r['production_atlas_changed']
    write(folder / 'review.json', dict(status='passed', results_sha256=sha(folder / 'results.json'),
        reviewer_sha256=sha(Path(__file__)), local_origins=len(local), outside_origins=len(outside),
        positive_sites_checked=int(positive.sum()), independent_monthly_inventory_recurrence=True,
        people_work_meals_shipments_verified=True, grain_residual_kcal=balance,
        population_residual=population_balance, zero_exports_from_rural_deficits=True,
        all_positive_catchments_source_supported=True, outside_rural_deficits_preserved=True,
        outside_cycle_replay_error_max_kcal=float(outside_error.max()),
        global_optimum_or_empirical_adoption_claimed=False))
    print(r['key'], 'independent population/work/monthly-grain review passed', flush=True)


def check_inputs(mode):
    path = OUT / f'{mode}_inputs.npz'; prep = json.loads((OUT / f'{mode}_preparation.json').read_text())
    assert prep['inputs_sha256'] == sha(path)
    for p, digest in prep['sources'].items():
        assert sha(ROOT / p) == digest, p
    x = dict(np.load(path)); shape = tuple(x['shape']); folder = DATA / ('corrected' if mode == 'corrected' else '')
    packet = json.loads((DATA / 'settled_reach.json').read_text())['packets'][mode]
    with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as f:
        prefix = f.read(packet['offsets']['masks'])
    owner = np.frombuffer(prefix, '<u2', count=int(np.prod(shape)), offset=packet['offsets']['catchments'])
    np.testing.assert_array_equal(x['local_index'], np.flatnonzero(owner > 0))
    np.testing.assert_array_equal(x['owner'], owner[x['local_index']] - 1)
    alpha = np.asarray(Image.open(ROOT / 'data/source/elevation.png').convert('RGBA'))[..., 3] > 128
    fraction = alpha.reshape(shape[0], alpha.shape[0] // shape[0], shape[1], alpha.shape[1] // shape[1]).mean((1, 3))
    # geometry returns float32 land fractions; the legacy area multiplication
    # retains float32 before crop energy promotes it to float64. Verify that
    # actual source convention, rather than silently changing the producer.
    legacy_area = fraction.astype(np.float32) * float(x['cell_km']) ** 2
    np.testing.assert_array_equal(x['area'], legacy_area)
    np.testing.assert_array_equal(x['land'], fraction > .5)
    with np.load(folder / 'administration_grid.npz') as z:
        close(x['people'], (z['density'] * float(x['cell_km']) ** 2).ravel())
    hm, hf = decode_harvest(folder)
    with np.load(folder / 'farm_work_grid.npz') as z:
        energy = np.where(z['cereal'] == 1, hf['kcal_wheat'], np.where(z['cereal'] == 2, hf['kcal_barley'], 0))
        expected = np.where(x['land'], energy * 100 * legacy_area * hf['arable'] * .6 * .6, 0)
        close(x['potential_kcal'], expected.ravel())
        np.testing.assert_array_equal(x['boundaries'], z['harvest_boundaries'].ravel())
    return x


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected')); a = p.parse_args()
    plan = json.loads(PLAN.read_text())
    for mode in [a.mode] if a.mode else plan['climate_modes']:
        inputs = check_inputs(mode)
        for case in plan['scenarios']:
            key = f'{mode}_h{case["hours_worker_year"]}_f{case["transfer_fraction"]:g}'
            check_case(OUT / key, inputs)
