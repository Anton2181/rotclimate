"""Rainfall-only calibration loss and local verification against monthly normals.

The loss can also rescore archived Earth comparisons without rerunning climate.
Every region receives equal weight; cells have equal weight within a region.
No temperature, biome label or fantasy-map target enters this loss.
"""
from __future__ import annotations

import numpy as np

LOSS_SPEC = dict(
    version=1,
    annual_log_weight=0.5,
    normalized_monthly_mae_weight=0.5,
    annual_log_offset_mm=50.0,
    monthly_normalization_floor_mm=10.0,
    formula='0.5 * annual_log_rmse + 0.5 * 12 * monthly_mae_mm / (obs_mean_annual_mm + 120)',
    aggregation='equal regions; equal scored land cells within each region',
)


def loss(metrics):
    """Dimensionless loss, lower is better; never an accuracy percentage.

    The log term measures local annual amounts rather than regional bias.
    The monthly term preserves season and location before averaging absolute
    errors. Normalizing by observed mean rain gives dry and wet regions a
    comparable influence; the 10 mm/month floor avoids division by desert rain.
    """
    r = metrics['rain']
    values = np.array([r['annual_log_rmse'], r['monthly_mae_mm'], r['obs_mean_annual_mm']], float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise ValueError('Rainfall loss requires finite, nonnegative observations and errors')
    return float(0.5 * (values[0] + 12 * values[1] / (values[2] + 120)))


def local_metrics(simulated, observed, mask):
    """Diagnostics on paired [12, ...] monthly rain arrays, all amounts in mm.

    Relative annual error uses observed rain, for land receiving >= 50 mm/year.
    The log loss's +50 mm smoothing is reported separately. Seasonality is
    total variation between the 12 monthly rainfall fractions, on wet cells
    where both annual totals are positive; zero simulated rain is maximal error.
    """
    sim, obs = np.asarray(simulated, float), np.asarray(observed, float)
    mask = np.asarray(mask, bool)
    if sim.shape != obs.shape or sim.shape != (12, *mask.shape):
        raise ValueError('Expected paired twelve-month fields matching the mask')
    if not mask.any():
        raise ValueError('No scored rainfall cells')
    s, o = sim[:, mask], obs[:, mask]
    if not np.isfinite(s).all() or not np.isfinite(o).all() or (s < 0).any() or (o < 0).any():
        raise ValueError('Invalid rainfall inside the scoring mask')
    sa, oa = s.sum(0), o.sum(0)
    wet = oa >= 50
    relative = np.abs(sa[wet] - oa[wet]) / oa[wet]
    sf = np.divide(s[:, wet], sa[wet], out=np.zeros_like(s[:, wet]), where=sa[wet] > 0)
    of = o[:, wet] / oa[wet]
    tv = 0.5 * np.abs(sf - of).sum(0)
    tv[sa[wet] == 0] = 1
    out = dict(
        scored_land_cells=int(mask.sum()), wet_scored_cells=int(wet.sum()),
        sim_mean_annual_mm=float(sa.mean()), obs_mean_annual_mm=float(oa.mean()),
        annual_mae_mm=float(np.abs(sa - oa).mean()),
        annual_bias_mm=float((sa - oa).mean()),
        annual_log_rmse=float(np.sqrt(np.mean(np.log((sa + 50) / (oa + 50)) ** 2))),
        monthly_mae_mm=float(np.abs(s - o).mean()),
        monthly_rmse_mm=float(np.sqrt(np.mean((s - o) ** 2))),
        annual_within_25pct=float(np.mean(relative <= .25)) if wet.any() else None,
        annual_within_50pct=float(np.mean(relative <= .50)) if wet.any() else None,
        annual_median_abs_relative_error=float(np.median(relative)) if wet.any() else None,
        seasonality_total_variation=float(tv.mean()) if wet.any() else None,
    )
    out['loss'] = loss(dict(rain=out))
    return out


def compare(result, case):
    from rotclimate.koppen import monthly_stats
    p = result.params
    monthly = monthly_stats(result.T, result.P, result.days, p.year_days,
                            summer_solstice=p.winter_solstice_day + p.year_days / 2)['Pm']
    mask = case.grid.inmap & case.grid.land & np.isfinite(case.obs_P).all(0)
    return local_metrics(monthly, case.obs_P, mask)
