"""Per-location temperature and rainfall accuracy on Earth regions, with the
errors attributed to geography.

    python3 -I scripts/benchmark_local.py --fit atlases/earth_fit/params.json --out output/local/baseline
    python3 -I scripts/benchmark_local.py --fit PARAMS.json --set '{"key": value}' --out DIR --regions california japan

Each scored land cell is compared with WorldClim 2.1's 1970-2000 monthly
normals aggregated to the same cell. Regions get equal weight in the summary;
cells get equal weight within a region. The geographic attribution pools the
cells of all regions. Per-cell arrays are saved (cells.npz) so that later
analyses (downscaling, corrections) need not rerun the climate.

Temperature metrics:
  monthly MAE / RMSE (deg C) over cells and months; annual-mean bias (mean,
  and MAE over cells); seasonal-range error (warmest minus coldest month);
  shares of cells with |annual-mean error| <= 1 and <= 2 deg C; the Pearson
  correlation of annual-mean temperature anomalies from the regional mean
  (the local pattern, not the regional level).
Rainfall metrics: scripts/rainfall_metrics.local_metrics, plus the Spearman
  correlation of annual totals (wet and dry places in the right order).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from multiprocessing import Pool
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from earth_benchmark import load_params  # noqa: E402
from rainfall_metrics import local_metrics  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.config import Params  # noqa: E402
from rotclimate.koppen import monthly_stats  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402
from local_benchmark_protocol import case_hash, file_hash, freeze, reusable, write_json  # noqa: E402

DEV19 = ["california", "iberia", "southeast_us", "levant", "central_asia", "east_china", "east_australia", "mexico",
         "chile", "cape", "sw_australia", "south_brazil", "japan",
         "pacific_nw", "western_europe", "eastern_europe", "us_midwest", "manchuria", "new_zealand"]
# 12 more development regions, predeclared before any result (their specs
# are in calibration/local_accuracy_20261023/regions_dev12.json and load
# automatically); DEV31 is the development set from r30 on
DEV12_SPECS = ROOT / "calibration/local_accuracy_20261023/regions_dev12.json"
DEV12 = list(json.loads(DEV12_SPECS.read_text()))
DEV31 = DEV19 + DEV12
GROUPS = dict(training=DEV19[:8], holdout=DEV19[8:13], midlatitude=DEV19[13:], dev12=DEV12)
BINS = dict(
    elevation_m=[0, 300, 1000, 2000, 9000],
    coast_km=[0, 50, 200, 500, 1e9],
    relief_m=[0, 300, 1000, 2000, 9000],      # highest minus mean ground within the cell
)


def spearman(a, b):
    if len(a) < 3 or np.ptp(a) == 0 or np.ptp(b) == 0: return None
    return float(spearmanr(a, b).statistic)


def temperature_metrics(Ts, To):
    """Ts, To: [12, n] monthly temperature on scored cells."""
    err = Ts - To
    ann = err.mean(0)
    rng = (Ts.max(0) - Ts.min(0)) - (To.max(0) - To.min(0))
    sa, oa = Ts.mean(0), To.mean(0)
    pattern = float(np.corrcoef(sa - sa.mean(), oa - oa.mean())[0, 1]) if len(sa) > 2 and np.ptp(sa) > 0 and np.ptp(oa) > 0 else None
    return dict(monthly_mae_C=float(np.abs(err).mean()), monthly_rmse_C=float(np.sqrt((err ** 2).mean())),
                annual_bias_C=float(ann.mean()), annual_mae_C=float(np.abs(ann).mean()),
                range_error_C=float(rng.mean()), range_mae_C=float(np.abs(rng).mean()),
                within_1C=float(np.mean(np.abs(ann) <= 1.0)), within_2C=float(np.mean(np.abs(ann) <= 2.0)),
                anomaly_pattern_r=pattern)


def one(job):
    region, params_dict, cell_km, out, specs, run_identity = job
    started = time.monotonic()
    earth.REGIONS.update(specs)
    p = Params(**params_dict)
    case = earth.region_case(region, cell_km)
    grid_identity = case_hash(case, observed_sea=p.sst_source == 'observed')
    record_path = Path(out)/'cases'/f'{region}.json'
    cells_path = Path(out)/'cells'/f'{region}.npz'
    previous = reusable(record_path, run_identity, grid_identity, cells_path)
    if previous is not None:
        print(f'{region}: reusing verified result', flush=True)
        return previous
    res = None
    try:
        res = earth.run_case(p, case, steps=p.steps_per_year)
        if res.numerics.get('all_checks_passed') is not True:
            raise RuntimeError('Observed numerical checks failed')
        if not np.isfinite(res.T).all() or not np.isfinite(res.P).all() or (res.P < 0).any():
            raise ValueError('Invalid climate fields')
    except Exception as error:
        record = dict(region=region, status='failed', identity=run_identity, case_identity=grid_identity,
                      error=repr(error), numerics=getattr(res, 'numerics', None), seconds=time.monotonic()-started)
        write_json(record_path, record)
        return record
    pr = res.params
    st = monthly_stats(res.T, res.P, res.days, pr.year_days, summer_solstice=pr.winter_solstice_day + pr.year_days / 2)
    g = case.grid
    m = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    if not m.any(): raise ValueError('No scored land cells: '+region)
    Ts, To = st["Tm"][:, m], np.asarray(case.obs_T)[:, m]
    Ps, Po = np.maximum(st["Pm"][:, m], 0.0), np.asarray(case.obs_P)[:, m]
    rain = local_metrics(np.maximum(st["Pm"], 0.0), np.nan_to_num(case.obs_P), m)
    rain["annual_spearman"] = spearman(Ps.sum(0), Po.sum(0))
    rec = dict(region=region, status='passed', identity=run_identity, case_identity=grid_identity,
               cells=int(m.sum()), temperature=temperature_metrics(Ts, To), rain=rain,
               numerics=getattr(res, "numerics", None))
    ii, jj = np.nonzero(m)
    temporary = cells_path.with_suffix('.tmp')
    with temporary.open('wb') as stream:
        np.savez_compressed(stream, Ts=Ts.astype(np.float32), To=To.astype(np.float32),
                            Ps=Ps.astype(np.float32), Po=Po.astype(np.float32), lat=g.lat[m], lon=case.lon[m],
                            elev=g.elev[m], elev_max=g.elev_max[m], coast_km=case.coast_km[m], i=ii, j=jj)
    temporary.replace(cells_path)
    rec.update(cells_sha256=file_hash(cells_path), seconds=time.monotonic()-started)
    write_json(record_path, rec)
    print(f'{region}: verified, rainfall loss {rain["loss"]:.4f}', flush=True)
    return rec


def attribution(out, regions):
    """Pooled per-cell errors by geographic class."""
    cols = {k: [] for k in ("Tann", "Trng", "Plog", "elevation_m", "coast_km", "relief_m")}
    for r in regions:
        z = np.load(Path(out) / "cells" / f"{r}.npz")
        cols["Tann"].append((z["Ts"] - z["To"]).mean(0))
        cols["Trng"].append((z["Ts"].max(0) - z["Ts"].min(0)) - (z["To"].max(0) - z["To"].min(0)))
        cols["Plog"].append(np.log((z["Ps"].sum(0) + 50) / (z["Po"].sum(0) + 50)))
        cols["elevation_m"].append(z["elev"])
        cols["coast_km"].append(z["coast_km"])
        cols["relief_m"].append(z["elev_max"] - z["elev"])
    c = {k: np.concatenate(v) for k, v in cols.items()}
    table = {}
    for key, edges in BINS.items():
        rows = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            k = (c[key] >= lo) & (c[key] < hi)
            if k.sum() < 20:
                continue
            rows.append(dict(bin=f"{lo:g}-{hi:g}", cells=int(k.sum()),
                             T_annual_bias=float(c["Tann"][k].mean()), T_annual_mae=float(np.abs(c["Tann"][k]).mean()),
                             T_range_bias=float(c["Trng"][k].mean()),
                             P_log_bias=float(c["Plog"][k].mean()), P_log_rmse=float(np.sqrt((c["Plog"][k] ** 2).mean()))))
        table[key] = rows
    return table


def group_means(recs, names):
    def mean(f):
        v = [f(recs[n]) for n in names if n in recs]
        v = [x for x in v if x is not None]
        return float(np.mean(v)) if v else None
    return dict(
        T_monthly_mae=mean(lambda r: r["temperature"]["monthly_mae_C"]),
        T_annual_mae=mean(lambda r: r["temperature"]["annual_mae_C"]),
        T_within_2C=mean(lambda r: r["temperature"]["within_2C"]),
        T_anomaly_r=mean(lambda r: r["temperature"]["anomaly_pattern_r"]),
        P_monthly_mae=mean(lambda r: r["rain"]["monthly_mae_mm"]),
        P_annual_log_rmse=mean(lambda r: r["rain"]["annual_log_rmse"]),
        P_within_25pct=mean(lambda r: r["rain"]["annual_within_25pct"]),
        P_spearman=mean(lambda r: r["rain"]["annual_spearman"]),
        P_loss=mean(lambda r: r["rain"]["loss"]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", required=True)
    ap.add_argument("--set", default="{}", help="json parameter overrides")
    ap.add_argument("--regions", nargs="+", default=DEV19, help="region names, or 'dev31' for all 31 development regions")
    ap.add_argument("--cell-km", type=float, default=56.0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--region-specs", help="json of extra region definitions (e.g. the sealed validation regions)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.regions == ["dev31"]:
        a.regions = DEV31
    if len(set(a.regions)) != len(a.regions): ap.error('Duplicate regions change weighting')
    if a.workers < 1: ap.error('Use at least one worker')
    specs = {r: v for r, v in json.loads(DEV12_SPECS.read_text()).items() if r in a.regions}
    if a.region_specs:
        specs.update(json.loads(Path(a.region_specs).read_text()))
    out = Path(a.out)
    (out / "cells").mkdir(parents=True, exist_ok=True)
    (out / 'cases').mkdir(exist_ok=True)
    overrides = json.loads(a.set)
    p = load_params(a.fit).replace(**overrides)
    if not (p.t_require_convergence and p.moisture_require_convergence and
            p.solver_require_convergence and p.moisture_residual_tol > 0):
        ap.error('Local accuracy benchmarks require strict numerical criteria')
    definitions = {**earth.REGIONS, **specs}
    if not set(a.regions) <= set(definitions): ap.error('Unknown region')
    sources = list((ROOT/'rotclimate').glob('*.py')) + [Path(__file__), ROOT/'scripts/rainfall_metrics.py',
               ROOT/'scripts/local_benchmark_protocol.py', ROOT/'scripts/earth_benchmark.py']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{name}.zip' for name in ['tavg','prec','elev']]
    if p.sst_source == 'observed': sources.append(earth.WOA_SST)
    protocol = dict(params=asdict(p), regions=a.regions, region_specs={r:definitions[r] for r in a.regions},
                    cell_km=a.cell_km, pad_km=1100.,
                    sources={str(path.relative_to(ROOT)):file_hash(path) for path in sources},
                    note='Reused development regions; actual derived model inputs are hashed per case.')
    run_identity = freeze(out/'protocol.json', protocol)
    # Generate shared fetch caches once, before parallel region preparation.
    earth.west_fetch(1700.)
    earth.west_fetch(5100.)
    earth.sea_reach()
    with Pool(a.workers) as pool:
        recs = {r["region"]: r for r in pool.map(one, [(r, asdict(p), a.cell_km, str(out), specs, run_identity) for r in a.regions],
                                                  chunksize=1)}
    failures = [r for r,row in recs.items() if row['status'] != 'passed']
    if failures:
        write_json(out/'summary.json', dict(complete=False, identity=run_identity, regions=recs, failures=failures))
        raise SystemExit('Failed cases retained; no aggregate score: '+', '.join(failures))
    summary = dict(complete=True, identity=run_identity, fit=a.fit, overrides=overrides, cell_km=a.cell_km, regions=recs,
                   groups={g: group_means(recs, n) for g, n in GROUPS.items() if any(x in recs for x in n)},
                   all=group_means(recs, a.regions), attribution=attribution(out, a.regions))
    write_json(out/'summary.json', summary)
    print(f"{'region':15s} {'T mMAE':>7s} {'T aMAE':>7s} {'T bias':>7s} {'rngErr':>7s} {'<=2C':>5s} {'anom r':>6s} | "
          f"{'P mMAE':>7s} {'logRMSE':>7s} {'<=25%':>6s} {'rho':>5s} {'loss':>6s}")
    for r in a.regions:
        t, p = recs[r]["temperature"], recs[r]["rain"]
        print(f"{r:15s} {t['monthly_mae_C']:7.2f} {t['annual_mae_C']:7.2f} {t['annual_bias_C']:+7.2f} {t['range_error_C']:+7.2f}"
              f" {t['within_2C']:5.0%} {t['anomaly_pattern_r']:6.2f} | {p['monthly_mae_mm']:7.1f} {p['annual_log_rmse']:7.3f}"
              f" {p['annual_within_25pct']:6.0%} {p['annual_spearman']:5.2f} {p['loss']:6.3f}")
    for g, v in summary["groups"].items():
        print(f"[{g}] " + " ".join(f"{k} {x:.3f}" for k, x in v.items() if x is not None))
    print("[all] " + " ".join(f"{k} {x:.3f}" for k, x in summary["all"].items() if x is not None))
    for key, rows in summary["attribution"].items():
        print(f"-- by {key}: " + " | ".join(f"{r['bin']} n{r['cells']} T {r['T_annual_bias']:+.1f}/{r['T_annual_mae']:.1f} "
                                            f"rng {r['T_range_bias']:+.1f} P {r['P_log_bias']:+.2f}/{r['P_log_rmse']:.2f}"
                                            for r in rows))


if __name__ == "__main__":
    main()
