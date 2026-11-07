"""plan_D climate check (calibration/geography_control_20261107/plan_D.json): the map world on r44 physics with the
tier ramps (output/r44_world/candidate_001.pkl, from scripts/check_r44_map.py) against the same world with
terrain_file = height map v2; strict climate-zone agreement raw and with the r44 Earth corrections.

    .venv/bin/python -I scripts/check_terrain_v2_climate.py
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/terrain_v2_climate_check"
TERRAIN = "output/terrain_erosion_20261107/map_height_v2.npz"


def main():
    from build_atlas_variant import load
    from rotclimate.model import run_ensemble
    from add_corrected_layers import corrected_fields
    OUT.mkdir(parents=True, exist_ok=True); t = time.time()
    with open(ROOT / "output/r44_world/candidate_001.pkl", "rb") as f:
        base = pickle.load(f)["result"]
    p = load(ROOT / "calibration/map_world_r44/params.json").replace(downsample=8, terrain_file=TERRAIN)
    new = run_ensemble(p, [1, 2, 3], workers=3)
    print(f"terrain v2 world simulated in {time.time() - t:.0f} s", flush=True)
    with open(OUT / "terrain_v2_result.pkl", "wb") as f:
        pickle.dump(new, f)
    res = dict(plan="calibration/geography_control_20261107/plan_D.json", terrain_file=TERRAIN)
    cal = ROOT / "calibration/earth_correction_r44_20261107"
    for tag, r in (("ramps", base), ("terrain_v2", new)):
        dT, ratio, fit, change, _ = corrected_fields(r, cal)
        res[tag] = dict(raw_strict=fit["raw"]["strict_accuracy"] if "strict_accuracy" in fit["raw"] else None, fit=fit, change=change)
    g = new.grid; mask = g.land & g.inmap
    a, b = np.asarray(base.T, float), np.asarray(new.T, float)
    res["raw_T_mean_abs_diff_c"] = float(np.abs(b - a)[..., mask].mean())
    res["raw_P_ratio_median"] = float(np.median((np.asarray(new.P, float)[..., mask] + 1) / (np.asarray(base.P, float)[..., mask] + 1)))
    rs = lambda tag, k: res[tag]["fit"][k]["strict_accuracy"]
    res["delta_strict_points"] = dict(raw=100 * (rs("terrain_v2", "raw") - rs("ramps", "raw")), corrected=100 * (rs("terrain_v2", "corrected") - rs("ramps", "corrected")))
    res["adopt_for_climate"] = bool(res["delta_strict_points"]["corrected"] >= -0.5)
    (OUT / "summary.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(dict(delta=res["delta_strict_points"], T=res["raw_T_mean_abs_diff_c"], P=res["raw_P_ratio_median"], adopt=res["adopt_for_climate"]), indent=1))


if __name__ == "__main__":
    main()
