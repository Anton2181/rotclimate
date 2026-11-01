"""FORGE on untested axes: storage, animal food, mobility (calibration/forager_binford_20261031/addendum_axes12_20261101.json).

    python -I scripts/forager_axes.py --out output/forager_binford_20261031
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from forager_earth_test import binford, site_climate, worldclim_months  # noqa: E402
from forager_salmon import run_D  # noqa: E402
from foraging.forcing import miami_npp, specification  # noqa: E402

PLAN = ROOT / "calibration/forager_binford_20261031/addendum_axes12_20261101.json"


def rho(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 8:
        return dict(rho=None, n=int(m.sum()))
    r, p = spearmanr(a[m], b[m])
    return dict(rho=float(r), p=float(p), n=int(m.sum()))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/forager_binford_20261031")
    a = ap.parse_args()
    df = binford(); df = df[(df["subpop"] == "n") & (df["density"].astype(float) > 0)].copy()
    tavg, prec = worldclim_months()
    rows, T, P = [], [], []
    num = lambda v: float(v) if str(v) not in ("nan", "<NA>", "None") else np.nan
    for _, r in df.iterrows():
        c = site_climate(tavg, prec, float(r["latitude"]), float(r["longitude"]))
        if c is None:
            continue
        rows.append(dict(name=str(r["name"]), area=str(r["wc.area"]), lat=float(r["latitude"]), lon=float(r["longitude"]),
                         qtstor=num(r["qtstor"]), nomov=num(r["nomov"]), hunting=num(r["hunting"]), gathering=num(r["gatherin"])))
        T.append(c[0]); P.append(c[1])
    sites = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    sites["T"] = np.array(T).T; sites["P"] = np.array(P).T; sites["npp"] = miami_npp(sites["T"], sites["P"])
    inputs = {(s["name"], round(s["lat"], 4), round(s["lon"], 4)): s
              for s in json.loads((a.out / "aquatic_inputs.json").read_text())["sites"]}
    for key in ("d_coast_km", "sst_annual_c", "w_fresh"):
        sites[key] = np.array([float(inputs[(r["name"], round(r["lat"], 4), round(r["lon"], 4))][key]) for r in rows])
    sites["s_salmon"] = np.zeros(len(rows))
    res = run_D(sites, specification(), 0)
    stored, meat, hours = res["mean_stored_share"], res["mean_meat_fraction"], res["mean_foraging_hours_day"]
    scarcity, dens = res["mean_scarcity_days_year"], res["density_people_km2"]
    hunt_share = sites["hunting"] / np.maximum(sites["hunting"] + sites["gathering"], 1e-9)
    out = dict(addendum=str(PLAN.relative_to(ROOT)), n=len(rows),
               T1_storage=rho(stored, sites["qtstor"]), T2_animal=rho(meat, hunt_share),
               T3_mobility_hours=rho(hours, sites["nomov"]), T3_mobility_density=rho(dens, sites["nomov"]),
               T4_shortfall_storage=rho(scarcity, sites["qtstor"]), by_area={})
    for ar in sorted(set(sites["area"])):
        m = sites["area"] == ar
        if m.sum() >= 10:
            out["by_area"][ar] = dict(n=int(m.sum()), T1=rho(stored[m], sites["qtstor"][m])["rho"], T2=rho(meat[m], hunt_share[m])["rho"],
                                      T3_density=rho(dens[m], sites["nomov"][m])["rho"])
    out["ranges"] = dict(stored_share=[float(np.nanmin(stored)), float(np.nanmedian(stored)), float(np.nanmax(stored))],
                         meat_fraction=[float(np.nanmin(meat)), float(np.nanmedian(meat)), float(np.nanmax(meat))])
    (a.out / "binford_axes.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
