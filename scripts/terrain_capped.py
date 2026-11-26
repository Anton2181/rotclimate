"""Height map v2.3 (owner, 26 Nov 2026): every drawn river is shown in full, and no NEW (undrawn) river may be larger
than the smallest drawn one, size = catchment area (owner's choice): no undrawn channel may collect more than the
smallest drawn river's catchment (403 km2 on the map) before it reaches a drawn river, a lake, the sea or the map edge.
Tier rules as before (the v2.1/v2.2 gates).

Imposing such a drainage on the eroded v2.2 surface needs 2.3 km gorges and breaks the tier-3 gate (prototype,
calibration/rivers_cap_20261126/notes.md), because v2.2's large undrawn basins are built into its relief. So the erosion
is regenerated on a capped drainage instead:

  1. capped tree: a min-cost flow on the tier ramps (every undrawn land cell supplies one cell of area; node
     throughput <= CAP_FLOW cells; outlets = sea, lakes, drawn rivers, map edge absorb all; arc cost = step length +
     WZ x uphill metres of the ramps), reduced to one receiver per cell by its largest outflow, then a local repair that
     moves subtrees off over-cap channels onto neighbouring channels with room (cap = the smallest drawn river's area);
  2. the same steady-state stream-power erosion and Earth-fitted settings as height map v2 (terrain_erosion.evolve,
     plan_B2 C*, hill fit), integrated along that fixed tree instead of re-routing each round (same area units as the
     Earth fits: accumulate(dx^2), i.e. cells x dx^4);
  3. the drawn rivers and open lakes conditioned in exactly as v2.2 (terrain_rivers.condition, amendment 5);
  4. elevations made to fall strictly along the stored tree (a fill along the tree, reported);
  5. the v2.2 gates (strict drawn-river check, tier bands 2-4 within 0.02 of v2.2, climate scale, lowland slope) plus
     the cap check. The tree is stored with the height map ('recv'); rotclimate.routing reads it.

    .venv/bin/python -I scripts/terrain_capped.py tree       # step 1 -> output/terrain_erosion_20261107/capped_tree.npz
    .venv/bin/python -I scripts/terrain_capped.py build      # steps 2-5 -> map_height_v23.npz + .json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numba
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
ERO = ROOT / "output/terrain_erosion_20261107"
NB = np.array([(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)], np.int64)
CAP_FLOW, WZ, EPS_M = 70, 0.2, 0.01
import os
WZ = float(os.environ.get("CAPPED_WZ", WZ)); CAP_FLOW = int(os.environ.get("CAPPED_FLOW", CAP_FLOW))
MIN_DRAWN_KM2 = float(os.environ.get("CAPPED_C", 0))   # >0: every drawn river collects >= this; undrawn channels stay below it
log = lambda *a: print(*a, flush=True)  # noqa: E731


def layers():
    from rotclimate.geography import elevation_fullres, source_layers
    tops = json.loads((ROOT / "calibration/map_world_r44_terrain/params.json").read_text())["tier_tops"]
    L = source_layers()
    land = L["land"].astype(bool); rivers = L["rivers"].astype(bool) & land
    h0 = elevation_fullres(tuple(tops))
    return L, tops, h0, land, rivers


def lake_through(land):
    """Open lakes the drawn rivers flow through (their level > 0 in v2.2)."""
    v22 = np.load(ERO / "map_height_v22.npz")
    return ~land & (np.asarray(v22["lake_level"]) > 0)


def drawn_receivers(land, rivers):
    """Receivers of the drawn-river cells: their paths in v2.2 (a strict-check-passing drainage along the drawing)."""
    from rotclimate.routing import _flood
    v22 = np.load(ERO / "map_height_v22.npz"); z = np.asarray(v22["z"], float); lv = np.asarray(v22["lake_level"], float)
    through = ~land & (lv > 0)
    recv, _ = _flood(np.where(land, z, np.where(through, lv, -1e9)), land | through, NB)
    return recv


def drawn_branches(land, rivers):
    """Branch id (1..n) of every drawn map cell: the original drawing's skeleton split at junctions, each drawn cell
    taking the branch of the nearest skeleton pixel (0 = unassigned)."""
    from PIL import Image
    from skimage.morphology import skeletonize
    H, W = land.shape
    im = np.array(Image.open(ROOT / "data/source/original/rivers.png").convert("RGBA")); m = im[..., 3] > 60
    oy, ox = m.shape; sk = skeletonize(m)
    nbc = ndi.convolve(sk.astype(int), np.ones((3, 3), int), mode="constant") - 1
    jb = ndi.binary_dilation(sk & (nbc >= 3), structure=np.ones((3, 3)), iterations=2)
    lab, nb = ndi.label(sk & ~jb, structure=np.ones((3, 3)))
    ys, xs = np.nonzero(lab)
    g = np.zeros((H, W), np.int64)
    gy = np.clip(((ys + 0.5) * H / oy).astype(int), 0, H - 1); gx = np.clip(((xs + 0.5) * W / ox).astype(int), 0, W - 1)
    g[gy, gx] = lab[ys, xs]
    _, (iy, ix) = ndi.distance_transform_edt(g == 0, return_indices=True)
    b = np.where(rivers, g[iy, ix], 0)
    # renumber 1..n over the branches present on the map
    u = np.unique(b[b > 0]); ren = np.zeros(int(b.max()) + 1, np.int64); ren[u] = np.arange(1, u.size + 1)
    return ren[b]


# ------------------------------------------------------------------ tree
def subtree_loads(recv, und):
    """Subtree sizes (cells) of undrawn cells on the tree (Kahn order); cells on a cycle keep partial counts."""
    return _loads(recv, und)


@numba.njit(cache=True)
def _loads(recv, und):
    N = recv.shape[0]; load = np.zeros(N, np.int64); indeg = np.zeros(N, np.int64)
    for c in range(N):
        if und[c] and recv[c] >= 0 and und[recv[c]]:
            indeg[recv[c]] += 1
    stack = np.empty(N, np.int64); sp = 0
    for c in range(N):
        if und[c]:
            load[c] = 1
            if indeg[c] == 0:
                stack[sp] = c; sp += 1
    while sp > 0:
        sp -= 1; c = stack[sp]; r = recv[c]
        if r >= 0 and und[r]:
            load[r] += load[c]; indeg[r] -= 1
            if indeg[r] == 0:
                stack[sp] = r; sp += 1
    return load


@numba.njit(cache=True)
def _repair(recv, load, z, und, ny, nx, NB, cap, wz, passes):
    N = recv.shape[0]
    for it in range(passes):
        moves = 0
        for c in range(N):
            if not und[c]:
                continue
            v = recv[c]; over = load[c] > cap
            while not over and v >= 0 and und[v]:
                if load[v] > cap:
                    over = True
                v = recv[v]
            if not over or load[c] > cap:
                continue
            add = load[c]; y = c // nx; x = c % nx; best = -2; bs = 1e18
            for k in range(8):
                yy = y + NB[k, 0]; xx = x + NB[k, 1]
                if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                    if bs > -1e9:
                        best = -1; bs = -1e9
                    continue
                w = yy * nx + xx
                if w == recv[c]:
                    continue
                if not und[w]:
                    if bs > -1e8:
                        best = w; bs = -1e8
                    continue
                ok = True; u = w; steps = 0
                while u >= 0 and und[u]:
                    if u == c or load[u] + add > cap:
                        ok = False; break
                    u = recv[u]; steps += 1
                    if steps > N:
                        ok = False; break
                if ok:
                    sc = load[w] + wz * max(z[w] - z[c], 0.0)
                    if sc < bs:
                        bs = sc; best = w
            if best == -2:
                continue
            u = recv[c]
            while u >= 0 and und[u]:
                load[u] -= add; u = recv[u]
            recv[c] = best
            u = best
            while u >= 0 and und[u]:
                load[u] += add; u = recv[u]
            moves += 1
        if moves == 0:
            break
    return recv


def capped_tree():
    from ortools.graph.python import min_cost_flow
    L, tops, h0, land, rivers = layers()
    H, W = land.shape; N = H * W; dx_km = 1.143 * 1.609344
    px_km2 = dx_km ** 2
    lab, n = ndi.label(rivers, structure=np.ones((3, 3)))
    recv_v22 = drawn_receivers(land, rivers)
    # the smallest drawn river's catchment (v2.2 drainage; area at its mouth)
    from rotclimate.routing import _accumulate, _flood
    v22 = np.load(ERO / "map_height_v22.npz"); lv = np.asarray(v22["lake_level"], float); through = ~land & (lv > 0)
    rv, order = _flood(np.where(land, np.asarray(v22["z"], float), np.where(through, lv, -1e9)), land | through, NB)
    A = _accumulate(order, rv, land.ravel().astype(float)).reshape(H, W) * px_km2
    mouths = np.array([A[lab == k].max() for k in range(1, n + 1)])
    cap_km2 = float(mouths.min()); cap = int(np.floor(cap_km2 / px_km2))
    branch = None; flow_cap = CAP_FLOW
    if MIN_DRAWN_KM2 > 0:
        # every drawn river (a branch of the drawing's skeleton) is guaranteed >= C of catchment; undrawn stay below C
        cap_km2 = MIN_DRAWN_KM2; cap = int(np.floor(cap_km2 / px_km2)) - 1
        flow_cap = int(0.6 * cap)
        branch = drawn_branches(land, rivers)
    log(f"drawn rivers {n}; cap {cap_km2:.0f} km2 -> {cap} cells; flow cap {flow_cap}")
    und = (land & ~rivers).ravel(); zc = h0.ravel().astype(float)
    ids = -np.ones(N, np.int64); ids[und] = np.arange(und.sum()); M = int(und.sum()); SINK = 2 * M
    cells = np.flatnonzero(und); yy, xx = np.divmod(cells, W)
    T = [np.arange(M)]; Hh = [np.arange(M) + M]; C = [np.full(M, flow_cap)]; Co = [np.zeros(M, np.int64)]
    nbr = 0 if branch is None else int(branch.max())
    BNODE = SINK + 1                                                 # branch nodes SINK+1 .. SINK+nbr
    def sink_of(target):                                             # flat cell index (or -1 off-map) -> sink node
        if branch is None:
            return np.full(target.shape, SINK)
        b = np.where(target >= 0, branch.ravel()[np.maximum(target, 0)], 0)
        return np.where(b > 0, BNODE + b - 1, SINK)
    for k in range(8):
        dy, dx = NB[k]; ny_, nx_ = yy + dy, xx + dx; step = 14 if dy and dx else 10
        inside = (ny_ >= 0) & (ny_ < H) & (nx_ >= 0) & (nx_ < W)
        j = np.where(inside, ny_ * W + nx_, 0)
        to_out = ~inside | (inside & ~und[j]); to_und = inside & und[j]
        tgt = np.where(inside, j, -1)[to_out]
        T.append(ids[cells[to_out]] + M); Hh.append(sink_of(tgt)); C.append(np.full(to_out.sum(), flow_cap)); Co.append(np.full(to_out.sum(), step, np.int64))
        up = np.maximum(zc[j[to_und]] - zc[cells[to_und]], 0.0)
        T.append(ids[cells[to_und]] + M); Hh.append(ids[j[to_und]]); C.append(np.full(to_und.sum(), flow_cap)); Co.append((step + np.round(WZ * up)).astype(np.int64))
    demand = np.zeros(max(nbr, 0), np.int64)
    if nbr:
        own = np.bincount(branch.ravel()[branch.ravel() > 0], minlength=nbr + 1)[1:]
        demand = np.maximum(int(np.ceil(cap_km2 / px_km2)) - own, 0)
        T.append(BNODE + np.arange(nbr)); Hh.append(np.full(nbr, SINK)); C.append(np.full(nbr, M)); Co.append(np.zeros(nbr, np.int64))
    T, Hh, C, Co = (np.concatenate(a) for a in (T, Hh, C, Co))
    smcf = min_cost_flow.SimpleMinCostFlow()
    arcs = smcf.add_arcs_with_capacity_and_unit_cost(T, Hh, C, Co)
    sup = np.zeros(2 * M + 1 + nbr, np.int64); sup[:M] = 1
    if nbr:
        sup[BNODE:BNODE + nbr] = -demand
    sup[SINK] = -(M - int(demand.sum()))
    smcf.set_nodes_supplies(np.arange(2 * M + 1 + nbr), sup)
    log(f"branch demands: {nbr} drawn rivers, total {int(demand.sum())} cells, max {int(demand.max()) if nbr else 0}")
    t0 = time.time(); st = smcf.solve(); log(f"min-cost flow {st} in {time.time() - t0:.0f}s ({len(T)} arcs)")
    if st != smcf.OPTIMAL:
        raise SystemExit("min-cost flow not optimal: raise CAP_FLOW")
    fl_all = smcf.flows(arcs); sel = (T >= M) & (T < 2 * M); f = fl_all[sel]; t = T[sel] - M; h = Hh[sel]
    o = np.argsort(f, kind="stable"); best = np.full(M, -1, np.int64); best[t[o]] = h[o]
    recv = recv_v22.copy(); recv[~(land | through).ravel()] = -1
    for i in range(M):
        c = cells[i]; b = best[i]
        if 0 <= b < M:
            recv[c] = cells[b]; continue
        y, x = divmod(c, W); r = -1                                    # outlet arc: an off-map, water or drawn neighbour
        for dy, dx in NB:
            a, bb = y + dy, x + dx
            if not (0 <= a < H and 0 <= bb < W):
                r = -1; break
            if not und[a * W + bb]:
                r = a * W + bb
                if land[a, bb]:
                    break
        recv[c] = r
    load = subtree_loads(recv, und)
    log(f"rounded: over cap {(load[und] > cap).sum()} cells, max {load[und].max()} cells")
    recv = _repair(recv, load, zc, und, H, W, NB, cap, WZ, 60)
    load = subtree_loads(recv, und)
    over = und & (load > cap)
    rec = dict(cap_km2=cap_km2, cap_cells=cap, flow_cap_cells=CAP_FLOW, wz=WZ, over_cap_cells=int(over.sum()),
               over_cap_land_share=float(over.sum() / land.sum()), max_undrawn_km2=float(load[und].max() * px_km2),
               smallest_drawn_km2=sorted(float(x) for x in mouths)[:5])
    log(json.dumps(rec, indent=1))
    np.savez_compressed(ERO / "capped_tree.npz", recv=recv, load=load.reshape(H, W).astype(np.int32))
    (ERO / "capped_tree.json").write_text(json.dumps(rec, indent=1))


@numba.njit(cache=True)
def _entry(v, recv, und):
    """First non-undrawn cell (drawn river, water) on v's path, or -1 (off-map)."""
    while v >= 0 and und[v]:
        v = recv[v]
    return v


