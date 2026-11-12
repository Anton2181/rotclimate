"""Independent food/work/population checks for finer search and threshold probes."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write
from review_settlement_feedback import inventory, cycle, production, harvest_series

OUT = ROOT / 'output/settlement_dispatch_search_20261112'
PARENT = ROOT / 'output/settlement_feedback_20261112'
JOINT = ROOT / 'output/settlement_dispatch_20261112'
WORK = ROOT / 'output/settlement_monthly_work_20261112'


def close(a, b):
    np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-3)


def trial_check(f, x, paths, hours, *, fine):
    owner = x['owner']; local = x['local_index']; n = len(x['nodes']); pop = x['people'][local]
    allowance = np.bincount(owner, weights=pop * .075, minlength=n)
    moved = pop * .075 * np.divide(f['total'], allowance, out=np.zeros(n), where=allowance > 0)[owner]
    close(f['moved'], moved); close(f['rural'], pop - moved)
    assert np.all(f['total'] <= allowance + 1e-7) and np.all(f['rural'] >= 0)
    active = x['affiliated'] & (f['total'] >= 150) & (x['civilian_request'] >= 50)
    np.testing.assert_array_equal(f['active'], active); close(f['staff'], np.where(active, 100., 0.))
    close(f['civil'] + f['staff'], f['total'])
    produced, _, available, peak = production(x['potential_kcal'][local], x['listed_hours'][local],
        x['reaping_hours'][local], f['rural'], hours)
    close(f['produced_kcal'], produced)
    close(f['annual_hours_used'], produced * x['listed_hours'][local] / 1e6)
    close(f['reaping_hours_used'], produced * x['reaping_hours'][local] / 1e6)
    assert np.all(f['annual_hours_used'] <= available + 1e-7) and np.all(f['reaping_hours_used'] <= peak + 1e-7)
    supply = harvest_series(produced, x['boundaries'][local]); rural_need = np.broadcast_to(f['rural'] * 2500 * 365 / 12, supply.shape)
    rural_capacity = rural_need.sum(axis=0)
    rural = inventory(supply, rural_need, rural_capacity, f['rural_initial_stock'])
    for name, value in rural.items():
        if name != 'unmet_path': close(f['rural_' + name], value)
    cycle(rural); origin_good = rural['unmet'] <= 1e-8 * np.maximum(1., rural_capacity)
    source_good = np.bincount(owner, weights=~origin_good, minlength=n) == 0
    np.testing.assert_array_equal(source_good, f['source_supported'])
    stock = f['rural_initial_stock'].copy(); overflow = []
    for harvest, need in zip(supply, rural_need):
        rest = np.maximum(stock + harvest - need, 0.); overflow.append(np.maximum(rest - rural_capacity, 0.) * origin_good)
        stock = np.minimum(rest, rural_capacity) * np.exp(np.log1p(-.05) / 12)
    collected = np.stack(overflow) * .1; export_capacity = collected.sum(axis=0)
    export = inventory(collected, f['origin_departures'], export_capacity, f['export_initial_stock'])
    for name, value in export.items():
        if name != 'unmet_path': close(f['export_' + name], value)
    cycle(export); assert np.all(export['unmet'] <= 1e-8 * np.maximum(1., export_capacity))
    assert not np.any(f['origin_departures'][~x['access']] > 0.)
    trips = np.where(f['origin_departures'] > 0, np.maximum(1., np.ceil(f['origin_departures'] / 120000.)), 0.)
    np.testing.assert_array_equal(trips, f['origin_trips'])
    origin_work = trips * ((paths['outward_days'] + paths['inward_days']) * 7 + .25)
    collection = np.stack([np.bincount(owner, weights=v, minlength=n) for v in origin_work])
    gross = np.broadcast_to(f['staff'] * 50, (12, n)); close(f['collection_hours'], collection); close(f['staff_gross_hours'], gross)
    assert np.all(collection <= gross)
    arrivals = .95 * np.roll(np.stack([np.bincount(owner, weights=d, minlength=n) for d in f['origin_departures']]), 1, axis=0)
    close(f['arrivals'], arrivals); town_need = np.broadcast_to(f['total'] * 2500 * 365 / 12, arrivals.shape)
    town = inventory(arrivals, town_need, f['total'] * 2500 * 90, f['town_initial_stock'])
    for name, value in town.items():
        if name != 'unmet_path': close(f['town_' + name], value)
    cycle(town)
    if fine:
        positive = f['total'] > 0
        assert source_good[positive].all() and np.all(town['unmet'] <= 1e-8 * np.maximum(1., town['needed']))
    else:
        admissible = (f['civil'] >= 0) & (f['civil'] <= x['civilian_request'] + 1e-8)
        expected = source_good & admissible & (town['unmet'] <= 1e-10 * np.maximum(1., town['needed']))
        np.testing.assert_array_equal(f['feasible'], expected)


def main():
    r = json.loads((OUT / 'results.json').read_text()); fields = dict(np.load(OUT / 'fields.npz'))
    assert not r['adopt'] and not r['original_sixteen_cases_and_maps_changed']
    for p, digest in {**r['sources'], **r['unchanged_maps_sha256']}.items(): assert sha(ROOT / p) == digest, p
    assert sha(OUT / 'fields.npz') == r['fields_sha256'] and len(r['rows']) == 4
    records = 0
    for row in r['rows']:
        key = row['key']; mode = row['climate']; hours = row['hours_worker_year']
        x = dict(np.load(PARENT / f'{mode}_inputs.npz')); paths = dict(np.load(WORK / f'{mode}_paths.npz'))
        original = dict(np.load(JOINT / key / 'fields.npz'))
        def subset(prefix):
            head = key + '__' + prefix
            return {name[len(head):]: value for name, value in fields.items() if name.startswith(head)}
        fine = subset('fine_')
        for name in ('scan_feasible', 'scan_source_supported', 'scan_destination_unmet'):
            np.testing.assert_array_equal(fine[name][::2], original[name])
        trial_check(fine, x, paths, hours, fine=True); records += 1
        delta = fine['total'] - original['total']
        close(row['town_people_difference'], delta.sum()); close(row['fine_town_people'], fine['total'].sum())
        assert row['source_switches'] == int((original['active'] != fine['active']).sum())
        for probe in row['probes']:
            f = subset('probe_' + probe['tag'] + '_'); trial_check(f, x, paths, hours, fine=False); records += 1
            threshold = 150 + probe['offset']; eligible = fields[key + '__upper'] >= threshold
            np.testing.assert_array_equal(f['eligible'], eligible); close(f['total'], np.where(eligible, threshold, 0.))
            good = eligible & f['feasible']; coarse_miss = good & (original['total'] == 0); fine_miss = good & (fine['total'] == 0)
            assert probe['eligible_sites'] == int(eligible.sum()) and probe['feasible_sites'] == int(good.sum())
            assert probe['coarse_missed_indices'] == np.flatnonzero(coarse_miss).tolist()
            assert probe['fine_missed_indices'] == np.flatnonzero(fine_miss).tolist()
            assert probe['coarse_zero_but_probe_feasible'] == int(coarse_miss.sum())
            assert probe['fine_zero_but_probe_feasible'] == int(fine_miss.sum())
        if np.any(fine['total'] > 0): assert row['source_gate']['status'] == 'passed'
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'),
        fields_sha256=sha(OUT / 'fields.npz'), reviewer_sha256=sha(Path(__file__)),
        independent_inventory_module_sha256=sha(ROOT / 'scripts/review_settlement_feedback.py'),
        final_and_probe_records_checked=records, overlap_arrays_exact=4 * 33 * 3,
        original_maps_and_source_hashes_preserved=True,
        independent_people_field_work_three_inventories_trips_monthly_hours=True,
        global_optimality_or_empirical_adoption_claimed=False))
    print('Finer-search and staff-transition review passed:', records, 'complete people/work/inventory records')


if __name__ == '__main__': main()
