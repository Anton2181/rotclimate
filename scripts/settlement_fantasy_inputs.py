"""Reassemble the published fantasy inputs used for town placement, tracks and local collection.

Mirrors polity.fields.compute and scripts/prepare_settlement_feedback.py without
rerunning climate. Callers verify exact reproduction of published towns/owners.
"""
import copy, json
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from harvest.export import climate_arrays, geometry
from harvest.models import core_term, lore_cores
from population.export import decode_harvest
from polity import fields as F, control as C, seasons as S, network as N
from rotclimate.geography import target_fullres

DATA = ROOT / 'atlases/earth_fit/data'


def world(mode):
    original = json.loads((DATA / 'atlas.json').read_text()); meta = copy.deepcopy(original)
    folder = DATA / ('corrected' if mode == 'corrected' else '')
    if mode == 'corrected':
        for k in ('arrays', 'lapse12', 'cell_px', 'harvest'):
            meta[k] = original['corrected_climate'][k]
    arrays = climate_arrays(folder, meta); elev = np.asarray(arrays['elev'], float); shape = elev.shape
    geo, _ = geometry(meta, shape); land = geo['land_fraction'] > .5
    cell = meta['width'] / shape[1] * meta['mi_per_px'] * 1.609344
    hm, hf = decode_harvest(folder)
    density = np.where(land, hf['settlement_base'] * hm['occupation']['scenarios']['central'], 0.)
    route = F.block_any(F.rgba('roads.png')[..., 3] > 0, shape); road = route & land
    ferry = ndi.binary_closing(route, iterations=2) & ~land
    towns = F.settlements(shape); _, nearest = ndi.distance_transform_edt(~land, return_indices=True)
    marked = [(int(nearest[0, t['row'], t['col']]), int(nearest[1, t['row'], t['col']])) for t in towns]
    ids, info = F.polity_fills(shape)
    biome = np.asarray(arrays['biome'])
    swamp = np.asarray(Image.fromarray((target_fullres() == 5).astype(np.uint8) * 255).resize((shape[1], shape[0]), Image.Resampling.BOX)) > 127
    prior = core_term(land, biome, elev, cell, lore_cores(meta['width'], meta['height'], shape))
    return dict(mode=mode, folder=folder, meta=meta, arrays=arrays, shape=shape, land=land, elev=elev, cell=cell, density=density,
        road=road, ferry=ferry, marked=marked, claim_ids=ids, claim_info=info, claimed=land & (ids > 0), biome=biome, swamp=swamp,
        water_km=geo['water_distance'], aridity=hf['aridity'], dry_water_km=F.map_dry_water_km(), prior=prior)


def collection_owner(w, nodes, base_bin, max_days):
    """One-day foot-collection partition (zero-based owner, -1 unassigned), as the reviewed ledger inputs."""
    shape = w['shape']; size = shape[0] * shape[1]; land = w['land']
    climate = F.map_climate(DATA, w['meta'], w['arrays'], shape)
    wd = dict(elev=w['elev'], land=land, road=w['road'], density=w['density'], cell_km=w['cell'], biome=w['biome'],
              swamp=w['swamp'], tilt=w['meta']['world']['tilt'], river=F.navigable_rivers(shape), **climate)
    st = N.statics(wd); cl = N.climate(wd, st); month = base_bin
    crossing = np.where(st['basin'] > 0, S.CROSS_DAYS * (1 + S.FLOOD_GAIN * S.flood_index(cl['flow'][month][st['basin']])), 0.)
    a, b, d = C.foot_edges(w['elev'], land, w['road'], S.month_terrain(st['eta'], cl, month), w['cell'],
        np.full(shape, C.OFF_PATH), road_factor=1 + (S.MUD_ROAD - 1) * cl['mud'][month], cross=crossing)
    g = csr_matrix((d, (a, b)), shape=(size, size))
    nodes = np.asarray(nodes, int)
    days, _, roots = dijkstra(g.T.tocsr(), indices=nodes, min_only=True, return_predecessors=True, directed=True)
    valid = land.ravel() & np.isfinite(days) & (days <= max_days)
    lookup = np.full(size, -1, int); lookup[nodes] = np.arange(len(nodes))
    owner = np.full(size, -1, int); owner[valid] = lookup[roots[valid]]
    return owner


def tracks(w, suggested):
    from polity.control import path_factor, terrain_coefficient, travel_graph
    from polity.settle import minor_roads
    bare = travel_graph(w['elev'], w['land'], w['road'], terrain_coefficient(w['biome'], w['swamp'], None), w['cell'],
                        path_factor(w['density']), w['ferry'])
    mask, routes, links = minor_roads(bare, w['shape'], w['road'], suggested, w['marked'])
    return mask
