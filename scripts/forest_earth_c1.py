"""Workstream C1 (calibration/geography_control_20261107/plan_C1.json): AD 200 forest = potential forest x (1 - cleared
share), clearing from the population model's density, scored on REVEALS open land TW6 (c. 250 BCE - 250 CE).

    .venv/bin/python -I scripts/forest_earth_c1.py dev       # fit P0, k on the development blocks
    .venv/bin/python -I scripts/forest_earth_c1.py blind     # the single blind evaluation
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
PLAN = ROOT / "calibration/geography_control_20261107/plan_C1.json"
REVEALS = ROOT / "data/cache/reveals_20261107/x/LANDCLIMII.RV.means.JUN2021/TW6.RV.estimates.jun21.csv"
OUT = ROOT / "output/forest_c1_20261107"
P0S = np.exp(np.linspace(np.log(1.0), np.log(300.0), 40))
KS = (0.5, 0.75, 1.0, 1.5, 2.0)


def earth_fields():
    """Per Earth-run cell: potential forest f0 and the population model's (cored) density P."""
    from harvest.models import FOREST_SHARE, settlement_fields
    from polity.earth import OCCUPATION_CENTRAL
    from rotclimate import biomes
    z = np.load(ROOT / "output/land_people/earth/earth.npz"); land = z["land"].astype(bool)
    biome = biomes.classify(np.nan_to_num(z["T_ann"]), np.nan_to_num(z["P_ann"]), land)
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(z["irr"]), 1e-12)), 300.0)
    f = settlement_fields(np.nan_to_num(z["capacity"]), np.nan_to_num(z["npp"]), biome, np.nan_to_num(z["arable"]), water_km, np.nan_to_num(z["malaria"]))
    base = np.where(land, np.nan_to_num(f["settlement_base"]) * OCCUPATION_CENTRAL, 0.0)
    D = np.load(ROOT / "output/settlement_model_20261107/core_distance_earth.npz")["D"].astype(float)
    t = base * np.exp(-D / 800.0); P = np.where(land, t * base[land].sum() / max(t[land].sum(), 1e-9), 0.0)
    f0 = np.zeros(land.shape)
    for code, share in FOREST_SHARE.items():
        f0[biome == code] = share
    ai = np.nan_to_num(np.asarray(z["P_ann"], float)) / np.maximum(np.nan_to_num(np.asarray(z["PET_ann"], float)), 1.0)
    return z["lat"], z["lon"], land, f0, P, ai, np.nan_to_num(np.asarray(z["gdd5"], float))


def cells():
    """REVEALS TW6 cells inside the Earth run, with the model fields gathered per cell (>= 30 % land)."""
    lat, lon, land, f0, P, ai, gdd = earth_fields()
    rows = list(csv.DictReader(open(REVEALS, encoding="utf-8")))
    out = []
    for r in rows:
        try:
            la, lo, ol = float(r["latDD"]), float(r["lonDD"]), float(r["OL"])
        except ValueError:                                   # '#N/A' rows: no estimate for the cell
            continue
        ii = np.flatnonzero((lat >= la - 0.5) & (lat < la + 0.5)); jj = np.flatnonzero((lon >= lo - 0.5) & (lon < lo + 0.5))
        if not len(ii) or not len(jj):
            continue
        m = land[np.ix_(ii, jj)]
        if m.mean() < 0.3:
            continue
        block = int(np.floor((la - 30) / 5) + np.floor((lo + 25) / 5))
        out.append(dict(lat=la, lon=lo, ol=ol / 100.0, dev=(block % 2 == 0),
                        f0=f0[np.ix_(ii, jj)][m], P=P[np.ix_(ii, jj)][m], ai=ai[np.ix_(ii, jj)][m], gdd=gdd[np.ix_(ii, jj)][m]))
    return out


AS, WS, G0S = (0.3, 0.4, 0.5, 0.6, 0.7), (0.2, 0.4, 0.8), (300.0, 600.0)


