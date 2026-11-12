"""Recover compatible current cell population/crop inputs and frozen foot paths.

Reads published r44 packets. Does not rerun climate, town placement, tracks or
authority. Hard-checks the local owner partition before producing new inputs.
"""
import copy
import gzip
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha, write
from harvest.export import climate_arrays, geometry
from population.export import decode_harvest
from polity import fields as F, control as C, seasons as S, network as N
from polity.sustained_presence import fixed_path_days
from rotclimate.geography import target_fullres
from land_people import FARMED_SHARE, FALLOW

OUT = ROOT / 'output/settlement_feedback_20261112'
PLAN = ROOT / 'calibration/settlement_feedback_20261112/plan.json'
DATA = ROOT / 'atlases/earth_fit/data'


def prepare(mode, out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    original = json.loads((DATA / 'atlas.json').read_text()); meta = copy.deepcopy(original)
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'):
            meta[k] = original['corrected_climate'][k]
    paths = [DATA / 'atlas.json', DATA / 'winds12.npz', DATA / 'settled_reach.json',
        folder / 'atlas.bin', folder / 'harvest.json', folder / 'harvest.bin', folder / 'farm_work_grid.npz',
        folder / 'administration_grid.npz', folder / 'settled_reach.json.gz', folder / 'settled_reach.bin.gz',
        ROOT / meta['world']['terrain_file'], ROOT / 'data/arable_slope_model.json',
        ROOT / 'data/source/elevation.png', ROOT / 'data/source/rivers.png', ROOT / 'data/source/original/rivers.png',
        ROOT / 'data/source/ravages_v8/roads.png']
    paths += [ROOT / p for p in ['scripts/prepare_settlement_feedback.py', 'harvest/export.py', 'population/export.py',
        'scripts/land_people.py', 'polity/fields.py', 'polity/control.py', 'polity/network.py',
        'polity/seasons.py', 'polity/sustained_presence.py', 'rotclimate/geography.py', 'scripts/vector_rivers.py']]
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    model = json.loads(gzip.decompress((folder / 'settled_reach.json.gz').read_bytes()))
    packet = json.loads((DATA / 'settled_reach.json').read_text())['packets'][mode]
    shape = tuple(packet['shape']); size = int(np.prod(shape)); cell = meta['width'] / shape[1] * meta['mi_per_px'] * 1.609344
    with gzip.open(folder / 'settled_reach.bin.gz', 'rb') as f:
        prefix = f.read(packet['offsets']['masks'])
    old_owner = np.frombuffer(prefix, '<u2', count=size, offset=packet['offsets']['catchments']).copy()
    old_land = np.frombuffer(prefix, '<u4', count=size).reshape(shape) > 0
    print(mode, 'reading current published population/crop geometry', flush=True)
    arrays = climate_arrays(folder, meta); hm, hf = decode_harvest(folder); geo, _ = geometry(meta, shape)
    land = geo['land_fraction'] > .5
    if not np.array_equal(land, old_land):
        raise ValueError('Published collection land differs from current geography')
    with np.load(folder / 'administration_grid.npz') as z:
        density = z['density']; archived_land = z['land']; elev = z['elev']
    expected_density = np.where(land, hf['settlement_base'] * hm['occupation']['scenarios']['central'], 0.)
    if not np.array_equal(archived_land, land) or not np.array_equal(density, expected_density):
        raise ValueError('Administrative population input is not the current crop/occupation packet')
    if not np.array_equal(elev, arrays['elev']):
        raise ValueError('Terrain input differs across published packets')
    with np.load(folder / 'farm_work_grid.npz') as z:
        # Harvest retains any coastal land fraction; political transport uses
        # majority-land cells. Verify BOTH original rules, without changing
        # the population/collection domain to fit the larger crop mask.
        farm_land = z['land']
        if not np.array_equal(farm_land, geo['land_fraction'] > 0) or np.any(land & ~farm_land):
            raise ValueError('Farm-work grid does not follow its published coastal-land rule')
        crop = z['cereal']; boundaries = z['harvest_boundaries']
        listed = np.nan_to_num(z['listed_hours_per_million_kcal']).astype(float)
        reaping = np.nan_to_num(z['reaping_hours_per_million_kcal']).astype(float)
    area = geo['land_fraction'] * cell ** 2
    kcal = np.where(crop == 1, hf['kcal_wheat'], np.where(crop == 2, hf['kcal_barley'], 0.))
    potential = np.where(land, kcal * 100 * area * hf['arable'] * FARMED_SHARE * FALLOW, 0.)
    people = np.where(land, density * cell ** 2, 0.)
    route = F.block_any(F.rgba('roads.png')[..., 3] > 0, shape); road = route & land
    swamp = np.asarray(Image.fromarray((target_fullres() == 5).astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.Resampling.BOX)) > 127
    climate = F.map_climate(DATA, meta, arrays, shape)
    world = dict(elev=elev, land=land, road=road, density=density, cell_km=cell,
        biome=np.asarray(arrays['biome']), swamp=swamp, tilt=meta['world']['tilt'], river=F.navigable_rivers(shape), **climate)
    st = N.statics(world); cl = N.climate(world, st)
    def graph(month):
        crossing = np.where(st['basin'] > 0, S.CROSS_DAYS * (1 + S.FLOOD_GAIN * S.flood_index(cl['flow'][month][st['basin']])), 0.)
        a, b, d = C.foot_edges(elev, land, road, S.month_terrain(st['eta'], cl, month), cell,
            np.full(shape, C.OFF_PATH), road_factor=1 + (S.MUD_ROAD - 1) * cl['mud'][month], cross=crossing)
        return csr_matrix((d, (a, b)), shape=(size, size))
    sites = model['sites']; nodes = np.array([s['node'] for s in sites], int); spec = model['specification']
    base = graph(spec['collection_base_bin'])
    days, parent, roots = dijkstra(base.T.tocsr(), indices=nodes, min_only=True, return_predecessors=True, directed=True)
    parent[nodes] = nodes; lookup = np.zeros(size, np.uint16); lookup[nodes] = np.arange(1, len(nodes) + 1)
    valid = land.ravel() & np.isfinite(days) & (days <= spec['collection_maximum_days_each_way'])
    assignment = np.zeros(size, np.uint16); assignment[valid] = lookup[roots[valid]]
    if not np.array_equal(assignment, old_owner):
        raise ValueError('Reconstructed foot-collection owners differ from the frozen current packet')
    local = np.flatnonzero(assignment > 0)
    order = np.flatnonzero(valid & (parent != np.arange(size))); order = order[np.argsort(days[order])]
    access = np.zeros((12, len(local)), bool)
    for month in range(12):
        g = base if month == spec['collection_base_bin'] else graph(month)
        outward, inward = fixed_path_days(g, parent, order)
        access[month] = (outward[local] <= spec['collection_maximum_days_each_way']) & (inward[local] <= spec['collection_maximum_days_each_way'])
        print(mode, 'verified local paths month', month + 1, flush=True)
    output = out / f'{mode}_inputs.npz'
    np.savez_compressed(output, shape=np.array(shape), cell_km=cell, land=land, area=area,
        people=people.ravel(), potential_kcal=potential.ravel(), boundaries=boundaries.ravel(),
        listed_hours=listed.ravel(), reaping_hours=reaping.ravel(), local_index=local,
        owner=assignment[local].astype(np.int64) - 1, access=access, nodes=nodes,
        civilian_request=np.array([s['civilian_request_people'] for s in sites]),
        affiliated=np.array([s['actor_index'] >= 0 for s in sites]),
        actor=np.array([s['actor_index'] for s in sites], int))
    for p, digest in sources.items():
        if sha(ROOT / p) != digest:
            raise ValueError('Input changed during preparation: ' + p)
    result = dict(status='current_cell_inputs_reconstructed', plan_sha256=sha(PLAN), sources=sources,
        inputs_sha256=sha(output), shape=list(shape), cell_km=cell, land_cells=int(land.sum()),
        local_origins=len(local), total_people=float(people.sum()), local_people=float(people.ravel()[local].sum()),
        outside_collection_people=float(people.sum() - people.ravel()[local].sum()),
        population_density_exact=True, collection_owner_exact=True, all_monthly_paths_recomputed=True,
        farm_coastal_land_rule_exact=True, partial_coastal_cells_outside_transport=int(np.sum(farm_land & ~land)),
        people_area='Same square cell area used by the existing transport population; crop area retains land fraction.',
        scope='Current r44 published inputs, no climate/town/track regeneration. Local collection population differs from wide trade catchments.')
    write(out / f'{mode}_preparation.json', result)
    print(mode, 'prepared', len(local), 'local origins with exact owner compatibility', flush=True)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('raw', 'corrected'), required=True)
    p.add_argument('--out', type=Path, default=OUT); a = p.parse_args(); prepare(a.mode, a.out)
