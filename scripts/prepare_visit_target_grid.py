"""Freeze five declared point grids and directed walking paths in small packets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from prepare_network_duty_visits import walking_graph, graph_digest, root_chain
from polity.administrative_world import audit_world
from polity.visit_target_grid import phased_land_targets

OUT = ROOT / 'output/network_visit_target_grid_20261112'
PLAN = ROOT / 'calibration/network_visit_target_grid_20261112/plan.json'
PARENT = ROOT / 'output/network_duty_visits_20261112'
INPUTS = ROOT / 'output/settlement_feedback_20261112'


def check_baseline_month(packet, old, month):
    selected = np.flatnonzero(old['keys'][:, 0] == month); begin, end = int(old['offsets'][selected[0]]), int(old['offsets'][selected[-1] + 1])
    np.testing.assert_array_equal(packet['keys'], old['keys'][selected])
    np.testing.assert_array_equal(packet['offsets'], old['offsets'][np.r_[selected, selected[-1] + 1]] - begin)
    for name in ('target_index', 'outward_days', 'inward_days'): np.testing.assert_array_equal(packet[name], old[name][begin:end])
    for direction in ('outward', 'inward'):
        offsets = old[direction + '_path_offsets']; first, last = int(offsets[begin]), int(offsets[end])
        np.testing.assert_array_equal(packet[direction + '_path_offsets'], offsets[begin:end + 1] - first)
        np.testing.assert_array_equal(packet[direction + '_path_nodes'], old[direction + '_path_nodes'][first:last])


def prepare(mode, out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit grid-spacing/phase declaration before route outputs')
    designs = json.loads(PLAN.read_text())['designs']; receipt = json.loads((PARENT / f'{mode}_paths.json').read_text())
    sources = dict(receipt['sources'])
    for p in (PLAN, Path(__file__), ROOT / 'polity/visit_target_grid.py', PARENT / f'{mode}_paths.json', PARENT / f'{mode}_paths.npz'):
        sources[str(p.relative_to(ROOT))] = sha(p)
    for path, digest in sources.items(): assert sha(ROOT / path) == digest, path
    x = dict(np.load(INPUTS / f'{mode}_inputs.npz')); cache = dict(np.load(INPUTS / f'{mode}_footprints.npz'))
    old = dict(np.load(PARENT / f'{mode}_paths.npz')); landnodes = cache['landnodes']
    lookup = {tuple(map(int, key)): i for i, key in enumerate(cache['keys'])}
    targets = {}; positions = {}; files = {}; summary = {}
    for design in designs:
        ident = design['id']; t = phased_land_targets(x['land'], x['area'], cell_km=float(x['cell_km']),
            **{k: design[k] for k in ('block_cells', 'row_phase', 'column_phase')})
        pos = np.searchsorted(landnodes, t['nodes']); np.testing.assert_array_equal(landnodes[pos], t['nodes'])
        if ident == 'b3_p0':
            for name, old_name in [('nodes', 'target_nodes'), ('block_ids', 'target_block_ids'), ('represented_area_km2', 'target_area_km2'), ('land_cells', 'target_land_cells')]:
                np.testing.assert_array_equal(t[name], old[old_name])
        assert t['land_cells'].sum() == x['land'].sum()
        np.testing.assert_allclose(t['represented_area_km2'].sum(), x['area'][x['land']].astype(float).sum(), rtol=1e-12)
        folder = out / mode / ident; folder.mkdir(parents=True, exist_ok=True)
        target_file = folder / 'targets.npz'
        np.savez_compressed(target_file, target_nodes=t['nodes'], target_block_ids=t['block_ids'], target_area_km2=t['represented_area_km2'],
            target_land_cells=t['land_cells'], target_land_positions=pos, target_reference_masks=cache['reference'][:, pos])
        files[str(target_file.relative_to(out))] = sha(target_file); targets[ident] = t['nodes']; positions[ident] = pos
        summary[ident] = dict(targets=len(t['nodes']), actual_block_edge_km=t['block_edge_km'], represented_land_km2=float(t['represented_area_km2'].sum()),
            actor_target_pairs=int((cache['reference'][:, pos] > 0).sum()), eligible_source_target_bins=0)
    r, _ = audit_world(ROOT / 'atlases/earth_fit', mode)
    np.testing.assert_array_equal(r['land'], x['land'])
    assert {t['row'] * x['land'].shape[1] + t['col'] for t in r['towns']} == set(x['nodes'].tolist())
    graph_hashes = {}; covered_count = 0
    for month in range(12):
        graph = walking_graph(r, month); reverse = graph.T.tocsr(); graph_hashes[str(month)] = graph_digest(graph)
        assert graph_hashes[str(month)] == receipt['graph_sha256'][str(month)]
        def one(site):
            root = int(x['nodes'][site]); a, pa = dijkstra(graph, directed=True, indices=root, limit=2., return_predecessors=True)
            b, pb = dijkstra(reverse, directed=True, indices=root, limit=2., return_predecessors=True)
            covered = np.flatnonzero((a[landnodes] <= 2.) & (b[landnodes] <= 2.) & (a[landnodes] + b[landnodes] + 1 / 7 <= 4.))
            i = lookup[(month, int(site))]; previous = cache['covered'][cache['offsets'][i]:cache['offsets'][i + 1]]
            assert not len(np.setdiff1d(covered, previous, assume_unique=True))
            found = {}
            for ident, nodes in targets.items():
                selected = np.flatnonzero((a[nodes] <= 2.) & (b[nodes] <= 2.) & (a[nodes] + b[nodes] + 1 / 7 <= 4.))
                forward = [root_chain(pa, int(nodes[j]), root)[::-1] for j in selected]
                backward = [root_chain(pb, int(nodes[j]), root) for j in selected]
                found[ident] = (selected, a[nodes[selected]], b[nodes[selected]], forward, backward)
            return int(site), found, len(covered)
        packets = {ident: dict(keys=[], offsets=[0], target_index=[], outward_days=[], inward_days=[],
            outward_path_offsets=[0], inward_path_offsets=[0], outward_path_nodes=[], inward_path_nodes=[]) for ident in targets}
        with ThreadPoolExecutor(max_workers=4) as pool:
            for site, found, count in pool.map(one, np.flatnonzero(x['actor'] >= 0)):
                covered_count += count
                for ident, (selected, a, b, forward, backward) in found.items():
                    p = packets[ident]; p['keys'].append((month, site)); p['offsets'].append(p['offsets'][-1] + len(selected))
                    p['target_index'].append(selected.astype('u4')); p['outward_days'].append(a); p['inward_days'].append(b)
                    for direction, paths in [('outward', forward), ('inward', backward)]:
                        for path in paths:
                            p[direction + '_path_nodes'].extend(path); p[direction + '_path_offsets'].append(len(p[direction + '_path_nodes']))
        for ident, p in packets.items():
            packet = {}
            for name, value in p.items():
                if name in ('target_index', 'outward_days', 'inward_days'): packet[name] = np.concatenate(value)
                else: packet[name] = np.asarray(value, 'u4' if name.endswith('_nodes') else 'i8')
            if ident == 'b3_p0': check_baseline_month(packet, old, month)
            target_file = out / mode / ident / f'paths_{month:02d}.npz'; np.savez_compressed(target_file, **packet)
            files[str(target_file.relative_to(out))] = sha(target_file)
            summary[ident]['eligible_source_target_bins'] += int(packet['offsets'][-1])
        print(mode, 'five target grids month', month + 1, 'original baseline paths exact', flush=True)
    for path, digest in sources.items(): assert sha(ROOT / path) == digest, path
    write(out / f'{mode}_paths.json', dict(status='five_declared_target_grids_prepared', climate=mode, sources=sources,
        files_sha256=files, designs=summary, graph_sha256=graph_hashes, full_footprint_land_cell_checks=covered_count,
        original_baseline_targets_and_paths_exact=True, all_designs_use_same_graphs=True, all_foot_cells_within_old_full_network=True,
        limits='Supplied task-spacing/phase scenarios;not empirical demand,territory,daily rosters or numerical convergence.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--mode', required=True, choices=('raw', 'corrected'))
    parser.add_argument('--out', type=Path, default=OUT); args = parser.parse_args(); prepare(args.mode, args.out)
