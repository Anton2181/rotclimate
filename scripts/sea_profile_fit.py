"""C1 stage 0 (calibration/sea_profile_20261122/plan.json): fit the zonal sea of the energy balance
(EBM ocean + sst_offset) to WOA18 zonal-mean sea-surface temperature, both hemispheres, every month.

    .venv/bin/python -I scripts/sea_profile_fit.py --woa <woa18_sst_1deg.npz> [--knobs a,b,...]
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import numpy as np
from scipy.optimize import minimize
from earth_benchmark import load_params
from rotclimate.ebm import ZonalClimate

OUT = ROOT / 'calibration/sea_profile_20261122'
MID = np.array([15, 45, 74, 105, 135, 166, 196, 227, 258, 288, 319, 349], float)
LATS = np.arange(0.5, 65.0, 1.0)
BOUNDS = dict(ocean_heat_capacity=(0.5, 6.0), ocean_mixed_seasonality=(0.0, 0.8), ocean_capacity_polar=(0.0, 20.0),
              ocean_transport=(0.0, 2.0), sst_offset=(-8.0, 2.0))


def observed(path):
    w = np.load(path); sst, lat = w['sst'], w['lat']
    with np.errstate(all='ignore'):
        zon = np.nanmean(sst, 2)                       # [12, 180]
    north = np.stack([np.interp(LATS, lat, zon[m]) for m in range(12)])
    south = np.roll(np.stack([np.interp(-LATS, lat, zon[m]) for m in range(12)]), 6, axis=0)   # mirrored calendar
    return north, south


def model(p):
    out = []
    for land in ('earth', 'earth_mirrored'):
        z = ZonalClimate(p.replace(ebm_land=land))
        out.append(np.stack([z.ocean(LATS, d) for d in MID]) + p.sst_offset)
    return out


def score(p, obs):
    w = np.cos(np.deg2rad(LATS))[None, :]
    errs = {}
    for name, m, o in zip(('north', 'south'), model(p), obs):
        e = m - o
        errs[name] = dict(rmse=float(np.sqrt((w * e ** 2).sum() / (12 * w.sum()))),
                          mean_bias=float((w * e).sum() / (12 * w.sum())),
                          range_err=float(np.average((m.max(0) - m.min(0)) - (o.max(0) - o.min(0)), weights=w[0])))
    return float(np.mean([errs[k]['rmse'] for k in errs])), errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--woa', required=True)
    ap.add_argument('--params', default='calibration/local_accuracy_20261023/r50_params.json')
    ap.add_argument('--knobs', default=','.join(BOUNDS))
    ap.add_argument('--tag', default='fit')
    a = ap.parse_args()
    obs = observed(a.woa)
    base = load_params(ROOT / a.params)
    knobs = a.knobs.split(',')
    s0, e0 = score(base, obs)
    print('base', round(s0, 3), json.dumps(e0))

    def f(v):
        v = np.clip(v, [BOUNDS[k][0] for k in knobs], [BOUNDS[k][1] for k in knobs])
        return score(base.replace(**dict(zip(knobs, map(float, v)))), obs)[0]
    best = None
    for start in ([getattr(base, k) for k in knobs], [np.mean(BOUNDS[k]) for k in knobs]):
        r = minimize(f, np.array(start, float), method='Nelder-Mead', options=dict(maxfev=400, xatol=1e-3, fatol=1e-4))
        if best is None or r.fun < best.fun:
            best = r
    v = np.clip(best.x, [BOUNDS[k][0] for k in knobs], [BOUNDS[k][1] for k in knobs])
    fit = dict(zip(knobs, map(float, v)))
    s1, e1 = score(base.replace(**fit), obs)
    print('fit', round(s1, 3), json.dumps(fit), json.dumps(e1))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'stage0_{a.tag}.json').write_text(json.dumps(dict(base=dict(score=s0, errors=e0, values={k: getattr(base, k) for k in knobs}),
                                                              fit=dict(score=s1, errors=e1, values=fit)), indent=1))


if __name__ == '__main__':
    main()
