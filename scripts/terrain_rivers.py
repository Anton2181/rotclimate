"""Plan R1 (calibration/geography_control_20261107/plan_R1.json): every drawn river is a flow path of the eroded height
map, from its source to the sea, a lake or the map edge, in a valley whose form is fitted on Earth.

Owner, 7 Nov 2026: "Remember that all of our drawn rivers also have to be there in the eroded map".

Method (references in the plan):
  1. order the drawn-river cells by geodesic distance g along the drawing to an outlet (sea, lake, map edge);
  2. breach a bed that never climbs: upstream to downstream r = min(z - b0, r_upstream - dec), floored at
     1 m + 2e-4 m per pixel of g (so the bed stays above sea level and still falls towards the mouth);
  3. a valley: land within W pixels of a river is lowered toward the nearest bed, z' = R + (z - R) (d / W)^p;
  4. the bed again, now also b0 below every adjacent non-river cell; banks are raised only where the floor binds;
  5. Priority-Flood + epsilon (Barnes et al. 2014) over all land, so flats and pits drain; river cells unchanged.

    .venv/bin/python -I scripts/terrain_rivers.py check <npz>      # strict owner check of any height map file
    .venv/bin/python -I scripts/terrain_rivers.py dev               # Earth fit of (W, p, b0) on D1-D4, check on B1-B4
    .venv/bin/python -I scripts/terrain_rivers.py build             # height map v2.1 = v2 composition + conditioning
"""
from __future__ import annotations

import itertools
import json
import math
import sys
import time
from pathlib import Path

import numba
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_R1.json"
OUT = ROOT / "output/terrain_rivers_20261107"
ERO = ROOT / "output/terrain_erosion_20261107"
FLOOR0, FSTEP, DECMIN, EPS = 1.0, 2e-4, 2e-4, 1e-4
FLAT_EPS = 2e-4                                                     # m per flat increment (amendment 4)
GRID = dict(ref=(("ramp", 0.3), ("ramp", 0.4), ("ramp", 0.5), ("ramp", 0.6), ("ramp", 0.7), ("ramp", 0.85), ("floor", 1.0)),
            W=(4, 7, 11, 16), p=(0.5, 1.0), b0=(1.0, 3.0, 10.0))           # plan_R1 amendment 1
RINGS = range(1, 9)
NB = np.array([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)], np.int64)
ND = np.array([math.sqrt(2), 1, math.sqrt(2), 1, 1, math.sqrt(2), 1, math.sqrt(2)])
log = lambda *a: print(*a, flush=True)  # noqa: E731


@numba.njit(cache=True)
def _ulp32(x):
    x = abs(x)
    if x < 1e-30:
        return 1e-45
    return 2.0 ** (math.floor(math.log2(x)) - 23)


@numba.njit(cache=True)
def _geodesic(riv, outlet, NB, ND):
    """Dijkstra along drawn-river cells (8-neighbour) from the outlet cells; inf where not connected."""
    ny, nx = riv.shape
    g = np.full(ny * nx, np.inf)
    size = int(riv.sum()) * 9 + 16
    hk = np.empty(size); hc = np.empty(size, np.int64); n = 0
    # binary heap on (hk, hc)
    for c in range(ny * nx):
        if outlet.ravel()[c]:
            g[c] = 0.0
            hk[n] = 0.0; hc[n] = c; n += 1
    # heapify by sifting (keys all 0 here: already a heap)
    while n > 0:
        d = hk[0]; c = hc[0]; n -= 1
        hk[0] = hk[n]; hc[0] = hc[n]
        i = 0
        while True:
            l = 2 * i + 1; r = l + 1; s = i
            if l < n and hk[l] < hk[s]:
                s = l
            if r < n and hk[r] < hk[s]:
                s = r
            if s == i:
                break
            hk[i], hk[s] = hk[s], hk[i]; hc[i], hc[s] = hc[s], hc[i]; i = s
        if d > g[c]:
            continue
        y = c // nx; x = c % nx
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if yy < 0 or yy >= ny or xx < 0 or xx >= nx or not riv[yy, xx]:
                continue
            nd = d + ND[k]; cc = yy * nx + xx
            if nd < g[cc]:
                g[cc] = nd
                hk[n] = nd; hc[n] = cc; i = n; n += 1
                while i > 0:
                    pa = (i - 1) // 2
                    if hk[pa] <= hk[i]:
                        break
                    hk[i], hk[pa] = hk[pa], hk[i]; hc[i], hc[pa] = hc[pa], hc[i]; i = pa
    return g.reshape(ny, nx)


@numba.njit(cache=True)
def _bed(z, riv, land, g, order, b0, use_bank, NB, ND, FLOOR0, FSTEP, DECMIN):
    """Upstream-to-downstream bed that never climbs (cells in order of decreasing g)."""
    ny, nx = z.shape
    R = np.full((ny, nx), np.inf)
    for c in order:
        y = c // nx; x = c % nx
        r = z[y, x] - b0
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                continue
            if riv[yy, xx]:
                if g[yy, xx] > g[y, x] and R[yy, xx] < np.inf:
                    dec = max(DECMIN * ND[k], 8.0 * _ulp32(R[yy, xx]))
                    r = min(r, R[yy, xx] - dec)
            elif use_bank and land[yy, xx]:
                r = min(r, z[yy, xx] - b0)
        R[y, x] = max(r, FLOOR0 + FSTEP * (g[y, x] + 1.0))
    return R


@numba.njit(cache=True)
def _envelopes(t, riv, g, order, NB, ND, FLOOR0, FSTEP, DECMIN):
    """Hybrid breach-fill bed (plan_R1 amendment 1): L breaches the reference t from the sources down, U fills it from
    the mouth up; both fall strictly downstream, so their mean does too."""
    ny, nx = t.shape
    Lo = np.full((ny, nx), np.inf); Up = np.full((ny, nx), -np.inf)
    for c in order:                                   # decreasing g: upstream first
        y = c // nx; x = c % nx; r = t[y, x]
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if 0 <= yy < ny and 0 <= xx < nx and riv[yy, xx] and g[yy, xx] > g[y, x] and Lo[yy, xx] < np.inf:
                r = min(r, Lo[yy, xx] - max(DECMIN * ND[k], 8.0 * _ulp32(Lo[yy, xx])))
        Lo[y, x] = max(r, FLOOR0 + FSTEP * (g[y, x] + 1.0))
    for i in range(order.size - 1, -1, -1):           # increasing g: mouth first
        c = order[i]; y = c // nx; x = c % nx; r = max(t[y, x], FLOOR0 + FSTEP * (g[y, x] + 1.0))
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if 0 <= yy < ny and 0 <= xx < nx and riv[yy, xx] and g[yy, xx] < g[y, x] and Up[yy, xx] > -np.inf:
                r = max(r, Up[yy, xx] + max(DECMIN * ND[k], 8.0 * _ulp32(Up[yy, xx])))
        Up[y, x] = r
    return Lo, Up


