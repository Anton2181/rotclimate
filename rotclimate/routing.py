"""Simulated rivers at the drawing's own resolution (one source pixel, ~1.84 km).

The climate grid (~15 km) routes its runoff over cell-mean heights (rotclimate.hydrology); drawn as segments between cell
centres, that network zig-zags and leaves the drawn valleys. For the atlas the model's annual runoff is routed instead over
the full-resolution surface:

  * the eroded height map when the world has one (Params.terrain_file): every drawn river is already a flow path of it
    (scripts/terrain_rivers.py, plan_R1);
  * otherwise the tier ramps with the drawn rivers burned in (stream burning, Hellweger 1997), so the drawn rivers carry
    the water they collect.

Drainage is Priority-Flood (Barnes, Lehman & Mulla 2014) from the sea, lakes and the map edge: every land cell drains,
depressions spill; discharge is the runoff accumulated down that tree. The climate model's own coarse hydrology and its
river check (score.river_network_check) are unchanged and stay an independent test.
"""
from __future__ import annotations

import numba
import numpy as np
from scipy import ndimage as ndi

BURN_M = 1.0e4          # drawn-river cells of a surface without terrain file are burned this deep (routing only)
NB = np.array([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)], np.int64)


@numba.njit(cache=True)
def _flood(key, land, NB):
    """Priority-Flood receivers (-1 = outlet) and the visiting order; seeds are land cells next to water or the edge."""
    ny, nx = key.shape; N = ny * nx
    recv = np.full(N, -1, np.int64); seen = ~land.copy(); order = np.empty(N, np.int64); no = 0
    hk = np.empty(N + 8); hc = np.empty(N + 8, np.int64); n = 0
    for y in range(ny):
        for x in range(nx):
            if not land[y, x]:
                continue
            edge = y == 0 or y == ny - 1 or x == 0 or x == nx - 1
            if not edge:
                for k in range(8):
                    if not land[y + NB[k, 0], x + NB[k, 1]]:
                        edge = True
                        break
            if edge:
                seen[y, x] = True; hk[n] = key[y, x]; hc[n] = y * nx + x; i = n; n += 1
                while i > 0:
                    pa = (i - 1) // 2
                    if hk[pa] <= hk[i]:
                        break
                    hk[i], hk[pa] = hk[pa], hk[i]; hc[i], hc[pa] = hc[pa], hc[i]; i = pa
    while n > 0:
        h = hk[0]; c = hc[0]; n -= 1; hk[0] = hk[n]; hc[0] = hc[n]; i = 0
        while True:
            l = 2 * i + 1; r = l + 1; s = i
            if l < n and hk[l] < hk[s]:
                s = l
            if r < n and hk[r] < hk[s]:
                s = r
            if s == i:
                break
            hk[i], hk[s] = hk[s], hk[i]; hc[i], hc[s] = hc[s], hc[i]; i = s
        order[no] = c; no += 1
        y = c // nx; x = c % nx
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if yy < 0 or yy >= ny or xx < 0 or xx >= nx or seen[yy, xx]:
                continue
            seen[yy, xx] = True; cc = yy * nx + xx; recv[cc] = c
            hk[n] = max(key[yy, xx], h); hc[n] = cc; i = n; n += 1
            while i > 0:
                pa = (i - 1) // 2
                if hk[pa] <= hk[i]:
                    break
                hk[i], hk[pa] = hk[pa], hk[i]; hc[i], hc[pa] = hc[pa], hc[i]; i = pa
    return recv, order[:no]


@numba.njit(cache=True)
def _accumulate(order, recv, src):
    acc = src.copy()
    for k in range(order.size - 1, -1, -1):
        c = order[k]; r = recv[c]
        if r >= 0:
            acc[r] += acc[c]
    return acc


def surface(params):
    """The routing surface at source resolution, the land mask and the drawn rivers."""
    from .geography import elevation_fullres, source_layers
    L = source_layers(); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    terrain = getattr(params, "terrain_file", "")
    z = elevation_fullres(tuple(params.tier_tops), terrain)
    if not terrain:
        z = np.where(rivers, z - BURN_M, z)
    return z, land, rivers


def fine_discharge(result):
    """Discharge (m3/s) and receivers at source resolution from the model's annual runoff."""
    from .hydrology import annual_runoff
    g, p = result.grid, result.params
    z, land, rivers = surface(p)
    H, W = land.shape
    ro = annual_runoff(result)                                         # mm/yr on the model grid (0 over water)
    # land-only runoff, nearest land value carried over water so coastal pixels are not diluted by the sea
    gl = g.land & g.inmap
    _, (iy, ix) = ndi.distance_transform_edt(~gl, return_indices=True)
    ro_l = ro[iy, ix]
    f = W / (g.nx - 2 * g.pad)                                         # source pixels per model cell
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    ro_px = ndi.map_coordinates(ro_l, [(yy + 0.5) / f - 0.5 + g.pad, (xx + 0.5) / f - 0.5 + g.pad], order=1, mode="nearest")
    px_m = p.map_width_mi * 1609.344 / W
    src = np.where(land, np.maximum(ro_px, 0.0), 0.0) / 1000.0 * px_m * px_m / (365.0 * 86400.0)
    recv, order = _flood(np.where(land, z, -1e9), land, NB)
    q = _accumulate(order, recv, src.ravel()).reshape(H, W)
    return q, recv, land, rivers


def river_segments_fine(result, q_min=15.0):
    """[x1, y1, x2, y2, q] in map pixels, pixel centre to downstream pixel centre, for land pixels with q > q_min;
    straight runs of the same flow class are merged into one segment."""
    q, recv, land, rivers = fine_discharge(result)
    H, W = land.shape
    classes = np.digitize(q, [50.0, 200.0, 800.0])
    sel = np.flatnonzero((q.ravel() > q_min) & land.ravel() & (recv >= 0))
    keep = np.zeros(H * W, bool); keep[sel] = True
    # merge collinear runs: a segment whose upstream partner continues in the same direction and class is absorbed
    nxt = recv
    dirn = np.where(recv >= 0, recv - np.arange(H * W), 0)
    has_up_same = np.zeros(H * W, bool)
    up_ok = keep & (recv >= 0)
    r = recv[up_ok]; src_idx = np.flatnonzero(up_ok)
    same = keep[r] & (dirn[r] == dirn[src_idx]) & (classes.ravel()[r] == classes.ravel()[src_idx])
    # a cell r is "continued" from upstream when exactly one upstream kept cell feeds it in the same direction
    cnt = np.bincount(r[same], minlength=H * W); has_up_same[cnt == 1] = True
    segs = []
    starts = sel[~has_up_same[sel]]
    for c in starts:
        a = c; b = nxt[c]
        while b >= 0 and keep[b] and has_up_same[b] and dirn[b] == dirn[a] and classes.ravel()[b] == classes.ravel()[a] and nxt[b] >= 0:
            b = nxt[b]
        y1, x1 = divmod(int(c), W); y2, x2 = divmod(int(b), W)
        segs.append([x1 + 0.5, y1 + 0.5, x2 + 0.5, y2 + 0.5, round(float(q.ravel()[c]), 1)])
    return segs
