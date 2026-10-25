"""Experimental directed trade contracts; not used by the published atlases.

The existing travel graph has asymmetric river, slope and wind costs. A
hinterland bringing goods to town uses cell -> town costs. Gravity shipments
are ordered pairs, with independent costs and routes in each direction.
The cost scale and population weights remain declared scenarios, not an
identified model of ancient town sizes.
"""
from __future__ import annotations

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra

from .trade import COST_SCALE, _depth


def _towns(net, towns):
    towns = np.asarray(towns, dtype=np.int64)
    if (towns.ndim != 1 or len(np.unique(towns)) != len(towns) or
            (towns < 0).any() or (towns >= net.n_cells).any()):
        raise ValueError('Need unique towns on physical cells')
    return towns


def inbound_catchments(net, towns, people):
    """Assign each cell to the town it can reach most cheaply.

    Returns people per town and town-array owner indices (-1 unreachable).
    Auxiliary river nodes route goods but do not hold a separate population.
    """
    towns = _towns(net, towns)
    people = np.asarray(people, dtype=float).ravel()
    if len(people) != net.n_cells or not np.isfinite(people).all() or (people < 0).any():
        raise ValueError('Need finite nonnegative population per physical cell')
    if not len(towns):
        return np.zeros(0), np.full(net.n_cells, -1, dtype=np.int64)
    # Deterministic tie-breaking uses physical node IDs, independent of the
    # order in which town records happen to be listed.
    _, _, roots = dijkstra(net.base.T.tocsr(), directed=True, indices=np.sort(towns),
                           min_only=True, return_predecessors=True)
    lookup = {int(t): i for i, t in enumerate(towns)}
    owner = np.array([lookup.get(int(t), -1) for t in roots[:net.n_cells]])
    reached = owner >= 0
    mass = np.bincount(owner[reached], weights=people[reached], minlength=len(towns))
    return mass, owner


def gravity_routes(nets, towns, mass, scale=COST_SCALE, sources=300, limit_scale=6.):
    """Mean ordered gravity shipments per directed edge (from, to, volume).

    A pair is retained if at least one endpoint is among the largest `sources`
    towns. Both directions of that pair are evaluated once. Smaller-to-smaller
    trade is omitted explicitly. Volumes P_i P_j exp(-c_ij/scale) are relative
    gravity weights, not tonnes, market equilibrium or conserved grain stocks.
    Paths beyond limit_scale * scale are excluded, as in the legacy model.
    """
    if not len(nets):
        raise ValueError('Need at least one seasonal network')
    towns = _towns(nets[0], towns)
    mass = np.asarray(mass, dtype=float)
    if (mass.shape != towns.shape or not np.isfinite(mass).all() or (mass < 0).any() or
            not np.isfinite(scale) or scale <= 0 or not np.isfinite(limit_scale) or limit_scale <= 0 or
            not isinstance(sources, int) or isinstance(sources, bool) or sources < 1):
        raise ValueError('Invalid directed gravity inputs')
    shape = nets[0].base.shape
    # Seasonal networks may have different auxiliary river nodes. Aggregate
    # directed physical edges only when node topology is actually the same.
    if any(net.base.shape != shape or net.n_cells != nets[0].n_cells for net in nets):
        raise ValueError('Directed route aggregation requires matching node topology')
    if shape[0]>nets[0].n_cells:
        mapping=getattr(nets[0],'river_cells',None)
        if mapping is None or any(not np.array_equal(getattr(net,'river_cells',None),mapping) for net in nets):
            raise ValueError('Auxiliary river-node identities differ between seasons')
    top = np.lexsort((towns, -mass))[:sources]
    selected = np.zeros(len(towns), dtype=bool)
    selected[top] = True
    accumulated = csr_matrix(shape, dtype=float)
    for net in nets:
        for i in top:
            for reverse in (False, True):
                keep = (~selected if reverse else np.ones(len(towns), dtype=bool)).copy()
                keep[i] = False
                if not keep.any() or mass[i]==0:
                    continue
                graph = net.base.T.tocsr() if reverse else net.base
                costs, parent = dijkstra(graph, directed=True, indices=int(towns[i]),
                                          limit=scale*limit_scale, return_predecessors=True)
                values = mass[i]*mass*np.exp(-costs[towns]/scale)
                values[~keep] = 0.
                traffic = np.zeros(shape[0])
                np.add.at(traffic, towns, values)
                live = np.flatnonzero((parent >= 0) & np.isfinite(costs))
                if not len(live) or not values.any():
                    continue
                depth = _depth(parent)
                order = live[np.argsort(-depth[live], kind='stable')]
                cuts = np.flatnonzero(np.diff(depth[order])) + 1
                for group in np.split(order, cuts):
                    np.add.at(traffic, parent[group], traffic[group])
                nodes = live[traffic[live] > 0]
                origin, destination = (nodes, parent[nodes]) if reverse else (parent[nodes], nodes)
                accumulated += csr_matrix((traffic[nodes], (origin, destination)), shape=shape)
    out = (accumulated/len(nets)).tocoo()
    return out.row, out.col, out.data