@numba.njit(cache=True)
def _add_drawn(v, s, recv, isdrawn, A):
    """Add s to the catchment of drawn cell v and every drawn cell below it."""
    while v >= 0 and isdrawn[v]:
        A[v] += s; v = recv[v]


@numba.njit(cache=True)
def _move(c, w, recv, load, und, isdrawn, A):
    """Re-route undrawn cell c (with its subtree) to w; keeps undrawn loads and drawn catchments exact."""
    s = load[c]
    u = recv[c]
    while u >= 0 and und[u]:
        load[u] -= s; u = recv[u]
    _add_drawn(u, -s, recv, isdrawn, A)
    recv[c] = w
    u = w
    while u >= 0 and und[u]:
        load[u] += s; u = recv[u]
    _add_drawn(u, s, recv, isdrawn, A)


@numba.njit(cache=True)
def _fits(w, s, c, recv, load, und, cap):
    u = w; steps = 0
    while u >= 0 and und[u]:
        if u == c or load[u] + s > cap:
            return False
        u = recv[u]; steps += 1
        if steps > 10000000:
            return False
    return True


@numba.njit(cache=True)
def _entries(recv, und, order):
    """Entry cell (first drawn / water cell, -1 off-map) of every cell's path; order = receivers first."""
    N = recv.shape[0]; ent = -np.ones(N, np.int64)
    for k in range(order.shape[0]):
        c = order[k]; r = recv[c]
        if not und[c]:
            ent[c] = c
        elif r < 0:
            ent[c] = -1
        else:
            ent[c] = ent[r] if und[r] else r
    return ent