@numba.njit(cache=True)
def _priority_flood(z, land, NB, EPS):
    """Priority-Flood + epsilon (Barnes, Lehman & Mulla 2014): seeds are land cells touching water or the map edge."""
    ny, nx = z.shape
    out = z.copy(); seen = ~land.copy()
    hk = np.empty(ny * nx + 8); hc = np.empty(ny * nx + 8, np.int64); n = 0
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
                seen[y, x] = True
                hk[n] = out[y, x]; hc[n] = y * nx + x; i = n; n += 1
                while i > 0:
                    pa = (i - 1) // 2
                    if hk[pa] <= hk[i]:
                        break
                    hk[i], hk[pa] = hk[pa], hk[i]; hc[i], hc[pa] = hc[pa], hc[i]; i = pa
    raised = 0
    while n > 0:
        h = hk[0]; c = hc[0]; n -= 1
        hk[0] = hk[n]; hc[0] = hc[n]; i = 0
        while True:
            l = 2 * i + 1; r = l + 1; s = i
            if l < n and hk[l] < hk[s]:
                s = l
            if r < n and hk[r] < hk[s]:
                s = r
            if s == i:
                break
            hk[i], hk[s] = hk[s], hk[i]; hc[i], hc[s] = hc[s], hc[i]; i = s
        y = c // nx; x = c % nx
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if yy < 0 or yy >= ny or xx < 0 or xx >= nx or seen[yy, xx]:
                continue
            seen[yy, xx] = True
            e = max(EPS, 4.0 * _ulp32(h))
            if out[yy, xx] < h + e:
                out[yy, xx] = h + e; raised += 1
            hk[n] = out[yy, xx]; hc[n] = yy * nx + xx; i = n; n += 1
            while i > 0:
                pa = (i - 1) // 2
                if hk[pa] <= hk[i]:
                    break
                hk[i], hk[pa] = hk[pa], hk[i]; hc[i], hc[pa] = hc[pa], hc[i]; i = pa
    return out, raised


@numba.njit(cache=True)
def _fill(z, land, NB):
    """Plain Priority-Flood fill (no epsilon): depressions become exact flats at their spill level."""
    ny, nx = z.shape
    out = z.copy(); seen = ~land.copy()
    hk = np.empty(ny * nx + 8); hc = np.empty(ny * nx + 8, np.int64); n = 0
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
                seen[y, x] = True; hk[n] = out[y, x]; hc[n] = y * nx + x; i = n; n += 1
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
        y = c // nx; x = c % nx
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if yy < 0 or yy >= ny or xx < 0 or xx >= nx or seen[yy, xx]:
                continue
            seen[yy, xx] = True
            if out[yy, xx] < h:
                out[yy, xx] = h
            hk[n] = out[yy, xx]; hc[n] = yy * nx + xx; i = n; n += 1
            while i > 0:
                pa = (i - 1) // 2
                if hk[pa] <= hk[i]:
                    break
                hk[i], hk[pa] = hk[pa], hk[i]; hc[i], hc[pa] = hc[pa], hc[i]; i = pa
    return out


@numba.njit(cache=True)
def _flat_increments(z, land, NB):
    """Barnes, Lehman & Mulla 2014b (Computers & Geosciences 62, 128-135; after Garbrecht & Martz 1997): on every flat
    (a cell with no lower land/water neighbour and an equal neighbour), increments that lead towards the flat's lower
    edges and away from its higher edges. Returns 2 x towards + away (0 off flats)."""
    ny, nx = z.shape; N = ny * nx
    flat = np.zeros((ny, nx), np.bool_); low = np.zeros((ny, nx), np.bool_); high = np.zeros((ny, nx), np.bool_)
    for y in range(ny):
        for x in range(nx):
            if not land[y, x]:
                continue
            haslow = False; haseq = False; hashigh = False
            for k in range(8):
                yy = y + NB[k, 0]; xx = x + NB[k, 1]
                if yy < 0 or yy >= ny or xx < 0 or xx >= nx or not land[yy, xx]:
                    haslow = True; continue
                if z[yy, xx] < z[y, x]:
                    haslow = True
                elif z[yy, xx] == z[y, x]:
                    haseq = True
                else:
                    hashigh = True
            if haseq and not haslow:
                flat[y, x] = True
                if hashigh:
                    high[y, x] = True
            elif haseq and haslow:
                low[y, x] = True                       # drains, and borders a flat of its own elevation
    # BFS distances within each flat (same elevation) from the low edges and from the high edges
    def_d = -1
    dl = np.full(N, def_d, np.int64); dh = np.full(N, def_d, np.int64)
    q = np.empty(N, np.int64)
    for which in range(2):
        d = dl if which == 0 else dh; src = low if which == 0 else high
        head = 0; tail = 0
        for y in range(ny):
            for x in range(nx):
                if src[y, x]:
                    c = y * nx + x; d[c] = 0 if which == 0 else 1; q[tail] = c; tail += 1
        while head < tail:
            c = q[head]; head += 1; y = c // nx; x = c % nx
            for k in range(8):
                yy = y + NB[k, 0]; xx = x + NB[k, 1]
                if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                    continue
                cc = yy * nx + xx
                if flat[yy, xx] and d[cc] == def_d and z[yy, xx] == z[y, x]:
                    d[cc] = d[c] + 1; q[tail] = cc; tail += 1
    # away from higher terrain: per flat, (max distance from its high edges) - distance; flats labelled by BFS
    lab = np.full(N, -1, np.int64); mx = np.zeros(N, np.int64); nl = 0
    for c0 in range(N):
        y0 = c0 // nx; x0 = c0 % nx
        if not flat[y0, x0] or lab[c0] >= 0:
            continue
        head = 0; tail = 0; q[tail] = c0; tail += 1; lab[c0] = nl; m = 0
        while head < tail:
            c = q[head]; head += 1; y = c // nx; x = c % nx
            if dh[c] > m:
                m = dh[c]
            for k in range(8):
                yy = y + NB[k, 0]; xx = x + NB[k, 1]
                if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                    continue
                cc = yy * nx + xx
                if flat[yy, xx] and lab[cc] < 0 and z[yy, xx] == z[y, x]:
                    lab[cc] = nl; q[tail] = cc; tail += 1
        mx[nl] = m; nl += 1
    inc = np.zeros((ny, nx))
    for c in range(N):
        y = c // nx; x = c % nx
        if flat[y, x]:
            towards = dl[c] if dl[c] >= 0 else 0
            away = (mx[lab[c]] - dh[c]) if dh[c] >= 0 else 0
            inc[y, x] = 2.0 * towards + away
    return inc


