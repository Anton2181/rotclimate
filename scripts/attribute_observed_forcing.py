"""Attribute Earth errors to the circulation and the sea by swapping in observations.

    python -I scripts/attribute_observed_forcing.py --params calibration/local_accuracy_20261023/r39_params.json \
        --regions dev31 --out output/physics_gaps_20261030/attribution.json

Runs every region four ways: the model as it is, with the reanalysis monthly
surface winds in place of the model's (wind_source="observed", NCEP/NCAR
sigma-0.995 1991-2020; scripts/prepare_ncep_reference.py), with the WOA18
monthly sea surface (sst_source="observed"), and with both. Everything else,
including all fitted settings, is unchanged, so the differences say how much
of each region's error the model's own winds and sea cause, given physics that
was tuned around them. Diagnostic only: an invented map has no observations.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scipy import ndimage as ndi  # noqa: E402

from benchmark_local import DEV12_SPECS, DEV31, GROUPS, temperature_metrics  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402

NCEP = ROOT / "data/cache/ncep_ltm/ncep_surface_ltm.npz"
CONFIGS = dict(model={}, observed_wind=dict(wind_source="observed"), observed_sst=dict(sst_source="observed"),
               observed_both=dict(wind_source="observed", sst_source="observed"))
_REF = None


def reference():
    global _REF
    if _REF is None:
        with np.load(NCEP) as z:                      # read fully: workers must not share a lazy zip handle
            _REF = {k: z[k] for k in z.files}
    return _REF


def ncep_at(case, keys=("u", "v", "pw", "slp", "rh")):
    """NCEP monthly fields [12, ny, nx] on a region's grid, in the model's frame
    (mirrored southern regions: months shifted by six, northward wind negated)."""
    ref, g = reference(), case.grid
    south = earth.REGIONS[case.name]["lat0"] < 0
    lat = -g.lat if south else g.lat
    i, j = (90.0 - lat) / 2.5, (case.lon % 360.0) / 2.5
    out = {}
    for k in keys:
        a = np.concatenate([ref[k], ref[k][:, :, :1]], axis=2)
        f = np.stack([ndi.map_coordinates(a[m], [i, j], order=1, mode="nearest") for m in range(12)])
        out[k] = np.roll(f, 6, axis=0) if south else f
    if south and "v" in out:
        out["v"] = -out["v"]
    return out


def one(job):
    region, params_path, name, overrides, cell_km, specs = job
    earth.REGIONS.update(specs)
    case = earth.region_case(region, cell_km)
    g = case.grid
    p = earth.earth_params(load_params(params_path), case).replace(**overrides)
    if p.wind_source == "observed":
        w = ncep_at(case, ("u", "v"))
        g.obs_wind = np.stack([w["u"], w["v"]], axis=1)
    try:
        res = ClimateModel(p, g).run(steps=p.steps_per_year)
    except Exception as error:
        return region, name, dict(status="failed", error=repr(error))
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    rain = local_metrics(np.maximum(st["Pm"], 0.0), np.nan_to_num(case.obs_P), m)
    return region, name, dict(status="passed" if res.numerics.get("all_checks_passed") else "numerics_failed",
                              temperature=temperature_metrics(st["Tm"][:, m], case.obs_T[:, m]), rain=rain,
                              monthly_rain_sim=st["Pm"][:, m].mean(1).tolist(), monthly_rain_obs=case.obs_P[:, m].mean(1).tolist())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--params", required=True)
    ap.add_argument("--regions", nargs="+", default=["dev31"])
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    specs = json.loads(DEV12_SPECS.read_text())
    regions = DEV31 if args.regions == ["dev31"] else args.regions
    reference()
    jobs = [(r, args.params, name, ov, args.cell_km, specs) for name, ov in CONFIGS.items() for r in regions]
    results = {name: {} for name in CONFIGS}
    with Pool(args.workers) as pool:
        for region, name, rec in pool.imap_unordered(one, jobs):
            results[name][region] = rec
            print(f"{name:14s} {region:18s} {rec['status']}", flush=True)
    groups = dict(GROUPS, all=list(regions))
    summary = {name: {g: dict(T_monthly_mae=float(np.mean([v[r]["temperature"]["monthly_mae_C"] for r in m if v.get(r, {}).get("status") == "passed"])),
                              P_loss=float(np.mean([v[r]["rain"]["loss"] for r in m if v.get(r, {}).get("status") == "passed"])))
                      for g, m in groups.items() if any(r in regions for r in m)} for name, v in results.items()}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(dict(params=args.params, cell_km=args.cell_km, configs=CONFIGS,
                                              summary=summary, regions=results), indent=1))
    for name, row in summary.items():
        print(name, {g: {k: round(x, 4) for k, x in v.items()} for g, v in row.items()})


if __name__ == "__main__":
    main()
