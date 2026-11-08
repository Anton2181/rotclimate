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


def surface(tier_tops, terrain_file=""):
    """The routing surface at source resolution, the land mask and the drawn rivers."""
    from .geography import elevation_fullres, source_layers
    L = source_layers(); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    z = elevation_fullres(tuple(tier_tops), terrain_file or "")
    if not terrain_file:
        z = np.where(rivers, z - BURN_M, z)
    return z, land, rivers


def discharge(runoff_px_mm, tier_tops, terrain_file, map_width_mi):
    """Discharge (m3/s) at source resolution from annual runoff (mm/yr) given per source pixel."""
    z, land, rivers = surface(tier_tops, terrain_file)
    H, W = land.shape
    px_m = map_width_mi * 1609.344 / W
    src = np.where(land, np.maximum(runoff_px_mm, 0.0), 0.0) / 1000.0 * px_m * px_m / (365.0 * 86400.0)
    recv, order = _flood(np.where(land, z, -1e9), land, NB)
    q = _accumulate(order, recv, src.ravel()).reshape(H, W)
    return q, recv, land, rivers


def fine_discharge(result):
    """Discharge (m3/s) and receivers at source resolution from the model's annual runoff."""
    from .geography import source_layers
    from .hydrology import annual_runoff
    g, p = result.grid, result.params
    H, W = source_layers()["land"].shape
    ro = annual_runoff(result)                                         # mm/yr on the model grid (0 over water)
    gl = g.land & g.inmap                                              # carry the nearest land value over water
    _, (iy, ix) = ndi.distance_transform_edt(~gl, return_indices=True)
    ro_l = ro[iy, ix]
    f = W / (g.nx - 2 * g.pad)                                         # source pixels per model cell
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    ro_px = ndi.map_coordinates(ro_l, [(yy + 0.5) / f - 0.5 + g.pad, (xx + 0.5) / f - 0.5 + g.pad], order=1, mode="nearest")
    return discharge(ro_px, p.tier_tops, getattr(p, "terrain_file", ""), p.map_width_mi)


def segments(q, recv, land, q_min=15.0):
    """[x1, y1, x2, y2, q] in map pixels, pixel centre to downstream pixel centre, for land pixels with q > q_min;
    straight runs of one direction and flow class are merged into one segment."""
    H, W = land.shape
    cls = np.digitize(q, [50.0, 200.0, 800.0]).ravel()
    sel = np.flatnonzero((q.ravel() > q_min) & land.ravel() & (recv >= 0))
    keep = np.zeros(H * W, bool); keep[sel] = True
    dirn = np.where(recv >= 0, recv - np.arange(H * W), 0)
    src_idx = np.flatnonzero(keep); r = recv[src_idx]
    same = (r >= 0) & keep[np.maximum(r, 0)] & (dirn[np.maximum(r, 0)] == dirn[src_idx]) & (cls[np.maximum(r, 0)] == cls[src_idx])
    continued = np.zeros(H * W, bool); continued[r[same]] = True          # fed by its own straight run
    out = []
    for c in sel[~continued[sel]]:
        b = recv[c]
        while b >= 0 and keep[b] and continued[b] and dirn[b] == dirn[c] and cls[b] == cls[c] and recv[b] >= 0:
            b = recv[b]
        y1, x1 = divmod(int(c), W); y2, x2 = divmod(int(b), W)
        out.append([x1 + 0.5, y1 + 0.5, x2 + 0.5, y2 + 0.5, round(float(q.ravel()[c]), 1)])
    return out


def river_segments_fine(result, q_min=15.0):
    q, recv, land, _ = fine_discharge(result)
    return segments(q, recv, land, q_min)


def runoff_from_months(t, p, days_per_bin):
    """Annual runoff (mm/yr) from 12 monthly surface temperatures (C) and precipitation totals (mm per bin), with the
    climate model's rule (rotclimate.hydrology.annual_runoff: evaporation capped by rain and 0.75 x a Hargreaves-like
    potential)."""
    pet = np.clip(0.0023 * 17.8 * (t + 17.8) * 1.9, 0.1, None) * days_per_bin
    return np.maximum(p - np.minimum(p, 0.75 * pet), 0.0).sum(0)