def outlets(land, riv):
    """Drawn-river land cells touching the sea, a lake or the map edge."""
    water = ndi.binary_dilation(~land, np.ones((3, 3)), border_value=1)
    return riv & water


def lake_network(land, lake, riv):
    """Lakes and drawn rivers as one network (owner, 8 Nov 2026: a river that flows into a lake and out of it again
    continues to the sea). Water bodies are nodes (0 = the sea and the map edge, i = lake i); a drawn-river component
    touching two or more of them links them. Lakes linked to the sea are open: rivers flow through them. A cluster of
    lakes with no link to the sea drains into its largest lake (terminal, endorheic). Returns (outlet, passable,
    lake_label, info): outlet = river cells draining to the sea, the map edge or a terminal sink lake; passable = cells of
    the lakes the rivers flow through."""
    from collections import deque
    land = land.astype(bool); lake = lake.astype(bool) & ~land; riv = riv.astype(bool) & land
    K = np.ones((3, 3)); sea = ~land & ~lake
    edge = np.zeros_like(land); edge[0, :] = edge[-1, :] = edge[:, 0] = edge[:, -1] = True
    lab, n = ndi.label(lake)
    rl, _ = ndi.label(riv, structure=K)
    water_of = {}
    for i in range(1, n + 1):
        for r in set(np.unique(rl[riv & ndi.binary_dilation(lab == i, K)])) - {0}:
            water_of.setdefault(int(r), set()).add(i)
    for r in set(np.unique(rl[riv & (ndi.binary_dilation(sea, K) | edge)])) - {0}:
        water_of.setdefault(int(r), set()).add(0)
    links = {r: s for r, s in water_of.items() if len(s) > 1}
    area = ndi.sum(np.ones_like(lab), lab, index=np.arange(n + 1))

    def reach(start):
        seen = {start: None}; q = deque([start])
        while q:
            w = q.popleft()
            for r, s in links.items():
                if w in s:
                    for v in s:
                        if v not in seen:
                            seen[v] = (r, w); q.append(v)
        return seen
    drains = reach(0); sinks = [0]
    rest = [i for i in range(1, n + 1) if i not in drains]
    while rest:                                             # terminal clusters: the largest lake is the sink
        cluster = reach(rest[0]); sink = max(cluster, key=lambda i: area[i])
        for k, v in reach(sink).items():
            drains.setdefault(k, v)
        sinks.append(sink); rest = [i for i in rest if i not in cluster]
    passable = np.isin(lab, [i for i in range(1, n + 1) if i not in sinks])
    sink_water = sea | np.isin(lab, [i for i in sinks if i > 0])
    outlet = riv & (ndi.binary_dilation(sink_water, K) | edge)
    info = dict(lakes=n, open_lakes=sorted(i for i in drains if i and i not in sinks and 0 in reach(i)),
                terminal_sinks=[i for i in sinks if i], pass_through=sorted(i for i in range(1, n + 1) if i not in sinks),
                drains_into={int(k): (None if v is None else int(v[1])) for k, v in drains.items() if k})
    return outlet, passable, lab, info


def connected(land, rivers):
    """Drawn-river cells joined to an outlet along the drawing (Earth sketches can leave fragments where the routing
    jumped a sink)."""
    land = land.astype(bool); riv = rivers.astype(bool) & land
    return riv & np.isfinite(_geodesic(riv, outlets(land, riv), NB, ND))


