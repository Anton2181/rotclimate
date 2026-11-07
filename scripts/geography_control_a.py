"""Workstream A of reports/GEOGRAPHY_CONTROL_PLAN_20261107.md (calibration/geography_control_20261107/plan_A.json):
summed influence instead of one 2-day disc per staffed town, and enclosed pockets as territory.

    .venv/bin/python -I scripts/geography_control_a.py prep rome      # development pools (seen)
    .venv/bin/python -I scripts/geography_control_a.py prep han
    .venv/bin/python -I scripts/geography_control_a.py dev            # fit the A1 grid on rome + han, choose C*
    .venv/bin/python -I scripts/geography_control_a.py prep T1        # blind pools: grip fields and masks, nothing scored
    .venv/bin/python -I scripts/geography_control_a.py prep T2
    .venv/bin/python -I scripts/geography_control_a.py blind          # the single blind evaluation

prep writes output/geography_control_20261107/<pool>.npz: the grip fields G[tau, mass], v2's mask, the kept-road
corridor, the target, band and terrain fields. Shared helpers (grip, pockets, shape) are reused for the atlas.
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/geography_control_20261107"
PLAN = ROOT / "calibration/geography_control_20261107/plan_A.json"
TAUS = (0.5, 1.0, 2.0)
R0S = (1.0, 1.5, 2.0, 2.5, 3.0)
MASSES = ("equal", "residents")
LIMIT_DAYS = 12.0
FOREST = (3, 4, 7, 9)              # rotclimate.biomes forest codes (harvest.models.FOREST_SHARE, whole forests)
log = lambda *a: print(*a, flush=True)  # noqa: E731


# ----------------------------------------------------------------------------------------------- shared helpers
def _bases(net):
    """(fair, beat, spell) CSR graphs of a monthly network; beat is None for a plain Network."""
    if hasattr(net, "fair"):
        return net.fair.base, net.beat.base, net.spell
    return net.base, None, None


def grip(nets, sites, masses, taus=TAUS, limit=LIMIT_DAYS, chunk=24, n_cells=None):
    """G[tau][mass] = sum_s w_s mean_m exp(-d_s,m / tau) over the cells, d the monthly days from each site."""
    from scipy.sparse.csgraph import dijkstra
    sites = np.asarray(sites, np.int64); n_cells = n_cells or nets[0].n_cells
    G = {t: {k: np.zeros(n_cells) for k in masses} for t in taus}
    for net in nets:
        fair, beat, spell = _bases(net)
        for s0 in range(0, len(sites), chunk):
            idx = sites[s0:s0 + chunk]
            d = dijkstra(fair, directed=True, indices=idx, limit=limit)[:, :n_cells]
            if beat is not None:
                db = dijkstra(beat, directed=True, indices=idx, limit=limit)[:, :n_cells]
                with np.errstate(invalid="ignore", divide="ignore"):
                    w = np.clip(1.0 - spell / np.maximum(d, 1e-9), 0.0, 1.0)
                    d = np.where(np.isfinite(d) & np.isfinite(db), d + (db - d) * w, np.where(np.isfinite(d), d, db))
            for t in taus:
                e = np.exp(-d / t); e[~np.isfinite(d)] = 0.0
                for k, wk in masses.items():
                    G[t][k] += (wk[s0:s0 + chunk, None] * e).sum(0) / len(nets)
    return G


def pockets(held, land, other=None):
    """Unheld land pockets bounded only by held land and sea (not the edge, not `other` states' land)."""
    un = land & ~held
    lab, n = ndi.label(un, structure=np.ones((3, 3)))
    if not n:
        return np.zeros_like(held), lab, np.zeros(0, bool)
    bad = np.zeros(n + 1, bool)
    bad[np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])] = True
    if other is not None:
        touch = ndi.binary_dilation(other, np.ones((3, 3))) & un
        bad[np.unique(lab[touch])] = True
    bad[0] = True
    return ~bad[lab] & un, lab, ~bad