@numba.njit(cache=True)
def _boost(recv, load, und, isdrawn, A, bcell, bid, ny, nx, NB, need, cap, protect, ent):
    """Raise every drawn branch below `need` (end cell bcell[b]) by re-routing undrawn subtrees onto a neighbour whose
    path already enters that branch (multi-hop), if the path has room and the branch the subtree leaves stays >= protect."""
    nb = bcell.shape[0]; moves = 0
    for b in range(nb):
        e = bcell[b]
        if e < 0 or A[e] >= need:
            continue
        for c in range(ny * nx):
            if A[e] >= need:
                break
            if not und[c]:
                continue
            oe = ent[c]
            if oe >= 0 and isdrawn[oe] and bid[oe] == b + 1:
                continue
            s = load[c]
            if oe >= 0 and isdrawn[oe]:
                ob = bid[oe]
                if ob > 0 and bcell[ob - 1] >= 0 and A[bcell[ob - 1]] - s < protect:
                    continue
            y = c // nx; x = c % nx; tgt = -1
            for k in range(8):
                yy = y + NB[k, 0]; xx = x + NB[k, 1]
                if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                    continue
                j = yy * nx + xx
                ej = ent[j]
                if ej >= 0 and isdrawn[ej] and bid[ej] == b + 1:
                    if (not und[j]) or _fits(j, s, c, recv, load, und, cap):
                        tgt = j; break
            if tgt < 0:
                continue
            _move(c, tgt, recv, load, und, isdrawn, A); moves += 1
            # c's subtree now enters branch b: mark the moved cell (its donors follow lazily next sweep)
            ent[c] = ent[tgt]
    return moves


