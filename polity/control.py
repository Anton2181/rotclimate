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
  unmarked tracks    25 km a day: the suggested minor roads between the unmarked
                     towns of polity/settle.py
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
TRACK_KM_DAY = 25.0             # an unmarked minor road (polity/settle.py)
FERRY_KM_DAY = 40.0             # a crossing on the map's ferry routes, waiting for the boat included
MARCH_HOURS = 7.0
OFF_PATH = 0.6
CONTROL_DAYS = 1.0
SNOW_COEFFICIENT = 2.5          # soft snow (Soule & Goldman 1972)
# terrain coefficients by rotclimate.biomes code
BIOME_COEFFICIENT = {0: 1.2, 1: 1.2, 2: 1.6, 3: 1.7, 4: 1.8, 5: 1.2, 6: 1.3, 7: 1.5, 8: 1.1, 9: 1.5}
SWAMP_COEFFICIENT = 1.8
HORSE_KM_DAY = 50.0             # mounted pastoralists on level open ground
HORSE_SNOW_COEFFICIENT = 2.0
STRONG_WIND = (8.0, 10.8)       # m/s: Beaufort 5 (uncertain) and 6 (closed)
# fitted on Han China, AD 2 (scripts/polity_earth_check.py, calibration/polity_20261025)
# (F2: counting a county seat 0.25-1 day farther than a commandery seat, or wearing places down by their
# days from the capital, gave no better account of the empire's extent, so places are not ranked)
RANK_OFFSET_DAYS = 0.0          # a county-level place counts as if this much farther than a commandery seat
# (F4: in Han China ln(registered / modelled people) per commandery fell by 2.60 per km of mean relief, 95 %
# -3.84 to -1.35; but on the Roman empire the factor made both the extent (T1) and the towns per block (T2:
# Spearman 0.146 -> 0.129) worse, so it is off: the Han slope is more likely the Harvest model's mountains
# than people out of the state's reach)
REFUGE_PER_KM = 0.0             # control x exp(this x relief in km)
UNCERTAIN, CLOSED = 0.5, 0.15


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


def foot_edges(elevation, land, road, eta, cell_km, paths=None, ferry=None, tracks=None,
               road_factor=None, track_factor=None, cross=None):
    """Directed 8-neighbour walking edges, cost in days; road-to-road steps at road speed.
    paths (optional): the walking pace factor of each cell (path_factor), else off-path.
    ferry (optional): water cells on a ferry route, crossed at FERRY_KM_DAY.
    tracks (optional): cells on an unmarked minor road, at TRACK_KM_DAY.
    road_factor, track_factor (optional, per cell): mud on the roads and tracks (polity/seasons.py).
    cross (optional, days per cell): fording a navigable river, paid on stepping
    onto it from off the river and off the roads.
    Returns (src, dst, days) flat-index arrays."""
    z = np.asarray(elevation, float); road = np.asarray(road, bool) & np.asarray(land, bool)
    ferry = np.zeros(z.shape, bool) if ferry is None else np.asarray(ferry, bool) & ~np.asarray(land, bool)
    tracks = np.zeros(z.shape, bool) if tracks is None else np.asarray(tracks, bool) & np.asarray(land, bool)
    rf = np.ones(z.shape) if road_factor is None else np.asarray(road_factor, float)
    tf = np.ones(z.shape) if track_factor is None else np.asarray(track_factor, float)
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
        on = km / ROAD_KM_DAY * 0.5 * (rf[src] + rf[dst])
        both_road = road[src] & road[dst]
        days = np.where(both_road, np.minimum(on, off), off)
        on_track = (tracks[src] | road[src]) & (tracks[dst] | road[dst]) & ~both_road
        days = np.where(on_track, np.minimum(km / TRACK_KM_DAY * 0.5 * (tf[src] + tf[dst]), days), days)
        days = np.where(ferry[src] | ferry[dst], km / FERRY_KM_DAY, days)
        if cross is not None:
            days = days + np.where((cross[dst] > 0) & (cross[src] <= 0) & ~both_road, cross[dst], 0.0)
        rows.append(nodes[src][ok]); cols.append(nodes[dst][ok]); cost.append(days[ok])
    return np.concatenate(rows), np.concatenate(cols), np.concatenate(cost)


def travel_graph(elevation, land, road, eta, cell_km, paths=None, ferry=None, tracks=None, **kw):
    """Directed 8-neighbour walking graph (csr), edge cost in days (foot_edges)."""
    r, c, d = foot_edges(elevation, land, road, eta, cell_km, paths, ferry, tracks, **kw)
    n = np.asarray(elevation).size
    return coo_matrix((d, (r, c)), shape=(n, n)).tocsr()


