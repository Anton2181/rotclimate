"""Basin cantons (calibration/basin_cantons_20261116/plan.json).

    .venv/bin/python -I scripts/basin_cantons.py prep rome|han|T6|T7|T8   # v2.1 territory and basin rasters, nothing scored
    .venv/bin/python -I scripts/basin_cantons.py dev                     # development report and level choice
    .venv/bin/python -I scripts/basin_cantons.py blind                   # the single blind evaluation
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/basin_cantons_20261116"
PLAN = ROOT / "calibration/basin_cantons_20261116/plan.json"
HB = ROOT / "data/cache/hydrobasins"
LEVELS = (7, 8)
BLIND = {"T6": (1400, "han"), "T7": (900, "han"), "T8": (1200, "rome")}
log = lambda *a: print(*a, flush=True)  # noqa: E731


def pool_inputs(pool):
    import geography_control_a2 as A2
    import polity_earth_check as P
    import earth_control_blind as B1
    from polity import earth as E
    if pool in ("rome", "han"):
        return _ORIGINAL(pool)
    P.apply_sea()
    year, window = BLIND[pool]
    g = P.load_window(window); land0 = g["land"].astype(bool); W = land0.shape[1]
    road = (E.draw_lines(g, [l for _, l in E.itinere_roads(150)]) & land0) if window == "rome" else np.zeros(land0.shape, bool)
    if window == "rome":
        import pandas as pd
        d = pd.read_stata(ROOT / "data/cache/bosker_cities_20261107/cities.tab"); y = d[(d["year"] == year) & (d["citypop_le5"] > 0)]
        pts = np.c_[y["latitude"].values.astype(float), y["longitude"].values.astype(float)]
    else:
        pts = A2.seats_year(year)
    r, c, ok = P.snap(g, pts[:, 0], pts[:, 1])
    world0 = P.world_of(g, road)
    nodes = np.unique((r * W + c)[ok]); nodes = nodes[world0["land"].ravel()[nodes]]
    inside, _ = B1.target(g, year)
    return g, road, nodes, inside & world0["land"], None, window


def basins(g, level):
    """HYBAS_ID of the polygon containing each cell centre (0 = none)."""
    import shapefile
    from matplotlib.path import Path as MPath
    lat, lon = np.asarray(g["lat"], float), np.asarray(g["lon"], float)
    box = (lon.min(), lat.min(), lon.max(), lat.max()); out = np.zeros(lat.shape, np.int64)
    pts = np.c_[lon.ravel(), lat.ravel()]
    for region in ("eu", "as", "af"):
        r = shapefile.Reader(str(HB / f"hybas_{region}_lev{level:02d}_v1c.shp"))
        for sr in r.iterShapeRecords(fields=["HYBAS_ID"]):
            b = sr.shape.bbox
            if b[0] > box[2] or b[2] < box[0] or b[1] > box[3] or b[3] < box[1]:
                continue
            cand = np.flatnonzero((pts[:, 0] >= b[0]) & (pts[:, 0] <= b[2]) & (pts[:, 1] >= b[1]) & (pts[:, 1] <= b[3]))
            if not len(cand):
                continue
            parts = list(sr.shape.parts) + [len(sr.shape.points)]; xy = np.asarray(sr.shape.points)
            inside = np.zeros(len(cand), bool)
            for a, e in zip(parts[:-1], parts[1:]):           # even-odd over rings (holes included)
                inside ^= MPath(xy[a:e]).contains_points(pts[cand])
            out.ravel()[cand[inside]] = sr.record[0]
    return out


def divides(lab, land):
    d = np.zeros(lab.shape, bool)
    for sl_a, sl_b in (((slice(None), slice(1, None)), (slice(None), slice(None, -1))), ((slice(1, None), slice(None)), (slice(None, -1), slice(None)))):
        diff = (lab[sl_a] != lab[sl_b]) & land[sl_a] & land[sl_b] & (lab[sl_a] > 0) & (lab[sl_b] > 0)
        d[sl_a] |= diff; d[sl_b] |= diff
    return d & land


def prep(pool):
    import geography_control_a2 as A2
    import geography_control_a3 as A3
    import polity_earth_check as P
    OUT.mkdir(parents=True, exist_ok=True)
    global _ORIGINAL
    _ORIGINAL = A2.pool_inputs; A2.pool_inputs = pool_inputs; A3.OUT = OUT          # the A3 preparation, on this plan's pools and folder
    A3.prep(pool)
    window = pool if pool in ("rome", "han") else BLIND[pool][1]
    g = P.load_window(window); extra = {}
    for lv in LEVELS:
        extra[f"basin{lv}"] = basins(g, lv)
    extra["river"] = np.asarray(g["river"], bool); extra["elev"] = np.asarray(g["elev"], np.float32)
    z = dict(np.load(OUT / f"{pool}.npz")); z.update(extra)
    np.savez_compressed(OUT / f"{pool}.npz", **z)
    log(pool, {lv: int(len(np.unique(extra[f'basin{lv}'][z['land']]))) for lv in LEVELS}, "basins on land; not scored")


def canton(terr, land, lab):
    out = terr.copy(); ids = lab[land]; t = terr[land]
    u, inv = np.unique(ids, return_inverse=True)
    share = np.bincount(inv, weights=t.astype(float)) / np.bincount(inv)
    maj = share[inv] >= 0.5; keep = ids == 0
    out[land] = np.where(keep, t, maj)
    return out


def score(pool, level):
    import geography_control_a as A
    import geography_control_a2 as A2
    z = dict(np.load(OUT / f"{pool}.npz")); land = z["land"]
    pk = A.pockets(z["held"], land)[0]
    v21 = z["held"] | pk
    lab = z[f"basin{level}"]; cant = canton(v21, land, lab)
    div = divides(lab, land)
    river = ndi.binary_dilation(z["river"], iterations=2) & land
    ai = z["ai"]; desert = (ai < 0.2) & ndi.binary_dilation(ai >= 0.2, iterations=2) & land
    feats = dict(divide=div.astype(float), river=river.astype(float), desert_edge=desert.astype(float))
    band = z["band"]
    real = A2.enrich(z["inside"], land, band, feats)
    res = dict(real_enrichment=real)
    for name, m in (("v21", v21), ("canton", cant)):
        e = A2.enrich(m, land, band, feats)
        res[name] = dict(**A.balanced_accuracy(m, z["inside"], band), enrichment=e,
                         divide_distance=abs(float(np.log(max(e["divide"], 1e-3) / max(real["divide"], 1e-3)))) if e["divide"] else None,
                         shape=A.shape(m, land), territory_cells=int(m.sum()))
    res["changed_cells"] = int((cant != v21).sum()); res["level"] = level
    res["basins_on_land"] = int(len(np.unique(lab[land & (lab > 0)]))); res["divide_share_of_land"] = float(div[land].mean())
    return res


def dev():
    res = dict(plan=str(PLAN.relative_to(ROOT)), pools={p: {lv: score(p, lv) for lv in LEVELS} for p in ("rome", "han")})
    ok = [lv for lv in LEVELS if all(res["pools"][p][lv]["canton"]["ba"] >= res["pools"][p][lv]["v21"]["ba"] - 0.01 for p in ("rome", "han"))]
    mean = {lv: float(np.mean([res["pools"][p][lv]["canton"]["divide_distance"] for p in ("rome", "han")])) for lv in LEVELS}
    res["mean_divide_distance"] = mean; res["qualifying_levels"] = ok
    res["chosen_level"] = min(ok, key=lambda lv: mean[lv]) if ok else None
    (OUT / "dev.json").write_text(json.dumps(res, indent=1)); summary(res["pools"]); log("chosen level:", res["chosen_level"], mean)


def summary(pools):
    for p, by in pools.items():
        for lv, o in by.items():
            log(f"{p} L{lv}: real divide x{o['real_enrichment']['divide']:.2f} river x{o['real_enrichment']['river']:.2f} | "
                f"v2.1 BA {o['v21']['ba']:.3f} divide x{o['v21']['enrichment']['divide']:.2f} river x{o['v21']['enrichment']['river']:.2f} | "
                f"canton BA {o['canton']['ba']:.3f} divide x{o['canton']['enrichment']['divide']:.2f} river x{o['canton']['enrichment']['river']:.2f}; "
                f"changed {o['changed_cells']:,}")


def blind():
    d = json.loads((OUT / "dev.json").read_text()); lv = d["chosen_level"]
    if lv is None:
        raise SystemExit("no level qualified on development; blind not run")
    res = dict(plan=str(PLAN.relative_to(ROOT)), level=lv, pools={p: {lv: score(p, lv)} for p in BLIND})
    o = {p: res["pools"][p][lv] for p in BLIND}
    g1 = all(o[p]["canton"]["ba"] >= o[p]["v21"]["ba"] - 0.01 for p in BLIND)
    g2 = sum(o[p]["canton"]["divide_distance"] < o[p]["v21"]["divide_distance"] for p in BLIND) >= 2
    res["gates"] = dict(G1=bool(g1), G2=bool(g2)); res["adopt"] = bool(g1 and g2)
    (OUT / "blind.json").write_text(json.dumps(res, indent=1)); summary(res["pools"]); log("gates", res["gates"], "adopt", res["adopt"])


if __name__ == "__main__":
    {"prep": lambda: prep(sys.argv[2]), "dev": dev, "blind": blind}[sys.argv[1]]()