def governable(pocket_lab, ok_ids, held, slope, forest, density):
    """Pockets whose median slope, forest share and food density lie in held land's Earth range (plan A2)."""
    s90, f90, d10 = (np.percentile(slope[held], 90), np.percentile(forest[held], 90), np.percentile(density[held], 10))
    gov = np.zeros_like(held)
    for k in np.flatnonzero(ok_ids):
        m = pocket_lab == k
        if np.median(slope[m]) <= s90 and np.median(forest[m]) <= f90 and np.median(density[m]) >= d10:
            gov |= m
    return gov


def shape(held, land, territory=None, desert=None, relief_hi=None, river_near=None):
    """Shape metrics of a held mask (plan_A metrics.shape_reported)."""
    out = {}
    terr = held if territory is None else territory
    out["hole_share"] = float((terr & ~held).sum() / max(terr.sum(), 1))
    lab, n = ndi.label(held, structure=np.ones((3, 3)))
    if n:
        size = ndi.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
        edge = held & ~ndi.binary_erosion(held, np.ones((3, 3)))
        per = ndi.sum(edge.astype(float), lab, index=np.arange(1, n + 1))
        small = (size >= 20) & (size <= 2000)
        out["small_patches"] = int(small.sum())
        out["small_circularity_median"] = float(np.median(4 * np.pi * size[small] / np.maximum(per[small], 1) ** 2)) if small.any() else None
    else:
        out["small_patches"] = 0; out["small_circularity_median"] = None
    t_edge = terr & ~ndi.binary_erosion(terr, np.ones((3, 3)))
    out["boundary_per_cell"] = float(t_edge.sum() / max(terr.sum(), 1))
    if desert is not None:
        border = terr & ndi.binary_dilation(~terr & land, np.ones((3, 3)))
        ring = land & (ndi.distance_transform_edt(~border) <= 33)
        if border.any():
            out["enrichment"] = {k: float(m[border].mean() / max(m[ring].mean(), 1e-9)) for k, m in
                                 (("desert_edge", desert), ("high_relief", relief_hi), ("river", river_near))}
    return out


def balanced_accuracy(h, inside, band):
    tpr = float((h & inside & band).sum() / max((inside & band).sum(), 1)); tnr = float((~h & ~inside & band).sum() / max((~inside & band).sum(), 1))
    return dict(ba=0.5 * (tpr + tnr), tpr=tpr, tnr=tnr)


# ----------------------------------------------------------------------------------------------- Earth pools
def _pool_inputs(pool):
    import polity_earth_check as P
    import earth_control_test as T
    import earth_control_blind as B1
    import earth_control_blind2 as B2
    from polity import earth as E
    P.apply_sea()
    if pool in ("rome", "han"):
        g = P.load_window(pool); land0 = g["land"].astype(bool)
        road = (E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land0) if pool == "rome" else np.zeros(land0.shape, bool)
        nodes, _, _ = T.sources(pool, g)
        world0 = P.world_of(g, road); nodes = nodes[world0["land"].ravel()[nodes]]
        z = dict(np.load(ROOT / f"output/earth_control_20261106/round2/{pool}.npz"))
        return g, road, nodes, z["inside"], z["band"], pool
    year, window = {"T1": (1080, "han"), "T2": (550, "rome")}[pool]
    g = P.load_window(window); land0 = g["land"].astype(bool); W = land0.shape[1]
    road = (E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land0) if window == "rome" else np.zeros(land0.shape, bool)
    pts = B2.seats(year) if pool == "T1" else B1.pleiades({"late-antique"})
    r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    world0 = P.world_of(g, road)
    nodes = np.unique((r * W + c)[ok]); nodes = nodes[world0["land"].ravel()[nodes]]
    inside, _ = B1.target(g, year)
    return g, road, nodes, inside & world0["land"], None, window


