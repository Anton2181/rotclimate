"""Trade routes as lines for drawing: land and river routes from the routed
edge flows, sea lanes bundled.

Ships between two ports have many nearly equal paths across open water, so
the routed sea flows spread over parallel grid tracks. Sea traffic is
therefore summed per cell, blurred (SEA_BLUR cells) and thinned to its
centre lines (Zhang-Suen), one lane per bundle. Classes are shares of the
busiest segment's traffic, separately for land and sea.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import vectors as V

CLASSES = (("local", 0.05), ("regional", 0.12), ("main", 0.30))
SEA_BLUR = 2.0
MIN_CHAIN = 5
EDGE_CELLS = 4            # sea lanes hugging the grid's own edge are artefacts of the boundary


def thin(mask):
    """Zhang-Suen thinning of a boolean image."""
    img = np.pad(mask.astype(np.uint8), 1)
    while True:
        changed = False
        for step in (0, 1):
            p2, p3, p4 = img[:-2, 1:-1], img[:-2, 2:], img[1:-1, 2:]
            p5, p6, p7 = img[2:, 2:], img[2:, 1:-1], img[2:, :-2]
            p8, p9 = img[1:-1, :-2], img[:-2, :-2]
            ring = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            b = sum(ring[:-1])
            a = sum(((ring[i] == 0) & (ring[i + 1] == 1)).astype(np.uint8) for i in range(8))
            if step == 0:
                c1, c2 = p2 * p4 * p6, p4 * p6 * p8
            else:
                c1, c2 = p2 * p4 * p8, p2 * p6 * p8
            core = img[1:-1, 1:-1]
            kill = (core == 1) & (b >= 2) & (b <= 6) & (a == 1) & (c1 == 0) & (c2 == 0)
            if kill.any():
                core[kill] = 0; changed = True
        if not changed:
            return img[1:-1, 1:-1].astype(bool)


def skeleton_chains(skel, weight):
    """Polylines (lists of flat indices) through an 8-connected skeleton."""
    h, w = skel.shape
    ys, xs = np.nonzero(skel)
    flat = ys * w + xs
    a, b, f = [], [], []
    for dy, dx in ((0, 1), (1, -1), (1, 0), (1, 1)):
        q, c = ys + dy, xs + dx
        ok = (q >= 0) & (q < h) & (c >= 0) & (c < w)
        ok[ok] = skel[q[ok], c[ok]]
        a.append(flat[ok]); b.append(q[ok] * w + c[ok])
        f.append(0.5 * (weight.ravel()[flat[ok]] + weight.ravel()[q[ok] * w + c[ok]]))
    if not a:
        return []
    return V.chains(np.concatenate(a), np.concatenate(b), np.concatenate(f), -np.inf)


def lines(tr, water, shape):
    """[(kind, class, [(row, col), ...], relative traffic)] from map trade fields."""
    h, w = shape
    cc, pc, fl = tr["edges"]
    wat = np.asarray(water, bool).ravel()
    sea = wat[cc] & wat[pc]
    out = []
    # land and river routes: the routed edges themselves
    f_land = fl[~sea]
    if len(f_land):
        mx = f_land.max()
        for label, share in CLASSES:
            for nodes, flows in V.chains(cc[~sea], pc[~sea], fl[~sea], share * mx):
                if len(nodes) >= (2 if label != "local" else MIN_CHAIN):
                    out.append(("land", label, [divmod(int(n), w) for n in nodes], float(np.mean(flows) / mx)))
    # sea lanes: bundled
    t = np.zeros(h * w)
    np.maximum.at(t, cc[sea], fl[sea])
    dens = ndi.gaussian_filter(t.reshape(h, w), SEA_BLUR)
    inner = np.zeros((h, w), bool); inner[EDGE_CELLS:-EDGE_CELLS, EDGE_CELLS:-EDGE_CELLS] = True
    dens = np.where(np.asarray(water, bool) & inner, dens, 0.0)
    if dens.max() > 0:
        rel = dens / dens.max()
        for label, share in CLASSES:
            skel = thin(rel >= share)
            for nodes, flows in skeleton_chains(skel, rel):
                if len(nodes) >= MIN_CHAIN:
                    out.append(("sea", label, [divmod(int(n), w) for n in nodes], float(np.mean(flows))))
    return out
