"""Independent geometry, directed routes, scalar task and shared-hour checks."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.administrative_world import audit_world
from review_network_duty_visits import graph_for_month, scalar_allocation

OUT = ROOT / 'output/network_visit_target_grid_20261112'
PLAN = ROOT / 'calibration/network_visit_target_grid_20261112/plan.json'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def independent_geometry(x, design):
    h, w = x['land'].shape; b = design['block_cells']; py, px = design['row_phase'], design['column_phase']
    groups = {}
    for node in np.flatnonzero(x['land']):
        row, col = divmod(int(node), w); groups.setdefault(((row + py) // b, (col + px) // b), []).append(int(node))
    nodes = []; ids = []; areas = []; counts = []; ncol = (w + px + b - 1) // b
    for (iy, ix), members in sorted(groups.items()):
        lo_y, hi_y = max(0, iy * b - py), min(h, (iy + 1) * b - py)
        lo_x, hi_x = max(0, ix * b - px), min(w, (ix + 1) * b - px)
        cy, cx = (lo_y + hi_y - 1) / 2, (lo_x + hi_x - 1) / 2
        nodes.append(min(members, key=lambda n: ((n // w - cy) ** 2 + (n % w - cx) ** 2, n)))
        ids.append(iy * ncol + ix); areas.append(sum(float(x['area'].ravel()[n]) for n in members)); counts.append(len(members))
    return dict(target_nodes=np.array(nodes), target_block_ids=np.array(ids), target_area_km2=np.array(areas), target_land_cells=np.array(counts))


def valid_recorded_paths(packet, targets, x, graph):
    provider = np.repeat(packet['keys'][:, 1], np.diff(packet['offsets']))
    for direction in ('outward', 'inward'):
        offsets, nodes = packet[direction + '_path_offsets'], packet[direction + '_path_nodes']
        assert offsets[0] == 0 and offsets[-1] == len(nodes) and np.all(np.diff(offsets) >= 1)
        assert x['land'].ravel()[nodes].all()
        edges = np.ones(len(nodes) - 1, bool); ends = offsets[1:] - 1; edges[ends[ends < len(edges)]] = False
        costs = np.zeros(len(nodes)); costs[:-1][edges] = np.asarray(graph[nodes[:-1][edges], nodes[1:][edges]]).ravel()
        assert np.all(costs[:-1][edges] > 0)
        np.testing.assert_allclose(np.add.reduceat(costs, offsets[:-1]), packet[direction + '_days'], rtol=1e-12, atol=1e-12)
        roots = x['nodes'][provider]; goals = targets['target_nodes'][packet['target_index']]
        if direction == 'inward': roots, goals = goals, roots
        np.testing.assert_array_equal(nodes[offsets[:-1]], roots); np.testing.assert_array_equal(nodes[offsets[1:] - 1], goals)


def review_routes(mode, designs):
    receipt = json.loads((OUT / f'{mode}_paths.json').read_text()); x = dict(np.load(INPUTS / f'{mode}_inputs.npz'))
    for path, digest in receipt['sources'].items(): assert sha(ROOT / path) == digest, path
    for path, digest in receipt['files_sha256'].items(): assert sha(OUT / path) == digest, path
    full = dict(np.load(INPUTS / f'{mode}_footprints.npz')); full_lookup = {tuple(k): i for i, k in enumerate(full['keys'])}
    targets = {}
    for design in designs:
        ident = design['id']; t = dict(np.load(OUT / mode / ident / 'targets.npz')); expected = independent_geometry(x, design)
        for name, value in expected.items(): np.testing.assert_array_equal(t[name], value)
        positions = np.searchsorted(full['landnodes'], t['target_nodes'])
        np.testing.assert_array_equal(full['landnodes'][positions], t['target_nodes'])
        np.testing.assert_array_equal(t['target_reference_masks'], full['reference'][:, positions])
        np.testing.assert_array_equal(t['target_land_positions'], positions)
        assert t['target_land_cells'].sum() == x['land'].sum()
        targets[ident] = t
    r, _ = audit_world(ROOT / 'atlases/earth_fit', mode)
    np.testing.assert_array_equal(r['land'], x['land'])
    assert {t['row'] * x['land'].shape[1] + t['col'] for t in r['towns']} == set(x['nodes'].tolist())
    old_paths = dict(np.load(PARENT / f'{mode}_paths.npz'))
    for month in range(12):
        graph = graph_for_month(r, month); reverse = graph.T.tocsr(); digest = hashlib.sha256()
        for part in (graph.indptr, graph.indices, graph.data): digest.update(part.tobytes())
        assert digest.hexdigest() == receipt['graph_sha256'][str(month)]
        packets = {ident: dict(np.load(OUT / mode / ident / f'paths_{month:02d}.npz')) for ident in targets}
        expected_keys = np.array([(month, i) for i in np.flatnonzero(x['actor'] >= 0)])
        for ident, p in packets.items():
            np.testing.assert_array_equal(p['keys'], expected_keys)
            assert p['offsets'][0] == 0 and p['offsets'][-1] == len(p['target_index'])
            assert np.all(np.diff(p['offsets']) >= 0)
            valid_recorded_paths(p, targets[ident], x, graph)
        def one(entry):
            i, source = entry; root = int(x['nodes'][source])
            a = dijkstra(graph, directed=True, indices=root, limit=2.); b = dijkstra(reverse, directed=True, indices=root, limit=2.)
            landnodes = full['landnodes']; eligible_land = np.flatnonzero((a[landnodes] <= 2) & (b[landnodes] <= 2) & (a[landnodes] + b[landnodes] + 1 / 7 <= 4))
            j = full_lookup[month, int(source)]; previous = full['covered'][full['offsets'][j]:full['offsets'][j + 1]]
            assert np.isin(eligible_land, previous, assume_unique=True).all()
            for ident, t in targets.items():
                nodes = t['target_nodes']; selected = np.flatnonzero((a[nodes] <= 2) & (b[nodes] <= 2) & (a[nodes] + b[nodes] + 1 / 7 <= 4))
                p = packets[ident]; begin, end = p['offsets'][i:i + 2]
                np.testing.assert_array_equal(p['target_index'][begin:end], selected)
                np.testing.assert_array_equal(p['outward_days'][begin:end], a[nodes[selected]])
                np.testing.assert_array_equal(p['inward_days'][begin:end], b[nodes[selected]])
        with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(one, enumerate(np.flatnonzero(x['actor'] >= 0))))
        # Exact original baseline endpoints, directed times and complete node paths.
        old_key = np.flatnonzero(old_paths['keys'][:, 0] == month); first, last = old_paths['offsets'][[old_key[0], old_key[-1] + 1]]
        p = packets['b3_p0']; np.testing.assert_array_equal(p['offsets'], old_paths['offsets'][np.r_[old_key, old_key[-1] + 1]] - first)
        for name in ('target_index', 'outward_days', 'inward_days'): np.testing.assert_array_equal(p[name], old_paths[name][first:last])
        for direction in ('outward', 'inward'):
            offsets = old_paths[direction + '_path_offsets']; start, end = offsets[[first, last]]
            np.testing.assert_array_equal(p[direction + '_path_offsets'], offsets[first:last + 1] - start)
            np.testing.assert_array_equal(p[direction + '_path_nodes'], old_paths[direction + '_path_nodes'][start:end])
        print(mode, 'all five grid route/eligibility/baseline checks', month + 1, flush=True)
    return {ident: t['target_nodes'] for ident, t in targets.items()}


def main():
    result = json.loads((OUT / 'results.json').read_text()); designs = json.loads(PLAN.read_text())['designs']
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    for name, digest in result['fields_sha256'].items(): assert sha(OUT / name) == digest
    raw = review_routes('raw', designs); corrected = review_routes('corrected', designs)
    for ident in raw: np.testing.assert_array_equal(raw[ident], corrected[ident])
    parent = json.loads((PARENT / 'results.json').read_text()); old = dict(np.load(PARENT / 'fields.npz')); reviewed = []
    for design in designs:
        ident = design['id']; saved = dict(np.load(OUT / (ident + '_fields.npz')))
        if ident == 'b3_p0':
            assert set(saved) == set(old)
            for name in saved: np.testing.assert_array_equal(saved[name], old[name])
        for mode in ('raw', 'corrected'):
            x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); t = dict(np.load(OUT / mode / ident / 'targets.npz')); demand = t['target_reference_masks'] > 0
            np.testing.assert_array_equal(saved[mode + '__demand'], demand)
            packets = [dict(np.load(OUT / mode / ident / f'paths_{m:02d}.npz')) for m in range(12)]
            for row in (r for r in result['rows'] if r['design'] == ident and r['climate'] == mode):
                key = row['key']; previous = next(r for r in parent['rows'] if r['key'] == key); f = dict(np.load(SEEDED / previous['parent_key'] / 'fields.npz'))
                for month, p in enumerate(packets):
                    provider = np.repeat(p['keys'][:, 1], np.diff(p['offsets'])); budget = f['work_secondary_hours'][0, month]
                    expected = scalar_allocation(provider, p['target_index'], 7 * (p['outward_days'] + p['inward_days']) + 1, x, f, budget, demand, row['crew'])
                    for name, value in expected.items(): np.testing.assert_array_equal(saved[key + '__' + name][month], value)
                    np.testing.assert_array_equal(saved[key + '__reserved_hours'][month], budget)
                    np.testing.assert_array_equal(saved[key + '__zero_budget_work_unavailable'][month], demand & ~expected['route_unreachable'])
                    partition = sum(expected[n].astype('u1') for n in ('served', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet'))
                    np.testing.assert_array_equal(partition, demand.astype('u1'))
                    total_used = f['work_fundable_collection_hours'][month] + f['work_secondary_hours'][1:, month].sum(axis=0) + expected['used_hours']
                    unused = f['work_gross_hours'][month] - total_used; assert np.all(unused >= -1e-8)
                    np.testing.assert_array_equal(saved[key + '__whole_provider_unused_hours'][month], unused)
                    np.testing.assert_allclose(unused, f['work_unused_hours'][month] + expected['unused_hours'], atol=1e-7)
                assert row['target_points'] == len(t['target_nodes']) and row['requested_visits'] == int(demand.sum() * 12)
                assert row['actual_spacing_km'] == float(x['cell_km'] * design['block_cells'])
                assert row['represented_land_km2'] == float(t['target_area_km2'].sum())
                assert row['requested_tasks_per_1000_land_km2'] == row['requested_visits'] / row['represented_land_km2'] * 1000
                for name in ('served', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet'):
                    assert row['completed_visits' if name == 'served' else name] == int(saved[key + '__' + name].sum())
                assert row['completed_fraction'] == row['completed_visits'] / row['requested_visits'] and row['zero_budget_visits'] == 0
                np.testing.assert_array_equal(row['completed_by_bin'], saved[key + '__served'].sum(axis=(1, 2)))
                for name, field in [('reserved_patrol_hours', 'reserved_hours'), ('visit_hours_used', 'used_hours'), ('unused_patrol_hours', 'unused_hours')]: assert row[name] == float(saved[key + '__' + field].sum())
                for a in row['actors']:
                    i = a['actor_index']; assert a['requested_visits'] == int(demand[i].sum() * 12)
                    for name in ('served', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet'):
                        assert a['completed_visits' if name == 'served' else name] == int(saved[key + '__' + name][:, i].sum())
                reviewed.append((ident, key)); print('Independent grid assignment/monthly ledger passed:', ident, key, flush=True)
    assert len(reviewed) == 40
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), reviewer_sha256=sha(Path(__file__)), cases=reviewed,
        independent_geometry=True, directed_recorded_path_edges=True, recomputed_route_eligibility=True, exact_original_baseline=True,
        all_actor_bin_partitions=True, scalar_integer_task_assignment=True, only_original_patrol_slice_used=True, original_maps_unchanged=True,
        limits='Same established SciPy shortest-path algorithm on independently rebuilt graphs;not an independent path-algorithm proof,empirical demand,daily rosters,global optimality or authority.'))


if __name__ == '__main__': main()
