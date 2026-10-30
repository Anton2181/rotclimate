"""Train and cross-validate the Earth rain-pattern correction.

    python -I scripts/train_rain_pattern.py --run output/earth_correction_20261030/r39_dev31 \
        --fields output/earth_correction_20261030/fields_dev31 \
        --params calibration/local_accuracy_20261023/r39_params.json --out calibration/earth_rain_pattern_20261030

--run is a complete benchmark_local output and --fields the same regions'
full-grid monthly fields (scripts/collect_earth_fields.py). The target is the
monthly log ratio log((P_obs + c) / (P_sim + c)) minus its own Gaussian mean
over RAIN_LOCAL_KM (300 km): how rain should be redistributed locally, not how
much falls in a region (regional amounts did not transfer between continents),
and defined the same way on a domain of any size. The
predictors add the simulated monthly winds over the terrain to the
temperature correction's inputs (rotclimate.correction.WIND_FEATURES).

Scores are leave-one-cluster-out with the clusters of train_earth_correction.
The weight is chosen by a rule fixed before the formal runs (after exploratory
runs of the same design, recorded in the report): among
PATTERN_WEIGHTS, the lowest equal-region rain loss such that every policy
group improves and no region's loss rises by more than MAX_REGION_WORSENING.
The final model is refitted on all regions; fold models are kept for honest
checks elsewhere (scripts/evaluate_rain_pattern.py --holdout).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS, GROUPS  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.correction import (RAIN_FEATURES, RAIN_LOCAL_KM, RAIN_OFFSET_MM, RainPatternCorrection,  # noqa: E402
                                   TreeEnsemble, local_mean, rain_feature_stack, season_phase, static_features,
                                   wind_terrain_features)
from train_earth_correction import CLUSTERS, HGB, sha256  # noqa: E402

LEAF = 500                     # min cell-months per leaf
PATTERN_WEIGHTS = (1.0, 0.7, 0.5)
MAX_REGION_WORSENING = 0.05    # rain loss units
EARTH_PHASE = season_phase(365.0, 354.5)


def load(run, fields, regions, cell_km):
    out = {}
    for r in regions:
        z, f = np.load(Path(run) / "cells" / f"{r}.npz"), np.load(Path(fields) / f"{r}.npz")
        i, j = z["i"], z["j"]
        if not (np.array_equal(f["Tm"][:, i, j], z["Ts"]) and np.array_equal(f["Pm"][:, i, j], z["Ps"])):
            raise ValueError(f"{r}: fields do not belong to this run")
        g = earth.region_case(r, cell_km).grid
        mask = np.zeros(g.land.shape, bool)
        mask[i, j] = True
        order = np.lexsort((j, i))                     # np.nonzero order, as wind_terrain_features
        static = {k: v[mask] for k, v in static_features(g).items()}
        wind = wind_terrain_features(g, f["um"], f["vm"], mask)
        Ts, Ps = z["Ts"][:, order].astype(float), z["Ps"][:, order].astype(float)
        Po, To = z["Po"][:, order].astype(float), z["To"][:, order].astype(float)
        y = np.log((Po + RAIN_OFFSET_MM) / (Ps + RAIN_OFFSET_MM))
        out[r] = dict(static=static, wind=wind, Ts=Ts, Ps=Ps, Po=Po, To=To, mask=mask, cell_km=g.cell_km,
                      X=rain_feature_stack(static, wind, Ts, Ps, EARTH_PHASE),
                      target=(y - local_mean(y, mask, g.cell_km)).T)    # [cells, 12], local mean removed
    return out


def fit(data, regions):
    from sklearn.ensemble import HistGradientBoostingRegressor

    X = np.concatenate([data[r]["X"] for r in regions]).reshape(-1, len(RAIN_FEATURES))
    y = np.concatenate([data[r]["target"] for r in regions]).ravel()
    w = np.concatenate([np.full(data[r]["X"].shape[0] * 12, 1.0 / data[r]["X"].shape[0]) for r in regions])
    return TreeEnsemble.from_sklearn(HistGradientBoostingRegressor(min_samples_leaf=LEAF, **HGB).fit(X, y, sample_weight=w))


def loss(P, Po):
    return local_metrics(P, Po, np.ones(P.shape[1], bool))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--fields", required=True)
    ap.add_argument("--params", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    import sklearn

    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    summary = json.loads((Path(args.run) / "summary.json").read_text())
    if not summary.get("complete") or any(v["status"] != "passed" for v in summary["regions"].values()):
        raise ValueError("Train only on a complete, fully passed benchmark run")
    regions = sorted(summary["regions"])
    if sorted(sum(CLUSTERS.values(), [])) != regions:
        raise ValueError("Every training region must sit in exactly one fixed cluster")
    for r in regions:
        if sha256(Path(args.run) / "cells" / f"{r}.npz") != summary["regions"][r]["cells_sha256"]:
            raise ValueError(f"{r}: cells differ from the run's record")
    data = load(args.run, args.fields, regions, summary["cell_km"])
    out = Path(args.out)
    (out / "folds").mkdir(parents=True, exist_ok=True)

    pattern = {}
    for name, members in CLUSTERS.items():
        train = [r for r in regions if r not in members]
        fold = RainPatternCorrection(fit(data, train), dict(pattern_weight=1.0, fold=name, trained_on=train))
        for r in members:
            d = data[r]
            pattern[r] = fold.log_ratio(d["static"], d["wind"], d["Ts"], d["Ps"], EARTH_PHASE, d["mask"], d["cell_km"])
        fold.save(out / "folds" / f"{name}.npz")
        print(f"fold {name}: trained on {len(train)} regions", flush=True)

    raw = {r: loss(data[r]["Ps"], data[r]["Po"]) for r in regions}
    groups = dict(GROUPS, all=regions)

    def table(per, key="loss"):
        return {g: float(np.mean([per[r][key] for r in m])) for g, m in groups.items()}

    grid = []
    for a in PATTERN_WEIGHTS:
        per = {r: loss(np.maximum((data[r]["Ps"] + RAIN_OFFSET_MM) * np.exp(a * pattern[r]) - RAIN_OFFSET_MM, 0.0),
                       data[r]["Po"]) for r in regions}
        ratio = {g: v / table(raw)[g] for g, v in table(per).items()}
        worst = max(regions, key=lambda r: per[r]["loss"] - raw[r]["loss"])
        row = dict(pattern_weight=a, loss=table(per)["all"], group_ratio=ratio, worst_region=worst,
                   worst_change=per[worst]["loss"] - raw[worst]["loss"],
                   regions_worse=sum(per[r]["loss"] > raw[r]["loss"] for r in regions), per_region=per)
        row["eligible"] = bool(all(v < 1.0 for v in ratio.values()) and row["worst_change"] <= MAX_REGION_WORSENING)
        grid.append(row)
        print(f"weight {a}: rain loss {row['loss']:.4f} (raw {table(raw)['all']:.4f}) worst {worst} "
              f"{row['worst_change']:+.3f} eligible {row['eligible']}", flush=True)
    eligible = [g for g in grid if g["eligible"]]
    if not eligible:
        raise SystemExit("No weight satisfies the declared rule; nothing is adopted")
    best = min(eligible, key=lambda g: g["loss"])
    meta = dict(pattern_weight=best["pattern_weight"], physics_params=str(Path(args.params)),
                physics_params_sha256=sha256(args.params), run=str(args.run), run_identity=summary["identity"],
                fields=str(args.fields), cell_km=summary["cell_km"], trained_on=regions, clusters=CLUSTERS, hgb=HGB,
                min_samples_leaf=LEAF, local_km=RAIN_LOCAL_KM, sklearn=sklearn.__version__, held_out_loss=best["loss"],
                raw_loss=table(raw)["all"])
    RainPatternCorrection(fit(data, regions), meta).save(out / "correction.npz")
    for name in CLUSTERS:
        fold = RainPatternCorrection.load(out / "folds" / f"{name}.npz")
        fold.meta.update(pattern_weight=best["pattern_weight"])
        fold.save(out / "folds" / f"{name}.npz")
    keys = ("loss", "annual_log_rmse", "monthly_mae_mm", "annual_within_25pct", "seasonality_total_variation")
    evaluation = dict(rule=dict(pattern_weights=PATTERN_WEIGHTS, max_region_worsening=MAX_REGION_WORSENING,
                                select="lowest all-region rain loss with every group improved"),
                      grid=[{k: v for k, v in g.items() if k != "per_region"} for g in grid], selected_weight=best["pattern_weight"],
                      raw=raw, held_out=best["per_region"],
                      groups=dict(raw={k: table(raw, k) for k in keys}, held_out={k: table(best["per_region"], k) for k in keys}))
    (out / "evaluation.json").write_text(json.dumps(evaluation, indent=1))
    files = {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*.npz"))}
    (out / "protocol.json").write_text(json.dumps(dict(script_sha256=sha256(__file__),
        module_sha256=sha256(ROOT / "rotclimate/correction.py"), files=files, meta=meta), indent=1))
    print(f"selected weight {best['pattern_weight']}: held-out rain loss {best['loss']:.4f} (raw {meta['raw_loss']:.4f})")


if __name__ == "__main__":
    main()