def potential(c, a, w, g0):
    """Amendment 1: forest potential from the moisture index with a warmth limit."""
    return np.clip((c["ai"] - a) / w, 0, 1) * np.clip((c["gdd"] - g0) / 300.0, 0, 1)


def open_share(c, P0, k, pot=None):
    cleared = 1.0 - np.exp(-np.power(c["P"] / P0, k))
    f0 = c["f0"] if pot is None else pot
    return float(np.mean(1.0 - f0 * (1.0 - cleared)))


def scores(cs, pred):
    from scipy.stats import spearmanr
    y = np.array([c["ol"] for c in cs]); p = np.array(pred)
    return dict(rmse=float(np.sqrt(np.mean((p - y) ** 2))), spearman=float(spearmanr(p, y).statistic), n=int(len(cs)),
                mean_obs=float(y.mean()), mean_pred=float(p.mean()))


def rmse(cs, pred):
    y = np.array([c["ol"] for c in cs]); return float(np.sqrt(np.mean((np.array(pred) - y) ** 2)))


def fit(dev):
    """Joint fit on the development cells: candidate (potential + clearing curve), B0 (potential only), B1 (potential +
    one constant cleared share)."""
    import itertools
    cand = b0 = b1 = None
    for a, w, g0 in itertools.product(AS, WS, G0S):
        pots = [potential(c, a, w, g0) for c in dev]
        r0 = rmse(dev, [float(np.mean(1 - p)) for p in pots])
        if b0 is None or r0 < b0[0]:
            b0 = (r0, dict(a=a, w=w, g0=g0))
        for cc in np.linspace(0, 1, 51):
            r1 = rmse(dev, [float(np.mean(1 - p * (1 - cc))) for p in pots])
            if b1 is None or r1 < b1[0]:
                b1 = (r1, dict(a=a, w=w, g0=g0, cleared=float(cc)))
        for P0 in P0S:
            for k in KS:
                r = rmse(dev, [open_share(c, P0, k, p) for c, p in zip(dev, pots)])
                if cand is None or r < cand[0]:
                    cand = (r, dict(a=a, w=w, g0=g0, P0=float(P0), k=float(k)))
    return dict(candidate=cand[1], B0=b0[1], B1=b1[1])


def evaluate(cs, prm):
    c, b0, b1 = prm["candidate"], prm["B0"], prm["B1"]
    return dict(candidate=scores(cs, [open_share(x, c["P0"], c["k"], potential(x, c["a"], c["w"], c["g0"])) for x in cs]),
                B0=scores(cs, [float(np.mean(1 - potential(x, b0["a"], b0["w"], b0["g0"]))) for x in cs]),
                B1=scores(cs, [float(np.mean(1 - potential(x, b1["a"], b1["w"], b1["g0"]) * (1 - b1["cleared"]))) for x in cs]),
                biome_potential_no_clearing=scores(cs, [float(np.mean(1 - x["f0"])) for x in cs]))


def dev():
    OUT.mkdir(parents=True, exist_ok=True)
    cs = cells(); d = [c for c in cs if c["dev"]]
    prm = fit(d); res = dict(plan=str(PLAN.relative_to(ROOT)), params=prm, development=evaluate(d, prm),
                             cells=dict(total=len(cs), development=len(d), blind=len(cs) - len(d)))
    (OUT / "dev.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


def blind():
    prm = json.loads((OUT / "dev.json").read_text())["params"]
    b = [c for c in cells() if not c["dev"]]
    ev = evaluate(b, prm)
    g1 = ev["candidate"]["rmse"] < ev["B0"]["rmse"] and ev["candidate"]["rmse"] < ev["B1"]["rmse"]
    g2 = ev["candidate"]["spearman"] > ev["B1"]["spearman"]
    res = dict(plan=str(PLAN.relative_to(ROOT)), params=prm, blind=ev, gates=dict(G1=bool(g1), G2=bool(g2)), adopt=bool(g1 and g2))
    (OUT / "blind.json").write_text(json.dumps(res, indent=1)); print(json.dumps(res, indent=1))


if __name__ == "__main__":
    {"dev": dev, "blind": blind}[sys.argv[1]]()