@numba.njit(cache=True)
def _boost_one(b, need_b, recv, load, und, isdrawn, A, bcell, bid, ny, nx, NB, cap, protect, ent, avoid):
    """As _boost, for one branch b (0-based) up to need_b; never takes land from branch `avoid` (1-based, 0 = none)."""
    e = bcell[b]; moves = 0
    for c in range(ny * nx):
        if A[e] >= need_b:
            break
        if not und[c]:
            continue
        oe = ent[c]
        if oe >= 0 and isdrawn[oe] and bid[oe] == b + 1:
            continue
        s = load[c]
        if oe >= 0 and isdrawn[oe]:
            ob = bid[oe]
            if ob == avoid:
                continue
            if ob > 0 and bcell[ob - 1] >= 0 and A[bcell[ob - 1]] - s < protect:
                continue
        y = c // nx; x = c % nx; tgt = -1
        for k in range(8):
            yy = y + NB[k, 0]; xx = x + NB[k, 1]
            if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                continue
            j = yy * nx + xx
            ej = ent[j]
            if ej >= 0 and isdrawn[ej] and bid[ej] == b + 1:
                if (not und[j]) or _fits(j, s, c, recv, load, und, cap):
                    tgt = j; break
        if tgt < 0:
            continue
        _move(c, tgt, recv, load, und, isdrawn, A); moves += 1; ent[c] = ent[tgt]
    return moves


