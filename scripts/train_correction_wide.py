"""K1: the Earth temperature correction trained on every region with a run (dev31 + spent sets, 97), with geographic
leave-one-cluster-out instead of the 12 hand-fixed clusters (scripts/train_earth_correction.py otherwise unchanged:
same features, trees, weight grid and selection rule, applied to all regions).

Clusters: regions whose centres lie within LINK_KM of each other are joined (single linkage), and the 12 original
clusters are never split, so no held-out region has a neighbour in its own training set. The comparison that
matters is the held-out error on the original 31 regions against the 31-region recipe on the same physics.

    .venv/bin/python -I scripts/train_correction_wide.py --runs output/ppe_20261127/edgez/zonal \
        --params calibration/local_accuracy_20261023/r58w_params.json --out calibration/earth_correction_r58w_wide
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
import numpy as np  # noqa: E402

import train_earth_correction as T  # noqa: E402
from benchmark_local import DEV12_SPECS, temperature_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.correction import TemperatureCorrection  # noqa: E402

import os
LINK_KM = float(os.environ.get("K1_LINK_KM", "1500"))
SPECS = {'retired_a': 'calibration/sealed_20261031/regions.json', 'retired_b': 'calibration/sealed_20261031b/regions.json',
         'retired_c': 'calibration/sealed_20261101c/regions.json', 'tropical_t': 'calibration/tropical_check_20261122t/regions.json',
         'sealed_r': 'calibration/sealed_20261122r/regions.json', 'sealed_S18': 'calibration/sealed_20261123S18/regions.json',
         'sealed_U18': 'calibration/sealed_20261124U18/regions.json'}
PARTS = ['dev31', *SPECS]


def km(a, b):
    la1, lo1, la2, lo2 = map(np.radians, (a[0], a[1], b[0], b[1]))
    h = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371.0 * np.arcsin(np.sqrt(h))


def clusters(regions):
    parent = {r: r for r in regions}
    def find(r):
        while parent[r] != r:
            parent[r] = parent[parent[r]]; r = parent[r]
        return r
    def join(a, b):
        parent[find(a)] = find(b)
    c = {r: (earth.REGIONS[r]["lat0"], earth.REGIONS[r]["lon0"]) for r in regions}
    for i, a in enumerate(regions):
        for b in regions[i + 1:]:
            if km(c[a], c[b]) < LINK_KM:
                join(a, b)
    for members in T.CLUSTERS.values():
        for m in members[1:]:
            join(members[0], m)
    out = {}
    for r in regions:
        out.setdefault(find(r), []).append(r)
    return {f"k{i:02d}_{sorted(v)[0]}": sorted(v) for i, v in enumerate(sorted(out.values(), key=lambda v: sorted(v)[0]))}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", required=True, help="folder holding candidate_<part> benchmark runs")
    ap.add_argument("--params", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    for f in SPECS.values():
        earth.REGIONS.update(json.loads((ROOT / f).read_text()))
    data, cell_km, dev31 = {}, None, None
    for part in PARTS:
        run = Path(a.runs) / f"candidate_{part}"; s = json.loads((run / "summary.json").read_text())
        assert s.get("complete") and all(v["status"] == "passed" for v in s["regions"].values()), part
        for r in s["regions"]:
            assert T.sha256(run / "cells" / f"{r}.npz") == s["regions"][r]["cells_sha256"], r
        cell_km = cell_km or s["cell_km"]; assert s["cell_km"] == cell_km
        data.update(T.load_cells(run, sorted(s["regions"]), cell_km))
        if part == "dev31":
            dev31 = sorted(s["regions"])
    regions = sorted(data)
    K = clusters(regions)
    print(f"{len(regions)} regions in {len(K)} clusters", flush=True)
    out = Path(a.out); (out / "folds").mkdir(parents=True, exist_ok=True)
    comp = {}
    for name, members in K.items():
        train = [r for r in regions if r not in members]
        shape, level = T.fit(data, train)
        fold = TemperatureCorrection(shape, level, dict(shape_weight=1.0, level_weight=1.0, fold=name, trained_on=train))
        for r in members:
            comp[r] = fold.components(data[r]["static"], data[r]["Ts"], data[r]["Ps"], T.EARTH_PHASE)
        fold.save(out / "folds" / f"{name}.npz")
    raw = {r: temperature_metrics(data[r]["Ts"], data[r]["To"]) for r in regions}
    mean = lambda d, rs: float(np.mean([d[r]["monthly_mae_C"] for r in rs]))
    grid = []
    for sw in T.SHAPE_WEIGHTS:
        for lw in T.LEVEL_WEIGHTS:
            per = {r: temperature_metrics(data[r]["Ts"] + sw * comp[r][0] + lw * comp[r][1][None], data[r]["To"]) for r in regions}
            ratio = {g: v / T.group_table(raw, "monthly_mae_C")[g] for g, v in T.group_table(per, "monthly_mae_C").items()}
            worst = max(regions, key=lambda r: per[r]["monthly_mae_C"] - raw[r]["monthly_mae_C"])
            row = dict(shape_weight=sw, level_weight=lw, monthly_mae_C=mean(per, regions), dev31_monthly_mae_C=mean(per, dev31),
                       group_ratio=ratio, worst_region=worst, worst_change_C=per[worst]["monthly_mae_C"] - raw[worst]["monthly_mae_C"])
            row["eligible"] = bool(all(v < 1.0 for v in ratio.values()) and row["worst_change_C"] <= T.MAX_REGION_WORSENING_C)
            grid.append(row)
            print(f"shape {sw} level {lw}: all {row['monthly_mae_C']:.4f} dev31 {row['dev31_monthly_mae_C']:.4f} "
                  f"worst {worst} {row['worst_change_C']:+.3f} eligible {row['eligible']}", flush=True)
    eligible = [g for g in grid if g["eligible"]]
    if not eligible:
        raise SystemExit("No weight pair satisfies the declared rule")
    best = min(eligible, key=lambda g: g["monthly_mae_C"])
    res = dict(link_km=LINK_KM, clusters=K, regions=len(regions), raw_all=mean(raw, regions), raw_dev31=mean(raw, dev31),
               selected=best, grid=grid, params=a.params, params_sha256=T.sha256(a.params), runs=a.runs)
    (out / "evaluation.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: res[k] for k in ("regions", "raw_all", "raw_dev31")} | dict(
        held_out_all=best["monthly_mae_C"], held_out_dev31=best["dev31_monthly_mae_C"],
        weights=(best["shape_weight"], best["level_weight"]), clusters=len(K)), indent=1))


if __name__ == "__main__":
    main()