def condition(z, land, rivers, W=4, p=1.0, b0=3.0, ramp=None, ref="ramp", alpha=0.5, lake=None):
    """The conditioned height map (float64) and a record of what changed (plan_R1 with amendment 1). With `lake` (plan_R1
    amendment 5), rivers flow through open lakes on to the sea; the record then carries each open lake's level."""
    land = land.astype(bool); riv = rivers.astype(bool) & land
    z = np.where(land, np.maximum(z.astype(float), 1.0), 0.0)            # the atlas loader's land floor (geography._terrain_file)
    if lake is not None:
        out_cells, passable, lake_lab, net = lake_network(land, lake, riv)
    else:
        out_cells, passable, lake_lab, net = outlets(land, riv), np.zeros_like(land), None, None
    flow = riv | passable                                                 # rivers plus the lakes they flow through
    g = _geodesic(flow, out_cells, NB, ND)
    ok = flow & np.isfinite(g)
    if (riv & ~ok).any():
        raise ValueError(f"{int((riv & ~ok).sum())} drawn-river cells are not connected to an outlet along the drawing")
    order = np.flatnonzero(ok.ravel())[np.argsort(-g[ok], kind="stable")]
    if ref == "ramp":
        t = np.maximum(alpha * ramp, 1.0)
    else:                                                                  # the composition's local valley floor
        t = np.maximum(-ndi.maximum_filter(np.where(land, -z, -np.inf), size=5), 1.0)
    if passable.any():                                                     # a lake's reference is its lowest shore's
        for i in np.unique(lake_lab[passable]):
            m = lake_lab == i; shore = land & ndi.binary_dilation(m, np.ones((3, 3)))
            t = np.where(m, t[shore].min(), t)
    gg = np.where(ok, g, -1.0)
    Lo, Up = _envelopes(np.where(flow, t, 0.0), flow, gg, order, NB, ND, FLOOR0, FSTEP, DECMIN)
    R = np.where(flow, 0.5 * (np.where(flow, Lo, 0.0) + np.where(flow, Up, 0.0)), 0.0)
    level = np.zeros(z.shape)
    if passable.any():                                                     # flat lake surface at the head of its outflow
        for i in np.unique(lake_lab[passable]):
            m = lake_lab == i; level[m] = R[m].min()
    R = np.where(riv, R, 0.0)
    zv = z.copy()
    if W > 0:
        d, (iy, ix) = ndi.distance_transform_edt(~riv, return_indices=True)
        Rn = R[iy, ix]; near = land & ~riv & (d <= W)
        hi = near & (z > Rn + b0)
        zv[hi] = np.maximum(Rn[hi] + (z[hi] - Rn[hi]) * (d[hi] / W) ** p, Rn[hi] + b0)
        lo = near & (zv < Rn + b0)
        zv[lo] = (Rn + b0)[lo]
    zc = np.where(riv, R, zv)
    Rmax = ndi.maximum_filter(np.where(riv, R, -np.inf), size=3)
    bank = land & ~riv & np.isfinite(Rmax) & (zc < Rmax + b0)
    zc[bank] = (Rmax + b0)[bank]
    shore_raised = 0
    if passable.any():                                                     # no shore below its lake (rivers excepted)
        lv = ndi.maximum_filter(level, size=3)
        shore = land & ~riv & (lv > 0) & (zc < lv + b0)
        zc[shore] = (lv + b0)[shore]; shore_raised = int(shore.sum())
    # amendment 4: flats drain towards their lower edges and away from higher ones (Barnes et al. 2014b), then PF + eps
    zfill = _fill(np.where(land, zc, 0.0), land, NB)
    inc = _flat_increments(zfill, land, NB)
    zfl = np.where(riv, zc, zfill + FLAT_EPS * inc)
    zf, raised = _priority_flood(np.where(land, zfl, 0.0), land, NB, EPS)
    rec = dict(W=W, p=p, b0=b0, ref=ref, alpha=alpha, river_cells=int(riv.sum()),
               bed_change_m={q: float(np.percentile((R - z)[riv], q)) for q in (1, 10, 50, 90, 99)},
               valley_lowered_cells=int((zv < z - 1e-9).sum()), valley_raised_cells=int((zv > z + 1e-9).sum()),
               banks_raised=int(bank.sum()), pf_raised_cells=int(raised),
               pf_changed_river_cells=int((np.abs(zf - zc) > 1e-9)[riv].sum()))
    if net is not None:
        rec.update(lakes=net, shore_raised_cells=shore_raised,
                   lake_levels_m={int(i): float(level[lake_lab == i].max()) for i in np.unique(lake_lab[passable])})
        return np.where(land, zf, 0.0), rec, level
    return np.where(land, zf, 0.0), rec


def strict_check(z, land, rivers, lake=None, level=None):
    """The owner requirement on the stored (float32) surface. With `lake` and `level` (plan_R1 amendment 5), a lake
    rivers flow through is water at its own level, so its inflows end in it and its outflow carries on to the sea."""
    land = land.astype(bool); riv = rivers.astype(bool) & land; ny, nx = z.shape
    z = np.where(land, np.asarray(z, np.float32).astype(float), 0.0)
    zz = np.where(land, z, -1.0)
    through = None
    if lake is not None:
        out_cells, passable, lake_lab, net = lake_network(land, lake, riv)
        lv = np.asarray(level, np.float32).astype(float)
        zz = np.where(passable, lv, zz); through = (out_cells, passable, lake_lab, net, lv)
    pad = np.pad(zz, 1, constant_values=-1.0)                                     # water and off-map = outlets
    best = np.zeros(z.shape); arg = np.full(z.shape, -1)
    for k, (dy, dx) in enumerate(NB):
        s = (zz - pad[1 + dy:1 + dy + ny, 1 + dx:1 + dx + nx]) / ND[k]
        m = s > best; best = np.where(m, s, best); arg = np.where(m, k, arg)
    ry = np.arange(ny)[:, None] + np.where(arg >= 0, NB[np.maximum(arg, 0), 0], 0)
    rx = np.arange(nx)[None, :] + np.where(arg >= 0, NB[np.maximum(arg, 0), 1], 0)
    off = (ry < 0) | (ry >= ny) | (rx < 0) | (rx >= nx)
    ryc, rxc = np.clip(ry, 0, ny - 1), np.clip(rx, 0, nx - 1)
    rec_ok = (arg >= 0) & (off | riv[ryc, rxc] | ~land[ryc, rxc])
    # follow receivers from every river cell
    state = np.zeros(z.shape, np.int8)
    for y0, x0 in zip(*np.nonzero(riv)):
        if state[y0, x0]:
            continue
        path = []; y, x = y0, x0
        while True:
            if not (0 <= y < ny and 0 <= x < nx) or not land[y, x]:
                res = 1; break
            if not riv[y, x] or arg[y, x] < 0:
                res = 2; break
            if state[y, x]:
                res = state[y, x]; break
            path.append((y, x)); k = arg[y, x]; y, x = y + NB[k, 0], x + NB[k, 1]
        for q in path:
            state[q] = res
    if through is None:
        g = _geodesic(riv, outlets(land, riv), NB, ND)
    else:
        g = _geodesic(riv | through[1], through[0], NB, ND)
    lake_report = {}
    if through is not None:                                  # every lake the rivers flow through must drain out
        _, passable, lake_lab, net, lv = through
        for i in np.unique(lake_lab[passable]):
            m = lake_lab == i; lvl = float(lv[m].max())
            outs = riv & ndi.binary_dilation(m, np.ones((3, 3))) & (z < lvl)
            ends = []
            for y, x in zip(*np.nonzero(outs)):
                for _ in range(ny * nx):
                    if not (0 <= y < ny and 0 <= x < nx) or not land[y, x] or arg[y, x] < 0:
                        break
                    k = arg[y, x]; y, x = y + NB[k, 0], x + NB[k, 1]
                ends.append(bool(not (0 <= y < ny and 0 <= x < nx) or lake_lab[y, x] != i))
            lake_report[int(i)] = dict(level_m=lvl, outflow_cells=int(outs.sum()), outflow_leaves_lake=bool(ends) and all(ends))
    climbs, steps = [], 0
    for y, x in zip(*np.nonzero(riv & np.isfinite(g) & (g > 0))):
        best_d = None
        for k, (dy, dx) in enumerate(NB):
            yy, xx = y + dy, x + dx
            if 0 <= yy < ny and 0 <= xx < nx and riv[yy, xx] and g[yy, xx] < g[y, x] and (best_d is None or g[yy, xx] < best_d[0]):
                best_d = (g[yy, xx], yy, xx)
        if best_d:
            steps += 1
            if z[best_d[1], best_d[2]] >= z[y, x]:
                climbs.append(z[best_d[1], best_d[2]] - z[y, x])
    nr = land & ~riv
    lowest_bank = -ndi.maximum_filter(np.where(nr, -z, -np.inf), size=3)
    below = (z < lowest_bank) | ~np.isfinite(lowest_bank)
    lab, n = ndi.label(riv, structure=np.ones((3, 3)))
    comp_ok = sum(1 for i in range(1, n + 1) if (state[lab == i] == 1).all())
    lakes_ok = all(v["outflow_leaves_lake"] for v in lake_report.values())
    return dict(river_cells=int(riv.sum()), receiver_on_river_or_water=float(rec_ok[riv].mean()),
                path_stays_on_river_to_outlet=float((state[riv] == 1).mean()),
                downstream_steps=steps, climbing_steps=len(climbs),
                climb_m_p50_p90_p99=[float(v) for v in np.percentile(climbs, [50, 90, 99])] if climbs else [],
                below_every_bank=float(below[riv].mean()), components=int(n), components_all_draining=int(comp_ok),
                **({"through_lakes": lake_report, "through_lakes_drain_out": lakes_ok} if through is not None else {}),
                passes=bool(rec_ok[riv].all() and (state[riv] == 1).all() and not climbs and below[riv].all() and lakes_ok))


