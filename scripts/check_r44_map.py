"""Does r44 (r43 + e72d plateau-steered storms) change the invented map's climate, and how much do the r44-trained
Earth corrections move its corrected climate? Runs the published world (calibration/map_world_r43/params.json, and
the same with r44's four e72 fields: calibration/map_world_r44/params.json) for seeds 1-3 at the atlas downsample,
compares the raw fields, and applies each release's own corrections (r43 corrections to the r43 run, r44 to r44).

    .venv/bin/python -I scripts/check_r44_map.py
Writes output/r44_map_check/summary.json and the r44 checkpoint output/r44_world/candidate_001.pkl.
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
OUT = ROOT / "output/r44_map_check"
SEEDS = [1, 2, 3]


def identity(p):
    """The checkpoint identity scripts/build_atlas_variant.py verifies."""
    ident = dict(params=json.loads(json.dumps(asdict(p))), seeds=SEEDS, sources={
        f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT / "rotclimate").glob("*.py")
        if f.name not in {"atlas.py", "render.py", "biomes.py", "climate_fields.py"}})
    ident["map_inputs"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (ROOT / "data/source").iterdir() if f.is_file()}
    return ident


def main():
    from build_atlas_variant import load
    from rotclimate.model import run_ensemble
    from add_corrected_layers import corrected_fields
    OUT.mkdir(parents=True, exist_ok=True)
    runs = {}
    for tag in ("r43", "r44"):
        t = time.time()
        p = load(ROOT / f"calibration/map_world_{tag}/params.json").replace(downsample=8)
        runs[tag] = run_ensemble(p, SEEDS, workers=3)
        print(f"{tag}: simulated in {time.time() - t:.0f} s", flush=True)
        if tag == "r44":
            ck = ROOT / "output/r44_world/candidate_001.pkl"; ck.parent.mkdir(parents=True, exist_ok=True)
            with ck.open("wb") as f:
                pickle.dump(dict(identity=identity(p), result=runs[tag]), f)
    a, b = runs["r43"], runs["r44"]
    raw = {k: float(np.nanmax(np.abs(np.asarray(getattr(a, k), float) - np.asarray(getattr(b, k), float)))) for k in ("T", "P", "u", "v")}
    res = dict(seeds=SEEDS, raw_max_abs_difference=raw, raw_identical=all(v == 0.0 for v in raw.values()))
    fields = {}
    for tag, cal in (("r43", "calibration/earth_correction_r43_20261103"), ("r44", "calibration/earth_correction_r44_20261107")):
        dT, ratio, fit, change, models = corrected_fields(runs[tag], ROOT / cal)
        fields[tag] = (dT, ratio); res[tag] = dict(fit=fit, change=change)
    g = b.grid; mask = g.land & g.inmap
    dd = fields["r44"][0] - fields["r43"][0]; rr = fields["r44"][1] / fields["r43"][1]
    res["r44_minus_r43_corrected"] = dict(
        temperature_mean_c=float(dd[:, mask].mean()), temperature_mean_abs_c=float(np.abs(dd[:, mask]).mean()),
        temperature_p95_abs_c=float(np.percentile(np.abs(dd[:, mask]), 95)), temperature_max_abs_c=float(np.abs(dd[:, mask]).max()),
        rain_ratio_median=float(np.median(rr[:, mask])), rain_ratio_p05=float(np.percentile(rr[:, mask], 5)), rain_ratio_p95=float(np.percentile(rr[:, mask], 95)))
    (OUT / "summary.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
