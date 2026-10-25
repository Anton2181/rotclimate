"""Trade: what it costs to move goods, market access and the main routes.

Costs are those of bulk goods, not of travellers: Diocletian's Price Edict
(AD 301) puts the cost of carrying a load by sea, river and road at about
1 : 5 : 28 per km (wagon on a road; the Edict charged twice as much upriver
as down). Each month's network (polity/network.py) is rebuilt with every
edge priced in road-km equivalents (the cost of carrying the load one km by
wagon): walking and riding edges by the days they take (a wagon covers 30
km of road a day, and a pack train costs about as much per km), ships by the
days at sea (a ship's hire runs by the day: Scheidel 2013 found the Edict's
sea freight rates follow sailing time), river boats by the km.

Market access (MA) of a place: the people of the whole map, each discounted
by exp(-cost / COST_SCALE). Trade flows: a gravity model between places,
T_ij ~ P_i P_j exp(-c_ij / COST_SCALE), routed along the cheapest paths.
Fitted and tested on Roman town sizes (scripts/polity_trade_check.py).
"""
from __future__ import annotations

import numpy as np
from scipy.sparse.csgraph import dijkstra

from . import control as C
from . import seasons as S
from . import transport as X

SEA_PER_KM = 1.0
RIVER_DOWN_PER_KM = 5.0
RIVER_UP_PER_KM = 10.0
ROAD_PER_KM = 28.0
SEA_KM_DAY = X.SAIL_FAIR_KNOTS * 24 * 1.852          # a fair-wind day at sea
COST_SCALE = 300.0       # road-km equivalents; set by the Earth fit
TRADE_MONTHS = (0, 3, 6, 9)  # one month a season (months from the winter solstice)


def cost_network(world, st, cl, m, ports=(), river_places=()):
    """Month m's network with edge weights in road-km equivalents."""
    eta = S.month_terrain(st["eta"], cl, m)
    mud = cl["mud"][m]
    flood = S.flood_index(cl["flow"][m][st["basin"]])
    cross = np.where(st["basin"] > 0, S.CROSS_DAYS * (1.0 + S.FLOOD_GAIN * flood), 0.0)
    land, cell_km = st["land"], world["cell_km"]
    a, b, d = C.foot_edges(world["elev"], land, world["road"], eta, cell_km, st["paths"], world.get("ferry"),
                           world.get("tracks"), road_factor=1.0 + (S.MUD_ROAD - 1.0) * mud,
                           track_factor=1.0 + (S.MUD_COEFFICIENT - 1.0) * mud, cross=cross)
    edges = [(a, b, d * C.ROAD_KM_DAY)]
    sea_day = SEA_KM_DAY * SEA_PER_KM / ROAD_PER_KM
    a, b, d = X.sea_edges(st["water"], world["u"][m], world["v"][m], world["wind"][m], cl["steadiness"][m],
                          cl["sea"][m], cell_km, st["coast_km"])
    edges.append((a, b, d * sea_day))
    if len(ports):
        a, b, d = X.harbour_edges(land, st["water"], list(ports), cell_km)
        edges.append((a, b, d * sea_day))
    extra = 0
    if len(st["river_cells"]):
        rr, rc, rd, cells = X.river_edges(st["basin"], st["steps"], cl["flow"][m], cell_km, land.size,
                                          down_km_day=ROAD_PER_KM / RIVER_DOWN_PER_KM,
                                          up_km_day=ROAD_PER_KM / RIVER_UP_PER_KM)
        edges.append((rr, rc, rd))
        a, b, d = X.river_harbour_edges(cells, land.size, list(river_places), land.shape)
        edges.append((a, b, d * X.RIVER_DOWN_KM_DAY * RIVER_DOWN_PER_KM / ROAD_PER_KM))
        extra = len(cells)
    net = C.Network(land.size, edges, extra)
    net.river_cells = cells if extra else np.zeros(0, np.int64)
    return net


def costs_from(net, sources, limit=np.inf, batch=24, predecessors=False):
    """Cost from each source (flat cell index) to every node, in batches;
    yields (sources, costs[, predecessors])."""
    sources = np.asarray(sources, np.int64)
    for i in range(0, len(sources), batch):
        s = sources[i:i + batch]
        out = dijkstra(net.base, directed=True, indices=s, limit=limit, return_predecessors=predecessors)
        yield (s,) + (out if predecessors else (out,))


def market_access(nets, sources, people, scales, limit_scale=6.0):
    """MA[k, i] = mean over the networks of sum_cells people * exp(-cost / scales[k])."""
    people = np.asarray(people, float).ravel()
    n = nets[0].n_cells
    ma = np.zeros((len(scales), len(sources)))
    limit = max(scales) * limit_scale
    for net in nets:
        j = 0
        for s, c in costs_from(net, sources, limit):
            c = c[:, :n]
            for k, sc in enumerate(scales):
                ma[k, j:j + len(s)] += (np.exp(-c / sc) * people).sum(1)
            j += len(s)
    return ma / len(nets)