def cross_profile(z, land, rivers, rings=RINGS):
    """Height above the nearest drawn river by distance: for every river cell, the mean elevation minus the river's of the
    non-river land cells at rounded distance d whose nearest river cell it is; median over river cells per d (m)."""
    land = land.astype(bool); riv = rivers.astype(bool) & land
    d, (iy, ix) = ndi.distance_transform_edt(~riv, return_indices=True)
    out = {}
    for r in rings:
        m = land & ~riv & (np.rint(d) == r)
        if not m.any():
            out[r] = np.nan; continue
        key = (iy[m] * z.shape[1] + ix[m]); dz = z[m] - z[iy[m], ix[m]]
        uk, inv = np.unique(key, return_inverse=True)
        mean = np.bincount(inv, dz) / np.bincount(inv)
        out[r] = float(np.median(mean))
    return out


def profile_loss(rec, true):
    return float(np.mean([abs(math.log((rec[r] + 2.0) / (true[r] + 2.0))) for r in RINGS
                          if np.isfinite(rec[r]) and np.isfinite(true[r]) and rec[r] > -2 and true[r] > -2]))


def bed_ratio(z, ramp, rivers):
    m = rivers & (ramp > 150.0)
    return {q: float(np.percentile(z[m] / ramp[m], q)) for q in (25, 50, 75)} if m.any() else {}


def bed_loss(rec, true):
    return float(np.mean([abs(math.log((rec[q] + 0.05) / (true[q] + 0.05))) for q in (25, 50, 75)])) if true else 0.0


def forms():
    return [dict(ref=r, alpha=a, W=W, p=p, b0=b0) for (r, a), W, p, b0 in itertools.product(*GRID.values())]


def earth(group):
    """Run the map pipeline on Earth windows and score every valley form (joint loss: profile + bed level)."""
    import terrain_earth_b2 as B2
    import terrain_erosion as TE
    cs = json.loads(B2.PLAN.read_text())["development_result"]["C_star"]
    hf = json.loads((ERO / "hill_fit.json").read_text())["best"]
    names = list(json.loads(B2.PLAN.read_text())["windows"][group]); ratio = B2.map_river_ratio()
    grid = forms(); res = {}
    for name in names:
        t0 = time.time(); T = B2.truth(name, ratio); land = T["land"]; riv = connected(land, T["rivers"])
        zc0, _ = TE.compose(T["h0"], land, riv, B2.DX_KM * 1000, cs, hf)
        true_prof = cross_profile(T["z"], land, riv); true_bed = bed_ratio(T["z"], T["h0"], riv)
        row = dict(true_profile=true_prof, true_bed=true_bed, rows=[])
        u = dict(profile=cross_profile(zc0, land, riv), bed=bed_ratio(zc0, T["h0"], riv))
        u["loss"] = profile_loss(u["profile"], true_prof) + bed_loss(u["bed"], true_bed); row["unconditioned"] = u
        for f in grid:
            zc, rec = condition(zc0, land, riv, ramp=T["h0"], **f)
            prof = cross_profile(zc, land, riv); bed = bed_ratio(zc, T["h0"], riv)
            pl, bl = profile_loss(prof, true_prof), bed_loss(bed, true_bed)
            row["rows"].append(dict(f, loss=pl + bl, profile_loss=pl, bed_loss=bl, bed=bed, pf_changed_river_cells=rec["pf_changed_river_cells"]))
        res[name] = row
        best = min(row["rows"], key=lambda r: r["loss"])
        log(f"{name}: true bed/ramp {[round(v, 2) for v in true_bed.values()]}; unconditioned loss {u['loss']:.3f}; best "
            f"{best['ref']} {best['alpha']} W{best['W']} p{best['p']} b{best['b0']} loss {best['loss']:.3f} "
            f"(profile {best['profile_loss']:.3f}, bed {best['bed_loss']:.3f}) ({time.time() - t0:.0f}s)")
    return res, grid


def side_effects(names, form):
    """plan_B2 M1-M3 with and without the chosen conditioning."""
    import terrain_earth_b2 as B2
    import terrain_erosion as TE
    cs = json.loads(B2.PLAN.read_text())["development_result"]["C_star"]
    hf = json.loads((ERO / "hill_fit.json").read_text())["best"]; ratio = B2.map_river_ratio(); out = {}
    for name in names:
        T = B2.truth(name, ratio); T["rivers"] = connected(T["land"], T["rivers"])
        zc0, _ = TE.compose(T["h0"], T["land"], T["rivers"], B2.DX_KM * 1000, cs, hf)
        zc, _ = condition(zc0, T["land"], T["rivers"], ramp=T["h0"], **form)
        keep = ("M1_divides_km", "M2_slope_ks", "M3_new_river_f1")
        a, b = B2.score(T, zc0), B2.score(T, zc)
        out[name] = dict(unconditioned={k: a[k] for k in keep}, conditioned={k: b[k] for k in keep})
        log(f"  {name}: divides {a['M1_divides_km']:.1f} -> {b['M1_divides_km']:.1f} km, slope KS {a['M2_slope_ks']:.3f} -> "
            f"{b['M2_slope_ks']:.3f}, new-river F1 {a['M3_new_river_f1']:.2f} -> {b['M3_new_river_f1']:.2f}")
    return out


