"""Vectorized bin-start food pulses with continuous meals and storage decay.

Source availability and shipment timing are supplied assumptions. This module
does not infer harvest dates, crew-carried food, diets or resident populations.
"""
import numpy as np

from harvest.food_stocks import FoodYear, _prepare


def _prepared(supply,need,capacity,loss,days):
    prepared=_prepare(supply,need,capacity,loss,days)
    with np.errstate(over='ignore',invalid='ignore'):
        upper_energy=prepared[2]+prepared[0].sum(axis=0)
    if not np.isfinite(upper_energy).all() or not np.isfinite(prepared[4]).all():
        raise ValueError('Inventory energies and decay hazard must remain finite')
    return prepared


def _decay_integral(hazard, length):
    h, dt = np.broadcast_arrays(hazard, length)
    return np.divide(-np.expm1(-h*dt), h, out=np.array(dt,copy=True,dtype=float), where=h>0)


def _advance(initial, prepared):
    supply,need,capacity,days,hazard,_=prepared;stock=np.array(initial,float,copy=True)
    for q,demand,dt in zip(supply,need,days):
        stock=np.minimum(capacity,stock+q)
        stock=np.maximum(0.,stock*np.exp(-hazard*dt)-demand/dt*_decay_integral(hazard,dt))
    return stock


def _year(initial,prepared,record):
    supply,need,capacity,days,hazard,tolerance=prepared
    initial=np.broadcast_to(np.asarray(initial,float),capacity.shape).copy()
    if not np.isfinite(initial).all() or ((initial<0)|(initial>capacity)).any():raise ValueError('Initial stock must be finite and within capacity')
    stock=initial.copy();peak=stock.copy();consumed=np.zeros_like(stock);unmet=consumed.copy();spoiled=consumed.copy();overflow=consumed.copy();shortfall=consumed.copy()
    stocks=[stock.copy()] if record else None;shortages=[] if record else None
    for q,demand,dt in zip(supply,need,days):
        available=stock+q;overflow+=np.maximum(0.,available-capacity);stock=np.minimum(available,capacity);peak=np.maximum(peak,stock)
        rate=demand/dt
        plain=np.divide(stock,rate,out=np.full_like(stock,np.inf),where=rate>0)
        ratio=np.divide(hazard*stock,rate,out=np.zeros_like(stock),where=rate>0)
        depletion=np.divide(np.log1p(ratio),hazard,out=plain.copy(),where=(hazard>0)&(rate>0))
        fed=np.minimum(dt,depletion);eaten=rate*fed;missing=rate*(dt-fed)
        after=np.maximum(0.,stock*np.exp(-hazard*fed)-rate*_decay_integral(hazard,fed))
        after=np.where(depletion<dt,0.,after)
        spoiled+=np.maximum(0.,stock-after-eaten);stock=after
        consumed+=eaten;unmet+=missing;shortfall+=np.where(rate>0,dt-fed,0.)
        if record:stocks.append(stock.copy());shortages.append(missing.copy())
    harvested=supply.sum(axis=0);needed=need.sum(axis=0)
    residual=initial+harvested-consumed-spoiled-overflow-stock;periodic=np.abs(stock-initial)
    roundoff=50*np.finfo(float).eps*(initial+harvested+needed+stock)
    if not np.isfinite(stock).all() or not np.isfinite(residual).all():raise FloatingPointError('Nonfinite continuous inventory')
    if (np.abs(residual)>20*tolerance+roundoff).any():raise ArithmeticError('Continuous grain ledger failed conservation')
    return FoodYear(initial,stock,peak,harvested,needed,consumed,unmet,spoiled,overflow,shortfall,residual,periodic,np.abs(periodic)<=tolerance,
        np.stack(stocks) if record else None,np.stack(shortages) if record else None)


def continuous_food_year(supply,need,capacity,*,initial_stock=0.,loss_fraction_year=0.,step_days=1.,record=False):
    """Supply at bin start, immediate capacity clip, then continuous meals/decay."""
    return _year(initial_stock,_prepared(supply,need,capacity,loss_fraction_year,step_days),record)


def periodic_continuous_food_year(supply,need,capacity,*,loss_fraction_year=0.,step_days=1.,record=False):
    """Minimum repeating stock of the positive clipped affine annual map."""
    prepared=_prepared(supply,need,capacity,loss_fraction_year,step_days)
    supply,need,capacity,days,hazard,tolerance=prepared
    low=_advance(np.zeros_like(capacity),prepared);high=_advance(capacity,prepared)
    balance=np.zeros_like(capacity)
    for q,demand,dt in zip(supply,need,days):
        balance=(balance+q)*np.exp(-hazard*dt)-demand/dt*_decay_integral(hazard,dt)
    root=np.divide(balance,-np.expm1(-hazard*days.sum()),out=np.zeros_like(capacity),where=hazard>0)
    initial=np.minimum(high,np.maximum(low,root))
    if np.any(hazard==0):
        # Zero loss can admit a whole interval of fixed points. A bracket
        # search explicitly chooses its smallest member, also in mixed arrays.
        left=np.zeros_like(capacity);right=capacity.copy();starts_empty=low<=tolerance
        for _ in range(96):
            middle=left+.5*(right-left);drift=_advance(middle,prepared)-middle
            left=np.where(drift>0,middle,left);right=np.where(drift<=0,middle,right)
            if np.all((right-left<=tolerance)|starts_empty):break
        initial=np.where(hazard==0,np.where(starts_empty,0.,right),initial)
    result=_year(initial,prepared,record)
    if not result.periodic_converged.all():raise ArithmeticError('Continuous periodic stock failed its tolerance')
    return result
