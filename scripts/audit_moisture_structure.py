"""Fast saved-field audit of moisture operators; never runs a climate model.

The finite-volume comparison freezes the existing water and winds. Its changes
are NOT predicted rainfall or a validated replacement climate. The symmetric
Gaussian operator is a periodic-domain prototype, not an open-boundary model.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DAY = 86400.


def face_transport(water, u, v, dx, closed=False):
    """Upwind finite-volume source, with map-up v and [..., y, x] arrays.

    Closed boundaries have zero normal flux. Open boundary faces use the saved
    edge state's wind/water (one-sided extrapolation); neither is a new boundary
    condition for an actual atmosphere. Source units: mm/day for W in mm.
    """
    water, u, v = [np.asarray(a, dtype=float) for a in (water, u, v)]
    if water.ndim < 2 or water.shape != u.shape or water.shape != v.shape:
        raise ValueError('Water and wind arrays must have the same [..., y, x] shape.')
    if not np.isfinite(dx) or dx <= 0 or not all(np.isfinite(a).all() for a in (water,u,v)):
        raise ValueError('Need finite fields and positive cell width.')
    fx = np.zeros(water.shape[:-1] + (water.shape[-1] + 1,))
    fy = np.zeros(water.shape[:-2] + (water.shape[-2] + 1, water.shape[-1]))
    uf = .5 * (u[..., 1:] + u[..., :-1])
    vf = -.5 * (v[..., 1:, :] + v[..., :-1, :])
    fx[..., 1:-1] = uf * np.where(uf >= 0, water[..., :-1], water[..., 1:])
    fy[..., 1:-1, :] = vf * np.where(vf >= 0, water[..., :-1, :], water[..., 1:, :])
    if not closed:
        fx[..., 0], fx[..., -1] = u[..., 0] * water[..., 0], u[..., -1] * water[..., -1]
        fy[..., 0, :], fy[..., -1, :] = -v[..., 0, :] * water[..., 0, :], -v[..., -1, :] * water[..., -1, :]
    source = -(np.diff(fx, axis=-1) + np.diff(fy, axis=-2)) / dx * DAY
    outward = ((fx[..., -1] - fx[..., 0]).sum(axis=-1)
               + (fy[..., -1, :] - fy[..., 0, :]).sum(axis=-1)) / dx * DAY
    return source, outward


def symmetric_exchange(water, rate, mix):
    """Pairwise-mean rate; conservative only for a symmetric normalized mix.

    C_ij = G_ij * (rate_i + rate_j)/2, source_i = sum_j C_ij*(W_j-W_i).
    Rates are nonnegative and in 1/day, giving sources in mm/day.
    """
    water, rate = np.asarray(water, float), np.asarray(rate, float)
    if water.shape != rate.shape or not np.isfinite(water).all() or not np.isfinite(rate).all() or (rate < 0).any():
        raise ValueError('Need matching finite water/rate fields and nonnegative rates.')
    return .5 * (rate * mix(water) + mix(rate * water) - water * (rate + mix(rate)))


def periodic_exchange(water, rate, sigma):
    if not np.isfinite(sigma) or sigma < 0:
        raise ValueError('Gaussian width must be finite and nonnegative.')
    return symmetric_exchange(water, rate, lambda a: gaussian_filter(a, sigma, mode='wrap'))


def two_box_example():
    w, rate = np.array([0., 10.]), np.array([2., 0.])
    mix = lambda a: np.full_like(a, a.mean())
    original = rate * (mix(w) - w)
    paired = symmetric_exchange(w, rate, mix)
    return dict(water_mm=w.tolist(), rate_per_day=rate.tolist(),
                original_source_mm_day=original.tolist(), original_net_mm_day=float(original.sum()),
                symmetric_source_mm_day=paired.tolist(), symmetric_net_mm_day=float(paired.sum()),
                note='Manufactured closed two-box example, not a measured global leak rate.')


def audit_saved(source):
    from scripts import overnight_mediterranean as night
    from rotclimate.geography import build_grid
    from rotclimate.koppen import monthly_weights, summer_months
    from rotclimate.numerics import matrix_product
    from rotclimate.transport import moisture_terms

    source = Path(source).resolve()
    experiment = json.loads((source / 'experiment.json').read_text())
    if night.source_id() != experiment['source_id']:
        raise ValueError('Source inputs changed; cannot reconstruct the saved grid safely.')
    p = night.Params(**experiment['anchor'])
    j = night.job('anchor_warm2', p, 2*p.steps_per_year, source, experiment['source_id'], full=True, transport=True)
    saved = night.cached(j)
    if saved is None or saved['status'] != 'ok':
        raise ValueError('Need the matching converged, captured two-year-warm-up anchor.')
    with np.load(saved['result'], allow_pickle=False) as z:
        if not night.matching_params(json.loads(str(z['params_json'])), p):
            raise ValueError('Saved full climate parameters do not match the anchor.')
        days = z['days']
        water, u, v = [np.asarray(z[k], float) for k in ('W','u','v')]
    g = build_grid(p)
    fv, boundary = face_transport(water,u,v,g.dx_m)
    original = np.stack([moisture_terms(w,a,b,g.dx_m,0,0,0,0,w)['advection']
                         for w,a,b in zip(water,u,v)])
    delta = fv - original
    sl = g.map_slice()
    local = delta[(slice(None),) + sl]
    weights = monthly_weights(days,p.year_days)
    monthly = matrix_product(weights,local.reshape(len(days),-1)).reshape((12,) + local.shape[1:])
    summer = summer_months(p.year_days,summer_solstice=p.winter_solstice_day + p.year_days/2)
    zones = {}
    for name,cid in (('med',4),('cold_dry',2),('hot_dry',7),('swamp',5)):
        mask = (g.land & (g.target == cid))[sl]
        periods = {}
        for season,months in (('winter',~summer),('summer',summer),('annual',np.ones(12,bool))):
            values = monthly[months].sum(axis=0)[mask] * p.year_days/12
            periods[season] = dict(signed_median_mm=float(np.median(values)),
                                   absolute_p95_mm=float(np.percentile(abs(values),95)),
                                   signed_mean_mm=float(values.mean()))
        zones[name] = dict(cells=int(mask.sum()), frozen_operator_difference=periods)
    d = json.loads((source / 'cases/anchor_warm2_diagnostic.json').read_text())
    med = d['moisture_transport']['zones']['med']['winter']['mean_total_mm_per_cell']
    return dict(source_id=experiment['source_id'], result=saved['result'], params=asdict(p),
                two_box_example=two_box_example(),
                Mediterranean_winter_local_terms_mm=med,
                finite_volume_boundary_cancellation_max_mm_day=float(np.max(abs(fv.sum(axis=(-1,-2)) + boundary))),
                zones=zones,
                interpretation='Frozen-state operator audit, NOT rainfall changes or a solved alternative climate. '
                               'Includes divergent-wind physics and different discrete face placement. '
                               'Surface-like winds are not established column moisture-weighted winds. '
                               'A flux-form replacement requires consistent atmospheric mass/vertical circulation. '
                               'Open domain boundary exchange is not a global water-budget error. '
                               'The two-box example isolates structural nonconservation on a closed domain.')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=ROOT/'output/overnight_mediterranean')
    ap.add_argument('--out',type=Path,help='Optional JSON output; otherwise just print the audit.')
    a = ap.parse_args(argv)
    report = audit_saved(a.source)
    text = json.dumps(report,indent=2,allow_nan=False) + '\n'
    if a.out is not None:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(text)
    print(text)


if __name__ == '__main__':
    main()
