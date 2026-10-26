"""Observe the discrete moisture equation without changing the simulation.

The default transports concentration with u.grad(W). The opt-in shared-face
flux form has an explicit regional vapor ledger. Neither is a closed-planet
or transient atmosphere simulation.
"""
from dataclasses import asdict
import json

import numpy as np

from .geography import TARGET_CLASSES
from .koppen import monthly_weights
from .numerics import matrix_product

DAY = 86400.


def vapor_face_fluxes(W,u,v,*,layers=None,mass=None):
    """Upwind vapor flux in mm*m/s across rightward/downward shared faces."""
    if layers is not None:
        result=None
        for weight,east,north in layers:
            if weight==0:continue
            faces=vapor_face_fluxes(W,east,north,mass=mass)
            if result is None:result=[weight*a for a in faces]
            else:
                for i,value in enumerate(faces):result[i]+=weight*value
        return tuple(result)
    east=.5*(u[:,1:]+u[:,:-1])
    south=-.5*(v[1:]+v[:-1])
    if mass is not None:
        q=W/mass
        return (.5*(mass[:,1:]+mass[:,:-1])*east*np.where(east>=0,q[:,:-1],q[:,1:]),
                .5*(mass[1:]+mass[:-1])*south*np.where(south>=0,q[:-1],q[1:]))
    return (east*np.where(east>=0,W[:,:-1],W[:,1:]),
            south*np.where(south>=0,W[:-1],W[1:]))


def diffusion_face_fluxes(W,diffusion,dx,*,mass=None):
    if mass is None:
        return -diffusion*(W[:,1:]-W[:,:-1])/dx,-diffusion*(W[1:]-W[:-1])/dx
    q=W/mass
    return (-diffusion*.5*(mass[:,1:]+mass[:,:-1])*(q[:,1:]-q[:,:-1])/dx,
            -diffusion*.5*(mass[1:]+mass[:-1])*(q[1:]-q[:-1])/dx)


def face_divergence(east,south,dx):
    return (east[1:-1,1:]-east[1:-1,:-1]+south[1:,1:-1]-south[:-1,1:-1])/dx


def boundary_supply(east,south,dx):
    """Inflow across the solved interior's four faces, mm/day times cell count."""
    return float(DAY/dx*(east[1:-1,0].sum()-east[1:-1,-1].sum()+
                         south[0,1:-1].sum()-south[-1,1:-1].sum()))


def flux_budget(W,u,v,dx,diffusion,evaporation,rain,exchange_rate,mixed_water,*,layers=None,mass=None):
    """Steady padded-domain vapor ledger, including physical border exchange.

    This is a local flat-grid ledger, not a closed planet or a transient
    atmosphere. Column drying counts in net evaporation. Storm exchange is
    only a boundary supply if that separate operator conserves water.
    """
    east,south=vapor_face_fluxes(W,u,v,layers=layers,mass=mass)
    advection=-DAY*face_divergence(east,south,dx)
    adv_boundary=boundary_supply(east,south,dx)
    de,ds=diffusion_face_fluxes(W,diffusion,dx,mass=mass)
    diff=-DAY*face_divergence(de,ds,dx)
    diff_boundary=boundary_supply(de,ds,dx)
    storm=DAY*exchange_rate*(mixed_water-W)
    e=np.broadcast_to(evaporation,W.shape)[1:-1,1:-1]
    p=rain[1:-1,1:-1]
    storm_interior=float(storm[1:-1,1:-1].sum())
    residual=float(e.sum()+adv_boundary+diff_boundary+storm_interior-p.sum())
    scale=float(np.maximum(p+np.abs(e),.1).sum())
    transport_scale=max(float(np.abs(advection).sum()+np.abs(diff).sum()),1e-30)
    cancellation=abs(float(advection.sum())-adv_boundary)+abs(float(diff.sum())-diff_boundary)
    return dict(advection_boundary_supply_cell_mm_day=adv_boundary,
                diffusion_boundary_supply_cell_mm_day=diff_boundary,
                storm_interior_net_cell_mm_day=storm_interior,
                net_evaporation_cell_mm_day=float(e.sum()),rain_cell_mm_day=float(p.sum()),
                equation_residual_cell_mm_day=residual,scaled_equation_residual=abs(residual)/max(scale,1e-30),
                transport_relative_cancellation=cancellation/transport_scale)


def moisture_terms(W, u, v, dx, diffusion, evaporation, rain, exchange_rate, mixed_water, *, form='concentration',layers=None,mass=None):
    """Signed sources in mm/day; exact upwind/central discrete transport.

    Evaporation and rain are mm/day, exchange_rate is 1/s, W is mm.
    Outer-ring terms are undefined and marked NaN. Production diagnostics crop
    them away with the model padding before saving anything.
    """
    left, right = np.roll(W, 1, 1), np.roll(W, -1, 1)
    above, below = np.roll(W, 1, 0), np.roll(W, -1, 0)
    wr = -v
    if form == 'concentration':
        if layers is not None or mass is not None:raise ValueError('Layered/mass-aware transport requires flux form')
        adv = (np.maximum(u, 0) * (W - left) + np.minimum(u, 0) * (right - W)
               + np.maximum(wr, 0) * (W - above) + np.minimum(wr, 0) * (below - W)) / dx
    elif form == 'flux':
        adv=np.full_like(W,np.nan,dtype=float)
        adv[1:-1,1:-1]=face_divergence(*vapor_face_fluxes(W,u,v,layers=layers,mass=mass),dx)
    else:
        raise ValueError('Unknown moisture transport form: '+form)
    lap = (left + right + above + below - 4 * W) / dx**2
    diff=DAY*diffusion*lap
    if mass is not None:
        diff=np.full_like(W,np.nan,dtype=float)
        diff[1:-1,1:-1]=-DAY*face_divergence(*diffusion_face_fluxes(W,diffusion,dx,mass=mass),dx)
    terms = dict(advection=-DAY * adv, diffusion=diff,
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
            components = ['rain', 'evaporation', 'advection', 'diffusion', 'storm_exchange', 'residual']
            components += [key for key in ('column_drying', 'convergence_import')
                           if f'monthly_{key}_mm_day' in arrays]
            periods[name] = dict(
                mean_total_mm_per_cell={k: mean(k) * days for k in components},
                mean_absolute_equation_residual_mm_day=mean('absolute_residual'),
                absolute_residual_over_rain=mean('absolute_residual') / max(rain, 1e-9))
        zones[key] = periods
    note='Local nonconservative discrete moisture-equation terms. Positive sources supply water; column_drying is negative. When present, residual = evaporation + column_drying + convergence_import + transport sources - rain. Older archives without these two components cannot reconstruct active drying/import. Absolute instantaneous residuals are averaged before seasonal aggregation. Not a conservative global water budget.'
    if getattr(p,'moisture_transport_form','concentration')=='flux':
        note='Steady flat-grid regional vapor equation with shared-face conservative mean-wind transport. Column drying is negative, convergence import is disabled. Storm exchange conserves separately only when its scheme does; see the numerical ledger. Fixed borders supply or remove water. This is not a closed planet or transient water budget.'
    return dict(note=note,zones=zones)
