"""Stage B: the model's sea surface against the observed one (WOA18), and a
direct fit of the sea-surface settings.

    python3 -I scripts/fit_sst.py score PARAMS [--set JSON] [--regions ...]
    python3 -I scripts/fit_sst.py fit PARAMS --out DIR [--regions ...] [--holdout ...] [--evals N]

The sea surface is computed exactly as the model's ClimateModel.sst does at
each month's middle day, from the zonal energy-balance ocean and land plus the
static current and enclosure fields, for every ocean cell of each region's
grid (the scored region and its margin). Coastal upwelling, which needs the
simulated winds, is left out here. Observations: data/cache/earth/woa18_sst_1deg.npz
(scripts/build_woa_sst.py), sampled at each cell, months shifted for mirrored
southern regions. Cells colder than -1 C in either field (sea ice) are skipped.

Metrics per region: monthly MAE, annual-mean MAE and bias, and the ratio of
the simulated to observed annual range; regions have equal weight.
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
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402

from benchmark_local import DEV19  # noqa: E402
from earth_benchmark import load_params  # noqa: E402
from rotclimate import earth  # noqa: E402
from rotclimate.ebm import ZonalClimate  # noqa: E402
from rotclimate.model import ClimateModel  # noqa: E402

SPACE = [("sst_offset", -4.0, 2.0), ("current_strength", 0.0, 12.0), ("subpolar_current", 0.0, 14.0),
         ("inland_sea_warming", 0.0, 10.0), ("lake_coupling", 0.0, 1.0), ("sea_winter_mixing", 0.0, 1.0),
         ("ocean_transport", 0.0, 1.5), ("ocean_heat_capacity", 0.5, 4.0)]
_MODELS = {}


def model_sst(region, p):
    """[12, ny, nx] model sea surface and the grid, reusing the static fields per region."""
    if region not in _MODELS:
        case = earth.region_case(region, 56.0)
        m = ClimateModel(earth.earth_params(p, case), grid=case.grid)
        _MODELS[region] = (case, m)
    case, m = _MODELS[region]
    pe = earth.earth_params(p, case)
    m.p = pe
    z = ZonalClimate(pe)
    out = []
    for k in range(12):
        d = (k + 0.5) * pe.year_days / 12.0
        To = z.ocean(m.lat, d) + pe.sst_offset
        Tl = z.land(m.lat, d) + pe.land_offset
        if pe.land_amplitude != 1.0:
            Tm = z.land_annual(m.lat) + pe.land_offset
            Tl = Tm + pe.land_amplitude * (Tl - Tm)
        out.append(m.sst(d, To, Tl))
    return np.stack(out), case


def region_metrics(job):
    region, pdict = job
    from rotclimate.config import Params
    p = Params(**pdict)
    sim, case = model_sst(region, p)
    obs = case.grid.obs_sst
    ok = (~case.grid.land) & (obs.min(0) > -1.0) & (sim.min(0) > -1.0)
    s, o = sim[:, ok], obs[:, ok]
    e = s - o
    return region, dict(cells=int(ok.sum()), monthly_mae=float(np.abs(e).mean()), annual_mae=float(np.abs(e.mean(0)).mean()),
                        annual_bias=float(e.mean()),
                        range_ratio=float(np.median((s.max(0) - s.min(0)) / np.maximum(o.max(0) - o.min(0), 0.5))))


def evaluate(pool, p, regions):
    from dataclasses import asdict
    res = dict(pool.map(region_metrics, [(r, asdict(p)) for r in regions], chunksize=1))
    return res, float(np.mean([res[r]["monthly_mae"] for r in regions]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["score", "fit"])
    ap.add_argument("params")
    ap.add_argument("--set", default="{}")
    ap.add_argument("--regions", nargs="+", default=DEV19)
    ap.add_argument("--holdout", nargs="*", default=[])
    ap.add_argument("--evals", type=int, default=240)
    ap.add_argument("--out")
    a = ap.parse_args()
    base = load_params(a.params).replace(**json.loads(a.set))
    with Pool(4) as pool:
        if a.mode == "score":
            res, cost = evaluate(pool, base, a.regions + a.holdout)
            for r in a.regions + a.holdout:
                v = res[r]
                print(f"{r:15s} cells {v['cells']:5d}  SST monthly MAE {v['monthly_mae']:5.2f}  annual MAE {v['annual_mae']:5.2f}"
                      f"  bias {v['annual_bias']:+5.2f}  range ratio {v['range_ratio']:4.2f}")
            print(f"mean monthly MAE {cost:.3f}")
            return
        import cma
        lo = np.array([g[1] for g in SPACE]); hi = np.array([g[2] for g in SPACE])
        x0 = np.clip((np.array([getattr(base, g[0]) for g in SPACE], float) - lo) / (hi - lo), 0, 1)
        es = cma.CMAEvolutionStrategy(x0, 0.2, dict(bounds=[0, 1], popsize=12, seed=1023, verbose=-9))
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        log = (out / "evals.jsonl").open("w")
        best = (evaluate(pool, base, a.regions)[1], x0)
        n = 1
        print(f"start mean monthly SST MAE {best[0]:.3f}", flush=True)
        while n < a.evals:
            xs = es.ask()
            costs = []
            for x in xs:
                p = base.replace(**{g[0]: float(v) for g, v in zip(SPACE, lo + np.asarray(x) * (hi - lo))})
                res, c = evaluate(pool, p, a.regions)
                costs.append(c)
                log.write(json.dumps(dict(cost=c, x=[float(v) for v in lo + np.asarray(x) * (hi - lo)])) + "\n")
                if c < best[0]:
                    best = (c, np.asarray(x))
            es.tell(xs, costs); n += len(xs); log.flush()
            print(f"[{n:4d}] best {best[0]:.3f} gen-median {np.median(costs):.3f}", flush=True)
        bp = base.replace(**{g[0]: float(v) for g, v in zip(SPACE, lo + best[1] * (hi - lo))})
        fitted = {g[0]: getattr(bp, g[0]) for g in SPACE}
        result = dict(start={g[0]: getattr(base, g[0]) for g in SPACE}, fitted=fitted, train_cost=best[0], regions=a.regions)
        if a.holdout:
            r0, c0 = evaluate(pool, base, a.holdout)
            r1, c1 = evaluate(pool, bp, a.holdout)
            result.update(holdout=a.holdout, holdout_start=c0, holdout_fitted=c1)
            print(f"holdout mean monthly SST MAE {c0:.3f} -> {c1:.3f}")
        (out / "result.json").write_text(json.dumps(result, indent=1))
        print(json.dumps(fitted, indent=1))


if __name__ == "__main__":
    main()
