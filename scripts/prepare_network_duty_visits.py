"""Freeze land targets and valid directed foot-only paths for funded visit tasks."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from polity.administrative_world import audit_world
from polity import control as C, seasons as S
from polity.network_visits import land_block_targets

OUT = ROOT / 'output/network_duty_visits_20261112'
PLAN = ROOT / 'calibration/network_duty_visits_20261112/plan.json'
PARENT = ROOT / 'output/settlement_feedback_20261112'
DATA = ROOT / 'atlases/earth_fit/data'


def walking_graph(r, month):
    world, st, climate = r['world'], r['statics'], r['climate']
    cross = np.where(st['basin'] > 0, S.CROSS_DAYS * (1 + S.FLOOD_GAIN * S.flood_index(climate['flow'][month][st['basin']])), 0.)
    rows, cols, days = C.foot_edges(world['elev'], st['land'], world['road'], S.month_terrain(st['eta'], climate, month),
        world['cell_km'], st['paths'], ferry=np.zeros_like(st['land']), tracks=world.get('tracks'),
        road_factor=1 + (S.MUD_ROAD - 1) * climate['mud'][month],
        track_factor=1 + (S.MUD_COEFFICIENT - 1) * climate['mud'][month], cross=cross)
    if not np.isfinite(days).all() or np.any(days <= 0): raise ValueError('Nonpositive/nonfinite walking edge')
    return csr_matrix((days, (rows, cols)), shape=(st['land'].size, st['land'].size))


def graph_digest(graph):
    digest = hashlib.sha256()
    for a in (graph.indptr, graph.indices, graph.data): digest.update(a.tobytes())
    return digest.hexdigest()


def root_chain(parent, node, root):
    chain = [int(node)]
    for _ in range(len(parent)):
        if node == root: return chain
        node = int(parent[node])
        if node < 0: raise ValueError('Missing predecessor for recorded foot route')
        chain.append(node)
    raise ValueError('Cyclic foot route')


def prepare(mode, out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit duty/target/cost/crew declaration before production outputs')
    receipt = json.loads((PARENT / f'{mode}_footprints.json').read_text()); sources = dict(receipt['sources'])
    for p in (PLAN, Path(__file__), ROOT / 'polity/network_visits.py', PARENT / f'{mode}_inputs.npz',
              PARENT / f'{mode}_footprints.json', PARENT / f'{mode}_footprints.npz', PARENT / f'{mode}_reach_review.json'):
        sources[str(p.relative_to(ROOT))] = sha(p)
    for path, digest in sources.items():
        if sha(ROOT / path) != digest: raise ValueError('Changed frozen route source: ' + path)
    if receipt['footprints_sha256'] != sha(PARENT / f'{mode}_footprints.npz'):
        raise ValueError('Original full-network footprints changed')
    x = dict(np.load(PARENT / f'{mode}_inputs.npz')); cache = dict(np.load(PARENT / f'{mode}_footprints.npz'))
    targets = land_block_targets(x['land'], x['area'], cell_km=float(x['cell_km']), block_cells=3)
    landnodes = cache['landnodes']; positions = np.searchsorted(landnodes, targets['nodes'])
    if not np.array_equal(landnodes[positions], targets['nodes']): raise ValueError('A fixed target is not on original land')
    target_reference = cache['reference'][:, positions]
    lookup = {tuple(map(int, key)): i for i, key in enumerate(cache['keys'])}
    print(mode, 'reconstructing frozen transport for foot-only duty paths', flush=True)
    r, _ = audit_world(DATA.parent, mode)
    if not np.array_equal(r['land'], x['land']): raise ValueError('Duty graph changed the original land raster')
    if {t['row'] * x['land'].shape[1] + t['col'] for t in r['towns']} != set(x['nodes'].tolist()):
        raise ValueError('Duty graph changed the original town/track reconstruction')
    keys = []; offsets = [0]; target_parts = []; outward = []; inward = []
    out_offsets = [0]; in_offsets = [0]; out_nodes = []; in_nodes = []; graph_hashes = {}; covered_count = 0
    for month in range(12):
        graph = walking_graph(r, month); reverse = graph.T.tocsr(); graph_hashes[str(month)] = graph_digest(graph)
        def one(site):
            root = int(x['nodes'][site])
            a, pa = dijkstra(graph, directed=True, indices=root, limit=2., return_predecessors=True)
            b, pb = dijkstra(reverse, directed=True, indices=root, limit=2., return_predecessors=True)
            covered = np.flatnonzero((a[landnodes] <= 2.) & (b[landnodes] <= 2.) & (a[landnodes] + b[landnodes] + 1 / 7 <= 4.))
            i = lookup[(month, int(site))]; old = cache['covered'][cache['offsets'][i]:cache['offsets'][i + 1]]
            if len(np.setdiff1d(covered, old, assume_unique=True)):
                raise ValueError('Foot-only duty route exceeds original full-network footprint')
            nodes = targets['nodes']; selected = np.flatnonzero((a[nodes] <= 2.) & (b[nodes] <= 2.) & (a[nodes] + b[nodes] + 1 / 7 <= 4.))
            forward_paths = [root_chain(pa, int(nodes[j]), root)[::-1] for j in selected]
            backward_paths = [root_chain(pb, int(nodes[j]), root) for j in selected]
            return int(site), selected, a[nodes[selected]], b[nodes[selected]], forward_paths, backward_paths, len(covered)
        with ThreadPoolExecutor(max_workers=4) as pool:
            for site, selected, a, b, paths_a, paths_b, count in pool.map(one, np.flatnonzero(x['actor'] >= 0)):
                keys.append((month, site)); offsets.append(offsets[-1] + len(selected)); target_parts.append(selected.astype(np.uint32))
                outward.append(a); inward.append(b); covered_count += count
                for path in paths_a:
                    out_nodes.extend(path); out_offsets.append(len(out_nodes))
                for path in paths_b:
                    in_nodes.extend(path); in_offsets.append(len(in_nodes))
        print(mode, 'foot-only duty month', month + 1, 'original reference upper bound passed', flush=True)
    out.mkdir(parents=True, exist_ok=True); packet = out / f'{mode}_paths.npz'
    np.savez_compressed(packet, target_nodes=targets['nodes'], target_block_ids=targets['block_ids'],
        target_area_km2=targets['represented_area_km2'], target_land_cells=targets['land_cells'],
        target_reference_masks=target_reference, target_land_positions=positions,
        keys=np.asarray(keys, np.int64), offsets=np.asarray(offsets, np.int64), target_index=np.concatenate(target_parts),
        outward_days=np.concatenate(outward), inward_days=np.concatenate(inward),
        outward_path_offsets=np.asarray(out_offsets, np.int64), outward_path_nodes=np.asarray(out_nodes, np.uint32),
        inward_path_offsets=np.asarray(in_offsets, np.int64), inward_path_nodes=np.asarray(in_nodes, np.uint32))
    for path, digest in sources.items():
        if sha(ROOT / path) != digest: raise ValueError('Frozen source changed during duty preparation: ' + path)
    write(out / f'{mode}_paths.json', dict(status='fixed_targets_and_foot_only_paths_prepared', sources=sources,
        paths_sha256=sha(packet), climate=mode, fixed_targets=len(targets['nodes']), block_cells=3,
        actual_block_edge_km=targets['block_edge_km'], recorded_source_months=len(keys), eligible_source_target_bins=offsets[-1],
        full_footprint_land_cell_checks=covered_count, graph_sha256=graph_hashes,
        all_foot_routes_within_original_full_network=True, boats_river_harbours_ferries_included=False,
        scope='Fixed conditional visit targets and recorded walking paths;not observed demand,visitedterritory,fullcrewrosters or authority.'))
    print(mode, 'prepared', len(targets['nodes']), 'target points and', offsets[-1], 'source/target/bin walking pairs', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--mode', required=True, choices=('raw', 'corrected'))
    parser.add_argument('--out', type=Path, default=OUT); args = parser.parse_args(); prepare(args.mode, args.out)
