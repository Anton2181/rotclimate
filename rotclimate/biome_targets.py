"""Experimental painted-zone crosswalk to Whittaker climate envelopes.

This is an alternative calibration hypothesis, not a relabeling of the atlas.
Hard matches use its exact published classifier. Soft credit guides a search
toward the allowed envelopes without assigning outside climates a biome.
"""
from functools import lru_cache
import json

import numpy as np
from matplotlib.path import Path

from . import biomes
from .config import DATA
from .geography import TARGET_CLASSES


@lru_cache(maxsize=1)
def specification():
    spec = json.loads((DATA / 'biome_target_crosswalk.json').read_text())
    keys = {key for _, key, _, _ in TARGET_CLASSES}
    for mapping in spec['profiles'].values():
        if set(mapping) != keys or any(not ids or not set(ids) <= set(range(1, 10))
                                      for ids in mapping.values()):
            raise ValueError('Crosswalk must define nonempty biome sets for every painted zone')
    scales = spec['distance_scales']
    if not all(np.isfinite(x) and x > 0 for x in scales.values()):
        raise ValueError('Distance scales must be finite and positive')
    return spec


def envelope_distance(temperature, precipitation, allowed):
    """Euclidean distance to the union of polygons, in declared scaled axes."""
    t, p = np.broadcast_arrays(np.asarray(temperature, float), np.asarray(precipitation, float))
    scales = specification()['distance_scales']
    points = np.column_stack((t.ravel() / scales['temperature_C'],
                              p.ravel() / scales['precipitation_mm']))
    distance2 = np.full(len(points), np.inf)
    valid = np.isfinite(points).all(1) & (p.ravel() >= 0)
    inside = np.zeros(len(points), bool)
    for code in allowed:
        vertices = biomes.polygons()[code] / [scales['temperature_C'], scales['precipitation_mm']]
        path = Path(vertices)
        inside |= path.contains_points(points, radius=1e-10) | path.contains_points(points, radius=-1e-10)
        for a, b in zip(vertices, np.roll(vertices, -1, axis=0)):
            edge = b - a
            length2 = float(edge @ edge)
            if length2 == 0:
                continue
            projection = np.clip(((points - a) @ edge) / length2, 0, 1)
            d2 = np.sum((points - a - projection[:, None] * edge) ** 2, axis=1)
            distance2 = np.minimum(distance2, d2)
    distance2[inside] = 0
    distance2[~valid] = np.inf
    return np.sqrt(distance2).reshape(t.shape)


def evaluate(indices, target, valid, profile='strict'):
    """Zone-balanced hard coverage and continuous envelope fit on model cells.

    Missing zones are omitted, as in the existing scorer. Nonfinite climates
    on valid painted cells receive zero credit rather than disappearing.
    """
    mapping = specification()['profiles'][profile]
    codes = biomes.classify(indices['MAT'], indices['MAP'])
    per = {}
    for cid, key, _, _ in TARGET_CLASSES:
        mask = np.asarray(valid, bool) & (target == cid)
        if not mask.any():
            continue
        hard = np.isin(codes[mask], mapping[key])
        distance = envelope_distance(indices['MAT'][mask], indices['MAP'][mask], mapping[key])
        soft = np.exp(-0.5 * distance ** 2)
        per[key] = dict(cells=int(mask.sum()), hard=float(hard.mean()), soft=float(soft.mean()))
    if not per:
        raise ValueError('No painted land cells available for biome calibration')
    hard = float(np.mean([v['hard'] for v in per.values()]))
    soft = float(np.mean([v['soft'] for v in per.values()]))
    painted = np.asarray(valid, bool) & (target > 0)
    return dict(profile=profile, score=(hard + soft) / 2, macro_hard=hard, macro_soft=soft,
                outside_share=float(np.mean(codes[painted] == 0)), per_zone=per)


def average(rows):
    """Average scores across individual layouts; do not average biome IDs."""
    if not rows or len({r['profile'] for r in rows}) != 1:
        raise ValueError('Need nonempty results from a single crosswalk profile')
    keys = set(rows[0]['per_zone'])
    if any(set(r['per_zone']) != keys for r in rows):
        raise ValueError('Layout results have different target-zone coverage')
    return dict(profile=rows[0]['profile'], layouts=len(rows),
                **{k: float(np.mean([r[k] for r in rows]))
                   for k in ('score', 'macro_hard', 'macro_soft', 'outside_share')},
                per_zone={k: {m: float(np.mean([r['per_zone'][k][m] for r in rows]))
                              for m in ('hard', 'soft')} for k in sorted(keys)})
