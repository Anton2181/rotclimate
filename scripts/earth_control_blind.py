"""Blind Earth control test (calibration/earth_control_20261106/plan_blind.json).

    .venv/bin/python -I scripts/earth_control_blind.py prepare B1     # window, sources, target, food (no outcome)
    .venv/bin/python -I scripts/earth_control_blind.py prepare B2
    .venv/bin/python -I scripts/earth_control_blind.py run B1         # chain + reach (writes masks, no scores printed)
    .venv/bin/python -I scripts/earth_control_blind.py run B2
    .venv/bin/python -I scripts/earth_control_blind.py score          # the single evaluation + decision
"""
from __future__ import annotations

import csv
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/earth_control_20261106/plan_blind.json"
OUT = ROOT / "output/earth_control_20261106/blind"
PLEIADES = ROOT / "data/cache/pleiades_20261107/pleiades-places-latest.csv.gz"
CLIO = ROOT / "data/cache/cliopatria_full_20261107/cliopatria_polities_only_v021.geojson"
POOLS = {"B1": dict(key="B1_hellenistic_200BC", tags={"hellenistic-republican", "hellenistic-middle-east"}, year=-200),
         "B2": dict(key="B2_neo_assyrian_700BC", tags={"neo-assyrian-babylonian-middle-east", "early-1st-millennium-mesopotamia"}, year=-700)}
FOOD_CASES = ["joint365", "fert_bare", "fert_legume"]
CENSUS = {"fert_bare": 0.459, "joint365": 0.538, "fert_legume": 0.685}
log = lambda *a: print(*a, flush=True)  # noqa: E731


