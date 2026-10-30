"""Train and cross-validate the Earth monthly temperature correction.

    python -I scripts/train_earth_correction.py --run output/local/r39_dev31 \
        --params calibration/local_accuracy_20261023/r39_params.json \
        --out calibration/earth_correction_20261030

--run is a complete scripts/benchmark_local.py output (summary.json and the
per-region cells). Every honest score here is leave-one-cluster-out: the
regions are grouped into twelve geographic clusters fixed below (regions in a
cluster touch or overlap, so leaving out one region alone would let its
neighbours teach the model its own errors), and each cluster is corrected by
models trained on the other eleven. An invented map is an unseen continent;
this is the closest Earth test of that.

The two weights are chosen by a rule declared before the run: among the grid
below, the lowest equal-region monthly temperature MAE such that every policy
group improves and no region worsens by more than MAX_REGION_WORSENING_C.
The final model is then refitted on all regions with the chosen weights. The
held-out fold models are saved too, for honest checks at other resolutions
(scripts/evaluate_earth_correction.py --holdout).

Training needs scikit-learn; applying the correction needs only numpy/scipy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV12_SPECS, GROUPS, temperature_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.correction import FEATURES, TemperatureCorrection, TreeEnsemble, feature_stack, season_phase, static_features  # noqa: E402

CLUSTERS = dict(
    na_west=["california", "pacific_nw", "great_basin"],
    na_central=["southeast_us", "mexico", "texas_plains", "us_midwest"],
    europe=["iberia", "western_europe", "alps", "morocco", "british_isles", "eastern_europe"],
    mideast=["levant", "anatolia", "iran_plateau", "central_asia"],
    east_asia=["east_china", "north_china_plain", "japan", "manchuria", "korea"],
    se_australia=["east_australia", "victoria"],
    sa_west=["chile", "patagonia"],
    south_brazil=["south_brazil"], cape=["cape"], sw_australia=["sw_australia"],
    new_zealand=["new_zealand"], north_india=["north_india"])
HGB = dict(max_iter=150, learning_rate=0.1, max_leaf_nodes=31, l2_regularization=1.0,
           early_stopping=False, random_state=0)
SHAPE_LEAF, LEVEL_LEAF = 200, 1000          # min samples per leaf (cell-months)
SHAPE_WEIGHTS = (1.0, 0.8, 0.6)
LEVEL_WEIGHTS = (0.0, 0.3, 0.5)
MAX_REGION_WORSENING_C = 0.25
EARTH_PHASE = season_phase(365.0, 354.5)     # earth.earth_params calendar


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cluster_of(region):
    for name, members in CLUSTERS.items():
        if region in members:
            return name
    return None


def load_cells(run, regions, cell_km):
    """Per region: features [n, 12, f], simulated and observed T [12, n]."""
    out = {}
    for r in regions:
        z = np.load(Path(run) / "cells" / f"{r}.npz")
        case = earth.region_case(r, cell_km)
        static = static_features(case.grid)
        i, j = z["i"], z["j"]
        if not np.allclose(case.grid.lat[i, j], z["lat"]) or not np.allclose(case.grid.elev[i, j], z["elev"]):
            raise ValueError(f"{r}: saved cells do not match the rebuilt grid")
        cells = {k: v[i, j] for k, v in static.items()}
        out[r] = dict(X=feature_stack(cells, z["Ts"], z["Ps"], EARTH_PHASE), Ts=z["Ts"].astype(float),
                      To=z["To"].astype(float), static=cells, Ps=z["Ps"].astype(float))
    return out


def fit(data, regions):
    """Shape and level ensembles trained on regions (equal region weights)."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    X = np.concatenate([data[r]["X"] for r in regions])
    err = np.concatenate([(data[r]["To"] - data[r]["Ts"]).T for r in regions])        # [n, 12]
    w = np.concatenate([np.full(len(data[r]["X"]), 1.0 / len(data[r]["X"])) for r in regions])
    flat, ww = X.reshape(-1, len(FEATURES)), np.repeat(w, 12)
    shape_y = (err - err.mean(1, keepdims=True)).ravel()
    level_y = np.repeat(err.mean(1), 12)
    shape = HistGradientBoostingRegressor(min_samples_leaf=SHAPE_LEAF, **HGB).fit(flat, shape_y, sample_weight=ww)
    level = HistGradientBoostingRegressor(min_samples_leaf=LEVEL_LEAF, **HGB).fit(flat, level_y, sample_weight=ww)
    return TreeEnsemble.from_sklearn(shape), TreeEnsemble.from_sklearn(level)


