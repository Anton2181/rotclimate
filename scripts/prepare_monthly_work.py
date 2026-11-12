"""Retain compatible original collection routes and monthly directed trip costs."""
import argparse
import copy
import gzip
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import prepare_settlement_feedback as P
from settlement_locations_earth import sha, write

OUT = ROOT / 'output/settlement_monthly_work_20261112'
PLAN = ROOT / 'calibration/settlement_monthly_work_20261112/plan.json'


def prepare(mode, out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit monthly work declaration first')
    old = P.OUT; data = P.DATA; folder = data / ('corrected' if mode == 'corrected' else '')
    prep = json.loads((old / f'{mode}_preparation.json').read_text())
    sources = dict(prep['sources'])
    sources[str((old / f'{mode}_inputs.npz').relative_to(ROOT))] = prep['inputs_sha256']
    sources[str((old / f'{mode}_preparation.json').relative_to(ROOT))] = sha(old / f'{mode}_preparation.json')
    sources[str(PLAN.relative_to(ROOT))] = sha(PLAN)
    sources[str(Path(__file__).relative_to(ROOT))] = sha(Path(__file__))
    for path, digest in sources.items():
        if sha(ROOT / path) != digest:
            raise ValueError('Original source changed: ' + path)
    x = dict(np.load(old / f'{mode}_inputs.npz'))
    meta = copy.deepcopy(json.loads((data / 'atlas.json').read_text()))
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'):
            meta[k] = meta['corrected_climate'][k]
    shape = tuple(x['shape']); size = int(np.prod(shape)); land = x['land']; cell = float(x['cell_km'])
    arrays = P.climate_arrays(folder, meta)
    with np.load(folder / 'administration_grid.npz') as z:
        elev = z['elev']; density = z['density']
        assert np.array_equal(z['land'], land)
    assert np.array_equal(elev, arrays['elev'])
    road = P.F.block_any(P.F.rgba('roads.png')[..., 3] > 0, shape) & land
    swamp = np.asarray(Image.fromarray((P.target_fullres() == 5).astype(np.uint8) * 255).resize(
        (shape[1], shape[0]), Image.Resampling.BOX)) > 127
    climate = P.F.map_climate(data, meta, arrays, shape)
    world = dict(elev=elev, land=land, road=road, density=density, cell_km=cell, biome=np.asarray(arrays['biome']),
                 swamp=swamp, tilt=meta['world']['tilt'], river=P.F.navigable_rivers(shape), **climate)
    st = P.N.statics(world); cl = P.N.climate(world, st)
    def graph(month):
        crossing = np.where(st['basin'] > 0, P.S.CROSS_DAYS * (1 + P.S.FLOOD_GAIN * P.S.flood_index(cl['flow'][month][st['basin']])), 0.)
        a, b, d = P.C.foot_edges(elev, land, road, P.S.month_terrain(st['eta'], cl, month), cell,
            np.full(shape, P.C.OFF_PATH), road_factor=1 + (P.S.MUD_ROAD - 1) * cl['mud'][month], cross=crossing)
        return csr_matrix((d, (a, b)), shape=(size, size))
    original = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
    spec = original['specification']; nodes = x['nodes']; base = graph(spec['collection_base_bin'])
    days, parent, roots = dijkstra(base.T.tocsr(), indices=nodes, min_only=True, return_predecessors=True, directed=True)
    parent[nodes] = nodes
    valid = land.ravel() & np.isfinite(days) & (days <= spec['collection_maximum_days_each_way'])
    local = np.flatnonzero(valid); lookup = np.full(size, -1, int); lookup[local] = np.arange(len(local))
    site_lookup = np.full(size, -1, int); site_lookup[nodes] = np.arange(len(nodes))
    if not np.array_equal(local, x['local_index']) or not np.array_equal(site_lookup[roots[local]], x['owner']):
        raise ValueError('Collection origin/owner partition differs from original')
    order = np.flatnonzero(valid & (parent != np.arange(size))); order = order[np.argsort(days[order])]
    out_days = []; back_days = []; edge_out = []; edge_back = []
    for month in range(12):
        g = base if month == spec['collection_base_bin'] else graph(month)
        a, b = P.fixed_path_days(g, parent, order)
        access = (a[local] <= spec['collection_maximum_days_each_way']) & (b[local] <= spec['collection_maximum_days_each_way'])
        if not np.array_equal(access, x['access'][month]):
            raise ValueError('Original monthly collection access changed')
        out_days.append(a[local]); back_days.append(b[local])
        edge_out.append(np.asarray(g[parent[local], local]).ravel())
        edge_back.append(np.asarray(g[local, parent[local]]).ravel())
        print(mode, 'checked original routes month', month + 1, flush=True)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'{mode}_paths.npz'
    np.savez_compressed(path, local_index=local, owner=x['owner'], nodes=nodes,
        parent_local=lookup[parent[local]], outward_days=np.asarray(out_days), inward_days=np.asarray(back_days),
        edge_outward_days=np.asarray(edge_out), edge_inward_days=np.asarray(edge_back), access=x['access'])
    for p, digest in sources.items():
        if sha(ROOT / p) != digest:
            raise ValueError('Original source changed during path rebuild: ' + p)
    write(out / f'{mode}_paths.json', dict(status='original_paths_reproduced', sources=sources,
        paths_sha256=sha(path), walking_hours_day=P.C.MARCH_HOURS, local_origins=len(local),
        owner_indices_nodes_and_all12access_masks_exact=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args(); prepare(args.mode, args.out)
