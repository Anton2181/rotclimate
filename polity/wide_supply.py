"""Wider grain supply for towns: hinterland delivery and cheapest-first shipments.

Transport is paid in grain: a path costing c road-km equivalents delivers
max(0, 1 - c / limit). A declared scenario built on the atlas's existing
freight coefficients; nothing here is fitted.
"""
from __future__ import annotations

import numpy as np

VALUE_LIMIT_ROAD_KM = 270.0      # polity.trade.COST_SCALE: road haulage eats a staple's value (Duncan-Jones 1982)


def delivered_share(cost, limit=VALUE_LIMIT_ROAD_KM):
    c = np.asarray(cost, float)
    return np.where(np.isfinite(c), np.clip(1.0 - c / limit, 0.0, 1.0), 0.0)


def hinterland_delivery(owner, share, grain, towns):
    """Sum grain x share by owning town. owner/share: (seasons, cells); owner -1 = none."""
    owner = np.asarray(owner); share = np.asarray(share, float); grain = np.asarray(grain, float)
    if owner.shape != share.shape or owner.shape[1:] != grain.shape or np.any(grain < 0):
        raise ValueError('Seasonal owners/shares and nonnegative cell grain must align')
    seasons = owner.shape[0]; delivered = np.zeros(towns); sent = np.zeros(towns)
    for s in range(seasons):
        ok = (owner[s] >= 0) & (share[s] > 0)
        delivered += np.bincount(owner[s][ok], weights=grain[ok] / seasons * share[s][ok], minlength=towns)
        sent += np.bincount(owner[s][ok], weights=grain[ok] / seasons, minlength=towns)
    return delivered, sent


def ship(excess, deficit, share):
    """Cheapest-first shipments. share[a, b]: delivered share from a to b.

    Returns (sent[a, b] leaving a, received[b]). Exporters never import.
    """
    excess = np.asarray(excess, float).copy(); deficit = np.asarray(deficit, float).copy(); share = np.asarray(share, float)
    n = len(excess)
    if share.shape != (n, n) or np.any(excess < 0) or np.any(deficit < 0) or np.any((excess > 0) & (deficit > 0)):
        raise ValueError('Square share matrix and disjoint nonnegative excess/deficit required')
    a, b = np.nonzero((share > 0) & (excess[:, None] > 0) & (deficit[None, :] > 0))
    order = np.lexsort((b, a, -share[a, b]))          # highest share first; ties by exporter, then importer
    sent = {}
    for k in order:
        i, j = int(a[k]), int(b[k])
        if excess[i] <= 0 or deficit[j] <= 0:
            continue
        move = min(excess[i], deficit[j] / share[i, j])
        sent[i, j] = move; excess[i] -= move; deficit[j] -= move * share[i, j]
        if deficit[j] < 1e-9 * max(1.0, move):
            deficit[j] = 0.0
    received = np.zeros(n)
    for (i, j), move in sent.items():
        received[j] += move * share[i, j]
    return sent, received