def dev():
    OUT.mkdir(parents=True, exist_ok=True)
    res, grid = earth("development")
    names = list(res); mean = [float(np.mean([res[n]["rows"][i]["loss"] for n in names])) for i in range(len(grid))]
    order = np.argsort(mean); best = int(order[0])
    near = [i for i in range(len(grid)) if mean[i] <= mean[best] + 0.01]          # ties within 0.01 -> smaller W
    chosen = min(near, key=lambda i: (grid[i]["W"], mean[i]))
    form = dict(grid[chosen])
    log("mean joint loss, best forms:", [(grid[i]["ref"], grid[i]["alpha"], grid[i]["W"], grid[i]["p"], grid[i]["b0"], round(mean[i], 3)) for i in order[:8]])
    log("unconditioned mean loss:", round(float(np.mean([res[n]["unconditioned"]["loss"] for n in names])), 3), "chosen:", form)
    log("check windows (B1-B4, previously the B2 blind):")
    chk, _ = earth("blind")
    chk_loss = {n: dict(unconditioned=chk[n]["unconditioned"]["loss"], true_bed=chk[n]["true_bed"],
                        chosen=[r for r in chk[n]["rows"] if all(r[k] == form[k] for k in form)][0]) for n in chk}
    log("side effects, development windows:"); se_d = side_effects(names, form)
    log("side effects, check windows:"); se_c = side_effects(list(chk), form)
    out = dict(plan=str(PLAN.relative_to(ROOT)), amendment=1, grid=grid, mean_loss=mean, chosen=form, chosen_mean_loss=mean[chosen],
               development=res, check=chk, check_loss=chk_loss, side_effects=dict(development=se_d, check=se_c))
    (OUT / "earth_valley_fit.json").write_text(json.dumps(out, indent=1, default=float))
    log("check: unconditioned -> chosen loss", {n: (round(v["unconditioned"], 3), round(v["chosen"]["loss"], 3)) for n, v in chk_loss.items()})
    log("check: bed/ramp median true vs chosen", {n: (round(v["true_bed"][50], 2), round(v["chosen"]["bed"][50], 2)) for n, v in chk_loss.items()})


def map_gates(z, h0, land, rivers, tier, tops, dx, c2):
    import terrain_erosion as TE
    c = TE.checks(z, h0, land, rivers, tier, tops, np.zeros(z.shape), dx)
    c["tier1_slope_9km_median_deg"] = float(np.median(TE.slopes_9km(z, land, dx, tier, 1)))
    gates = dict(tier_bands=all(c["tier_band_share"][k] >= c2["tier_band_share"][k] - 0.02 for k in c2["tier_band_share"]),
                 climate_scale=c["climate_scale_mean_abs_m"] <= c2["climate_scale_mean_abs_m"] + 5.0,
                 lowland_slope=abs(c["tier1_slope_9km_median_deg"] / 0.167 - 1) <= 0.10)
    return c, gates


def scan():
    """Amendment 2: the first Earth-ranked form that passes every map gate (hill height of the first refit)."""
    import terrain_erosion as TE
    from rotclimate.geography import elevation_fullres, source_layers
    fit = json.loads((OUT / "earth_valley_fit.json").read_text()); grid, mean = fit["grid"], fit["mean_loss"]
    plan = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text()); cs = plan["development_result"]["C_star"]
    tops = json.loads((ROOT / "calibration/map_world_r44_terrain/params.json").read_text())["tier_tops"]
    L = source_layers(); h0 = elevation_fullres(tuple(tops)); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    tier = L["tier"].astype(int); dx = 1.143 * 1609.344
    hf = dict(json.loads((ERO / "hill_fit.json").read_text())["best"], height_m=1600)
    z0, _ = TE.compose(h0, land, rivers, dx, cs, hf)
    v2 = np.load(ERO / "map_height_v2.npz")["z"].astype(float)
    c2 = TE.checks(v2, h0, land, rivers, tier, tops, np.zeros(v2.shape), dx)
    rows = []
    for rank, i in enumerate(np.argsort(mean)):
        f = grid[i]; z, _ = condition(z0, land, rivers, ramp=h0, **f)
        c, gates = map_gates(np.asarray(z, np.float32).astype(float), h0, land, rivers, tier, tops, dx, c2)
        rows.append(dict(f, rank=rank, earth_loss=mean[i], gates=gates, tier_bands=c["tier_band_share"],
                         climate_scale=c["climate_scale_mean_abs_m"], tier1_slope=c["tier1_slope_9km_median_deg"]))
        log(f"#{rank} {f['ref']} {f['alpha']} W{f['W']} p{f['p']} b{f['b0']} Earth {mean[i]:.3f}: bands "
            f"{ {k: round(v, 3) for k, v in c['tier_band_share'].items()} } scale {c['climate_scale_mean_abs_m']:.1f} slope {c['tier1_slope_9km_median_deg']:.3f} {gates}")
        if all(gates.values()):
            break
    out = dict(rule="plan_R1 amendment 2", v2_bands=c2["tier_band_share"], v2_scale=c2["climate_scale_mean_abs_m"], rows=rows,
               chosen={k: rows[-1][k] for k in ("ref", "alpha", "W", "p", "b0")} if all(rows[-1]["gates"].values()) else None,
               earth_loss_given_up=rows[-1]["earth_loss"] - float(np.min(mean)))
    (OUT / "map_form_scan.json").write_text(json.dumps(out, indent=1, default=float))
    log("chosen:", out["chosen"], "Earth loss given up:", round(out["earth_loss_given_up"], 3))


