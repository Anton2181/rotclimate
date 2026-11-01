"""Forager lifeways from FORGE (calibration/forager_binford_20261031/addendum_lifeways14_20261101.json).

    python -I scripts/forager_lifeways.py --out output/forager_binford_20261031
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import cohen_kappa_score, confusion_matrix  # noqa: E402

from forager_earth_test import binford, site_climate, worldclim_months  # noqa: E402
from forager_salmon import run_D  # noqa: E402
from foraging.forcing import miami_npp, specification  # noqa: E402

PLAN = ROOT / "calibration/forager_binford_20261031/addendum_lifeways14_20261101.json"
CLASSES = ("hunting", "gathering", "fishing")


def features(res, npp):
    fish, meat = res["mean_fish_share"], res["mean_meat_fraction"]
    return np.column_stack([np.log10(np.maximum(res["density_people_km2"], 1e-4)), (1 - fish) * meat, (1 - fish) * (1 - meat),
                            fish, res["mean_scarcity_days_year"] / 365.0, np.log10(np.maximum(npp, 1.0))])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/forager_binford_20261031")
    a = ap.parse_args()
    df = binford(); df = df[(df["subpop"] == "n") & (df["density"].astype(float) > 0)].copy()
    tavg, prec = worldclim_months()
    rows, T, P = [], [], []
    for _, r in df.iterrows():
        c = site_climate(tavg, prec, float(r["latitude"]), float(r["longitude"]))
        if c is None:
            continue
        rows.append(dict(name=str(r["name"]), area=str(r["wc.area"]), lat=float(r["latitude"]), lon=float(r["longitude"]),
                         density=float(r["density"]) / 100.0, h=float(r["hunting"]), g=float(r["gatherin"]), f=float(r["fishing"]),
                         nomov=float(r["nomov"]) if str(r["nomov"]) not in ("nan", "<NA>") else np.nan))
        T.append(c[0]); P.append(c[1])
    s = {k: np.array([x[k] for x in rows]) for k in rows[0]}
    s["T"] = np.array(T).T; s["P"] = np.array(P).T; s["npp"] = miami_npp(s["T"], s["P"])
    inputs = {(x["name"], round(x["lat"], 4), round(x["lon"], 4)): x for x in json.loads((a.out / "aquatic_inputs.json").read_text())["sites"]}
    for key in ("d_coast_km", "sst_annual_c", "w_fresh"):
        s[key] = np.array([float(inputs[(x["name"], round(x["lat"], 4), round(x["lon"], 4))][key]) for x in rows])
    s["s_salmon"] = np.zeros(len(rows))
    res = run_D(s, specification(), 0)
    X = features(res, s["npp"])
    obs = np.stack([s["h"], s["g"] + 1e-6, s["f"] + 2e-6], 1)      # ties go to fishing, then gathering
    y = obs.argmax(1)
    area = s["area"]
    held = np.full(len(y), -1)
    for ar in sorted(set(area)):
        m = area == ar
        mu, sd = X[~m].mean(0), X[~m].std(0) + 1e-9
        clf = LogisticRegression(max_iter=4000, C=1.0, class_weight="balanced").fit((X[~m] - mu) / sd, y[~m])
        held[m] = clf.predict((X[m] - mu) / sd)
    acc = float((held == y).mean()); kappa = float(cohen_kappa_score(y, held))
    geo = np.array([np.bincount(y[area == ar], minlength=3).argmax() for ar in area])
    out = dict(addendum=str(PLAN.relative_to(ROOT)), n=int(len(y)), accuracy=acc, kappa=kappa,
               confusion=confusion_matrix(y, held, labels=[0, 1, 2]).tolist(), classes=CLASSES,
               area_majority_reference=dict(accuracy=float((geo == y).mean()), kappa=float(cohen_kappa_score(y, geo))),
               majority_class_baseline=float(np.bincount(y).max() / len(y)),
               by_area={ar: dict(n=int((area == ar).sum()), accuracy=float((held[area == ar] == y[area == ar]).mean())) for ar in sorted(set(area))})
    rule = json.loads(PLAN.read_text())["adopt_if"]
    out["adopted"] = bool(acc >= 0.60 and kappa >= 0.40); out["rule"] = rule
    if out["adopted"]:
        mu, sd = X.mean(0), X.std(0) + 1e-9
        clf = LogisticRegression(max_iter=4000, C=1.0, class_weight="balanced").fit((X - mu) / sd, y)
        ok = np.isfinite(s["nomov"]) & (s["nomov"] > 0)
        slope, icpt = np.polyfit(np.log10(np.maximum(res["density_people_km2"][ok], 1e-4)), np.log10(s["nomov"][ok]), 1)
        model = dict(source=str(PLAN.relative_to(ROOT)), classes=CLASSES,
                     features=["log10 density", "hunting share", "gathering share", "fish share", "scarcity days / 365", "log10 NPP"],
                     mean=mu.tolist(), std=sd.tolist(), coef=clf.coef_.tolist(), intercept=clf.intercept_.tolist(),
                     moves=dict(note="log10 residential moves per year = a + b log10 FORGE density (Binford groups)", a=float(icpt), b=float(slope)))
        (ROOT / "data/forager_lifeways.json").write_text(json.dumps(model, indent=1))
    (a.out / "binford_lifeways.json").write_text(json.dumps(out, indent=1))
    print(json.dumps({k: v for k, v in out.items() if k not in ("by_area", "rule")}, indent=1))


if __name__ == "__main__":
    main()
