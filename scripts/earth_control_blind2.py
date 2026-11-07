"""Second blind Earth control test (calibration/earth_control_20261106/plan_blind2.json): CHGIS county seats
(Western Jin AD 280, Ming AD 1580) in the Han window, round-2 chain (scaled rural claim, P2) against transport only.

    .venv/bin/python -I scripts/earth_control_blind2.py run C1
    .venv/bin/python -I scripts/earth_control_blind2.py run C2
    .venv/bin/python -I scripts/earth_control_blind2.py score        # the single evaluation + decision
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/earth_control_20261106/plan_blind2.json"
OUT = ROOT / "output/earth_control_20261106/blind2"
CHGIS = ROOT / "data/cache/chgis_v6_20261107/shp/v6_time_cnty_pts_utf_wgs84"
CLIO = ROOT / "data/cache/cliopatria_full_20261107/cliopatria_polities_only_v021.geojson"
POOLS = {"C1": dict(year=280, names=("Western Jin", "Eastern Wu")), "C2": dict(year=1580, names=("Ming Dynasty",))}
FOOD_CASES = ["joint365", "fert_bare", "fert_legume"]
CENSUS = {"fert_bare": 0.459, "joint365": 0.538, "fert_legume": 0.685}
log = lambda *a: print(*a, flush=True)  # noqa: E731


def seats(year):
    import shapefile
    r = shapefile.Reader(str(CHGIS), encoding="utf-8")
    pts = [(float(x["Y_COOR"]), float(x["X_COOR"])) for x in r.records() if int(x["BEG_YR"]) <= year <= int(x["END_YR"])]
    return np.array(pts)


def target(g, year, names):
    from polity import earth as E
    d = json.loads(CLIO.read_text()); rings = []
    for f in d["features"]:
        p = f["properties"]
        if p["Name"] in names and p["FromYear"] <= year <= p["ToYear"] and f["geometry"]:
            geo = f["geometry"]; rings.extend([geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"])
    return E.inside_polygons(g, rings), len(rings)


def run(pool):
    import polity_earth_check as P
    import earth_control_round2 as R
    import earth_control_test as T
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    P.apply_sea()
    g = P.load_window("han")
    road = np.zeros(g["land"].shape, bool)
    world = P.world_of(g, road); land = world["land"]; W = land.shape[1]
    pts = seats(POOLS[pool]["year"])
    r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    nodes = np.unique((r * W + c)[ok]); nodes = nodes[land.ravel()[nodes]]
    inside, n_rings = target(g, POOLS[pool]["year"], POOLS[pool]["names"]); inside &= land
    log(f"{pool}: {len(pts)} seats, {ok.sum()} in window -> {len(nodes)} seat cells; target polygons {n_rings}")
    S_ = R.setup(g, nodes, road)
    ff = dict(np.load(T.OUT / "han_food.npz"))
    actives, info = {"reference": np.ones(len(nodes), bool)}, {}
    for case in FOOD_CASES:
        actives[case], info[case] = R.chain(S_, ff, ff["F_" + case], scaled=True)
    held = R.reach(g, S_, nodes, road, actives)
    eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
    v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], S_["st"]["paths"])
    band = land & (dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(land.shape) <= 15)
    np.savez_compressed(OUT / f"{pool}_masks.npz", band=band, inside=inside, land=land, legacy_0=held["reference"]["P1"],
                        **{f"{c}__{k}": m for c, d in held.items() for k, m in d.items()}, **{f"active__{c}": a for c, a in actives.items()})
    (OUT / f"{pool}_chain.json").write_text(json.dumps(dict(sources=int(len(nodes)), seats=int(len(pts)), chain=info), indent=1))
    log(f"{pool} run complete ({time.time() - t0:.0f}s); masks written, not scored")


def score():
    r_star = json.loads((ROOT / "output/earth_control_20261106/round2/results_round2.json").read_text())["selection"]["R_star"]
    res = dict(plan=str(PLAN.relative_to(ROOT)), R_star=r_star, pools={})
    for pool in POOLS:
        z = dict(np.load(OUT / f"{pool}_masks.npz")); band, inside = z["band"], z["inside"]

        def m1(h):
            tpr = float((h & inside & band).sum() / max((inside & band).sum(), 1)); tnr = float((~h & ~inside & band).sum() / max((~inside & band).sum(), 1))
            return dict(ba=0.5 * (tpr + tnr), tpr=tpr, tnr=tnr, held_km2=float((h & band).sum() * 81))
        out = dict(band_cells=int(band.sum()), inside_share=float((inside & band).sum() / max(band.sum(), 1)), legacy_0=m1(z["legacy_0"]))
        for c in FOOD_CASES:
            out[c] = dict(m1(z[f"{c}__{r_star}"]), staffed_share=float(z[f"active__{c}"].mean()))
        out["chain"] = json.loads((OUT / f"{pool}_chain.json").read_text())
        res["pools"][pool] = out
    gates = {c: dict(G1=all(res["pools"][p][c]["staffed_share"] >= 0.75 for p in POOLS),
                     G2=all(res["pools"][p][c]["ba"] >= res["pools"][p]["legacy_0"]["ba"] - 0.02 for p in POOLS), census_error=CENSUS[c])
             for c in FOOD_CASES}
    passing = [c for c in FOOD_CASES if gates[c]["G1"] and gates[c]["G2"]]
    res["decision"] = dict(gates=gates, passing=passing, default=min(passing, key=CENSUS.get) if passing else "legacy_0")
    (OUT / "results_blind2.json").write_text(json.dumps(res, indent=1))
    for p, o in res["pools"].items():
        log(f"== {p}: {o['chain']['sources']} seat cells; legacy_0 BA {o['legacy_0']['ba']:.3f} (TPR {o['legacy_0']['tpr']:.2f} TNR {o['legacy_0']['tnr']:.2f})")
        for c in FOOD_CASES:
            v = o[c]; log(f"   {c:12s} BA {v['ba']:.3f} (TPR {v['tpr']:.2f} TNR {v['tnr']:.2f}) staffed {v['staffed_share']:.0%}")
    log("decision:", json.dumps(res["decision"]))


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2]), "score": score}[sys.argv[1]]()
