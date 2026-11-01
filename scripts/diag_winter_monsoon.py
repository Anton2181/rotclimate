"""P6 diagnostic: East Asia's winter monsoon on r41 (winters too warm and 1.6-3x too wet).

For each region and configuration (r41; r41 with observed NCEP winds), the
monthly land-mean temperature bias and rain ratio, and over land the model's
precipitable water, surface wind and evaporation against NCEP's
precipitable water and 995 hPa winds.

    python -I scripts/diag_winter_monsoon.py --out output/winter_monsoon_20261101
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
CONF = {"model": {}, "obs_wind": {"wind_source": "observed"}}
REGIONS = ["manchuria", "korea", "japan", "north_china_plain", "east_china", "eastern_europe", "us_midwest"]


def monthly(x, days, year_days):
    m = np.floor(days / year_days * 12).astype(int) % 12
    return np.stack([x[m == k].mean(0) for k in range(12)])


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
    nc = ncep_at(case, ("u", "v", "pw", "rh"))
    if p.wind_source == "observed":
        g.obs_wind = np.stack([nc["u"], nc["v"]], axis=1)
    res = ClimateModel(p, g).run(steps=p.steps_per_year)
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    W = monthly(res.W, res.days, p.year_days)[:, m].mean(1)
    E = monthly(res.E, res.days, p.year_days)[:, m].mean(1)
    u = monthly(res.u, res.days, p.year_days)[:, m].mean(1); v = monthly(res.v, res.days, p.year_days)[:, m].mean(1)
    return dict(region=region, conf=name,
                dT=(st["Tm"][:, m] - case.obs_T[:, m]).mean(1).tolist(),
                P_ratio=(st["Pm"][:, m].mean(1) / np.maximum(case.obs_P[:, m].mean(1), 1e-6)).tolist(),
                P_model=st["Pm"][:, m].mean(1).tolist(), P_obs=case.obs_P[:, m].mean(1).tolist(),
                W_model=W.tolist(), W_ncep=nc["pw"][:, m].mean(1).tolist(), rh_ncep=nc["rh"][:, m].mean(1).tolist(),
                E_model=E.tolist(), u_model=u.tolist(), v_model=v.tolist(),
                u_ncep=nc["u"][:, m].mean(1).tolist(), v_ncep=nc["v"][:, m].mean(1).tolist())


def main():
    from multiprocessing import Pool
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=ROOT / "output/winter_monsoon_20261101")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with Pool(a.workers) as pool:
        rows = pool.map(one, [(r, n, CONF[n]) for r in REGIONS for n in CONF])
    for r in rows:
        w = [0, 1, 11]
        f = lambda k: float(np.mean([r[k][i] for i in w]))
        print(f"{r['region']:18s} {r['conf']:8s} DJF dT {f('dT'):+5.2f} rain x{f('P_model') / max(f('P_obs'), 1e-6):4.2f} "
              f"({f('P_model'):.2f} vs {f('P_obs'):.2f} mm/d) W {f('W_model'):5.1f} vs NCEP {f('W_ncep'):5.1f} mm  E {f('E_model'):.2f} mm/d  "
              f"wind ({f('u_model'):+4.1f},{f('v_model'):+4.1f}) vs NCEP ({f('u_ncep'):+4.1f},{f('v_ncep'):+4.1f}) m/s", flush=True)
    (a.out / "diag.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