def group_table(per_region, key):
    groups = dict(GROUPS, all=sorted(per_region))
    return {g: float(np.mean([per_region[r][key] for r in members if r in per_region]))
            for g, members in groups.items() if any(r in per_region for r in members)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True)
    ap.add_argument("--params", required=True, help="the physics parameters the run used")
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
    data = load_cells(args.run, regions, summary["cell_km"])
    out = Path(args.out)
    (out / "folds").mkdir(parents=True, exist_ok=True)

    # leave-one-cluster-out components (unweighted), one fold model per cluster
    comp = {}
    for name, members in CLUSTERS.items():
        train = [r for r in regions if r not in members]
        shape, level = fit(data, train)
        fold = TemperatureCorrection(shape, level, dict(shape_weight=1.0, level_weight=1.0, fold=name, trained_on=train))
        for r in members:
            comp[r] = fold.components(data[r]["static"], data[r]["Ts"], data[r]["Ps"], EARTH_PHASE)
        fold.save(out / "folds" / f"{name}.npz")
        print(f"fold {name}: trained on {len(train)} regions", flush=True)

    raw = {r: temperature_metrics(data[r]["Ts"], data[r]["To"]) for r in regions}
    grid = []
    for a in SHAPE_WEIGHTS:
        for b in LEVEL_WEIGHTS:
            per = {r: temperature_metrics(data[r]["Ts"] + a * comp[r][0] + b * comp[r][1][None], data[r]["To"]) for r in regions}
            ratio = {g: v / group_table(raw, "monthly_mae_C")[g] for g, v in group_table(per, "monthly_mae_C").items()}
            worst = max(regions, key=lambda r: per[r]["monthly_mae_C"] - raw[r]["monthly_mae_C"])
            row = dict(shape_weight=a, level_weight=b, monthly_mae_C=group_table(per, "monthly_mae_C")["all"],
                       group_ratio=ratio, worst_region=worst,
                       worst_change_C=per[worst]["monthly_mae_C"] - raw[worst]["monthly_mae_C"],
                       regions_worse=sum(per[r]["monthly_mae_C"] > raw[r]["monthly_mae_C"] for r in regions))
            row["eligible"] = bool(all(v < 1.0 for v in ratio.values()) and row["worst_change_C"] <= MAX_REGION_WORSENING_C)
            grid.append(row)
            print(f"shape {a} level {b}: T MAE {row['monthly_mae_C']:.4f} worst {worst} {row['worst_change_C']:+.3f} "
                  f"eligible {row['eligible']}", flush=True)
    eligible = [g for g in grid if g["eligible"]]
    if not eligible:
        raise SystemExit("No weight pair satisfies the declared rule; nothing is adopted")
    best = min(eligible, key=lambda g: g["monthly_mae_C"])
    a, b = best["shape_weight"], best["level_weight"]
    held_out = {r: temperature_metrics(data[r]["Ts"] + a * comp[r][0] + b * comp[r][1][None], data[r]["To"]) for r in regions}

    shape, level = fit(data, regions)
    meta = dict(shape_weight=a, level_weight=b, physics_params=str(Path(args.params)), physics_params_sha256=sha256(args.params),
                run=str(args.run), run_identity=summary["identity"], cell_km=summary["cell_km"], trained_on=regions,
                clusters=CLUSTERS, hgb=HGB, shape_min_samples_leaf=SHAPE_LEAF, level_min_samples_leaf=LEVEL_LEAF,
                sklearn=sklearn.__version__, held_out_monthly_mae_C=best["monthly_mae_C"],
                raw_monthly_mae_C=group_table(raw, "monthly_mae_C")["all"])
    TemperatureCorrection(shape, level, meta).save(out / "correction.npz")
    for name in CLUSTERS:                       # fold models carry the chosen weights too
        fold = TemperatureCorrection.load(out / "folds" / f"{name}.npz")
        fold.meta.update(shape_weight=a, level_weight=b)
        fold.save(out / "folds" / f"{name}.npz")
    evaluation = dict(rule=dict(shape_weights=SHAPE_WEIGHTS, level_weights=LEVEL_WEIGHTS,
                                max_region_worsening_C=MAX_REGION_WORSENING_C,
                                select="lowest all-region monthly MAE with every group improved"),
                      grid=grid, selected=best, raw=raw, held_out=held_out,
                      groups=dict(raw={k: group_table(raw, k) for k in ("monthly_mae_C", "annual_mae_C", "range_mae_C")},
                                  held_out={k: group_table(held_out, k) for k in ("monthly_mae_C", "annual_mae_C", "range_mae_C")}),
                      rain="not corrected: rain corrections tested in the same leave-one-cluster-out design made unseen continents worse")
    (out / "evaluation.json").write_text(json.dumps(evaluation, indent=1))
    files = {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob("*.npz"))}
    (out / "protocol.json").write_text(json.dumps(dict(script_sha256=sha256(__file__),
        module_sha256=sha256(ROOT / "rotclimate/correction.py"), files=files, meta=meta), indent=1))
    print(f"selected shape {a} level {b}: held-out T MAE {best['monthly_mae_C']:.4f} "
          f"(raw {meta['raw_monthly_mae_C']:.4f})")


if __name__ == "__main__":
    main()
