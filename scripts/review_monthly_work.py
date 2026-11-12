"""Independent ancestor sums and scalar monthly collection/duty ledgers."""
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_monthly_work_20261112'
PARENT = ROOT / 'output/settlement_feedback_20261112'


def close(actual, expected):
    if isinstance(actual, (int, float, np.integer, np.floating)) and isinstance(expected, (int, float, np.integer, np.floating)):
        if not math.isclose(actual, expected, rel_tol=2e-11, abs_tol=1e-7):
            raise ValueError(f'Independent scalar difference: {actual} != {expected}')
        return
    np.testing.assert_allclose(actual, expected, rtol=2e-11, atol=1e-7)


def main():
    result = json.loads((OUT / 'results.json').read_text())
    assert not result['adopt'] and not result['people_food_staff_reallocated'] and not result['actual_patrol_reach_recomputed']
    for p, digest in {**result['sources_sha256'], **result['unchanged_atlas_sha256']}.items():
        assert sha(ROOT / p) == digest, p
    assert sha(OUT / 'fields.npz') == result['fields_sha256']
    data = dict(np.load(OUT / 'fields.npz')); parents = {}; path_fields = {}; case_fields = {}
    path_checks = origin_checks = provider_bins = 0
    for mode in ('raw', 'corrected'):
        receipt = json.loads((OUT / f'{mode}_paths.json').read_text())
        assert receipt['status'] == 'original_paths_reproduced'
        assert sha(OUT / f'{mode}_paths.npz') == receipt['paths_sha256']
        for p, digest in receipt['sources'].items():
            assert sha(ROOT / p) == digest, p
        p = dict(np.load(OUT / f'{mode}_paths.npz')); x = dict(np.load(PARENT / f'{mode}_inputs.npz'))
        path_fields[mode] = p; parents[mode] = x
        for name in ('local_index', 'owner', 'nodes', 'access'):
            np.testing.assert_array_equal(p[name], x[name])
        n = len(p['owner']); parent = p['parent_local']
        assert np.all((parent >= 0) & (parent < n))
        for j in range(n):
            chain = []; current = j; seen = set()
            while parent[current] != current:
                assert current not in seen, 'Cycle in collection forest'
                seen.add(current); chain.append(current); current = int(parent[current])
            assert p['local_index'][current] == p['nodes'][p['owner'][j]]
            assert p['owner'][current] == p['owner'][j]
            for month in range(12):
                outward = math.fsum(float(p['edge_outward_days'][month, i]) for i in chain)
                inward = math.fsum(float(p['edge_inward_days'][month, i]) for i in chain)
                close(p['outward_days'][month, j], outward); close(p['inward_days'][month, j], inward)
                assert bool(p['access'][month, j]) == (outward <= 1. and inward <= 1.)
                path_checks += 1
        for h in (600, 300):
            key = f'{mode}_h{h}_f0.075'; folder = PARENT / key
            old = json.loads((folder / 'results.json').read_text()); review = json.loads((folder / 'review.json').read_text())
            assert review['status'] == 'passed' and review['results_sha256'] == sha(folder / 'results.json')
            assert review['all_positive_catchments_source_supported'] and old['source_gate']['status'] == 'passed'
            assert old['fields_sha256'] == sha(folder / 'fields.npz')
            case_fields[key] = dict(np.load(folder / 'fields.npz'))
    combinations = {(f'{m}_h{h}_f0.075', load, profile) for m in ('raw', 'corrected') for h in (600, 300)
                    for load in (60000., 120000.) for profile in ('all_open', 'bins6_7_8_closed')}
    assert len(result['rows']) == 16
    assert {(r['parent'], r['load_kcal'], r['availability']) for r in result['rows']} == combinations
    reviewed_trips = set()
    for row in result['rows']:
        key = row['parent']; mode = row['climate']; load = row['load_kcal']; tag = row['key']
        z, x, p = case_fields[key], parents[mode], path_fields[mode]
        n = len(z['total']); collection = np.zeros((12, n))
        trip_key = f'{key}_load{int(load)}'; expected_trips = np.zeros_like(z['origin_departures']); expected_work = expected_trips.copy()
        for month in range(12):
            for j, site in enumerate(x['owner']):
                food = float(z['origin_departures'][month, j])
                trips = max(1, math.ceil(food / load)) if food > 0 else 0
                if food > 0:
                    assert p['access'][month, j]
                hours = trips * (7 * (float(p['outward_days'][month, j]) + float(p['inward_days'][month, j])) + .25) if trips else 0.
                expected_trips[month, j] = trips; expected_work[month, j] = hours
                collection[month, site] += hours
        np.testing.assert_array_equal(data[trip_key + '__trips'], expected_trips)
        close(data[trip_key + '__origin_hours'], expected_work)
        if trip_key not in reviewed_trips:
            origin_checks += expected_trips.size; reviewed_trips.add(trip_key)
        def field(name):
            return data[tag + '__' + name]
        close(field('required_collection_hours'), collection)
        demand = data[key + '__requested']; assert demand.shape == (3, 12, n)
        close(demand[0], np.broadcast_to(z['staff'], (12, n)))
        close(demand[1], np.broadcast_to(z['total'] / 12, (12, n))); close(demand[2], demand[1])
        qualified = np.ones(n, bool); by_actor = {}
        for j in range(n):
            gross = [float(z['staff'][j]) * (0 if row['availability'] != 'all_open' and m in (6, 7, 8) else 50.) for m in range(12)]
            supported = bool(z['source_supported'][j]) and all(collection[m, j] <= gross[m] for m in range(12))
            qualified[j] = supported
            for month in range(12):
                required = collection[month, j]; funded = min(required, gross[month]); missing = required - funded
                spare = gross[month] - funded if supported else 0.
                requests = [float(v) for v in demand[:, month, j]]; cost = [14., 1., 2.]
                needed = math.fsum(q * c for q, c in zip(requests, cost))
                fraction = min(1., spare / needed) if needed else 1.
                if not supported:
                    fraction = 0.
                served = [q * fraction for q in requests]
                unreachable = [0. if supported else q for q in requests]
                capacity = [max(0., q - s - u) for q, s, u in zip(requests, served, unreachable)]
                used = [s * c for s, c in zip(served, cost)]
                for name, value in [('gross_hours', gross[month]), ('fundable_collection_hours', funded),
                                    ('collection_unmet_hours', missing), ('unused_hours', max(0., gross[month] - funded - sum(used))),
                                    ('invalid_reused_budget_hours', sum(min(q * c, spare) for q, c in zip(requests, cost)))]:
                    close(field(name)[month, j], value)
                for name, value in [('secondary_served', served), ('secondary_unreachable', unreachable),
                                    ('secondary_capacity_unmet', capacity), ('secondary_hours', used)]:
                    close(field(name)[:, month, j], value)
                assert funded + sum(used) <= gross[month] + 1e-7
                provider_bins += 1
        np.testing.assert_array_equal(field('qualified'), qualified)
        positive = z['total'] > 0
        for name, value in [('original_town_people', z['total'].sum()), ('original_active_sites', z['active'].sum()),
                            ('positive_sites', positive.sum()), ('qualified_positive_sites', (positive & qualified).sum()),
                            ('qualified_active_sites', (z['active'] & qualified).sum()),
                            ('conditional_qualified_town_people', z['total'][qualified].sum()),
                            ('positive_sites_without_staff', (positive & (z['staff'] == 0)).sum()),
                            ('collection_deficit_sites', (positive & np.any(field('collection_unmet_hours') > 0, axis=0)).sum()),
                            ('required_collection_hours', collection.sum())]:
            close(row[name], value)
        for summary, name in [('gross_hours', 'gross_hours'), ('collection_unmet_hours', 'collection_unmet_hours'),
                              ('fundable_collection_hours', 'fundable_collection_hours'), ('secondary_hours', 'secondary_hours'), ('unused_hours', 'unused_hours')]:
            close(row[summary], field(name).sum())
        for summary, name in [('secondary_served', 'secondary_served'), ('secondary_unreachable', 'secondary_unreachable'),
                              ('secondary_capacity_unmet', 'secondary_capacity_unmet')]:
            close(row[summary], field(name).sum(axis=(1, 2)))
        close(row['secondary_requested'], demand.sum(axis=(1, 2)))
        excess = np.maximum(field('fundable_collection_hours') + field('invalid_reused_budget_hours') - field('gross_hours'), 0.)
        close(row['invalid_independent_budget_excess_hours'], excess.sum())
        assert row['invalid_independent_budget_excess_site_bins'] == int((excess > 1e-7).sum())
        assert {a['actor_index'] for a in row['actors']} == set(x['actor'].tolist())
        for actor in row['actors']:
            mask = x['actor'] == actor['actor_index']
            close(actor['original_town_people'], z['total'][mask].sum())
            close(actor['qualified_town_people'], z['total'][mask & qualified].sum())
            assert actor['qualified_active_sites'] == int((z['active'] & qualified & mask).sum())
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'),
        fields_sha256=sha(OUT / 'fields.npz'), reviewer_sha256=sha(Path(__file__)),
        independent_ancestor_origin_bins=path_checks, independent_trip_origin_bins=origin_checks,
        independent_provider_bins=provider_bins, scenarios_checked=16, all_original_source_hashes_preserved=True,
        no_producer_work_solver_imported=True, source_food_receipts_verified=True,
        scope='Independent scalar paths/trips/work/requests/qualification;fixed-plan scenario audit,not empirical or political validation.'))
    print('Independent review passed:', path_checks, 'path bins;', origin_checks, 'trip bins;', provider_bins, 'provider bins')


if __name__ == '__main__':
    main()
