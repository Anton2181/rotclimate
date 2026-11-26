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
    log(f"drawn rivers {n}; smallest catchment {cap_km2:.0f} km2 -> cap {cap} cells; flow cap {CAP_FLOW}")
    und = (land & ~rivers).ravel(); zc = h0.ravel().astype(float)
    ids = -np.ones(N, np.int64); ids[und] = np.arange(und.sum()); M = int(und.sum()); SINK = 2 * M
    cells = np.flatnonzero(und); yy, xx = np.divmod(cells, W)
    T = [np.arange(M)]; Hh = [np.arange(M) + M]; C = [np.full(M, CAP_FLOW)]; Co = [np.zeros(M, np.int64)]
    for k in range(8):
        dy, dx = NB[k]; ny_, nx_ = yy + dy, xx + dx; step = 14 if dy and dx else 10
        inside = (ny_ >= 0) & (ny_ < H) & (nx_ >= 0) & (nx_ < W)
        j = np.where(inside, ny_ * W + nx_, 0)
        to_out = ~inside | (inside & ~und[j]); to_und = inside & und[j]
        T.append(ids[cells[to_out]] + M); Hh.append(np.full(to_out.sum(), SINK)); C.append(np.full(to_out.sum(), CAP_FLOW)); Co.append(np.full(to_out.sum(), step, np.int64))
        up = np.maximum(zc[j[to_und]] - zc[cells[to_und]], 0.0)
        T.append(ids[cells[to_und]] + M); Hh.append(ids[j[to_und]]); C.append(np.full(to_und.sum(), CAP_FLOW)); Co.append((step + np.round(WZ * up)).astype(np.int64))
    T, Hh, C, Co = (np.concatenate(a) for a in (T, Hh, C, Co))
    smcf = min_cost_flow.SimpleMinCostFlow()
    arcs = smcf.add_arcs_with_capacity_and_unit_cost(T, Hh, C, Co)
    sup = np.zeros(2 * M + 1, np.int64); sup[:M] = 1; sup[SINK] = -M
    smcf.set_nodes_supplies(np.arange(2 * M + 1), sup)
    t0 = time.time(); st = smcf.solve(); log(f"min-cost flow {st} in {time.time() - t0:.0f}s ({len(T)} arcs)")
    if st != smcf.OPTIMAL:
        raise SystemExit("min-cost flow not optimal: raise CAP_FLOW")
    f = smcf.flows(arcs)[M:]; t = T[M:] - M; h = Hh[M:]
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
    z0 = np.where(land, np.maximum(h0 + detail + hill, 0.5), 0.0)
    lake = L["lake"].astype(bool) & ~land
    zc, rec, level = TR.condition(z0, land, rivers, ramp=h0, lake=lake, **form)
    # elevations fall strictly along the stored tree (undrawn cells only; drawn rivers and lakes as conditioned)
    isbase, order, _ = tree_geometry(recv, land, W)
    und = (land & ~rivers).ravel()
    zt, raised = _fall_along(np.where(land, zc, 0.0).ravel().astype(float), order, recv, isbase, und, EPS_M)
    zt = zt.reshape(H, W); dz = (zt - zc)[land]
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
                 undrawn_below_smallest_drawn=bool((load[und] <= tj["cap_cells"]).all()))
    out = dict(tree=tj, gates=gates, strict=strict, tier_bands=(c["tier_band_share"], c2["tier_band_share"]),
               climate_scale=(c["climate_scale_mean_abs_m"], c2["climate_scale_mean_abs_m"]),
               tier1_slope=c["tier1_slope_9km_median_deg"], fall_along_tree_raised_cells=int(raised),
               fall_along_tree_raise_m={q: float(np.percentile(dz, q)) for q in (50, 90, 99, 100)},
               over_cap_cells=int((load[und] > tj["cap_cells"]).sum()), conditioning=rec)
    np.savez_compressed(ERO / "map_height_v23.npz", z=z32, area=area.astype(np.float32), tier_tops=np.asarray(tops, float),
                        lake_level=lv32, recv=recv)
    (ERO / "map_height_v23.json").write_text(json.dumps(out, indent=1, default=float))
    log(json.dumps(dict(gates=gates, tier_bands=out["tier_bands"], climate_scale=out["climate_scale"], tier1_slope=out["tier1_slope"],
                        raised=out["fall_along_tree_raise_m"], over_cap=out["over_cap_cells"]), indent=1, default=float))


if __name__ == "__main__":
    {"tree": capped_tree, "build": build}[sys.argv[1]]()
