"""Independently check recorded walking routes, integer tasks and shared hours.

Does not import the visit allocator or target-selection implementation.
Recorded valid paths and replay are checked; shortest-path/global assignment
optimality and individual daily crew rostering are not certified.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.sparse import csr_matrix

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.administrative_world import audit_world
from polity import control as C, seasons as S

OUT = ROOT / 'output/network_duty_visits_20261112'
PARENT = ROOT / 'output/settlement_feedback_20261112'
SEEDED = ROOT / 'output/settlement_dispatch_seeded_20261112'


def graph_for_month(r, month):
    w, st, climate = r['world'], r['statics'], r['climate']
    crossings = np.zeros_like(st['eta'], dtype=float)
    river = st['basin'] > 0
    crossings[river] = S.CROSS_DAYS * (1 + S.FLOOD_GAIN * S.flood_index(climate['flow'][month][st['basin'][river]]))
    a, b, hours = C.foot_edges(w['elev'], st['land'], w['road'], S.month_terrain(st['eta'], climate, month),
        w['cell_km'], st['paths'], ferry=np.zeros(st['land'].shape, bool), tracks=w.get('tracks'),
        road_factor=1 + (S.MUD_ROAD - 1) * climate['mud'][month],
        track_factor=1 + (S.MUD_COEFFICIENT - 1) * climate['mud'][month], cross=crossings)
    return csr_matrix((hours, (a, b)), shape=(st['land'].size, st['land'].size))


def check_targets(x, p):
    land = x['land']; h, w = land.shape; expected = []; blocks = []; area = []; counts = []
    for row in range(0, h, 3):
        for col in range(0, w, 3):
            cells = [(i, j) for i in range(row, min(row + 3, h)) for j in range(col, min(col + 3, w)) if land[i, j]]
            if not cells: continue
            center = ((row + min(row + 3, h) - 1) / 2, (col + min(col + 3, w) - 1) / 2)
            best = min(cells, key=lambda v: ((v[0] - center[0]) ** 2 + (v[1] - center[1]) ** 2, v[0] * w + v[1]))
            expected.append(best[0] * w + best[1]); blocks.append((row // 3) * ((w + 2) // 3) + col // 3)
            area.append(sum(float(x['area'][i, j]) for i, j in cells)); counts.append(len(cells))
    for name, values in [('target_nodes', expected), ('target_block_ids', blocks), ('target_land_cells', counts)]:
        np.testing.assert_array_equal(p[name], values)
    np.testing.assert_allclose(p['target_area_km2'], area, rtol=1e-14)


def check_paths(mode):
    receipt = json.loads((OUT / f'{mode}_paths.json').read_text()); p = dict(np.load(OUT / f'{mode}_paths.npz'))
    assert receipt['paths_sha256'] == sha(OUT / f'{mode}_paths.npz')
    for path, digest in receipt['sources'].items(): assert sha(ROOT / path) == digest, path
    x = dict(np.load(PARENT / f'{mode}_inputs.npz')); original = dict(np.load(PARENT / f'{mode}_footprints.npz'))
    check_targets(x, p)
    pos = np.searchsorted(original['landnodes'], p['target_nodes'])
    np.testing.assert_array_equal(original['landnodes'][pos], p['target_nodes'])
    np.testing.assert_array_equal(p['target_reference_masks'], original['reference'][:, pos])
    expected_keys = np.array([(m, i) for m in range(12) for i in np.flatnonzero(x['actor'] >= 0)])
    np.testing.assert_array_equal(p['keys'], expected_keys)
    assert p['offsets'][0] == 0 and p['offsets'][-1] == len(p['target_index']) and np.all(np.diff(p['offsets']) >= 0)
    full_lookup = {tuple(k): i for i, k in enumerate(original['keys'])}
    for i, key in enumerate(p['keys']):
        targets = p['target_index'][p['offsets'][i]:p['offsets'][i + 1]]
        assert np.all(np.diff(targets.astype('i8')) > 0)
        oi = full_lookup[tuple(key)]; old = original['covered'][original['offsets'][oi]:original['offsets'][oi + 1]]
        assert np.isin(pos[targets], old).all(), 'A walking target exceeded its old full-network footprint'
    r, _ = audit_world(ROOT / 'atlases/earth_fit', mode)
    np.testing.assert_array_equal(r['land'], x['land'])
    assert {t['row'] * x['land'].shape[1] + t['col'] for t in r['towns']} == set(x['nodes'].tolist())
    provider = np.repeat(p['keys'][:, 1], np.diff(p['offsets']))
    month_of_pair = np.repeat(p['keys'][:, 0], np.diff(p['offsets']))
    for month in range(12):
        graph = graph_for_month(r, month); digest = hashlib.sha256()
        for part in (graph.indptr, graph.indices, graph.data): digest.update(part.tobytes())
        assert digest.hexdigest() == receipt['graph_sha256'][str(month)]
        ids = np.flatnonzero(month_of_pair == month)
        for direction in ('outward', 'inward'):
            offsets, nodes = p[direction + '_path_offsets'], p[direction + '_path_nodes']
            assert offsets[0] == 0 and offsets[-1] == len(nodes) and np.all(np.diff(offsets) >= 1)
            start, end = int(offsets[ids[0]]), int(offsets[ids[-1] + 1])
            path = nodes[start:end]; cut = offsets[ids + 1] - start - 1
            edges = np.ones(len(path) - 1, bool); edges[cut[cut < len(edges)]] = False
            costs = np.zeros(len(path)); costs[:-1][edges] = np.asarray(graph[path[:-1][edges], path[1:][edges]]).ravel()
            assert np.all(costs[:-1][edges] > 0) and x['land'].ravel()[path].all()
            sums = np.add.reduceat(costs, offsets[ids] - start)
            np.testing.assert_allclose(sums, p[direction + '_days'][ids], rtol=1e-12, atol=1e-12)
            roots, goals = x['nodes'][provider[ids]], p['target_nodes'][p['target_index'][ids]]
            if direction == 'inward': roots, goals = goals, roots
            np.testing.assert_array_equal(nodes[offsets[ids]], roots)
            np.testing.assert_array_equal(nodes[offsets[ids + 1] - 1], goals)
        print(mode, 'independent directed path-edge review', month + 1, flush=True)
    assert np.all(p['outward_days'] <= 2) and np.all(p['inward_days'] <= 2)
    assert np.all(p['outward_days'] + p['inward_days'] + 1 / 7 <= 4)
    return x, p


def scalar_allocation(providers, targets, per_person, x, parent, budget, demand, crew):
    physical = np.zeros(demand.shape, bool); chosen = np.full(demand.shape, -1, 'i8'); cost = np.zeros(demand.shape)
    for source, target, person_hours in zip(providers.tolist(), targets.tolist(), per_person.tolist()):
        actor = int(x['actor'][source])
        if actor < 0 or not parent['active'][source] or not demand[actor, target]: continue
        physical[actor, target] = True; required = person_hours * crew
        if parent['staff'][source] < crew or budget[source] < required: continue
        old = int(chosen[actor, target])
        if old < 0 or (required, source) < (cost[actor, target], old):
            chosen[actor, target] = source; cost[actor, target] = required
    jobs = [[] for _ in x['nodes']]
    for actor, target in zip(*np.where(chosen >= 0)):
        jobs[chosen[actor, target]].append((float(cost[actor, target]), int(target), int(actor)))
    served = np.zeros_like(demand); used = np.zeros(len(jobs))
    for source, tasks in enumerate(jobs):
        for hours, target, actor in sorted(tasks):
            if used[source] + hours > budget[source]: break
            used[source] += hours; served[actor, target] = True
    return dict(provider_for_target=chosen, chosen_cost_hours=cost, served=served, used_hours=used, unused_hours=budget - used,
        route_unreachable=demand & ~physical, provider_work_unavailable=demand & physical & (chosen < 0), capacity_unmet=demand & (chosen >= 0) & ~served)


def main():
    result = json.loads((OUT / 'results.json').read_text()); saved = dict(np.load(OUT / 'fields.npz'))
    for path, digest in {**result['sources'], **result['producers'], **result['unchanged_map_sha256']}.items(): assert sha(ROOT / path) == digest, path
    assert result['fields_sha256'] == sha(OUT / 'fields.npz') and len(result['rows']) == 8
    targets = {}; reviewed = []
    for mode in ('raw', 'corrected'):
        x, p = check_paths(mode); targets[mode] = p['target_nodes']; demand = p['target_reference_masks'] > 0
        np.testing.assert_array_equal(saved[mode + '__demand'], demand)
        for row in (r for r in result['rows'] if r['climate'] == mode):
            key = row['key']; parent = dict(np.load(SEEDED / row['parent_key'] / 'fields.npz'))
            parent_review = json.loads((SEEDED / row['parent_key'] / 'review.json').read_text())
            assert parent_review['status'] == 'passed' and parent_review['all_positive_collection_work_supported']
            for month in range(12):
                selected = np.flatnonzero(p['keys'][:, 0] == month)
                ids = np.concatenate([np.arange(p['offsets'][i], p['offsets'][i + 1]) for i in selected])
                providers = np.repeat(p['keys'][selected, 1], np.diff(p['offsets'])[selected])
                budget = parent['work_secondary_hours'][0, month]
                expected = scalar_allocation(providers, p['target_index'][ids], 7 * (p['outward_days'][ids] + p['inward_days'][ids]) + 1,
                    x, parent, budget, demand, row['crew'])
                for name, values in expected.items(): np.testing.assert_array_equal(saved[key + '__' + name][month], values)
                np.testing.assert_array_equal(saved[key + '__reserved_hours'][month], budget)
                np.testing.assert_array_equal(saved[key + '__zero_budget_work_unavailable'][month], demand & ~expected['route_unreachable'])
                partition = sum(expected[n].astype('u1') for n in ('served', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet'))
                np.testing.assert_array_equal(partition, demand.astype('u1'))
                nonpatrol = parent['work_fundable_collection_hours'][month] + parent['work_secondary_hours'][1:, month].sum(axis=0)
                unused = parent['work_gross_hours'][month] - nonpatrol - expected['used_hours']
                assert np.all(unused >= -1e-8)
                np.testing.assert_allclose(saved[key + '__whole_provider_unused_hours'][month], unused, atol=1e-7)
                np.testing.assert_allclose(unused, parent['work_unused_hours'][month] + expected['unused_hours'], atol=1e-7)
            for name in ('served', 'route_unreachable', 'provider_work_unavailable', 'capacity_unmet'):
                value = 'completed_visits' if name == 'served' else name
                assert row[value] == int(saved[key + '__' + name].sum())
            assert row['requested_visits'] == int(demand.sum() * 12) and row['zero_budget_visits'] == 0
            for name, array in [('reserved_patrol_hours', 'reserved_hours'), ('visit_hours_used', 'used_hours'), ('unused_patrol_hours', 'unused_hours')]:
                assert row[name] == float(saved[key + '__' + array].sum())
            for actor in row['actors']:
                i = actor['actor_index']; assert actor['requested_visits'] == int(demand[i].sum() * 12)
                assert actor['completed_visits'] == int(saved[key + '__served'][:, i].sum())
                for n in ('route_unreachable', 'provider_work_unavailable', 'capacity_unmet'): assert actor[n] == int(saved[key + '__' + n][:, i].sum())
            reviewed.append(key); print('Independent scalar assignment and whole-provider ledger passed:', key, flush=True)
    np.testing.assert_array_equal(targets['raw'], targets['corrected'])
    write(OUT / 'review.json', dict(status='passed', results_sha256=sha(OUT / 'results.json'), fields_sha256=sha(OUT / 'fields.npz'),
        reviewer_sha256=sha(Path(__file__)), cases=reviewed, independent_target_geometry=True, recorded_directed_edges_and_roundtrips=True,
        integer_tasks_and_no_double_assignment=True, exact_reserved_patrol_slice=True, unchanged_nonpatrol_commitments=True,
        zero_work_control=True, all_actor_target_bin_partitions=True, original_maps_unchanged=True,
        limits='Valid recorded paths and scalar allocation checked;not independent shortest-path optimality,full individual rosters,observed demand or authority.'))


if __name__ == '__main__': main()
