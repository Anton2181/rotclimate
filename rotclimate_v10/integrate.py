"""Bounded seasonal integration with explicit monthly rainfall and budgets."""
from dataclasses import dataclass
import numpy as np

from .core import DAY,EDGES,State,advance,air_masses,stable_step
from .weather import catalogue,flow_at


@dataclass
class YearResult:
    state: State
    rain_mm: np.ndarray
    budget: dict


def integrate_year(domain,config,state,storms=True,progress=None):
    domain.validate();config.validate()
    events = catalogue(domain,config)
    ml,mu,_ = air_masses(domain,config)
    rain = np.zeros((12,)+domain.land.shape)
    initial = float((state.lower+state.upper+state.soil).mean())
    totals = {k:0. for k in ('ocean_evaporation_mm','land_evaporation_mm','rain_mm','ocean_rain_mm',
                             'runoff_mm','boundary_export_mm','roundoff_correction_mm')}
    t = 0.;steps = 0;max_error = 0.;continuity = 0.;minimum = float('inf')
    next_forcing = 0.;flow = None;dt_limit = None
    for month in range(12):
        while t < EDGES[month+1]-1e-6:
            if flow is None or t >= next_forcing-1e-6:
                flow = flow_at(domain,config,events,t,storms=storms)
                dt_limit = stable_step(flow,ml,mu,domain.dx,domain.dy,config)
                next_forcing = min(t+config.forcing_interval_s,EDGES[-1])
            dt = min(dt_limit,next_forcing-t,EDGES[month+1]-t)
            if dt < .01 or steps >= 500000:
                raise RuntimeError('Step/iteration bound reached; inspect the circulation instead of waiting indefinitely.')
            state,p,budget = advance(state,domain,config,flow,dt,t)
            rain[month] += p
            for key in totals:totals[key] += budget[key]
            max_error = max(max_error,abs(budget['water_error_mm']))
            continuity = max(continuity,budget['air_continuity_max_kg_m2_s'])
            minimum = min(minimum,float(state.lower.min()),float(state.upper.min()),float(state.soil.min()))
            t += dt;steps += 1
        # Avoid cumulative floating-point time drift at exact calendar boundaries.
        t = float(EDGES[month+1])
        if progress is not None:progress(month+1,steps)
    final = float((state.lower+state.upper+state.soil).mean())
    expected = totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm']
    error = final-initial-expected
    if not np.isfinite(rain).all() or not np.isfinite(error) or abs(error)>1e-6:
        raise FloatingPointError(f'Annual combined water budget failed: {error:g} mm.')
    totals.update(initial_inventory_mm=initial,final_inventory_mm=final,
                  annual_water_error_mm=float(error),max_step_water_error_mm=max_error,
                  max_air_continuity_kg_m2_s=continuity,min_store_mm=minimum,steps=steps,
                  storm_events=len(events) if storms else 0,forcing_year_days=365)
    return YearResult(state,rain,totals)


def settling(previous,current,mask):
    """Two completed repeated-forcing years; final-year fields must be stable."""
    delta = current.rain_mm-previous.rain_mm
    monthly = float(np.percentile(abs(delta[:,mask]),95))
    annual = float(np.percentile(abs(delta.sum(axis=0)[mask]),95))
    stores = [float(np.percentile(abs(a-b),95)) for a,b in zip(
        (previous.state.lower,previous.state.upper,previous.state.soil),
        (current.state.lower,current.state.upper,current.state.soil))]
    # Soil can retain memory even when this year's rain is unchanged.
    passed = monthly <= 1. and annual <= 5. and max(stores) <= 1.
    return {'passed':bool(passed),'monthly_rain_p95_change_mm':monthly,
            'annual_rain_p95_change_mm':annual,'end_store_p95_changes_mm':stores,
            'limits':{'monthly_rain_p95_mm':1.,'annual_rain_p95_mm':5.,'end_store_p95_mm':1.}}


def rain_metrics(case,predicted):
    """Continuous precipitation skill only. Temperature is prescribed input."""
    mask = case.score_mask
    if predicted.shape != case.observed_rain_mm.shape or not np.isfinite(predicted).all() or (predicted<0).any():
        raise ValueError('Invalid model rain fields.')
    observed = case.observed_rain_mm
    annual = predicted.sum(axis=0);reference = observed.sum(axis=0)
    winter = np.array([0,1,2,9,10,11])
    fraction = predicted[winter].sum(axis=0)/np.maximum(annual,1e-9)
    ref_fraction = observed[winter].sum(axis=0)/np.maximum(reference,1e-9)
    seasonal_mask = mask & (reference>=50.) & (annual>=1.)
    seasonal = float(abs(fraction-ref_fraction)[seasonal_mask].mean()) if seasonal_mask.any() else None
    groups = {}
    for name,selected in (('coastal',mask&(case.coast_distance_km<150)),('interior',mask&(case.coast_distance_km>300))):
        groups[name] = {'cells':int(selected.sum()),'predicted_annual_mm':float(annual[selected].mean()) if selected.any() else None,
                        'observed_annual_mm':float(reference[selected].mean()) if selected.any() else None}
    contrast = None
    if groups['coastal']['cells'] and groups['interior']['cells']:
        contrast = {key:groups['coastal'][key]-groups['interior'][key] for key in ('predicted_annual_mm','observed_annual_mm')}
    return {'scored_land_cells':int(mask.sum()),'annual_bias_mm':float((annual-reference)[mask].mean()),
            'annual_rmse_mm':float(np.sqrt(np.mean((annual-reference)[mask]**2))),
            'monthly_mae_mm':float(abs(predicted-observed)[:,mask].mean()),
            'winter_fraction_mae':seasonal,'winter_fraction_scored_cells':int(seasonal_mask.sum()),
            'dry_model_cells_lt_1mm':int((mask&(annual<1.)).sum()),
            'predicted_mean_annual_mm':float(annual[mask].mean()),'observed_mean_annual_mm':float(reference[mask].mean()),
            'coast_interior':groups,'coast_minus_interior':contrast,
            'predicted_monthly_mean_mm':predicted[:,mask].mean(axis=1).tolist(),
            'observed_monthly_mean_mm':observed[:,mask].mean(axis=1).tolist()}
