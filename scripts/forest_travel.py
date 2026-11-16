"""Forest in travel cost, C2 (calibration/forest_travel_20261116/plan.json).

    .venv/bin/python -I scripts/forest_travel.py prep rome|han|T9|T10|T11   # baseline and C2 territory, nothing scored
    .venv/bin/python -I scripts/forest_travel.py dev                       # development report
    .venv/bin/python -I scripts/forest_travel.py blind                     # the single blind evaluation
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/forest_travel_20261116"
PLAN = ROOT / "calibration/forest_travel_20261116/plan.json"
BLIND = {"T9": (1600, "han"), "T10": (609, "han"), "T11": (1700, "rome")}
FOREST_BIOMES = (3, 4, 7, 9)
log = lambda *a: print(*a, flush=True)  # noqa: E731


def forest_share(g):
    import land_people_earth as LPE
    from land_people import hargreaves, sunlight_top, DAYS
    T = g["tavg"].astype(float); P = g["prec"].astype(float); D = np.maximum((g["tmax"] - g["tmin"]).astype(float), 0.1)
    PET = hargreaves(T.reshape(12, -1), D.reshape(12, -1), sunlight_top(g["lat"].ravel(), LPE.TILT, LPE.WS_DAY)).reshape(T.shape)
    ai = P.sum(0) / np.maximum(PET.sum(0), 1.0); gdd = np.maximum(T - 5.0, 0.0).sum(0) * DAYS
    return 0.60 * np.clip((ai - 0.3) / 0.2, 0, 1) * np.clip((gdd - 300.0) / 300.0, 0, 1)


def c2_coefficient(f):
    from polity import control as C
    original = C.terrain_coefficient

    def coefficient(biome, swamp, snow_share=None):
        b = np.asarray(biome).astype(int); base = np.vectorize(lambda v: C.BIOME_COEFFICIENT.get(int(v), 1.2))(b)
        forest_biome = np.isin(b, FOREST_BIOMES)
        open_ = np.where(forest_biome, 1.2, base); dense = np.where(forest_biome, base, 1.5)
        ff = f if f.shape == b.shape else np.zeros(b.shape)
        eta = open_ * (1 - ff) + dense * ff
        eta = np.where(swamp, np.maximum(eta, C.SWAMP_COEFFICIENT), eta)
        if snow_share is not None:
            eta = eta * (1.0 + (C.SNOW_COEFFICIENT - 1.0) * np.clip(snow_share, 0, 1))
        return eta
    return original, coefficient


def prep(pool):
    import basin_cantons as BC
    import geography_control_a2 as A2
    import geography_control_a3 as A3
    import polity_earth_check as P
    from polity import control as C, fields as F
    OUT.mkdir(parents=True, exist_ok=True)
    BC.BLIND.update(BLIND); BC._ORIGINAL = A2.pool_inputs; A2.pool_inputs = BC.pool_inputs; A3.OUT = OUT
    window = pool if pool in ("rome", "han") else BLIND[pool][1]
    g = P.load_window(window); f = forest_share(g)
    A3.prep(pool); base = dict(np.load(OUT / f"{pool}.npz"))
    original, c2 = c2_coefficient(f)
    C.terrain_coefficient = c2; F.terrain_coefficient = c2
    try:
        A3.prep(pool); c = dict(np.load(OUT / f"{pool}.npz"))
    finally:
        C.terrain_coefficient = original; F.terrain_coefficient = original
    np.savez_compressed(OUT / f"{pool}.npz", **base, held_c2=c["held"], band_c2=c["band"], forest=f.astype(np.float32),
                        river=np.asarray(g["river"], bool))
    log(pool, "forest share of land", round(float(f[base["land"]].mean()), 3), "; held cells base", int(base["held"].sum()), "C2", int(c["held"].sum()), "; not scored")


def score(pool):
    import geography_control_a as A
    import geography_control_a2 as A2
    z = dict(np.load(OUT / f"{pool}.npz")); land = z["land"]; band = z["band"]
    river = ndi.binary_dilation(z["river"], iterations=2) & land
    ai = z["ai"]; desert = (ai < 0.2) & ndi.binary_dilation(ai >= 0.2, iterations=2) & land
    feats = dict(forest=z["forest"].astype(float), river=river.astype(float), desert_edge=desert.astype(float))
    real = A2.enrich(z["inside"], land, band, feats); res = dict(real_enrichment=real)
    terr = {}
    for name, h in (("base", z["held"]), ("C2", z["held_c2"])):
        t = h | A.pockets(h, land)[0]; terr[name] = t; e = A2.enrich(t, land, band, feats)
        res[name] = dict(**A.balanced_accuracy(t, z["inside"], band), enrichment=e,
                         forest_distance=abs(float(np.log(max(e["forest"], 1e-3) / max(real["forest"], 1e-3)))),
                         territory_cells=int(t.sum()))
    res["changed_cells"] = int((terr["base"] != terr["C2"]).sum()); res["forest_share_of_land"] = float(z["forest"][land].mean())
    return res


def summary(pools):
    for p, o in pools.items():
        log(f"{p}: real forest x{o['real_enrichment']['forest']:.2f} | base BA {o['base']['ba']:.3f} forest x{o['base']['enrichment']['forest']:.2f} | "
            f"C2 BA {o['C2']['ba']:.3f} forest x{o['C2']['enrichment']['forest']:.2f}; changed {o['changed_cells']:,}")


def dev():
    res = dict(plan=str(PLAN.relative_to(ROOT)), pools={p: score(p) for p in ("rome", "han")})
    (OUT / "dev.json").write_text(json.dumps(res, indent=1)); summary(res["pools"])


def blind():
    res = dict(plan=str(PLAN.relative_to(ROOT)), pools={p: score(p) for p in BLIND})
    o = res["pools"]
    g1 = all(o[p]["C2"]["ba"] >= o[p]["base"]["ba"] - 0.01 for p in BLIND)
    g2 = sum(o[p]["C2"]["forest_distance"] < o[p]["base"]["forest_distance"] for p in BLIND) >= 2
    res["gates"] = dict(G1=bool(g1), G2=bool(g2)); res["adopt"] = bool(g1 and g2)
    (OUT / "blind.json").write_text(json.dumps(res, indent=1)); summary(o); log("gates", res["gates"], "adopt", res["adopt"])


if __name__ == "__main__":
    {"prep": lambda: prep(sys.argv[2]), "dev": dev, "blind": blind}[sys.argv[1]]()
