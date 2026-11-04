"""Conserved dry-matter feed diagnostics, not herd or human carrying capacity.

Annual production and its seasonal allocation are supplied scenarios. Protein,
energy, water volume, animal demography and mobility are not inferred here.
"""
from dataclasses import dataclass
import numpy as np
from .food_stocks import minimum_zero_loss_capacity,periodic_food_year


@dataclass
class PastureBudget:
    annual_dm: np.ndarray
    annual_feed_units: np.ndarray
    lean_growth_fraction: np.ndarray
    minimum_reserve_days: np.ndarray
    shortfall_bins: np.ndarray
    resolved: np.ndarray
    maximum_ledger_residual: float


def forage_allocation(npp,arable,edible_share,*,farmed_share=.6,aboveground_share=.5,usable_share=.25):
    """g DM/m²/year → kg DM/km²/year, excluding the assigned cropped land."""
    npp,arable,edible=np.broadcast_arrays(np.asarray(npp,float),np.asarray(arable,float),np.asarray(edible_share,float))
    if not all(np.isfinite(a).all() for a in [npp,arable,edible]) or np.any(npp<0) or np.any((arable<0)|(arable>1)|(edible<0)|(edible>1)):
        raise ValueError('Finite nonnegative productivity and fractional land/edibility required')
    if not all(np.isfinite(x) and 0<=x<=1 for x in [farmed_share,aboveground_share,usable_share]):
        raise ValueError('Allocation coefficients must be fractions')
    cropped=arable*farmed_share;remaining=1-cropped
    annual=npp*1000*aboveground_share*edible*usable_share*remaining
    return annual,cropped,remaining


def seasonal_forage(temperature,rain,annual,*,temperature_floor=0.,temperature_span=15.,rain_half=50.):
    """Normalize an explicit climate phenology proxy to the annual DM budget.

    Zero active weights with positive annual production remain UNRESOLVED,
    rather than inventing uniform growth. No-forage cells retain zero supply.
    """
    t,p=np.asarray(temperature,float),np.asarray(rain,float);annual=np.asarray(annual,float)
    if t.shape!=p.shape or t.ndim<2 or t.shape[0]!=12 or annual.shape!=t.shape[1:]:raise ValueError('Twelve matching climate bins and annual budget required')
    if not all(np.isfinite(a).all() for a in [t,p,annual]) or np.any(p<0) or np.any(annual<0):raise ValueError('Finite climate and nonnegative rain/production required')
    if not np.isfinite([temperature_floor,temperature_span,rain_half]).all() or temperature_span<=0 or rain_half<=0:raise ValueError('Valid phenology scales required')
    weight=np.clip((t-temperature_floor)/temperature_span,0,1)*p/(p+rain_half)
    total=weight.sum(0);resolved=(total>0)|(annual==0)
    supply=np.divide(weight,total,out=np.zeros_like(weight),where=total>0)*annual
    supply[:,~resolved]=np.nan
    np.testing.assert_allclose(supply[:,resolved].sum(0),annual[resolved],rtol=3e-14,atol=1e-10)
    return supply,resolved


def feed_diagnostics(supply,*,intake_kg_day=6.25,demand_fraction=.5,buffer_days=90.,year_days=365.):
    """Annual feed equivalents and an explicit constant-demand storage test.

    The supplied usable production is grazed or stored exactly once. A buffer
    of `buffer_days` holds that many days of the DECLARED test demand. Zero
    spoilage is an optimistic reference. Missing phenology remains unscored.
    """
    supply=np.asarray(supply,float)
    if supply.ndim<2 or supply.shape[0]!=12 or np.any(supply<0) or np.isinf(supply).any():raise ValueError('Twelve nonnegative production bins or all-NaN missing cells required')
    missing=np.isnan(supply)
    if np.any(missing.any(0)!=missing.all(0)):raise ValueError('Missing seasonal cells must be missing in every bin')
    if not np.isfinite([intake_kg_day,demand_fraction,buffer_days,year_days]).all() or intake_kg_day<=0 or not 0<demand_fraction<=1 or buffer_days<0 or year_days<=0:
        raise ValueError('Positive intake/year, fractional demand and nonnegative buffer required')
    resolved=~missing.all(0);annual=np.sum(supply,axis=0)
    positive=resolved&(annual>0);shape=annual.shape
    lean=np.full(shape,np.nan);reserve=lean.copy();shortfall=lean.copy();residual=0.
    if positive.any():
        selected=supply[:,positive];a=annual[positive];daily=a*demand_fraction/year_days
        need=np.broadcast_to((daily*year_days/12)[None],selected.shape)
        capacity=minimum_zero_loss_capacity(selected,need)
        reserve[positive]=capacity/daily
        lean[positive]=np.clip(np.min(selected,axis=0)/(a/12),0,1)
        year=periodic_food_year(selected,need,daily*buffer_days,step_days=year_days/12,record=True)
        shortfall[positive]=np.sum(year.unmet_path>1e-10*np.maximum(1,a),axis=0)
        residual=float(np.max(np.abs(year.ledger_residual)))
    return PastureBudget(annual,annual/(intake_kg_day*year_days),lean,reserve,shortfall,resolved,residual)
