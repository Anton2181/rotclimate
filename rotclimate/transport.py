"""Observe the discrete moisture equation without changing the simulation.

The model transports concentration with u.grad(W), not conservative flux
divergence. These are local equation terms, not a global water-budget proof.
"""
from dataclasses import asdict
import json

import numpy as np

from .geography import TARGET_CLASSES
from .koppen import monthly_weights
from .numerics import matrix_product

DAY = 86400.


def moisture_terms(W, u, v, dx, diffusion, evaporation, rain, exchange_rate, mixed_water):
    """Signed sources in mm/day; exact upwind/central discrete transport.

    Evaporation and rain are mm/day, exchange_rate is 1/s, W is mm.
    Outer-ring terms are undefined and marked NaN. Production diagnostics crop
    them away with the model padding before saving anything.
    """
    left, right = np.roll(W, 1, 1), np.roll(W, -1, 1)
    above, below = np.roll(W, 1, 0), np.roll(W, -1, 0)
    wr = -v
    adv = (np.maximum(u, 0) * (W - left) + np.minimum(u, 0) * (right - W)
           + np.maximum(wr, 0) * (W - above) + np.minimum(wr, 0) * (below - W)) / dx
    lap = (left + right + above + below - 4 * W) / dx**2
    terms = dict(advection=-DAY * adv, diffusion=DAY * diffusion * lap,
                 storm_exchange=DAY * exchange_rate * (mixed_water - W))
    terms['residual'] = evaporation + sum(terms.values()) - rain
    # Preserve absolute instantaneous errors before averaging; signed residuals
    # alone can cancel between dates or adjacent cells.
    terms['absolute_residual'] = np.abs(terms['residual'])
    for a in terms.values():
        a[[0, -1], :] = np.nan
        a[:, [0, -1]] = np.nan
    return terms


def save_transport(result, evaluation, path):
    if result.moisture_budget is None:
        raise ValueError('Run with diagnose_moisture=True before exporting transport')
    p, g = result.params, result.grid
    sl = g.map_slice()
    weights = monthly_weights(result.days, p.year_days)
    def monthly(a):
        return matrix_product(weights, a.reshape(len(result.days), -1)).reshape((12,) + a.shape[1:])
    arrays = dict(target=g.target[sl], valid=(g.inmap & g.land)[sl],
                  params_json=np.array(json.dumps(asdict(p))),
                  summer=evaluation['monthly']['summer'],
                  monthly_rain_mm_day=evaluation['monthly']['Pm'][(slice(None),) + sl] * 12 / p.year_days,
                  monthly_temperature_c=evaluation['monthly']['Tm'][(slice(None),) + sl])
    for key, values in result.moisture_budget.items():
        arrays[f'monthly_{key}_mm_day'] = monthly(values)
    for field, key in [('E', 'evaporation_mm_day'), ('W', 'water_mm'), ('u', 'u_ms'), ('v', 'v_ms')]:
        arrays[f'monthly_{key}'] = monthly(getattr(result, field)[(slice(None),) + sl])
    np.savez_compressed(path, **arrays)
    zones = {}
    for cid, key, _, _ in TARGET_CLASSES:
        own = arrays['valid'] & (arrays['target'] == cid)
        if not own.any():
            continue
        periods = {}
        for name, months in [('winter', ~arrays['summer']), ('summer', arrays['summer']),
                             ('annual', np.ones(12, bool))]:
            def mean(field):
                return float(arrays[f'monthly_{field}_mm_day'][months][:, own].mean())
            days = int(months.sum()) * p.year_days / 12
            rain = mean('rain')
            periods[name] = dict(
                mean_total_mm_per_cell={k: mean(k) * days for k in
                    ('rain', 'evaporation', 'advection', 'diffusion', 'storm_exchange', 'residual')},
                mean_absolute_equation_residual_mm_day=mean('absolute_residual'),
                absolute_residual_over_rain=mean('absolute_residual') / max(rain, 1e-9))
        zones[key] = periods
    return dict(note='Local nonconservative discrete moisture-equation terms. Positive transport terms supply water; residual = evaporation + transport sources - rain. Absolute instantaneous residuals are averaged before seasonal aggregation. Not a conservative global water budget.',
                zones=zones)
