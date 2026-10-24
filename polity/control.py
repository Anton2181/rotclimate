"""Effective control: travel time from a polity's roads and towns, and its fade.

A polity governs where its officials, tax collectors and patrols can get to
and back. Its reach is measured in days of travel for a person on foot:

  roads              30 km a day (ORBIS's civilian on foot; Scheidel & Meeks 2012)
  off the road       Tobler's hiking function, 6 exp(-3.5 |slope + 0.05|) km/h,
                     x 0.6 off paths, for 7 marching hours a day (21 km on
                     level open ground), divided by the terrain coefficient
                     of the ground (Soule & Goldman 1972: light brush 1.2,
                     heavy brush 1.5, swamp 1.8, loose sand 2.1, soft snow 2.5)
  footpaths          the off-path 0.6 rises toward 1.0 with the people per km2
                     (half-way at 20): farmed land is laced with tracks
  ferry routes       the map's dotted routes over water, 40 km a day with the wait
  other water        not crossed (no open-sea shipping yet)

Days beyond the network = the cheapest travel to the nearest road or
settlement. Effective control = exp(-days / 1 day): one day out (and one back)
is the reach a county seat or a fort holds directly; at two days a third of it
remains, at three days a twentieth (the "day's walk to the seat" of premodern
administrative geography; Skinner 1977, Scott 2009 on the friction of terrain).
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROAD_KM_DAY = 30.0
FERRY_KM_DAY = 40.0             # a crossing on the map's ferry routes, waiting for the boat included
MARCH_HOURS = 7.0
OFF_PATH = 0.6
CONTROL_DAYS = 1.0
SNOW_COEFFICIENT = 2.5          # soft snow (Soule & Goldman 1972)
# terrain coefficients by rotclimate.biomes code
BIOME_COEFFICIENT = {0: 1.2, 1: 1.2, 2: 1.6, 3: 1.7, 4: 1.8, 5: 1.2, 6: 1.3, 7: 1.5, 8: 1.1, 9: 1.5}
SWAMP_COEFFICIENT = 1.8


def tobler_km_h(slope, factor=OFF_PATH):
    return 6.0 * factor * np.exp(-3.5 * np.abs(np.asarray(slope) + 0.05))


def terrain_coefficient(biome, swamp, snow_share=None):
    """Soule-Goldman coefficient per cell; snow_share (0-1) of the season under snow."""
    eta = np.vectorize(lambda b: BIOME_COEFFICIENT.get(int(b), 1.2))(np.asarray(biome))
    eta = np.where(swamp, np.maximum(eta, SWAMP_COEFFICIENT), eta)
    if snow_share is not None:
        eta = eta * (1.0 + (SNOW_COEFFICIENT - 1.0) * np.clip(snow_share, 0, 1))
    return eta


def path_factor(density):
    """Footpaths thicken with people: Tobler's off-path pace (x 0.6) in empty
    land, rising toward his on-path pace (x 1.0) where farms and villages lace
    the ground with tracks; half-way at 20 people per km2."""
    d = np.maximum(np.nan_to_num(np.asarray(density, float)), 0.0)
    return OFF_PATH + (1.0 - OFF_PATH) * d / (d + 20.0)


def travel_graph(elevation, land, road, eta, cell_km, paths=None, ferry=None):
    """Directed 8-neighbour graph, edge cost in days; road-to-road steps at road speed.
    paths (optional): the walking pace factor of each cell (path_factor), else off-path.
    ferry (optional): water cells on a ferry route, crossed at FERRY_KM_DAY."""
    z = np.asarray(elevation, float); road = np.asarray(road, bool) & np.asarray(land, bool)
    ferry = np.zeros(z.shape, bool) if ferry is None else np.asarray(ferry, bool) & ~np.asarray(land, bool)
    land = np.asarray(land, bool) | ferry          # passable
    h, w = z.shape; nodes = np.arange(z.size).reshape(z.shape)
    rows, cols, cost = [], [], []
    for dy, dx in [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]:
        y0, y1 = max(0, -dy), min(h, h - dy); x0, x1 = max(0, -dx), min(w, w - dx)
        src = np.s_[y0:y1, x0:x1]; dst = np.s_[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = land[src] & land[dst]
        if dy and dx:            # no corner cutting across water
            ok &= land[y0:y1, x0 + dx:x1 + dx] & land[y0 + dy:y1 + dy, x0:x1]
        km = cell_km * np.hypot(dy, dx)
        slope = (z[dst] - z[src]) / (km * 1000.0)
        pace = OFF_PATH if paths is None else 0.5 * (paths[src] + paths[dst])
        off = km / (tobler_km_h(slope, pace) * MARCH_HOURS / (0.5 * (eta[src] + eta[dst])))
        on = km / ROAD_KM_DAY
        days = np.where(road[src] & road[dst], np.minimum(on, off), off)
        days = np.where(ferry[src] | ferry[dst], km / FERRY_KM_DAY, days)
        rows.append(nodes[src][ok]); cols.append(nodes[dst][ok]); cost.append(days[ok])
    return coo_matrix((np.concatenate(cost), (np.concatenate(rows), np.concatenate(cols))),
                      shape=(z.size, z.size)).tocsr()


def days_from(graph, shape, sources):
    """Cheapest days from any source cell (outward travel, as a patrol goes)."""
    ids = sorted({int(r) * shape[1] + int(c) for r, c in sources})
    if not ids:
        return np.full(shape, np.inf)
    return dijkstra(graph, directed=True, indices=ids, min_only=True).reshape(shape)


def control(days):
    return np.exp(-np.asarray(days) / CONTROL_DAYS)
