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
Tested on Roman town sizes (scripts/polity_trade_check.py): market access did not explain them, so
the map does not size towns by it.
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
# trade falls by e per COST_SCALE road-km: hauling wheat 148 km by land cost 55 % of its value (Duncan-Jones
# 1982, p. 368), so road haulage eats a staple's whole value at ~270 km. Roman town sizes did not identify
# the scale (calibration/polity_20261025/trade.json: no scale explained them)
COST_SCALE = 270.0
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


def catchments(net, towns, people):
    """People served by each town: every cell goes to its cheapest town."""
    from scipy.sparse.csgraph import dijkstra as dj
    n = net.n_cells
    d, _, src = dj(net.base, directed=True, indices=np.asarray(towns, np.int64), min_only=True,
                   return_predecessors=True)
    src = src[:n]
    lookup = {int(t): k for k, t in enumerate(towns)}
    owner = np.array([lookup.get(int(s), -1) for s in src])
    mass = np.bincount(owner[owner >= 0], weights=np.asarray(people, float).ravel()[owner >= 0], minlength=len(towns))
    return mass, owner


def _depth(pred):
    """Hops from the root of a shortest-path tree (pred < 0 at the root and unreached)."""
    n = len(pred)
    up = np.where(pred >= 0, pred, np.arange(n))
    depth = (pred >= 0).astype(np.int64)
    for _ in range(int(np.ceil(np.log2(max(n, 2)))) + 1):
        depth = depth + np.where(up != np.arange(n), depth[up], 0)
        nxt = up[up]
        if np.array_equal(nxt, up):
            break
        up = nxt
    return depth


def flows(nets, towns, mass, scale=None, sources=300, limit_scale=6.0):
    """Gravity flows P_i P_j exp(-c_ij / scale) between the `sources` largest
    towns and every town, routed along each month's cheapest paths and
    averaged over the networks. Returns {(node, parent_node): flow} as
    arrays (child, parent, flow) and each town's through-traffic."""
    from scipy.sparse import coo_matrix
    scale = scale or COST_SCALE
    towns = np.asarray(towns, np.int64); mass = np.asarray(mass, float)
    top = np.argsort(-mass)[:sources]
    in_top = np.zeros(len(towns), bool); in_top[top] = True
    acc = None
    for net in nets:
        n = net.n
        for s_idx, cost, pred in costs_from(net, towns[top], scale * limit_scale, predecessors=True):
            for row, src in enumerate(s_idx):
                i = int(np.flatnonzero(towns == src)[0])
                c = cost[row][towns]
                f = mass[i] * mass * np.exp(-c / scale)
                f[~np.isfinite(c)] = 0.0
                f[i] = 0.0
                f[in_top & (np.arange(len(towns)) < i)] = 0.0    # each top pair once
                x = np.zeros(n)
                np.add.at(x, towns, f)
                p = pred[row]
                reach = np.flatnonzero(x > 0)
                if not len(reach):
                    continue
                depth = _depth(p)
                live = np.flatnonzero((p >= 0) & np.isfinite(cost[row]))
                order = live[np.argsort(-depth[live], kind="stable")]
                d_sorted = depth[order]
                cuts = np.flatnonzero(np.diff(d_sorted)) + 1
                for grp in np.split(order, cuts):
                    np.add.at(x, p[grp], x[grp])
                m = live[x[live] > 0]
                e = coo_matrix((x[m], (m, p[m])), shape=(n, n))
                acc = e if acc is None else acc + e
    acc = (acc / len(nets)).tocoo()
    return acc.row, acc.col, acc.data


# the Roman fit (scripts/polity_trade_check.py): log10 town area (ha) = a + b LOCAL + c MA, LOCAL and MA in
# log10 people; None until the test passes
SIZE_COEF = None
LOCAL_SCALE = 30.0


def map_fields(r, scale=None, sources=300):
    """Trade on the map from polity.fields.compute's result: each town's
    catchment people, local and wide market access, the gravity flows between
    towns routed over the four seasons' cheapest paths, and each cell's
    through-traffic."""
    scale = scale or COST_SCALE
    W = r["land"].shape[1]
    towns = np.array([t["row"] * W + t["col"] for t in r["towns"]])
    # the people a town serves and trades for: those of the claimed land (the unclaimed north is herders' country,
    # where the farming density does not apply)
    people = np.where(r["land"] & (r["claim"] >= 0), r["density"], 0.0) * r["cell_km"] ** 2
    nets = [cost_network(r["world"], r["statics"], r["climate"], m, r["ports"], r["river_places"])
            for m in TRADE_MONTHS]
    mass, owner = catchments(nets[len(nets) // 2], towns, people)
    ma = market_access(nets, towns, people, [LOCAL_SCALE, scale])
    child, parent, flow = flows(nets, towns, mass, scale, sources)
    n = nets[0].n_cells
    node_cell = np.arange(nets[0].n)
    for net in nets:                                  # river-boat nodes sit on their river cells
        rc = getattr(net, "river_cells", np.zeros(0, np.int64))
        node_cell[n:n + len(rc)] = rc
    node_cell[node_cell >= n] = -1
    cc, pc = node_cell[child], node_cell[parent]
    ok = (cc >= 0) & (pc >= 0) & (cc != pc)
    through = np.zeros(n)
    np.maximum.at(through, cc[ok], flow[ok])
    size = None
    if SIZE_COEF is not None:
        a, b, c = SIZE_COEF
        size = 10 ** (a + b * np.log10(np.maximum(ma[0], 1)) + c * np.log10(np.maximum(ma[1], 1)))
    return dict(towns=towns, mass=mass, catchment=owner.reshape(r["land"].shape), ma_local=ma[0], ma=ma[1],
                edges=(cc[ok], pc[ok], flow[ok]), through=through.reshape(r["land"].shape), area_ha=size,
                scale=scale)
