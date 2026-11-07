"""Workstream A2 (calibration/geography_control_20261107/plan_A2.json): a ruggedness-sensitive travel cost, eta x
(1 + beta x R) with R the local relief in km, under the adopted control rule v2.1 (P2 held + enclosed pockets).

    .venv/bin/python -I scripts/geography_control_a2.py prep rome     # development (seen)
    .venv/bin/python -I scripts/geography_control_a2.py prep han
    .venv/bin/python -I scripts/geography_control_a2.py dev          # choose beta*
    .venv/bin/python -I scripts/geography_control_a2.py prep T3      # blind pools: masks only, nothing scored
    .venv/bin/python -I scripts/geography_control_a2.py prep T4
    .venv/bin/python -I scripts/geography_control_a2.py prep T5
    .venv/bin/python -I scripts/geography_control_a2.py blind        # the single blind evaluation
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/geography_control_a2_20261107"
PLAN = ROOT / "calibration/geography_control_20261107/plan_A2.json"
BETAS = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def seats_year(year):
    import shapefile
    import earth_control_blind2 as B2
    r = shapefile.Reader(str(B2.CHGIS), encoding="utf-8")
    return np.array([(float(x["Y_COOR"]), float(x["X_COOR"])) for x in r.records()
                     if int(x["BEG_YR"]) <= year <= int(x["END_YR"]) and x["Y_COOR"] is not None and x["X_COOR"] is not None])


def pool_inputs(pool):
    import polity_earth_check as P
    import earth_control_blind as B1
    import geography_control_a as A
    from polity import earth as E
    if pool in ("rome", "han"):
        g, road, nodes, inside, band, window = A._pool_inputs(pool)
        return g, road, nodes, inside, band, window
    P.apply_sea()
    year, window = {"T3": (1200, "han"), "T4": (1820, "han"), "T5": (1500, "rome")}[pool]
    g = P.load_window(window); land0 = g["land"].astype(bool); W = land0.shape[1]
    road = (E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land0) if window == "rome" else np.zeros(land0.shape, bool)
    if pool == "T5":
        import pandas as pd
        d = pd.read_stata(ROOT / "data/cache/bosker_cities_20261107/cities.tab"); y = d[(d["year"] == 1500) & (d["citypop_le5"] > 0)]
        pts = np.c_[y["latitude"].values.astype(float), y["longitude"].values.astype(float)]
    else:
        pts = seats_year(year)
    r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    world0 = P.world_of(g, road)
    nodes = np.unique((r * W + c)[ok]); nodes = nodes[world0["land"].ravel()[nodes]]
    inside, _ = B1.target(g, year)
    return g, road, nodes, inside & world0["land"], None, window


def nets_with(g, world, places, factor):
    from polity import network as N, transport as X
    st = N.statics(world); st["eta"] = st["eta"] * factor
    cl = N.climate(world, st)
    ports = X.ports_of(places, st["water"])
    near_river = ndi.binary_dilation(st["basin"] > 0, iterations=1)
    river_places = [(y, x) for y, x in places if near_river[y, x]]
    return [N.month_network(world, st, cl, m, ports, river_places) for m in range(12)]


def enrich(mask, land, band, features):
    border = mask & ndi.binary_dilation(~mask & land, np.ones((3, 3))) & band
    if not border.any():
        return {k: None for k in features}
    ring = land & band & (ndi.distance_transform_edt(~border) <= 33)
    return {k: float(f[border].mean() / max(f[ring].mean(), 1e-9)) for k, f in features.items()}


def shape_distance(model, target):
    v = [abs(np.log(max(model[k], 1e-3) / max(target[k], 1e-3))) for k in target if model.get(k) is not None and target[k] is not None]
    return float(np.mean(v)) if v else None


def prep(pool):
    import polity_earth_check as P
    import earth_control_round2 as R
    import earth_control_test as T
    import geography_control_a as A
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    g, road, nodes, inside, band, window = pool_inputs(pool)
    S_ = R.setup(g, nodes, road); land, shp = S_["land"], S_["shape"]; W = shp[1]; world = S_["world"]
    ff = dict(np.load(T.OUT / f"{window}_food.npz"))
    staffed_mask, info = R.chain(S_, ff, ff["F_joint365"], scaled=True); staffed = nodes[staffed_mask]
    if band is None:
        eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
        v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], S_["st"]["paths"])
        band = land & (dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(shp) <= 15)
    relief_km = np.clip(np.asarray(g["relief"], float), 0, 4000) / 1000.0
    places = [(int(v) // W, int(v) % W) for v in nodes]
    roads = np.flatnonzero(road.ravel() & land.ravel())
    P_ann = g["prec"].sum(0); arid = (P_ann < 250) & land
    feats = dict(desert=ndi.binary_dilation(arid, np.ones((5, 5))) & ndi.binary_dilation(~arid & land, np.ones((5, 5))),
                 high_relief=relief_km * 1000 > np.percentile(relief_km[land] * 1000, 75),
                 river=ndi.distance_transform_edt(~g["river"].astype(bool)) * float(world["cell_km"]) <= 18)
    masks = {}
    for beta in BETAS:
        nets = nets_with(g, world, places, 1.0 + beta * relief_km)
        d1 = P.year_days(nets, staffed).ravel(); near = roads[d1[roads] <= 2.0] if len(roads) else roads
        held = (P.year_days(nets, np.unique(np.r_[staffed, near])).ravel() <= 2.0).reshape(shp) & land
        masks[beta] = held | A.pockets(held, land)[0]
        log(f"{pool} beta {beta}: territory {masks[beta].sum():,} cells ({time.time() - t0:.0f}s)")
    np.savez_compressed(OUT / f"{pool}.npz", land=land, inside=inside & land, band=band,
                        **{f"terr_{b}": m for b, m in masks.items()}, **{f"feat_{k}": f for k, f in feats.items()})
    (OUT / f"{pool}_info.json").write_text(json.dumps(dict(sources=int(len(nodes)), staffed=int(len(staffed)), chain=info), indent=1))
    log(f"{pool} prep complete ({time.time() - t0:.0f}s); not scored")


def score_pool(pool):
    import geography_control_a as A
    z = dict(np.load(OUT / f"{pool}.npz")); feats = {k[5:]: z[k] for k in z if k.startswith("feat_")}
    target = enrich(z["inside"], z["land"], z["band"], feats)
    out = dict(target=target)
    for b in BETAS:
        m = z[f"terr_{b}"]; e = enrich(m, z["land"], z["band"], feats)
        out[str(b)] = dict(**A.balanced_accuracy(m, z["inside"], z["band"]), enrichment=e, D=shape_distance(e, target))
    return out


def dev():
    res = dict(plan=str(PLAN.relative_to(ROOT)), pools={p: score_pool(p) for p in ("rome", "han")})
    mean = {str(b): float(np.mean([res["pools"][p][str(b)]["ba"] for p in res["pools"]])) for b in BETAS}
    best = max(mean.values()); tied = [b for b in BETAS if mean[str(b)] >= best - 0.002]
    relief_gap = lambda b: float(np.mean([abs(np.log(max(res["pools"][p][str(b)]["enrichment"]["high_relief"], 1e-3) /
                                                   max(res["pools"][p]["target"]["high_relief"], 1e-3))) for p in res["pools"]]))
    res["mean_ba"] = mean; res["beta_star"] = min(tied, key=relief_gap)
    (OUT / "dev.json").write_text(json.dumps(res, indent=1))
    for p, o in res["pools"].items():
        log(f"== {p}: target enrichment {o['target']}")
        for b in BETAS:
            v = o[str(b)]; log(f"   beta {b}: BA {v['ba']:.3f} (TPR {v['tpr']:.2f} TNR {v['tnr']:.2f}) D {v['D']:.3f} enrichment {v['enrichment']}")
    log("mean BA", {k: round(v, 4) for k, v in mean.items()}, "beta* =", res["beta_star"])


def blind():
    bstar = json.loads((OUT / "dev.json").read_text())["beta_star"]
    res = dict(plan=str(PLAN.relative_to(ROOT)), beta_star=bstar, pools={})
    for p in ("T3", "T4", "T5"):
        o = score_pool(p); res["pools"][p] = dict(target=o["target"], base=o["0.0"], cand=o[str(bstar)],
                                                  info=json.loads((OUT / f"{p}_info.json").read_text()))
    P = res["pools"]
    g1 = all(P[p]["cand"]["ba"] >= P[p]["base"]["ba"] - 0.01 for p in P)
    g2 = sum((P[p]["cand"]["D"] is not None and P[p]["base"]["D"] is not None and P[p]["cand"]["D"] < P[p]["base"]["D"]) for p in P) >= 2
    res["gates"] = dict(G1=bool(g1), G2=bool(g2)); res["adopt"] = bool(g1 and g2)
    (OUT / "blind.json").write_text(json.dumps(res, indent=1))
    for p, o in P.items():
        log(f"== {p}: {o['info']['sources']} sources, {o['info']['staffed']} staffed; target enrichment {o['target']}")
        for k in ("base", "cand"):
            v = o[k]; log(f"   {k}: BA {v['ba']:.3f} (TPR {v['tpr']:.2f} TNR {v['tnr']:.2f}) D {v['D']} enrichment {v['enrichment']}")
    log("gates:", res["gates"], "adopt:", res["adopt"])


if __name__ == "__main__":
    {"prep": lambda: prep(sys.argv[2]), "dev": dev, "blind": blind}[sys.argv[1]]()