def pleiades(tags):
    pts = []
    with gzip.open(PLEIADES, "rt", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            ft = {t.strip() for t in (r["featureTypes"] or "").split(",")}
            per = {t.strip() for t in (r["timePeriodsKeys"] or "").split(",")}
            if "settlement" in ft and per & tags and r["locationPrecision"] in ("precise", "rough") and r["reprLat"] and r["reprLong"]:
                pts.append((float(r["reprLat"]), float(r["reprLong"])))
    return np.array(pts)


def target(g, year):
    from polity import earth as E
    d = json.loads(CLIO.read_text())
    rings = []
    for f in d["features"]:
        p = f["properties"]
        if p["FromYear"] <= year <= p["ToYear"] and f["geometry"]:
            geo = f["geometry"]
            rings.extend([geo["coordinates"]] if geo["type"] == "Polygon" else geo["coordinates"])
    return E.inside_polygons(g, rings), len(rings)


def prepare(pool):
    import polity_earth_check as P
    import earth_control_test as T
    from polity import earth as E
    cfg = json.loads(PLAN.read_text())["pools"][POOLS[pool]["key"]]["window"]
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    path = OUT / f"{pool}_window.npz"
    if not path.exists():
        g = E.window(cfg["lat0"], cfg["lon0"], cfg["width_km"], cfg["height_km"], cfg["cell_km"])
        np.savez_compressed(path, **{k: np.asarray(v) for k, v in g.items()})
    g = dict(np.load(path))
    for k in ("cell_km", "lat0", "lon0"):
        g[k] = float(g[k])
    land0 = g["land"].astype(bool)
    log(f"{pool}: window {land0.shape}, land {land0.sum():,} ({time.time() - t0:.0f}s)")
    pts = pleiades(POOLS[pool]["tags"])
    r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    world = P.world_of(g, np.zeros(land0.shape, bool))
    W = land0.shape[1]
    nodes = np.unique((r * W + c)[ok])
    nodes = nodes[world["land"].ravel()[nodes]]
    inside, n_rings = target(g, POOLS[pool]["year"])
    inside &= world["land"]
    log(f"{pool}: {ok.sum()} source points in window -> {len(nodes)} source cells; target polygons {n_rings} ({time.time() - t0:.0f}s)")
    food = OUT / f"{pool}_food.npz"
    if not food.exists():
        ff = T.food_fields(g, world["land"]); np.savez_compressed(food, **ff)
    np.savez_compressed(OUT / f"{pool}_setup.npz", nodes=nodes, inside=inside)
    log(f"{pool} prepared ({time.time() - t0:.0f}s)")


def run(pool):
    import polity_earth_check as P
    from scipy.sparse.csgraph import dijkstra
    from polity import control as C
    import earth_control_round2 as R
    t0 = time.time()
    P.apply_sea()
    g = dict(np.load(OUT / f"{pool}_window.npz"))
    for k in ("cell_km", "lat0", "lon0"):
        g[k] = float(g[k])
    s = dict(np.load(OUT / f"{pool}_setup.npz")); nodes = s["nodes"]
    road = np.zeros(g["land"].shape, bool)
    S_ = R.setup(g, nodes, road)
    ff = dict(np.load(OUT / f"{pool}_food.npz"))
    actives, info = {"reference": np.ones(len(nodes), bool)}, {}
    for c in FOOD_CASES:
        actives[c], info[c] = R.chain(S_, ff, ff["F_" + c], scaled=True)
    held = R.reach(g, S_, nodes, road, actives)
    world, land = S_["world"], S_["land"]
    eta = C.terrain_coefficient(world["biome"], world["swamp"], None)
    v1 = C.travel_graph(world["elev"], land, road, eta, world["cell_km"], S_["st"]["paths"])
    d1 = dijkstra(v1, directed=True, indices=nodes, min_only=True).reshape(land.shape)
    band = land & (d1 <= 15)
    np.savez_compressed(OUT / f"{pool}_masks.npz", band=band, inside=s["inside"], land=land,
                        legacy_0=held["reference"]["P1"], **{f"{c}__{r}": m for c, d in held.items() for r, m in d.items()},
                        **{f"active__{c}": a for c, a in actives.items()})
    (OUT / f"{pool}_chain.json").write_text(json.dumps(dict(sources=int(len(nodes)), chain=info), indent=1))
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
            out[c] = dict(m1(z[f"{c}__{r_star}"]), staffed_share=float(z[f"active__{c}"].mean()),
                          other_rules={r: m1(z[f"{c}__{r}"])["ba"] for r in ("P0", "P1", "P2", "P3")})
        out["chain"] = json.loads((OUT / f"{pool}_chain.json").read_text())
        res["pools"][pool] = out
    gates = {c: dict(G1=all(res["pools"][p][c]["staffed_share"] >= 0.75 for p in POOLS),
                     G2=all(res["pools"][p][c]["ba"] >= res["pools"][p]["legacy_0"]["ba"] - 0.02 for p in POOLS), census_error=CENSUS[c])
             for c in FOOD_CASES}
    passing = [c for c in FOOD_CASES if gates[c]["G1"] and gates[c]["G2"]]
    res["decision"] = dict(gates=gates, passing=passing, default=min(passing, key=CENSUS.get) if passing else "legacy_0")
    (OUT / "results_blind.json").write_text(json.dumps(res, indent=1))
    for p, o in res["pools"].items():
        log(f"== {p}: {o['chain']['sources']} sources, state share of band {o['inside_share']:.2f}; legacy_0 BA {o['legacy_0']['ba']:.3f} (TPR {o['legacy_0']['tpr']:.2f} TNR {o['legacy_0']['tnr']:.2f})")
        for c in FOOD_CASES:
            v = o[c]
            log(f"   {c:12s} {r_star} BA {v['ba']:.3f} (TPR {v['tpr']:.2f} TNR {v['tnr']:.2f}) staffed {v['staffed_share']:.0%}  rules {v['other_rules']}")
    log("decision:", json.dumps(res["decision"]))


if __name__ == "__main__":
    {"prepare": lambda: prepare(sys.argv[2]), "run": lambda: run(sys.argv[2]), "score": score}[sys.argv[1]]()
