"""P7 diagnostic: why subtropical land peaks early on r41 (autumns cold relative to springs).

Runs the early-phase regions with r41's parameters as they are, with the
observed sea surface (WOA18), with observed winds (NCEP), and with both
(the existing diagnostic switches sst_source / wind_source), and reports each
region's first-harmonic phase error, spring and autumn bias, and the model
sea's own seasonal cycle against WOA18 over the region's sea cells.

    python -I scripts/diag_autumn_phase.py --out output/autumn_phase_20261101 [--workers 2]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

PARAMS = ROOT / "calibration/local_accuracy_20261023/r41_params.json"
CONF = {"model": {}, "obs_sst": {"sst_source": "observed"}, "obs_wind": {"wind_source": "observed"},
        "obs_both": {"wind_source": "observed", "sst_source": "observed"}}
REGIONS = ["levant", "anatolia", "iran_plateau", "morocco", "japan", "east_china", "korea", "texas_plains", "southeast_us"]


def harmonic(x):
    w = 2 * np.pi * (np.arange(12) + 0.5) / 12
    a, b = np.sum(x * np.cos(w)), np.sum(x * np.sin(w))
    return float(np.hypot(a, b) * 2 / 12), float(np.degrees(np.arctan2(b, a)) / 360 * 365)


def one(job):
    region, name, overrides = job
    from attribute_observed_forcing import ncep_at
    from benchmark_local import DEV12_SPECS
    from earth_benchmark import load_params
    from rotclimate import earth
    from rotclimate.koppen import monthly_stats
    from rotclimate.model import ClimateModel
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case = earth.region_case(region, 56.0); g = case.grid
    p = earth.earth_params(load_params(str(PARAMS)), case).replace(**overrides)
    if p.wind_source == "observed":
        w = ncep_at(case, ("u", "v")); g.obs_wind = np.stack([w["u"], w["v"]], axis=1)
    res = ClimateModel(p, g).run(steps=p.steps_per_year)
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    Ts, To = st["Tm"][:, m].mean(1), case.obs_T[:, m].mean(1)
    sea = g.inmap & ~g.land
    out = dict(region=region, conf=name, Ts=Ts.tolist(), To=To.tolist(), mae=float(np.abs(st["Tm"][:, m] - case.obs_T[:, m]).mean()))
    if sea.any() and g.obs_sst is not None:
        out["sea_model"] = st["Tm"][:, sea].mean(1).tolist(); out["sea_obs"] = np.asarray(g.obs_sst)[:, sea].mean(1).tolist()
    return out


def main():
    from multiprocessing import Pool
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/autumn_phase_20261101")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--confs", help="JSON {name: overrides} in place of the observed-forcing set")
    ap.add_argument("--regions", help="comma-separated regions in place of the early-phase set")
    ap.add_argument("--tag", default="diag")
    a = ap.parse_args()
    global CONF, REGIONS
    if a.confs:
        CONF = json.loads(a.confs)
    if a.regions:
        REGIONS = a.regions.split(",")
    a.out.mkdir(parents=True, exist_ok=True)
    with Pool(a.workers) as pool:
        rows = pool.map(one, [(r, n, CONF[n]) for r in REGIONS for n in CONF])
    for r in rows:
        Ts, To = np.array(r["Ts"]), np.array(r["To"])
        As, ps = harmonic(Ts - Ts.mean()); Ao, po = harmonic(To - To.mean())
        e = Ts - To
        r.update(phase_days=(ps - po + 182.5) % 365 - 182.5, amp_ratio=As / Ao, spring=float(e[[2, 3, 4]].mean()),
                 autumn=float(e[[8, 9, 10]].mean()))
        if "sea_model" in r:
            Am, pm = harmonic(np.array(r["sea_model"]) - np.mean(r["sea_model"])); Aw, pw = harmonic(np.array(r["sea_obs"]) - np.mean(r["sea_obs"]))
            r.update(sea_phase_days=(pm - pw + 182.5) % 365 - 182.5, sea_amp_ratio=Am / Aw)
        print(f"{r['region']:13s} {r['conf']:9s} MAE {r['mae']:4.2f} phase {r['phase_days']:+6.1f} d amp {r['amp_ratio']:4.2f} "
              f"spring {r['spring']:+5.2f} autumn {r['autumn']:+5.2f}"
              + (f" | sea phase {r['sea_phase_days']:+6.1f} amp {r['sea_amp_ratio']:4.2f}" if "sea_phase_days" in r else ""), flush=True)
    (a.out / f"{a.tag}.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