@numba.njit(cache=True)
def _transfer(recv, load, und, isdrawn, A, from_b, to_b, end_from, end_to, bid, ny, nx, NB, keep_min):
    """Move undrawn subtrees that drain into branch from_b and touch branch to_b over to to_b until
    A[end_from] < A[end_to] (thin below thick), keeping A[end_from] >= keep_min."""
    moves = 0
    for sweep in range(6):
        if A[end_from] < A[end_to]:
            break
        got = False
        for c in range(ny * nx):
            if not und[c]:
                continue
            old = _entry(recv[c], recv, und)
            if old < 0 or not isdrawn[old] or bid[old] != from_b:
                continue
            if A[end_from] - load[c] < keep_min:
                continue
            y = c // nx; x = c % nx; tgt = -1
            for k in range(8):
                yy = y + NB[k, 0]; xx = x + NB[k, 1]
                if yy < 0 or yy >= ny or xx < 0 or xx >= nx:
                    continue
                j = yy * nx + xx
                if isdrawn[j] and bid[j] == to_b:
                    tgt = j; break
            if tgt < 0:
                continue
            _move(c, tgt, recv, load, und, isdrawn, A); moves += 1; got = True
            if A[end_from] < A[end_to]:
                break
        if not got:
            break
    return moves


def post():
    """Tree post-processing (owner rules): every drawn river >= C; undrawn channels < C; at every confluence a thin
    river below the thick one it joins. Exact bookkeeping of undrawn loads and drawn catchments (cells)."""
    import river_order_check as RO
    L, tops, h0, land, rivers = layers(); H, W = land.shape; N = H * W
    px = (1.143 * 1.609344) ** 2
    t = np.load(ERO / "capped_tree.npz"); recv = t["recv"].astype(np.int64).copy()
    np.savez_compressed(ERO / "capped_tree_raw.npz", recv=recv)
    und = (land & ~rivers).ravel(); isdrawn = rivers.ravel()
    C = MIN_DRAWN_KM2 or 800.0; cap = int(np.floor(C / px)) - 1; need = cap + 1
    bid = drawn_branches(land, rivers).ravel()
    isbase, order, _ = tree_geometry(recv, land, W)
    A = accumulate_tree(order, recv, land.ravel().astype(float))           # cells
    nb = int(bid.max()); bcell = -np.ones(nb, np.int64)
    for b in range(1, nb + 1):
        cs = np.flatnonzero(bid == b)
        if cs.size:
            bcell[b - 1] = cs[np.argmax(A[cs])]
    load = subtree_loads(recv, und)
    def report(tag):
        sizes = A[bcell[bcell >= 0]]
        log(f"{tag}: smallest drawn river {sizes.min() * px:.0f} km2 ({(sizes < need).sum()} below {need * px:.0f}); "
            f"undrawn max {load[und].max() * px:.0f} km2, over cap {(load[und] > cap).sum()} cells")
    report("start")
    for rnd in range(3):
        m1 = 0
        for sweep in range(40):
            ent = _entries(recv, und, tree_geometry(recv, land, W)[1])
            mm = _boost(recv, load, und, isdrawn, A, bcell, bid, H, W, NB, need, cap, need, ent); m1 += mm
            if mm == 0:
                break
        recv[:] = _repair(recv, load, h0.ravel().astype(float), und, H, W, NB, cap, WZ, 30)
        load = subtree_loads(recv, und)
        A = accumulate_tree(order := tree_geometry(recv, land, W)[1], recv, land.ravel().astype(float))
        report(f"round {rnd + 1} (boost moves {m1})")
    # confluences: thin below the thick stem it joins (river_order_check's junction logic, mapped to the branch ids)
    br = RO.branches(land, rivers)
    bid2 = bid.reshape(H, W)
    for rnd in range(4):
        A2 = A.reshape(H, W)
        Atr = ndi.maximum_filter(np.where(rivers, A2, 0.0), size=5)
        for b in br:
            a = np.sort(Atr[b["gy"], b["gx"]]); a = a[3:-3] if a.size > 6 else a
            b["A"] = float(a.max())
            ids = bid2[b["gy"], b["gx"]]; ids = ids[ids > 0]
            b["bid"] = int(np.bincount(ids).argmax()) if ids.size else 0
        byj = {}
        for b in br:
            for j in b["junctions"]:
                byj.setdefault(j, []).append(b)
        bad = []
        for j, bs in byj.items():
            if len(bs) < 2:
                continue
            out = max(bs, key=lambda b: b["A"]); inc = [b for b in bs if b is not out]
            thick_in = [b for b in inc if b["thick"]]; thin_in = [b for b in inc if not b["thick"]]
            if thick_in and thin_in:
                k = max(thick_in, key=lambda b: b["A"])
                for t in thin_in:
                    if t["A"] >= k["A"] and t["bid"] and k["bid"]:
                        bad.append((t["bid"], k["bid"]))
        log(f"confluence round {rnd + 1}: thin not below thick {len(bad)}")
        if not bad:
            break
        for tb, kb in bad:
            # feed the thick stem's system (never from the thin river) until it out-collects the thin tributary
            for sweep in range(60):
                if A[bcell[kb - 1]] > A[bcell[tb - 1]]:
                    break
                ent = _entries(recv, und, tree_geometry(recv, land, W)[1])
                mm = _boost_one(kb - 1, A[bcell[tb - 1]] + 1, recv, load, und, isdrawn, A, bcell, bid, H, W, NB, cap, need, ent, tb)
                if mm == 0:
                    break
            _transfer(recv, load, und, isdrawn, A, tb, kb, bcell[tb - 1], bcell[kb - 1], bid, H, W, NB, need)
            log(f"   thin {tb} {A[bcell[tb - 1]] * px:.0f} km2 vs thick {kb} {A[bcell[kb - 1]] * px:.0f} km2")
        A = accumulate_tree(tree_geometry(recv, land, W)[1], recv, land.ravel().astype(float))
        load = subtree_loads(recv, und)
    report("final")
    np.savez_compressed(ERO / "capped_tree.npz", recv=recv, load=load.reshape(H, W).astype(np.int32))
    tj = json.loads((ERO / "capped_tree.json").read_text())
    tj.update(min_drawn_km2=C, cap_cells=cap, over_cap_cells=int((load[und] > cap).sum()),
              smallest_drawn_km2_after=float(A[bcell[bcell >= 0]].min() * px), max_undrawn_km2=float(load[und].max() * px))
    (ERO / "capped_tree.json").write_text(json.dumps(tj, indent=1))


