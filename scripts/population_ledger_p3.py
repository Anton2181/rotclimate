"""Plan P3 (calibration/population_ledger_20261108/plan.json): the predicted population ledger on Earth, three fixed
candidates (P0 capacity, P1 settlement base, P2 capacity x old-core occupancy), developed on seen data (Han AD 2, the
ten historical regions) and scored once on Domesday England 1086 (20 km blocks + the England level).

    .venv/bin/python -I scripts/population_ledger_p3.py dev        # seen data, report only
    .venv/bin/python -I scripts/population_ledger_p3.py blind      # once, after the statistics database is in place
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/population_ledger_20261108/plan.json"
OUT = ROOT / "output/population_ledger_20261108"
DD = ROOT / "data/cache/domesday"
EARTH = ROOT / "output/land_people/earth/earth.npz"
log = lambda *a: print(*a, flush=True)  # noqa: E731


# ------------------------------------------------------------------ candidates on the Earth-harness grid
def candidates():
    """people/km2 on the Earth harness grid for P0, P1, P2, with lat, lon, land and cell km2."""
    from polity.earth import OCCUPATION_CENTRAL
    from harvest.models import settlement_fields
    from rotclimate import biomes
    import population_cores as PC
    z = dict(np.load(EARTH)); lat, lon, land = z["lat"], z["lon"], z["land"].astype(bool)
    km2 = (111.32 / 12) ** 2 * np.cos(np.radians(lat))[:, None] * np.ones((1, len(lon)))
    cap = np.where(land, np.nan_to_num(z["capacity"]), 0.0)
    biome = biomes.classify(np.nan_to_num(z["T_ann"]), np.nan_to_num(z["P_ann"]), land)
    irr_d = z["irr_distance"] if "irr_distance" in z else z["irr"]
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(irr_d), 1e-12)), 300.0)
    f = settlement_fields(cap, np.nan_to_num(z["npp"]), biome, np.nan_to_num(z["arable"]), water_km, np.nan_to_num(z["malaria"]))
    base = np.where(land, np.nan_to_num(f["settlement_base"]) * OCCUPATION_CENTRAL, 0.0)
    OUT.mkdir(parents=True, exist_ok=True); cache = OUT / "core_distance.npz"
    if cache.exists():
        D = np.load(cache)["D"]
    else:
        D = PC.travel_distance(z, PC.CORE_SETS["cradles + Rome"], forest_cost=2.0, sea_cost=1.0, relief_cost=1.0).astype(np.float32)
        np.savez_compressed(cache, D=D)
    cored = cap * np.exp(-np.asarray(D, float) / 800.0)
    return dict(P0_capacity=cap, P1_base=base, P2_cored=cored), lat, lon, land, km2


# ------------------------------------------------------------------ development (seen data)
def dev():
    import han_census_check as H
    from matplotlib.path import Path as Poly
    import land_people_earth as E
    C, lat, lon, land, km2 = candidates()
    rows = H.used(H.commanderies(str(ROOT / "data/cache/han_ad2/shp/ResearchArea"), lat, lon, km2))
    res = {"han_commanderies": len(rows)}
    for k, dens in C.items():
        people = [float((dens[r["idx"]] * km2[r["idx"]]).sum()) for r in rows]
        res[k] = dict(han=H.score(rows, people))
    LA, LO = np.meshgrid(lat, lon, indexing="ij"); pts = np.stack([LO.ravel(), LA.ravel()], 1)
    regions = {}
    for name, r in E.REGIONS.items():
        inside = Poly(r["poly"]).contains_points(pts).reshape(land.shape) & land
        a = float(km2[inside].sum()); lo, hi = r["people"] if "people" in r else (d * a / 1e6 for d in r["density"])
        regions[name] = dict(hist_m=(lo + hi) / 2, fitted=r.get("fitted", False),
                             **{k: float((C[k] * km2)[inside].sum() / 1e6) for k in ("P0_capacity", "P2_cored")})
    for k in ("P0_capacity", "P2_cored"):
        e = [math.log(v["hist_m"] / max(v[k], 1e-9)) for v in regions.values() if not v["fitted"]]
        res[k]["regions_rms_ln"] = float(np.sqrt(np.mean(np.square(e))))
    res["regions"] = regions
    (OUT / "dev.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    for k in C:
        h = res[k]["han"]; log(f"{k:12s} Han AD 2 spearman {h['spearman']:.3f} moved {h['moved_share']:.2f}" + (f" | regions RMS ln {res[k]['regions_rms_ln']:.3f}" if "regions_rms_ln" in res[k] else ""))
    for n, v in regions.items():
        log(f"  {n[:34]:34s} hist {v['hist_m']:7.2f} M | P0 {v['P0_capacity']:7.2f} | P2 {v['P2_cored']:7.2f}" + (" (fitted)" if v["fitted"] else ""))


# ------------------------------------------------------------------ British National Grid
OS_LETTERS = "ABCDEFGHJKLMNOPQRSTUVWXYZ"


def osref_to_en(ref):
    """1-km Ordnance Survey reference ('SO7567') to the easting / northing (m) of the square's centre."""
    s = str(ref or "").replace(" ", "").upper()
    if len(s) < 4 or s[0] not in OS_LETTERS or s[1] not in OS_LETTERS:
        return None
    digits = s[2:]
    if not digits.isdigit() or len(digits) % 2:
        return None
    l1, l2 = OS_LETTERS.index(s[0]), OS_LETTERS.index(s[1])
    e100 = ((l1 - 2) % 5) * 5 + l2 % 5
    n100 = (19 - (l1 // 5) * 5) - l2 // 5
    h = len(digits) // 2; unit = 10 ** (5 - h)
    e = e100 * 100000 + int(digits[:h]) * unit + unit / 2
    n = n100 * 100000 + int(digits[h:]) * unit + unit / 2
    return e, n


def en_to_latlon(E, N):
    """OSGB36 National Grid (Airy 1830, transverse Mercator) easting / northing to latitude / longitude in degrees."""
    a, b = 6377563.396, 6356256.909; F0 = 0.9996012717
    lat0, lon0 = math.radians(49.0), math.radians(-2.0); N0, E0 = -100000.0, 400000.0
    e2 = 1 - (b * b) / (a * a); n = (a - b) / (a + b)
    lat = lat0; M = 0.0
    while abs(N - N0 - M) >= 1e-5:
        lat = (N - N0 - M) / (a * F0) + lat
        M = b * F0 * ((1 + n + 1.25 * n ** 2 + 1.25 * n ** 3) * (lat - lat0)
                      - (3 * n + 3 * n ** 2 + 21 / 8 * n ** 3) * math.sin(lat - lat0) * math.cos(lat + lat0)
                      + (15 / 8 * n ** 2 + 15 / 8 * n ** 3) * math.sin(2 * (lat - lat0)) * math.cos(2 * (lat + lat0))
                      - 35 / 24 * n ** 3 * math.sin(3 * (lat - lat0)) * math.cos(3 * (lat + lat0)))
    sl, cl, tl = math.sin(lat), math.cos(lat), math.tan(lat)
    nu = a * F0 / math.sqrt(1 - e2 * sl * sl); rho = a * F0 * (1 - e2) / (1 - e2 * sl * sl) ** 1.5; eta2 = nu / rho - 1
    VII = tl / (2 * rho * nu); VIII = tl / (24 * rho * nu ** 3) * (5 + 3 * tl ** 2 + eta2 - 9 * tl ** 2 * eta2)
    IX = tl / (720 * rho * nu ** 5) * (61 + 90 * tl ** 2 + 45 * tl ** 4)
    X = 1 / (cl * nu); XI = 1 / (cl * 6 * nu ** 3) * (nu / rho + 2 * tl ** 2)
    XII = 1 / (cl * 120 * nu ** 5) * (5 + 28 * tl ** 2 + 24 * tl ** 4)
    XIIA = 1 / (cl * 5040 * nu ** 7) * (61 + 662 * tl ** 2 + 1320 * tl ** 4 + 720 * tl ** 6)
    dE = E - E0
    phi = lat - VII * dE ** 2 + VIII * dE ** 4 - IX * dE ** 6
    lam = lon0 + X * dE - XI * dE ** 3 + XII * dE ** 5 - XIIA * dE ** 7
    return math.degrees(phi), math.degrees(lam)


def latlon_to_en_grid(lat, lon):
    """Approximate BNG easting / northing of grid cells (inverse by Newton on en_to_latlon), for block assignment."""
    E = 400000.0 + (lon + 2.0) * 111320.0 * np.cos(np.radians(lat)); N = -100000.0 + (lat - 49.0) * 111132.0
    for _ in range(4):
        la, lo = np.vectorize(en_to_latlon)(E, N)
        E = E + (lon - lo) * 111320.0 * np.cos(np.radians(lat)); N = N + (lat - la) * 111132.0
    return E, N


# ------------------------------------------------------------------ the blind test
PEOPLE = ("Villagers", "Smallholders", "Slaves", "Female slaves", "Freemen", "free men", "Priests", "cottagers", "OtherPop",
          "MiscPop", "Burgesses")


def domesday_points():
    """Located places with their recorded people (plan amendment 1): easting, northing (m), people, and the join report."""
    from collections import defaultdict
    from access_parser import AccessParser
    P = AccessParser(str(DD / "places_content.mdb")).parse_table("Places")
    st = AccessParser(str(DD / "statistics_content.mdb")); M = st.parse_table("Manors"); B = st.parse_table("ByPlace")
    loc = {}
    for idx, ref in zip(P["PlacesIdx"], P["OSrefs"]):
        en = osref_to_en(str(ref or "").split(",")[0].split(";")[0].split("/")[0])
        if en is not None:
            loc[idx] = en
    places_of = defaultdict(set)
    for s, p in zip(B["StructIdx"], B["PlacesIdx"]):
        places_of[s].add(p)
    num = lambda v: float(v) if v not in (None, "") else 0.0  # noqa: E731
    people_at = defaultdict(float); rep = dict(holdings=len(M["StructIdx"]), excluded_x_duplicates=0, people_recorded=0.0,
                                               people_unlocated=0.0, holdings_without_place=0)
    for i, s in enumerate(M["StructIdx"]):
        if str(M["Duplicates"][i]) == "X":
            rep["excluded_x_duplicates"] += 1; continue
        heads = sum(num(M[c][i]) for c in PEOPLE)
        rep["people_recorded"] += heads
        ps = places_of.get(s, set())
        if not ps:
            rep["holdings_without_place"] += 1; rep["people_unlocated"] += heads; continue
        share = heads / len(ps)
        for p in ps:
            if p in loc:
                people_at[p] += share
            else:
                rep["people_unlocated"] += share
    keys = sorted(people_at)
    E = np.array([loc[k][0] for k in keys]); N = np.array([loc[k][1] for k in keys]); pop = np.array([people_at[k] for k in keys])
    allE = np.array([v[0] for v in loc.values()]); allN = np.array([v[1] for v in loc.values()])
    rep.update(places_located=len(loc), places_with_people=int((pop > 0).sum()))
    return E, N, pop, allE, allN, rep


def blind():
    from scipy.spatial import cKDTree
    from scipy.stats import spearmanr
    if (OUT / "blind.json").exists():
        raise SystemExit("already scored once (output/population_ledger_20261108/blind.json)")
    Ep, Np, pop, allE, allN, rep = domesday_points()
    C, lat, lon, land, km2 = candidates()
    ri = np.nonzero((lat >= 49.8) & (lat <= 56.0))[0]; ci = np.nonzero((lon >= -6.5) & (lon <= 2.1))[0]
    LA, LO = np.meshgrid(lat[ri], lon[ci], indexing="ij")
    Ec, Nc = latlon_to_en_grid(LA, LO)
    ld = land[np.ix_(ri, ci)]; ar = km2[np.ix_(ri, ci)]
    d, _ = cKDTree(np.column_stack([allE, allN])).query(np.column_stack([Ec.ravel(), Nc.ravel()]))
    mask = ld & (d.reshape(ld.shape) <= 15000.0)
    res = dict(plan=str(PLAN.relative_to(ROOT)), join=rep, surveyed_land_km2=float(ar[mask].sum()), blocks={}, level={})
    for size in (20000, 40000):
        bc = (np.floor(Ec / size).astype(int), np.floor(Nc / size).astype(int)); bp = (np.floor(Ep / size).astype(int), np.floor(Np / size).astype(int))
        keys = sorted(set(zip(bc[0][ld], bc[1][ld])))
        obs, mod = [], {k: [] for k in C}
        for kx, ky in keys:
            inb = (bc[0] == kx) & (bc[1] == ky)
            nl, nm = int((inb & ld).sum()), int((inb & mask).sum())
            if nl < 4 or nm < 0.5 * nl:
                continue
            area = float(ar[inb & mask].sum())
            obs.append(float(pop[(bp[0] == kx) & (bp[1] == ky)].sum()) / area)
            for k, dens in C.items():
                sub = dens[np.ix_(ri, ci)]
                mod[k].append(float((sub * ar)[inb & mask].sum()) / area)
        obs = np.array(obs); out = dict(n_blocks=len(obs))
        for k in C:
            m = np.array(mod[k]); w = m / max(m.sum(), 1e-12); o = obs / max(obs.sum(), 1e-12)
            out[k] = dict(spearman=float(spearmanr(m, obs).statistic), moved_share=float(0.5 * np.abs(w - o).sum()))
        res["blocks"][f"{size // 1000}km"] = out
    for k in ("P0_capacity", "P2_cored"):
        tot = float((C[k][np.ix_(ri, ci)] * ar)[mask].sum())
        res["level"][k] = dict(people_m=tot / 1e6, ln_vs_1p71=float(np.log(tot / 1.71e6)), inside_1p2_2p6=bool(1.2e6 <= tot <= 2.6e6))
    b20 = res["blocks"]["20km"]
    res["gates"] = {k: dict(R_pass=b20[k]["spearman"] >= 0.30, L_pass=res["level"].get(k, {}).get("inside_1p2_2p6")) for k in C}
    res["atlas_predicted_total"] = bool(res["gates"]["P2_cored"]["R_pass"] and res["gates"]["P2_cored"]["L_pass"])
    (OUT / "blind.json").write_text(json.dumps(res, indent=1))
    log(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"dev": dev, "blind": blind}[sys.argv[1]]()