def tier1_weight(tier):
    """Amendment 3: hills fade to zero at the edge of tier 1."""
    return np.clip(2.0 * ndi.gaussian_filter((tier == 1).astype(float), 3.0) - 1.0, 0.0, 1.0)


HILL_HEIGHTS = (1000, 1300, 1600, 2000, 2500)


def map_gates3(z, h0, land, rivers, tier, tops, dx, c2):
    c, _ = map_gates(z, h0, land, rivers, tier, tops, dx, c2)
    gates = dict(tier_bands_2_4=all(c["tier_band_share"][k] >= c2["tier_band_share"][k] - 0.02 for k in (2, 3, 4)),
                 climate_scale=c["climate_scale_mean_abs_m"] <= c2["climate_scale_mean_abs_m"] + 5.0,
                 lowland_slope=abs(c["tier1_slope_9km_median_deg"] / 0.167 - 1) <= 0.10)
    return c, gates


def scan3():
    """Amendment 3: Earth-ranked forms, each with its hill height refitted (hills in tier 1 only); first that passes."""
    import terrain_erosion as TE
    from scipy.stats import ks_2samp
    from rotclimate.geography import elevation_fullres, source_layers
    fit = json.loads((OUT / "earth_valley_fit.json").read_text()); grid, mean = fit["grid"], fit["mean_loss"]
    plan = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text()); cs = plan["development_result"]["C_star"]
    tops = json.loads((ROOT / "calibration/map_world_r44_terrain/params.json").read_text())["tier_tops"]
    L = source_layers(); h0 = elevation_fullres(tuple(tops)); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    tier = L["tier"].astype(int); dx = 1.143 * 1609.344; w = tier1_weight(tier)
    hf0 = json.loads((ERO / "hill_fit.json").read_text())["best"]; ref9 = np.load(ERO / "earth_lowland_slopes.npz")["s9"]
    z0s = {hm: TE.compose(h0, land, rivers, dx, cs, dict(hf0, height_m=hm), hill_weight=w)[0] for hm in HILL_HEIGHTS}
    v2 = np.load(ERO / "map_height_v2.npz")["z"].astype(float)
    c2 = TE.checks(v2, h0, land, rivers, tier, tops, np.zeros(v2.shape), dx)
    rows = []
    for rank, i in enumerate(np.argsort(mean)):
        f = grid[i]; hrows = []
        for hm, z0 in z0s.items():
            z, _ = condition(z0, land, rivers, ramp=h0, **f); z = np.asarray(z, np.float32).astype(float)
            s9 = TE.slopes_9km(z, land, dx, tier, 1)
            hrows.append((float(ks_2samp(s9, ref9).statistic), hm, z))
        ks, hm, z = min(hrows, key=lambda r: r[0])
        c, gates = map_gates3(z, h0, land, rivers, tier, tops, dx, c2)
        rows.append(dict(f, rank=rank, earth_loss=mean[i], hill_height_m=hm, hill_ks=ks, gates=gates, tier_bands=c["tier_band_share"],
                         climate_scale=c["climate_scale_mean_abs_m"], tier1_slope=c["tier1_slope_9km_median_deg"]))
        log(f"#{rank} {f['ref']} {f['alpha']} W{f['W']} p{f['p']} b{f['b0']} Earth {mean[i]:.3f}: hills {hm} m (KS {ks:.3f}) bands "
            f"{ {k: round(v, 3) for k, v in c['tier_band_share'].items()} } scale {c['climate_scale_mean_abs_m']:.1f} slope {c['tier1_slope_9km_median_deg']:.3f} {gates}")
        if all(gates.values()):
            break
    ok = all(rows[-1]["gates"].values())
    out = dict(rule="plan_R1 amendment 3", v2_bands=c2["tier_band_share"], v2_scale=c2["climate_scale_mean_abs_m"], rows=rows,
               chosen={k: rows[-1][k] for k in ("ref", "alpha", "W", "p", "b0")} if ok else None,
               hill_height_m=rows[-1]["hill_height_m"] if ok else None,
               earth_loss_given_up=rows[-1]["earth_loss"] - float(np.min(mean)))
    (OUT / "map_form_scan3.json").write_text(json.dumps(out, indent=1, default=float))
    log("chosen:", out["chosen"], "hills", out["hill_height_m"], "Earth loss given up:", round(out["earth_loss_given_up"], 3))


