"""T8: fit the occupation ratio (historical people / model settlement base) as a
field on Earth, as declared in calibration/occupation_field_20261121/plan.json.

    .venv/bin/python -I scripts/occupation_field.py --out calibration/occupation_field_20261121
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.path import Path as Poly

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from harvest_earth_hyde import earth_stages  # noqa: E402
from population_cores import CORE_SETS, travel_distance  # noqa: E402
from land_people_earth import REGIONS  # noqa: E402
from harvest.models import settlement_fields  # noqa: E402,F401
from rotclimate import biomes  # noqa: E402

WEST = ["Egypt", "Roman Italy (mainland)", "Roman Gaul", "Iberia", "Asia Minor", "Roman Syria", "Mesopotamian alluvium"]
MODELS = {"M0": [], "M1": ["D"], "M2": ["D", "herd"], "M3": ["D", "herd", "malaria", "arid"]}


def unit_covariates(mask, base, km2, fields):
    w = (base * km2)[mask]
    w = w / max(w.sum(), 1e-12)
    return {k: float((v[mask] * w).sum()) for k, v in fields.items()}


def build_units(z):
    lat, lon, land = z["lat"], z["lon"], z["land"].astype(bool)
    km2, stages = earth_stages(z)
    base = np.nan_to_num(stages["+ malaria (settlement base)"]) * land
    biome = biomes.classify(np.nan_to_num(z["T_ann"]), np.nan_to_num(z["P_ann"]), land)
    water_km = np.minimum(-6.0 * np.log(np.maximum(np.nan_to_num(z["irr"]), 1e-12)), 300.0)
    f = settlement_fields(np.nan_to_num(z["capacity"]), np.nan_to_num(z["npp"]), biome, np.nan_to_num(z["arable"]),
                          water_km, np.nan_to_num(z["malaria"]))
    herd = np.nan_to_num(f["pastoral_capacity"] / np.maximum(f["food_capacity"], 1e-9))
    D = travel_distance(z, CORE_SETS["cradles + Rome"], 2.0, 1.0, 1.0)
    D = np.where(np.isfinite(D), D, 5000.0)
    arid = np.log(np.maximum(np.nan_to_num(z["P_ann"]), 1.0) / np.maximum(np.nan_to_num(z["PET_ann"]), 1.0))
    cov = dict(D=D / 1000.0, herd=herd, malaria=np.clip(np.nan_to_num(z["malaria"]), 0, 1), arid=arid)
    LAT, LON = np.meshgrid(lat, lon, indexing="ij")
    units = []
    from han_census_check import commanderies
    for c in commanderies(str(ROOT / "data/cache/han_ad2/shp/ResearchArea"), lat, lon, km2):
        i, j = c.pop("idx")
        mask = np.zeros(land.shape, bool)
        mask[i, j] = True
        mask &= land
        b = float((base * km2)[mask].sum())
        if c["coverage"] < 0.9 or b <= 0 or c["pop"] <= 0:
            continue
        units.append(dict(pool="han", name=c["name"], lat=c["lat"], lon=c["lon"], people=c["pop"], base=b,
                          **unit_covariates(mask, base, km2, cov)))
    pts = np.stack([LON.ravel(), LAT.ravel()], 1)
    for name in WEST:
        r = REGIONS[name]
        mask = Poly(r["poly"]).contains_points(pts).reshape(land.shape) & land
        area = float(km2[mask].sum())
        lo, hi = r["people"] if "people" in r else (d * area / 1e6 for d in r["density"])
        b = float((base * km2)[mask].sum())
        units.append(dict(pool="west", name=name, lat=float(LAT[mask].mean()), lon=float(LON[mask].mean()),
                          people=float(np.sqrt(lo * hi) * 1e6), base=b, **unit_covariates(mask, base, km2, cov)))
    return units


def design(units, keys):
    return np.column_stack([np.ones(len(units))] + [[u[k] for u in units] for k in keys])


def weights(units):
    pools = {}
    for u in units:
        pools[u["pool"]] = pools.get(u["pool"], 0) + 1
    return np.array([0.5 / pools[u["pool"]] for u in units])


def fit(units, keys):
    X, y, w = design(units, keys), np.array([np.log(u["people"] / u["base"]) for u in units]), weights(units)
    sw = np.sqrt(w)
    beta, *_ = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)
    return beta


def folds(units):
    han = [i for i, u in enumerate(units) if u["pool"] == "han"]
    mlat = np.median([units[i]["lat"] for i in han]); mlon = np.median([units[i]["lon"] for i in han])
    out = {}
    for i in han:
        u = units[i]
        out.setdefault(f"han_{'N' if u['lat'] >= mlat else 'S'}{'E' if u['lon'] >= mlon else 'W'}", []).append(i)
    for i, u in enumerate(units):
        if u["pool"] == "west":
            out[f"west_{u['name']}"] = [i]
    return out


def cross_validate(units, keys):
    y = np.array([np.log(u["people"] / u["base"]) for u in units])
    pred = np.full(len(units), np.nan)
    fold_people = {}
    for name, idx in folds(units).items():
        train = [u for i, u in enumerate(units) if i not in idx]
        beta = fit(train, keys)
        test = [units[i] for i in idx]
        pred[idx] = design(test, keys) @ beta
        fold_people[name] = float(sum(np.exp(pred[i]) * units[i]["base"] for i in idx) / sum(units[i]["people"] for i in idx))
    err = np.abs(pred - y)
    pools = {p: float(np.mean([e for e, u in zip(err, units) if u["pool"] == p])) for p in ("han", "west")}
    return dict(score=float(np.mean(list(pools.values()))), pools=pools, fold_people_ratio=fold_people,
                residuals=(y - pred).tolist())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--earth", default="output/land_people/earth/earth.npz")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    z = np.load(ROOT / a.earth)
    units = build_units(z)
    res = dict(units=units, models={})
    for m, keys in MODELS.items():
        beta = fit(units, keys)
        cv = cross_validate(units, keys)
        res["models"][m] = dict(keys=keys, coefficients=dict(zip(["const"] + keys, map(float, beta))), cv=cv)
        print(f"{m} {keys}: CV score {cv['score']:.3f} (han {cv['pools']['han']:.3f}, west {cv['pools']['west']:.3f}) "
              f"coef {np.round(beta, 3).tolist()}")
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