# ------------------------------------------------------------------ erosion on the fixed tree
@numba.njit(cache=True)
def _order_from_bases(recv, isbase):
    """Cells in an order with every receiver before its donors (bases first)."""
    N = recv.shape[0]; head = -np.ones(N, np.int64); nxt = -np.ones(N, np.int64)
    for c in range(N):
        r = recv[c]
        if not isbase[c] and r >= 0:
            nxt[c] = head[r]; head[r] = c
    out = np.empty(N, np.int64); no = 0; stack = np.empty(N, np.int64); sp = 0
    for c in range(N):
        if isbase[c]:
            stack[sp] = c; sp += 1
    while sp > 0:
        sp -= 1; c = stack[sp]; out[no] = c; no += 1
        d = head[c]
        while d >= 0:
            stack[sp] = d; sp += 1; d = nxt[d]
    return out[:no]


def tree_geometry(recv, land, W):
    N = recv.size
    isbase = ~land.ravel() | (recv < 0)
    order = _order_from_bases(recv, isbase)
    c = np.arange(N); r = np.where(recv >= 0, recv, c)
    dy = np.abs(r // W - c // W); dxx = np.abs(r % W - c % W)
    step = np.where((dy > 0) & (dxx > 0), np.sqrt(2.0), 1.0)
    return isbase, order, step


def accumulate_tree(order, recv, src):
    acc = src.astype(float).copy()
    for k in range(order.size - 1, -1, -1):
        cc = order[k]; rr = recv[cc]
        if rr >= 0 and rr != cc:
            acc[rr] += acc[cc]
    return acc


def evolve_fixed(h0, land, rivers, dx_m, prm, recv):
    """terrain_erosion.evolve on a fixed drainage tree (same numerics otherwise)."""
    from terrain_erosion import DEFAULTS
    p = dict(DEFAULTS, **(prm or {})); t0 = time.time()
    ny, nx = h0.shape; cells_km = dx_m / 1000.0
    rng = np.random.default_rng(p["seed"])
    def smooth_noise(km):
        n = ndi.gaussian_filter(rng.standard_normal(h0.shape), max(km / cells_km, 0.5)); return n / n.std()
    lp = lambda a: ndi.gaussian_filter(np.where(land, a, 0.0), p["lowpass_km"] / cells_km) / np.maximum(
        ndi.gaussian_filter(land.astype(float), p["lowpass_km"] / cells_km), 1e-6)
    target = lp(h0)
    rock = np.exp(p["noise_sigma"] * smooth_noise(p["noise_km"]))
    ksn = np.where(land, rock, 0.0)
    _ = np.where(land, h0 * (1 + 0.15 * smooth_noise(p["noise_km"] / 2)) + 5 * smooth_noise(p["noise_km"]), 0.0)  # keep the RNG stream
    isbase, order, step = tree_geometry(recv, land, nx)
    area_unit = 1.0 if p.get("area_m2") else dx_m * dx_m
    A = accumulate_tree(order, recv, np.where(land.ravel(), dx_m * dx_m * area_unit, 0.0)) + np.where(rivers, p["river_boost_km2"] * 1e6, 0.0).ravel()
    dist = step * dx_m
    z = np.zeros(h0.shape)
    for r in range(p["rounds"]):
        incr = ksn.ravel() * np.power(np.maximum(A, dx_m * dx_m), -p["m"]) * dist
        zz = _integrate(order, recv, isbase, incr).reshape(h0.shape)
        scale = np.where(land, target / np.maximum(lp(zz), 1e-6), 1.0)
        scale = np.exp(ndi.gaussian_filter(np.log(np.clip(scale, 1e-3, 1e3)), p["lowpass_km"] / cells_km))
        ksn = np.where(land, ksn * scale, 0.0)
        z = np.where(land, zz * scale, 0.0)
        if p["smooth_px"]:
            z = np.where(land, ndi.gaussian_filter(z, p["smooth_px"]) * (1 - p["smooth_mix"]) + z * p["smooth_mix"], 0.0)
        log(f"   round {r + 1}: mean |lowpass(z) - lowpass(h0)| {np.abs(lp(z) - target)[land].mean():.1f} m ({time.time() - t0:.0f}s)")
    z = np.where(land, np.maximum(z + (target - lp(z)), 0.5), 0.0)
    return z, dict(params=p, seconds=time.time() - t0)


@numba.njit(cache=True)
def _integrate(order, recv, isbase, incr):
    zz = np.zeros(recv.shape[0])
    for k in range(order.shape[0]):
        c = order[k]
        if not isbase[c]:
            zz[c] = zz[recv[c]] + incr[c]
    return zz


@numba.njit(cache=True)
def _fall_along(z, order, recv, isbase, und, eps):
    """Raise any undrawn cell not above its receiver to receiver + eps (receivers first)."""
    zz = z.copy(); raised = 0
    for k in range(order.shape[0]):
        c = order[k]
        if isbase[c] or not und[c]:
            continue
        r = recv[c]
        if zz[c] <= zz[r] + 0.5 * eps:
            zz[c] = zz[r] + eps; raised += 1
    return zz, raised


def build():
    import terrain_erosion as TE
    import terrain_rivers as TR
    L, tops, h0, land, rivers = layers()
    H, W = land.shape; dx = 1.143 * 1609.344
    tier = L["tier"].astype(int)
    tree = np.load(ERO / "capped_tree.npz"); recv = tree["recv"].astype(np.int64)
    scan = json.loads((TR.OUT / "map_form_scan3.json").read_text()); form = scan["chosen"]
    plan = json.loads((ROOT / "calibration/geography_control_20261107/plan_B2.json").read_text())
    cs = plan["development_result"]["C_star"]
    hf = dict(json.loads((ERO / "hill_fit.json").read_text())["best"], height_m=scan["hill_height_m"])
    # composition as terrain_erosion.compose, with both steady-state runs on the capped tree
    prm = dict(cs, rounds=6, burn_m=4.0, lowpass_km=14.0)
    z, info = evolve_fixed(h0, land, rivers, dx, prm, recv)
    cells = dx / 1000.0
    lp = lambda a: ndi.gaussian_filter(np.where(land, a, 0.0), 14.0 / cells) / np.maximum(ndi.gaussian_filter(land.astype(float), 14.0 / cells), 1e-6)
    rng = np.random.default_rng(3)
    n = ndi.gaussian_filter(rng.standard_normal(land.shape), 80.0 / cells); n /= n.std()
    htarget = np.where(land, hf["height_m"] * np.exp(hf["sigma"] * n - 0.5 * hf["sigma"] ** 2), 0.0)
    zh, _ = evolve_fixed(htarget, land, rivers, dx, dict(TE.DEFAULTS, **prm), recv)
    hill = np.where(land, zh - lp(zh), 0.0)
    if hf.get("cap_m"):
        hill = np.where(hill > 0, hf["cap_m"] * np.tanh(hill / hf["cap_m"]), hill)
    hill = hill * TR.tier1_weight(tier)
    detail = z - lp(z); detail = np.where(detail > 0, 1500.0 * np.tanh(detail / 1500.0), detail)
    # the hill height was fitted on Earth to the lowland slope target (0.167 deg at 9 km); erosion on this drainage
    # makes gentler hills, so the hill amplitude is re-fitted to the same target (secant on the composition)
    def slope_of(f):
        zz = np.where(land, np.maximum(h0 + detail + f * hill, 0.5), 0.0)
        return float(np.median(TE.slopes_9km(zz, land, dx, tier, 1)))
    f0, f1 = 1.0, 2.0; s0, s1 = slope_of(f0), slope_of(f1)
    for _ in range(6):
        if abs(s1 - 0.167) < 0.002 or s1 == s0:
            break
        f0, f1, s0 = f1, max(0.2, f1 + (0.167 - s1) * (f1 - f0) / (s1 - s0)), s1; s1 = slope_of(f1)
    hill_factor = f1
    log(f"hill factor {hill_factor:.2f} -> composition tier-1 slope {s1:.3f}")
    z0 = np.where(land, np.maximum(h0 + detail + hill_factor * hill, 0.5), 0.0)
    lake = L["lake"].astype(bool) & ~land
    isbase, order, _ = tree_geometry(recv, land, W)
    und = (land & ~rivers).ravel()
    target14 = lp(h0)
    # the 14 km scale is corrected on the composition BEFORE the rivers are conditioned (so banks stay above beds),
    # iterated through the conditioning and the fall-along-tree fill
    for it in range(3):
        zc, rec, level = TR.condition(z0, land, rivers, ramp=h0, lake=lake, **form)
        zt, raised = _fall_along(np.where(land, zc, 0.0).ravel().astype(float), order, recv, isbase, und, EPS_M)
        zt = zt.reshape(H, W)
        err = np.abs(lp(zt) - target14)[land].mean(); log(f"   scale iteration {it + 1}: mean |lowpass error| {err:.1f} m")
        if it < 2:
            z0 = np.where(land, np.maximum(z0 + (target14 - lp(zt)), 0.5), 0.0)
    dz = (zt - zc)[land]
    z32 = np.where(land, zt, 0.0).astype(np.float32); lv32 = level.astype(np.float32)
    area = accumulate_tree(order, recv, land.ravel().astype(float) * dx * dx).reshape(H, W)
    # gates as v2.2 (terrain_rivers.build) plus the cap
    v22 = np.load(ERO / "map_height_v22.npz")
    strict = TR.strict_check(z32, land, rivers, lake=lake, level=lv32)
    c = TE.checks(z32.astype(float), h0, land, rivers, tier, tops, area, dx)
    c2 = TE.checks(np.asarray(v22["z"], float), h0, land, rivers, tier, tops, np.asarray(v22["area"], float), dx)
    c["tier1_slope_9km_median_deg"] = float(np.median(TE.slopes_9km(z32.astype(float), land, dx, tier, 1)))
    load = subtree_loads(recv, und); tj = json.loads((ERO / "capped_tree.json").read_text())
    gates = dict(owner_rivers=strict["passes"],
                 tier_bands_2_4=all(c["tier_band_share"][k] >= c2["tier_band_share"][k] - 0.02 for k in (2, 3, 4)),
                 climate_scale=c["climate_scale_mean_abs_m"] <= c2["climate_scale_mean_abs_m"] + 5.0,
                 lowland_slope=abs(c["tier1_slope_9km_median_deg"] / 0.167 - 1) <= 0.10,
                 undrawn_below_cap=bool((load[und] <= tj["cap_cells"]).all()))
    out = dict(tree=tj, gates=gates, strict=strict, tier_bands=(c["tier_band_share"], c2["tier_band_share"]),
               climate_scale=(c["climate_scale_mean_abs_m"], c2["climate_scale_mean_abs_m"]),
               tier1_slope=c["tier1_slope_9km_median_deg"], fall_along_tree_raised_cells=int(raised),
               fall_along_tree_raise_m={q: float(np.percentile(dz, q)) for q in (50, 90, 99, 100)},
               over_cap_cells=int((load[und] > tj["cap_cells"]).sum()), hill_factor=hill_factor, conditioning=rec)
    np.savez_compressed(ERO / "map_height_v23.npz", z=z32, area=area.astype(np.float32), tier_tops=np.asarray(tops, float),
                        lake_level=lv32, recv=recv)
    (ERO / "map_height_v23.json").write_text(json.dumps(out, indent=1, default=float))
    log(json.dumps(dict(gates=gates, tier_bands=out["tier_bands"], climate_scale=out["climate_scale"], tier1_slope=out["tier1_slope"],
                        raised=out["fall_along_tree_raise_m"], over_cap=out["over_cap_cells"]), indent=1, default=float))


if __name__ == "__main__":
    {"tree": capped_tree, "post": post, "build": build}[sys.argv[1]]()
