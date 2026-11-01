"""FORGE with a cold-climate growing-season limit on land food (calibration/forager_binford_20261031/addendum_cold_20261101.json).

    python -I scripts/forager_cold.py --out output/forager_binford_20261031
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from forager_earth_test import FIT_AREAS, binford, metrics, site_climate, worldclim_months  # noqa: E402
from foraging.forcing import daily_resources, miami_npp, specification  # noqa: E402
from foraging.models import ForagingParams, simulate_foraging  # noqa: E402

PLAN = ROOT / "calibration/forager_binford_20261031/addendum_cold_20261101.json"
GAMMAS = [0, 0.5, 1, 1.5, 2, 3]


def run_D(sites, spec, gamma):
    run = dict(spec["run"]); run.update(years=600, averaging_years=300)
    forcing = daily_resources(sites["T"], sites["P"], sites["npp"], spec["adapter"])
    f = np.clip(sites["gs"] / 6.0, 0.1, 1.0) ** gamma
    plant, meat = forcing["plant_supply"] * 0.5 * f, forcing["meat_supply"] * 0.5 * f
    marine = np.exp(-sites["d_coast_km"] / 25.0) * np.clip((28.0 - sites["sst_annual_c"]) / 20.0, 0.2, 1.0)
    annual = 3000.0 * marine + 100.0 * sites["w_fresh"]
    fish = np.broadcast_to(annual / plant.shape[0], plant.shape).copy()
    return simulate_foraging(plant, meat, params=ForagingParams(**spec["kernel_parameters"]), display="mean",
                             aquatic_supply=fish, **run)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/forager_binford_20261031")
    a = ap.parse_args()
    df = binford(); df = df[(df["subpop"] == "n") & (df["density"].astype(float) > 0)].copy()
    tavg, prec = worldclim_months()
    rows, T, P = [], [], []
    for _, r in df.iterrows():
        lat, lon = float(r["latitude"]), float(r["longitude"])
        c = site_climate(tavg, prec, lat, lon)
        if c is None:
            continue
        rows.append(dict(name=str(r["name"]), area=str(r["wc.area"]), lat=lat, lon=lon, density_km2=float(r["density"]) / 100.0,
                         fishing=float(r["fishing"]), gathering=float(r["gatherin"]), hunting=float(r["hunting"]), store=float("nan")))
        T.append(c[0]); P.append(c[1])
    sites = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    sites["T"] = np.array(T).T; sites["P"] = np.array(P).T; sites["npp"] = miami_npp(sites["T"], sites["P"])
    sites["gs"] = (sites["T"] >= 5.0).sum(0).astype(float)
    inputs = {(s["name"], round(s["lat"], 4), round(s["lon"], 4)): s
              for s in json.loads((a.out / "aquatic_inputs.json").read_text())["sites"]}
    for key in ("d_coast_km", "sst_annual_c", "w_fresh"):
        sites[key] = np.array([float(inputs[(r["name"], round(r["lat"], 4), round(r["lon"], 4))][key]) for r in rows])
    area = sites["area"]
    sets = dict(fit=area == "NNA", arctic=area == "ARC", wna=area == "WNA", world=~np.isin(area, list(FIT_AREAS)))
    print({k: int(v.sum()) for k, v in sets.items()}, "GS median by set", {k: float(np.median(sites['gs'][v])) for k, v in sets.items()}, flush=True)
    spec = specification(); res = {}
    for g in GAMMAS:
        r_ = run_D(sites, spec, g)
        res[g] = {k: metrics(r_["density_people_km2"], sites, m, r_) for k, m in sets.items()}
        print(g, {k: (round(v["median_abs_log10_error"], 3), round(v["median_log10_bias"], 2)) for k, v in res[g].items()}, flush=True)
    best = min(GAMMAS, key=lambda g: (round(res[g]["fit"]["median_abs_log10_error"], 6), g))
    b, z = res[best], res[0]
    ok = (best > 0 and b["arctic"]["median_abs_log10_error"] <= z["arctic"]["median_abs_log10_error"] - 0.05
          and all(b[k]["median_abs_log10_error"] <= z[k]["median_abs_log10_error"] + 0.01 and
                  b[k]["density_spearman"] >= z[k]["density_spearman"] - 0.01 for k in ("wna", "world")))
    out = dict(addendum=str(PLAN.relative_to(ROOT)), gamma_fitted=best, results={str(g): v for g, v in res.items()}, adopted=bool(ok),
               rule=json.loads(PLAN.read_text())["adopt_if"])
    (a.out / "binford_cold.json").write_text(json.dumps(out, indent=1, default=float))
    print(json.dumps(dict(gamma=best, adopted=ok), indent=1))


if __name__ == "__main__":
    main()
