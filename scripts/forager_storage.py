"""F13: FORGE's food store scored on storage itself
(calibration/forager_binford_20261031/addendum_storage13_20261101.json).

    python -I scripts/forager_storage.py --out output/forager_binford_20261031
"""
from __future__ import annotations

import argparse
import copy
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

PLAN = ROOT / "calibration/forager_binford_20261031/addendum_storage13_20261101.json"
CAPS = (250.0, 500.0, 1000.0, 2000.0, 4000.0)
DECAYS = (0.0, 0.005)
AREAS = ("SW", "AUS", "BC NWC", "NNA", "ARC", "WNA", "REST")


def rho(a, b):
    m = np.isfinite(a) & np.isfinite(b)
    r, p = spearmanr(a[m], b[m])
    return float(r) if np.isfinite(r) else 0.0


def dens_err(pred, obs):
    return float(np.median(np.abs(np.log10(np.maximum(pred, 1e-4)) - np.log10(obs))))


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
                         qtstor=num(r["qtstor"]), density=float(r["density"]) / 100.0))
        T.append(c[0]); P.append(c[1])
    S = {k: np.array([row[k] for row in rows]) for k in rows[0]}
    S["T"] = np.array(T).T; S["P"] = np.array(P).T; S["npp"] = miami_npp(S["T"], S["P"])
    inputs = {(s["name"], round(s["lat"], 4), round(s["lon"], 4)): s
              for s in json.loads((a.out / "aquatic_inputs.json").read_text())["sites"]}
    for key in ("d_coast_km", "sst_annual_c", "w_fresh"):
        S[key] = np.array([float(inputs[(r["name"], round(r["lat"], 4), round(r["lon"], 4))][key]) for r in rows])
    S["s_salmon"] = np.zeros(len(rows))
    area = np.array([x if x in AREAS else "REST" for x in S["area"]])
    ok = np.isfinite(S["qtstor"])
    base_spec = specification()

    def run(cap, decay):
        spec = copy.deepcopy(base_spec)
        spec["kernel_parameters"]["storage_capacity_mj"] = cap
        spec["kernel_parameters"]["storage_decay_day"] = decay
        r = run_D(S, spec, 0)
        return dict(stored=np.asarray(r["mean_stored_share"], float), dens=np.asarray(r["density_people_km2"], float),
                    scarcity=np.asarray(r["mean_scarcity_days_year"], float))
    D = run(0.0, 0.0)
    settings = [(c, d) for c in CAPS for d in DECAYS]
    R = {}
    for c, d in settings:
        R[(c, d)] = run(c, d)
        x = R[(c, d)]
        print(f"cap {c:6.0f} decay {d:.3f}: rho {rho(x['stored'][ok], S['qtstor'][ok]):+.3f}  density err {dens_err(x['dens'], S['density']):.3f} "
              f"(D {dens_err(D['dens'], S['density']):.3f})  stored share median {np.median(x['stored']):.3f}", flush=True)
    pred_store = np.full(len(rows), np.nan); pred_dens = np.full(len(rows), np.nan); chosen = {}
    for ar in AREAS:
        te = area == ar; tr = ~te
        if not te.any():
            continue
        best = None
        for c, d in settings:
            x = R[(c, d)]
            if dens_err(x["dens"][tr], S["density"][tr]) > dens_err(D["dens"][tr], S["density"][tr]) + 0.02:
                continue
            r_ = rho(x["stored"][tr & ok], S["qtstor"][tr & ok])
            if best is None or r_ > best[0]:
                best = (r_, (c, d))
        if best is None:
            pred_store[te] = D["stored"][te]; pred_dens[te] = D["dens"][te]; chosen[ar] = None
        else:
            x = R[best[1]]; pred_store[te] = x["stored"][te]; pred_dens[te] = x["dens"][te]; chosen[ar] = list(best[1])
    held_rho = rho(pred_store[ok], S["qtstor"][ok])
    scar_rho = rho(D["scarcity"][ok], S["qtstor"][ok])
    err_d, err_h = dens_err(D["dens"], S["density"]), dens_err(pred_dens, S["density"])
    adopt = held_rho >= 0.30 and held_rho >= scar_rho + 0.10 and err_h <= err_d + 0.02
    cal = (area == "SW") & (S["lat"] > 32.5) & (S["lat"] < 42.0) & (S["lon"] < -114.0)
    out = dict(addendum=str(PLAN.relative_to(ROOT)), n=len(rows), heldout_rho=held_rho, scarcity_rho_D=scar_rho,
               density_err_D=err_d, density_err_heldout=err_h, chosen=chosen, adopted=bool(adopt),
               settings={f"{c:g}/{d:g}": dict(rho=rho(R[(c, d)]["stored"][ok], S["qtstor"][ok]),
                                              density_err=dens_err(R[(c, d)]["dens"], S["density"]),
                                              stored_median=float(np.median(R[(c, d)]["stored"]))) for c, d in settings},
               by_area={ar: dict(n=int((area == ar).sum()), rho_heldout=rho(pred_store[(area == ar) & ok], S["qtstor"][(area == ar) & ok])
                                 if ((area == ar) & ok).sum() >= 8 else None,
                                 qtstor_mean=float(np.nanmean(S["qtstor"][area == ar]))) for ar in AREAS},
               california=dict(n=int(cal.sum()), stored_share=float(np.nanmean(pred_store[cal])) if cal.any() else None,
                               rest_sw=float(np.nanmean(pred_store[(area == "SW") & ~cal])),
                               qtstor=float(np.nanmean(S["qtstor"][cal])) if cal.any() else None))
    (a.out / "binford_storage13.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k != "settings"}, indent=1))


if __name__ == "__main__":
    main()