def prep(pool):
    import polity_earth_check as P
    import earth_control_round2 as R
    import earth_control_test as T
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    g, road, nodes, inside, band, window = _pool_inputs(pool)
    S_ = R.setup(g, nodes, road); land, shp = S_["land"], S_["shape"]; W = shp[1]
    ff = dict(np.load(T.OUT / f"{window}_food.npz"))
    staffed_mask, info = R.chain(S_, ff, ff["F_joint365"], scaled=True)
    staffed = nodes[staffed_mask]; req = S_["request"][staffed_mask]
    log(f"{pool}: {len(nodes)} sources, {len(staffed)} staffed (joint365, L1) ({time.time() - t0:.0f}s)")
    if band is None:
        world = S_["world"]; eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
        v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], S_["st"]["paths"])
        band = land & (dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(shp) <= 15)
    places = [(int(v) // W, int(v) % W) for v in nodes]
    _, _, nets = P.monthly_nets(g, S_["world"], places)
    d1 = P.year_days(nets, staffed).ravel()
    roads = np.flatnonzero(road.ravel() & land.ravel()); near = roads[d1[roads] <= 2.0] if len(roads) else roads
    v2 = (P.year_days(nets, np.unique(np.r_[staffed, near])).ravel() <= 2.0).reshape(shp) & land
    corridor = ((P.year_days(nets, near).ravel() <= 2.0).reshape(shp) & land) if len(near) else np.zeros(shp, bool)
    log(f"{pool}: v2 and road corridor ({time.time() - t0:.0f}s); grip from {len(staffed)} sites x 12 months")
    masses = {"equal": np.ones(len(staffed)), "residents": req / max(np.median(req), 1e-9)}
    G = grip(nets, staffed, masses, n_cells=land.size)
    log(f"{pool}: grip done ({time.time() - t0:.0f}s)")
    elev = np.asarray(S_["world"]["elev"], float); km = float(S_["world"]["cell_km"])
    gy, gx = np.gradient(elev, km * 1000); slope = np.degrees(np.arctan(np.hypot(gy, gx)))
    forest = np.isin(np.asarray(S_["world"]["biome"]), FOREST).astype(float)
    P_ann = g["prec"].sum(0); arid = (P_ann < 250) & land
    desert = ndi.binary_dilation(arid, np.ones((5, 5))) & ndi.binary_dilation(~arid & land, np.ones((5, 5)))
    relief = g["relief"]; river_near = ndi.distance_transform_edt(~g["river"].astype(bool)) * km <= 18
    np.savez_compressed(OUT / f"{pool}.npz", land=land, inside=inside & land, band=band, v2=v2, corridor=corridor,
                        slope=slope.astype(np.float32), forest=forest.astype(np.float32), density=np.asarray(g["density"], np.float32),
                        desert=desert, relief=relief.astype(np.float32), river_near=river_near,
                        **{f"G_{t}_{k}": G[t][k].reshape(shp).astype(np.float32) for t in TAUS for k in masses})
    (OUT / f"{pool}_info.json").write_text(json.dumps(dict(sources=int(len(nodes)), staffed=int(len(staffed)), chain=info,
                                                           kept_road_cells=int(len(near))), indent=1))
    log(f"{pool} prep complete ({time.time() - t0:.0f}s); not scored")


def settings():
    return [dict(tau=t, r0=r, mass=k, roads=rd) for t, r, k, rd in itertools.product(TAUS, R0S, MASSES, (False, True))]


def evaluate(z, s):
    land = z["land"]
    held = (z[f"G_{s['tau']}_{s['mass']}"] >= np.exp(-s["r0"] / s["tau"])) & land
    if s["roads"]:
        held |= z["corridor"]
    return held


def score_pool(z, held):
    land = z["land"]; terr = held | pockets(held, land)[0]
    hi = z["relief"] > np.percentile(z["relief"][land], 75)
    return dict(**balanced_accuracy(terr, z["inside"], z["band"]),
                shape=shape(held, land, terr, z["desert"], hi, z["river_near"]))


def dev():
    pools = {p: dict(np.load(OUT / f"{p}.npz")) for p in ("rome", "han")}
    res = dict(plan=str(PLAN.relative_to(ROOT)), baseline={}, fallback={}, settings=[])
    for p, z in pools.items():
        res["baseline"][p] = dict(**balanced_accuracy(z["v2"], z["inside"], z["band"]))
        res["fallback"][p] = score_pool(z, z["v2"])
        hi = z["relief"] > np.percentile(z["relief"][z["land"]], 75)
        res.setdefault("target_shape", {})[p] = shape(z["inside"] & z["band"], z["land"], None, z["desert"], hi, z["river_near"])
    for s in settings():
        row = dict(s, pools={p: score_pool(z, evaluate(z, s)) for p, z in pools.items()})
        row["mean_ba"] = float(np.mean([row["pools"][p]["ba"] for p in pools]))
        row["small_patches"] = int(sum(row["pools"][p]["shape"]["small_patches"] for p in pools))
        res["settings"].append(row)
    best = max(r["mean_ba"] for r in res["settings"])
    tied = [r for r in res["settings"] if r["mean_ba"] >= best - 0.002]
    cstar = min(tied, key=lambda r: (r["small_patches"], -r["mean_ba"]))
    res["C_star"] = {k: cstar[k] for k in ("tau", "r0", "mass", "roads", "mean_ba")}
    res["fallback_mean_ba"] = float(np.mean([res["fallback"][p]["ba"] for p in pools]))
    res["baseline_mean_ba"] = float(np.mean([res["baseline"][p]["ba"] for p in pools]))
    (OUT / "dev.json").write_text(json.dumps(res, indent=1))
    log("v2 (no pockets) mean BA", round(res["baseline_mean_ba"], 4), "| v2 + A2 (F)", round(res["fallback_mean_ba"], 4))
    for r in sorted(res["settings"], key=lambda r: -r["mean_ba"])[:8]:
        log({k: r[k] for k in ("tau", "r0", "mass", "roads")}, "mean BA", round(r["mean_ba"], 4), "small patches", r["small_patches"],
            {p: round(r["pools"][p]["ba"], 3) for p in pools})
    log("C* =", res["C_star"])
    for p in pools:
        log(p, "v2 shape", res["fallback"][p]["shape"], "\n   C* shape", next(r for r in res["settings"] if all(r[k] == res["C_star"][k] for k in ("tau", "r0", "mass", "roads")))["pools"][p]["shape"],
            "\n   target", res["target_shape"][p])


def blind():
    d = json.loads((OUT / "dev.json").read_text()); cs = d["C_star"]
    res = dict(plan=str(PLAN.relative_to(ROOT)), C_star=cs, pools={})
    for p in ("T1", "T2"):
        z = dict(np.load(OUT / f"{p}.npz"))
        hi = z["relief"] > np.percentile(z["relief"][z["land"]], 75)
        res["pools"][p] = dict(v2=dict(**balanced_accuracy(z["v2"], z["inside"], z["band"]),
                                       shape=shape(z["v2"], z["land"], None, z["desert"], hi, z["river_near"])),
                               F=score_pool(z, z["v2"]), C_star=score_pool(z, evaluate(z, cs)),
                               target_shape=shape(z["inside"] & z["band"], z["land"], None, z["desert"], hi, z["river_near"]),
                               info=json.loads((OUT / f"{p}_info.json").read_text()))
    g1 = {k: all(res["pools"][p][k]["ba"] >= res["pools"][p]["v2"]["ba"] - 0.01 for p in ("T1", "T2")) for k in ("C_star", "F")}
    res["gates"] = dict(G1_C_star=g1["C_star"], G1_F=g1["F"])
    res["adopt"] = "C_star" if g1["C_star"] else ("F" if g1["F"] else "v2 + A4 only")
    (OUT / "blind.json").write_text(json.dumps(res, indent=1))
    for p, o in res["pools"].items():
        log(f"== {p}: {o['info']['sources']} sources, {o['info']['staffed']} staffed")
        for k in ("v2", "F", "C_star"):
            log(f"   {k:7s} BA {o[k]['ba']:.3f} (TPR {o[k]['tpr']:.2f} TNR {o[k]['tnr']:.2f})  shape {o[k]['shape']}")
        log("   target shape", o["target_shape"])
    log("gates:", res["gates"], "adopt:", res["adopt"])


if __name__ == "__main__":
    {"prep": lambda: prep(sys.argv[2]), "dev": dev, "blind": blind}[sys.argv[1]]()