def horse_edges(elevation, land, eta, cell_km, forest_or_swamp=None):
    """Mounted pastoralists: HORSE_KM_DAY on level open ground, Tobler's slope
    shape, the excess terrain coefficient doubled in forest and swamp, no
    roads needed. Returns (src, dst, days)."""
    z = np.asarray(elevation, float); land = np.asarray(land, bool)
    eta = np.asarray(eta, float)
    if forest_or_swamp is not None:
        eta = np.where(forest_or_swamp, 1.0 + 2.0 * (eta - 1.0), eta)
    h, w = z.shape; nodes = np.arange(z.size).reshape(z.shape)
    rows, cols, cost = [], [], []
    level = float(tobler_km_h(0.0, 1.0))
    for dy, dx in [(a, b) for a in (-1, 0, 1) for b in (-1, 0, 1) if a or b]:
        y0, y1 = max(0, -dy), min(h, h - dy); x0, x1 = max(0, -dx), min(w, w - dx)
        src = np.s_[y0:y1, x0:x1]; dst = np.s_[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
        ok = land[src] & land[dst]
        if dy and dx:
            ok &= land[y0:y1, x0 + dx:x1 + dx] & land[y0 + dy:y1 + dy, x0:x1]
        km = cell_km * np.hypot(dy, dx)
        slope = (z[dst] - z[src]) / (km * 1000.0)
        km_day = HORSE_KM_DAY * tobler_km_h(slope, 1.0) / level / (0.5 * (eta[src] + eta[dst]))
        rows.append(nodes[src][ok]); cols.append(nodes[dst][ok]); cost.append((km / km_day)[ok])
    return np.concatenate(rows), np.concatenate(cols), np.concatenate(cost)


class Network:
    """One month's graph of every way of travelling, with a virtual source
    node so that places can start with a head start or a handicap (ranks,
    loss of strength). Nodes: the grid cells, then the river-boat nodes, then
    the virtual node."""

    def __init__(self, n_cells, edges, n_extra=0):
        r = np.concatenate([e[0] for e in edges]); c = np.concatenate([e[1] for e in edges])
        d = np.concatenate([e[2] for e in edges])
        self.n_cells = n_cells; self.n = n_cells + n_extra + 1; self.virtual = self.n - 1
        self.base = coo_matrix((d, (r, c)), shape=(self.n, self.n)).tocsr()

    def days(self, sources, offsets=None, limit=np.inf):
        """Cheapest days from the sources (flat cell indices) to every cell,
        each source starting `offsets` days late (>= 0)."""
        src = np.asarray(sorted(set(int(s) for s in sources)) if offsets is None else sources, np.int64)
        if not len(src):
            return np.full(self.n_cells, np.inf)
        off = np.zeros(len(src)) if offsets is None else np.asarray(offsets, float)
        if offsets is not None:                     # keep each cell's best offset
            order = np.lexsort((off, src)); src, off = src[order], off[order]
            first = np.r_[True, src[1:] != src[:-1]]; src, off = src[first], off[first]
        v = coo_matrix((off + 1e-9, (np.full(len(src), self.virtual), src)), shape=(self.n, self.n)).tocsr()
        d = dijkstra(self.base + v, directed=True, indices=self.virtual, limit=limit)
        return d[:self.n_cells]


def effective_days(days_by_month):
    """Year-round days: the days whose control equals the mean control over
    the months, -D ln(mean_m exp(-days_m / D))."""
    c = np.mean(np.exp(-np.asarray(days_by_month) / CONTROL_DAYS), 0)
    with np.errstate(divide="ignore"):
        return -CONTROL_DAYS * np.log(c)


def sea_season(sigma, wind, uncertain_sigma, closed_sigma):
    """Closure factor of the sea: storminess (the swing of the wind about its
    mean, m/s) against thresholds fitted to Vegetius' sailing season, and
    strong mean winds (Beaufort 5 uncertain, 6 closed)."""
    f = np.ones(np.shape(sigma))
    unc = (np.asarray(sigma) >= uncertain_sigma) | (np.asarray(wind) >= STRONG_WIND[0])
    clo = (np.asarray(sigma) >= closed_sigma) | (np.asarray(wind) >= STRONG_WIND[1])
    f = np.where(unc, UNCERTAIN, f)
    return np.where(clo, CLOSED, f)


def days_from(graph, shape, sources):
    """Cheapest days from any source cell (outward travel, as a patrol goes)."""
    ids = sorted({int(r) * shape[1] + int(c) for r, c in sources})
    if not ids:
        return np.full(shape, np.inf)
    return dijkstra(graph, directed=True, indices=ids, min_only=True).reshape(shape)


def control(days):
    return np.exp(-np.asarray(days) / CONTROL_DAYS)
