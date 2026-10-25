"""Where the unmarked towns and minor roads would be.

The campaign map marks the main roads and the walled places. A populated
countryside also has market towns and county seats, joined by tracks. Sites
and spacing follow simple central-place rules:

  where      among farming people (the Harvest density, central scenario),
             beside rivers and lakes (x 2 at the water, fading over ~3 km), on
             sheltered coasts (x 1.5), on flat ground, along the marked roads
             (x 1.5), never inside a marked town's own catchment
  how many   one town per 40,000 people (the mean Han county of AD 2), so its
             catchment radius is R = sqrt(40,000 / (pi x density)): ~20 km in
             rich valleys, ~50 km in thin country, none below 2 people per km2
  spacing    greedy, best site first, no town within 1.6 R of another (a
             hexagonal tiling of such catchments has its centres 1.9 R apart)
  sites      +-25 % for the local quirks no layer holds (springs, fords, a
             defensible hill), fixed seed; claimed land only
  tracks     a relative neighbourhood graph on travel days between the towns,
             the marked settlements and the marked roads (minor_roads)

A town's size is a guess: 5-10 % of its catchment (premodern urban shares).
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse.csgraph import dijkstra

SEAT_PEOPLE = 40000.0
MAX_RADIUS_KM = 60.0            # no catchment wider than this, however thin the people
MIN_DENSITY = 2.0
SPACING = 1.6
URBAN_SHARE = 0.075


def site_score(density, land, water_km, coast_km, road, elev, cell_km):
    d = ndi.gaussian_filter(np.where(land, density, 0.0), 1.0)
    river = 1.0 + np.exp(-np.maximum(np.nan_to_num(water_km, nan=99), 0) / 3.0)
    coast = 1.0 + 0.5 * (coast_km <= 6.0)
    near_road = 1.0 + 0.5 * (ndi.distance_transform_edt(~road) * cell_km <= 4.0)
    gy, gx = np.gradient(np.asarray(elev, float), cell_km * 1000.0)
    flat = 1.0 / (1.0 + 20.0 * np.hypot(gx, gy))
    return np.where(land, d * river * coast * near_road * flat, 0.0), d


def place_towns(density, land, water_km, road, elev, cell_km, marked, allowed=None, seed=1,
                seat_people=None, max_radius_km=None):
    seat_people = SEAT_PEOPLE if seat_people is None else seat_people
    max_radius_km = MAX_RADIUS_KM if max_radius_km is None else max_radius_km
    coast_km = ndi.distance_transform_edt(land) * cell_km
    score, d = site_score(density, land, water_km, coast_km, road, elev, cell_km)
    # local quirks of site (springs, fords, a defensible hill) that no map layer
    # holds: +-25 % on a ~10 km scale, fixed seed
    rng = np.random.default_rng(seed)
    quirk = ndi.gaussian_filter(rng.standard_normal(land.shape), 1.5)
    score = score * np.exp(0.25 * quirk / max(quirk.std(), 1e-9))
    radius = np.sqrt(seat_people / (np.pi * np.maximum(d, 1e-9))) / cell_km        # cells
    ok = land & (d >= MIN_DENSITY)
    if allowed is not None:
        ok &= allowed
    blocked = np.zeros(land.shape, bool)
    h, w = land.shape

    def block(y, x, rad):
        r = int(np.ceil(rad))
        y0, y1, x0, x1 = max(0, y - r), min(h, y + r + 1), max(0, x - r), min(w, x + r + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        blocked[y0:y1, x0:x1] |= (yy - y) ** 2 + (xx - x) ** 2 <= rad * rad
    for y, x in marked:                         # a marked town serves its own catchment
        block(y, x, SPACING * min(radius[y, x], max_radius_km / cell_km))
    towns = []
    order = np.argsort(-score[ok]); cy, cx = np.nonzero(ok)
    for k in order:
        y, x = int(cy[k]), int(cx[k])
        if blocked[y, x]:
            continue
        towns.append((y, x))
        block(y, x, SPACING * min(radius[y, x], max_radius_km / cell_km))
    return towns, coast_km, d


def minor_roads(graph, shape, road, towns, marked, limit_days=4.0):
    """Tracks between neighbouring places: a relative neighbourhood graph on
    travel days (Toussaint 1980), the sparse mesh that real minor road networks
    resemble. Two places within limit_days are joined unless a third place is
    nearer to both; a place joins the marked roads directly only when no
    neighbour lies between. Each link follows its cheapest walking route.
    Returns the track mask and the routes (cell lists)."""
    places = [(int(y), int(x)) for y, x in towns] + [(int(y), int(x)) for y, x in marked]
    n_towns = len(towns); ROAD = len(places)
    node_of = {y * shape[1] + x: i for i, (y, x) in enumerate(places)}
    road_nodes = np.flatnonzero(road.ravel())
    dist = {}                                     # i -> {j: days}
    for i, (y, x) in enumerate(places):
        d = dijkstra(graph, directed=True, indices=y * shape[1] + x, limit=limit_days)
        near = {}
        for node, j in node_of.items():
            if j != i and np.isfinite(d[node]):
                near[j] = float(d[node])
        rd = d[road_nodes]
        if i < n_towns and np.isfinite(rd).any():
            near[ROAD] = float(rd.min())
        dist[i] = near
    def days(i, j):
        a = dist.get(i, {}).get(j, np.inf); b = dist.get(j, {}).get(i, np.inf)
        return min(a, b)
    edges = set()
    for i in range(n_towns):                      # links from each suggested town
        for j, dij in dist[i].items():
            if j == ROAD:
                blocked = any(max(dist[i].get(k, np.inf), dist[k].get(ROAD, np.inf) if k < n_towns else 0.0) < dij
                              for k in dist[i] if k != ROAD)
            else:
                if j >= n_towns and j < ROAD and False:
                    pass
                blocked = any(max(days(i, k), days(k, j)) < dij for k in dist[i] if k not in (j, ROAD))
            if not blocked:
                edges.add((min(i, j), max(i, j)) if j != ROAD else (i, ROAD))
    tracks = np.zeros(shape, bool); routes = []
    by_start = {}
    for a, b in edges:
        by_start.setdefault(a, []).append(b)
    for a, targets in by_start.items():
        y, x = places[a]
        _, pred = dijkstra(graph, directed=True, indices=y * shape[1] + x, limit=limit_days, return_predecessors=True)
        for b in targets:
            if b == ROAD:
                d = dijkstra(graph, directed=True, indices=y * shape[1] + x, limit=limit_days)
                end = int(road_nodes[np.argmin(d[road_nodes])])
            else:
                end = places[b][0] * shape[1] + places[b][1]
            path = []; node = end
            while node >= 0:
                path.append(divmod(int(node), shape[1]))
                if node == y * shape[1] + x:
                    break
                node = pred[node]
            if node < 0:
                continue
            for q, c in path:
                tracks[q, c] = True
            routes.append(path[::-1])
    return tracks, routes, edges
