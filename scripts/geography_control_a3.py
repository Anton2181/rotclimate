"""Plan A3 (calibration/geography_control_20261107/plan_A3.json): enclosed desert or empty pockets stay holes.

    .venv/bin/python -I scripts/geography_control_a3.py prep rome|han|T3|T4|T5    # masks and pocket fields, nothing scored
    .venv/bin/python -I scripts/geography_control_a3.py dev                      # development report
    .venv/bin/python -I scripts/geography_control_a3.py blind                    # the single blind evaluation
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/geography_control_a3_20261107"
PLAN = ROOT / "calibration/geography_control_20261107/plan_A3.json"
AI_DESERT = 0.2
EMPTY_DENSITY = 0.5
log = lambda *a: print(*a, flush=True)  # noqa: E731


def aridity(g):
    import land_people_earth as LPE
    from land_people import hargreaves, sunlight_top
    T = g["tavg"].astype(float); P = g["prec"].astype(float); D = (g["tmax"] - g["tmin"]).astype(float)
    PET = hargreaves(T.reshape(12, -1), D.reshape(12, -1), sunlight_top(g["lat"].ravel(), LPE.TILT, LPE.WS_DAY)).reshape(T.shape)
    return P.sum(0) / np.maximum(PET.sum(0), 1e-6)


def hole_rule(held, land, ai, density):
    """v2.1 pockets split into territory pockets and desert / empty holes (plan_A3 rule)."""
    import geography_control_a as A
    from scipy import ndimage as ndi
    pk, lab, ok = A.pockets(held, land)
    holes = np.zeros_like(held)
    for k in np.flatnonzero(ok):
        m = lab == k
        if np.median(ai[m]) < AI_DESERT or np.median(density[m]) < EMPTY_DENSITY:
            holes |= m
    return pk, holes


def prep(pool):
    import polity_earth_check as P
    import earth_control_round2 as R
    import earth_control_test as T
    import geography_control_a2 as A2
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    OUT.mkdir(parents=True, exist_ok=True); t0 = time.time()
    g, road, nodes, inside, band, window = A2.pool_inputs(pool)
    S_ = R.setup(g, nodes, road); land, shp = S_["land"], S_["shape"]; W = shp[1]; world = S_["world"]
    ff = dict(np.load(T.OUT / f"{window}_food.npz"))
    staffed_mask, info = R.chain(S_, ff, ff["F_joint365"], scaled=True); staffed = nodes[staffed_mask]
    if band is None:
        eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
        v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], S_["st"]["paths"])
        band = land & (dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(shp) <= 15)
    places = [(int(v) // W, int(v) % W) for v in nodes]
    nets = A2.nets_with(g, world, places, 1.0)
    roads = np.flatnonzero(road.ravel() & land.ravel())
    d1 = P.year_days(nets, staffed).ravel(); near = roads[d1[roads] <= 2.0] if len(roads) else roads
    held = (P.year_days(nets, np.unique(np.r_[staffed, near])).ravel() <= 2.0).reshape(shp) & land
    np.savez_compressed(OUT / f"{pool}.npz", land=land, inside=inside & land, band=band, held=held,
                        ai=aridity(g).astype(np.float32), density=np.asarray(g["density"], np.float32))
    (OUT / f"{pool}_info.json").write_text(json.dumps(dict(sources=int(len(nodes)), staffed=int(len(staffed)), chain=info), indent=1))
    log(f"{pool} prep complete ({time.time() - t0:.0f}s); not scored")


def score(pool):
    import geography_control_a as A
    z = dict(np.load(OUT / f"{pool}.npz"))
    pk, holes = hole_rule(z["held"], z["land"], z["ai"], z["density"])
    v21 = z["held"] | pk; a3 = v21 & ~holes
    return dict(v21=A.balanced_accuracy(v21, z["inside"], z["band"]), A3=A.balanced_accuracy(a3, z["inside"], z["band"]),
                pockets_cells=int(pk.sum()), hole_cells=int(holes.sum()), territory_cells=int(v21.sum()))


def dev():
    res = dict(plan=str(PLAN.relative_to(ROOT)), pools={p: score(p) for p in ("rome", "han")})
    (OUT / "dev.json").write_text(json.dumps(res, indent=1)); log(json.dumps(res, indent=1))


def blind():
    res = dict(plan=str(PLAN.relative_to(ROOT)), pools={p: dict(score(p), info=json.loads((OUT / f"{p}_info.json").read_text())) for p in ("T3", "T4", "T5")})
    g1 = all(o["A3"]["ba"] >= o["v21"]["ba"] - 0.01 for o in res["pools"].values())
    res["gates"] = dict(G1=bool(g1)); res["adopt"] = bool(g1)
    (OUT / "blind.json").write_text(json.dumps(res, indent=1))
    for p, o in res["pools"].items():
        log(f"{p}: v2.1 BA {o['v21']['ba']:.3f} | A3 BA {o['A3']['ba']:.3f}; pockets {o['pockets_cells']:,} cells, of which holes {o['hole_cells']:,}")
    log("gates:", res["gates"], "adopt:", res["adopt"])


if __name__ == "__main__":
    {"prep": lambda: prep(sys.argv[2]), "dev": dev, "blind": blind}[sys.argv[1]]()