def build(version="v21"):
    """Height map v2.1: the released v2 composition with the drawn rivers conditioned in (Earth-fitted valley form,
    map tier gates as constraints: plan_R1 amendment 2). version="v22" (amendment 5): the same, with rivers flowing
    through open lakes on to the sea and each such lake at its own level (stored as lake_level); gated against v2.1."""
    lakes = version == "v22"
    import terrain_erosion as TE
    from rotclimate.geography import elevation_fullres, source_layers
    scan = json.loads((OUT / "map_form_scan3.json").read_text()); form = scan["chosen"]            # amendment 3
    plan = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text())
    cs = plan["development_result"]["C_star"]; ref = plan["earth_tier_band_reference"]
    tops = json.loads((ROOT / "calibration/map_world_r44_terrain/params.json").read_text())["tier_tops"]
    L = source_layers(); h0 = elevation_fullres(tuple(tops)); land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    tier = L["tier"].astype(int); dx = 1.143 * 1609.344
    hf = dict(json.loads((ERO / "hill_fit.json").read_text())["best"], height_m=scan["hill_height_m"], weight="tier 1 only (amendment 3)")
    hill_rows = [{k: r[k] for k in ("hill_height_m", "hill_ks")} for r in scan["rows"][-1:]]
    z0, info = TE.compose(h0, land, rivers, dx, cs, hf, hill_weight=tier1_weight(tier))
    base = "map_height_v21.npz" if lakes else "map_height_v2.npz"
    v2 = np.load(ERO / base)["z"].astype(float)
    if lakes:
        lake = L["lake"].astype(bool) & ~land
        z, rec, level = condition(z0, land, rivers, ramp=h0, lake=lake, **form)
    else:
        z, rec = condition(z0, land, rivers, ramp=h0, **form)
    z32 = np.where(land, z, 0.0).astype(np.float32)
    import fastscapelib as fs
    status = {(int(i), int(j)): fs.NodeStatus.FIXED_VALUE for i, j in zip(*np.nonzero(~land))}
    grid = fs.RasterGrid(list(z.shape), [dx, dx], fs.NodeStatus.FIXED_VALUE, status)
    flow = fs.FlowGraph(grid, [fs.SingleFlowRouter(), fs.MSTSinkResolver()]); flow.update_routes(z32.astype(float))
    A = flow.accumulate(1.0)
    if lakes:
        lv32 = level.astype(np.float32)
        strict = strict_check(z32, land, rivers, lake=lake, level=lv32); strict_v2 = strict_check(v2, land, rivers, lake=lake, level=np.zeros(z.shape))
    else:
        strict = strict_check(z32, land, rivers); strict_v2 = strict_check(v2, land, rivers)
    c = TE.checks(z32.astype(float), h0, land, rivers, tier, tops, A, dx)
    c2 = TE.checks(v2, h0, land, rivers, tier, tops, np.load(ERO / base)["area"].astype(float), dx)
    c["tier1_slope_9km_median_deg"] = float(np.median(TE.slopes_9km(z32.astype(float), land, dx, tier, 1)))
    gates = dict(
        owner_rivers=strict["passes"],
        tier_bands_2_4=all(c["tier_band_share"][k] >= c2["tier_band_share"][k] - 0.02 for k in (2, 3, 4)),
        climate_scale=c["climate_scale_mean_abs_m"] <= c2["climate_scale_mean_abs_m"] + 5.0,
        lowland_slope=abs(c["tier1_slope_9km_median_deg"] / 0.167 - 1) <= 0.10)
    c["river_bed_over_ramp"] = bed_ratio(z32.astype(float), h0, rivers); c2["river_bed_over_ramp"] = bed_ratio(v2, h0, rivers)
    out = dict(plan=str(PLAN.relative_to(ROOT)), form=form, hills=hf, hill_refit=hill_rows, conditioning=rec, strict=strict, strict_v2=strict_v2,
               checks=c, checks_v2=c2, tier_band_reference_earth=ref, gates=gates, adopt=bool(all(gates.values())),
               composition_matches_v2_off_rivers=float(np.median(np.abs(z0 - v2)[land & ~ndi.binary_dilation(rivers, iterations=12)])))
    OUT.mkdir(parents=True, exist_ok=True)
    extra = dict(lake_level=lv32) if lakes else {}
    np.savez_compressed(ERO / f"map_height_{version}.npz", z=z32, area=A.astype(np.float32), tier_tops=np.asarray(tops, float), **extra)
    (OUT / f"map_height_{version}.json").write_text(json.dumps(out, indent=1, default=float))
    log(json.dumps(dict(strict=strict, gates=gates, conditioning=rec, hills=hf, bed_over_ramp=(c["river_bed_over_ramp"], c2["river_bed_over_ramp"]),
                        tier_bands=(c["tier_band_share"], c2["tier_band_share"]),
                        climate_scale=(c["climate_scale_mean_abs_m"], c2["climate_scale_mean_abs_m"]),
                        tier1_slope=c["tier1_slope_9km_median_deg"]), indent=1, default=float))
    preview(z32.astype(float), v2, land, rivers, dx, A)
    if lakes:                                                # keep the v2.1 previews; name these v2.2
        for kind in ("detail", "full"):
            src = OUT / f"map_height_v21_{kind}.png"
            if src.exists():
                src.replace(OUT / f"map_height_v22_{kind}.png")


def preview(z, v2, land, rivers, dx, A):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    ls = LightSource(azdeg=315, altdeg=38)
    def shade(e, rows, cols, mark):
        E = np.where(land, e, 0.0)[rows, cols]
        from matplotlib.colors import LinearSegmentedColormap
        cm = LinearSegmentedColormap.from_list("land", ["#8fb87a", "#b9c98a", "#d9cf9c", "#c9a77c", "#a1816a", "#e8e2dc"])
        rgb = ls.shade(np.clip(E, 0, 2900), cmap=cm, vert_exag=5, dx=dx, dy=dx, blend_mode="soft", vmin=0, vmax=2900)[..., :3]
        rgb[~land[rows, cols]] = [0.74, 0.84, 0.92]
        if mark:
            new = (A[rows, cols] >= 3000e6) & land[rows, cols] & ~rivers[rows, cols]
            rgb[new] = rgb[new] * 0.25 + np.array([0.20, 0.70, 0.90]) * 0.75
            mk = rivers[rows, cols]; rgb[mk] = rgb[mk] * 0.1 + np.array([0.05, 0.25, 0.70]) * 0.9
        return rgb
    rows, cols = slice(250, 650), slice(700, 1300)
    fig, ax = plt.subplots(1, 2, figsize=(16, 5.6), constrained_layout=True)
    ax[0].imshow(shade(v2, rows, cols, False)); ax[0].set_title("Height map v2 (released): drawn rivers not kept as flow paths", fontsize=10)
    ax[1].imshow(shade(z, rows, cols, True)); ax[1].set_title("Height map v2.1: every drawn river (blue) drains along itself; undrawn rivers > 3,000 km² cyan", fontsize=10)
    for a in ax:
        a.axis("off")
    fig.savefig(OUT / "map_height_v21_detail.png", dpi=110); plt.close(fig)
    fig = plt.figure(figsize=(20, 9.6)); a = fig.add_axes([0, 0, 1, 0.96]); a.imshow(shade(z, slice(None), slice(None), True)); a.axis("off")
    fig.suptitle("Height map v2.1: eroded terrain with every drawn river as a flow path (blue); undrawn rivers > 3,000 km² cyan", fontsize=12)
    fig.savefig(OUT / "map_height_v21_full.png", dpi=100); plt.close(fig)
    log("wrote", OUT / "map_height_v21_detail.png", OUT / "map_height_v21_full.png")


def check_cmd(path):
    from rotclimate.geography import source_layers
    L = source_layers(); d = np.load(path); z = d["z"]
    if "lake_level" in d.files:                              # amendment 5: rivers flow through open lakes
        log(json.dumps(strict_check(z, L["land"], L["rivers"], lake=L["lake"], level=d["lake_level"]), indent=1, default=float))
    else:
        log(json.dumps(strict_check(z, L["land"], L["rivers"]), indent=1))


if __name__ == "__main__":
    {"check": lambda: check_cmd(sys.argv[2]), "dev": dev, "scan": scan, "scan3": scan3, "build": build, "build22": lambda: build("v22")}[sys.argv[1]]()
