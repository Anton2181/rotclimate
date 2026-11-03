"""Seasonal edible-food inventories under explicit harvest/demand scenarios.

Inputs are energy per accounting area per step, typically MJ/km², in one
homogeneous edible-food pool. Harvest must already exclude seed and processing
deductions; seed inventories need separate accounting. This module does not
infer crop yields, calendars, population, institutions, trade or weather risk.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class FoodYear:
    initial_stock: np.ndarray
    final_stock: np.ndarray
    peak_stock: np.ndarray
    harvested: np.ndarray
    needed: np.ndarray
    consumed: np.ndarray
    unmet: np.ndarray
    spoiled: np.ndarray
    overflow: np.ndarray
    shortfall_days: np.ndarray
    ledger_residual: np.ndarray
    periodic_residual: np.ndarray
    periodic_converged: np.ndarray
    stock_path: np.ndarray | None = None
    unmet_path: np.ndarray | None = None


def _series(harvest, need):
    harvest, need = np.broadcast_arrays(np.asarray(harvest, float), np.asarray(need, float))
    if harvest.ndim < 1 or harvest.shape[0] < 1:
        raise ValueError('Need a nonempty time axis')
    if not np.isfinite(harvest).all() or not np.isfinite(need).all() or (harvest < 0).any() or (need < 0).any():
        raise ValueError('Harvest and demand must be finite nonnegative energies')
    with np.errstate(over='ignore'):
        totals = (harvest.sum(0), need.sum(0))
    if any(not np.isfinite(total).all() for total in totals):
        raise ValueError('Annual energy totals must remain finite')
    return harvest, need


def _prepare(harvest, need, capacity, loss_fraction_year, step_days):
    harvest, need = _series(harvest, need)
    shape = harvest.shape[1:]
    capacity = np.broadcast_to(np.asarray(capacity, float), shape)
    loss = np.broadcast_to(np.asarray(loss_fraction_year, float), shape)
    days = np.broadcast_to(np.asarray(step_days, float), (harvest.shape[0],))
    if not np.isfinite(capacity).all() or (capacity < 0).any():
        raise ValueError('Storage capacity must be finite and nonnegative')
    if not np.isfinite(loss).all() or ((loss < 0) | (loss >= 1)).any():
        raise ValueError('Annual stored-food loss fraction must be in [0,1)')
    if not np.isfinite(days).all() or (days <= 0).any():
        raise ValueError('Step lengths must be positive finite days')
    with np.errstate(over='ignore'):
        year_days = days.sum()
    if not np.isfinite(year_days):
        raise ValueError('Year length must remain finite')
    # This is loss from food that stays stored, not a fraction of harvest.
    hazard = -np.log1p(-loss) / year_days
    tolerance = 1e-10 * np.maximum(1., np.maximum(harvest.sum(0), need.sum(0)))
    return harvest, need, capacity, days, hazard, tolerance


def _advance(initial, prepared):
    harvest, need, capacity, days, hazard, _ = prepared
    stock = np.array(initial, float, copy=True)
    for supply, demand, length in zip(harvest, need, days):
        stock = np.minimum(np.maximum(stock + supply - demand, 0.), capacity) * np.exp(-hazard * length)
    return stock


def _year(initial, prepared, record):
    harvest, need, capacity, days, hazard, tolerance = prepared
    initial = np.broadcast_to(np.asarray(initial, float), capacity.shape).copy()
    if not np.isfinite(initial).all() or ((initial < 0) | (initial > capacity)).any():
        raise ValueError('Initial stocks must be finite and within storage capacity')
    stock = initial.copy(); peak = initial.copy()
    consumed = np.zeros_like(stock); unmet = consumed.copy(); spoiled = consumed.copy()
    overflow = consumed.copy(); shortfall_days = consumed.copy()
    stocks = [stock.copy()] if record else None
    shortages = [] if record else None
    for supply, demand, length in zip(harvest, need, days):
        available = stock + supply
        eaten = np.minimum(available, demand)
        missing = demand - eaten
        remaining = available - eaten
        spilled = np.maximum(remaining - capacity, 0.)
        remaining = np.minimum(remaining, capacity)
        peak = np.maximum(peak, remaining)
        lost = remaining * -np.expm1(-hazard * length)
        stock = remaining - lost
        consumed += eaten; unmet += missing; spoiled += lost; overflow += spilled
        # A step with insufficient food is a shortage interval; this is not
        # a probabilistic famine duration or a mortality estimate.
        shortfall_days += np.where(missing > tolerance, length, 0.)
        if record:
            stocks.append(stock.copy()); shortages.append(missing.copy())
    harvested = harvest.sum(0); needed = need.sum(0)
    ledger = initial + harvested - consumed - spoiled - overflow - stock
    if not np.isfinite(stock).all() or not np.isfinite(ledger).all():
        raise FloatingPointError('Nonfinite inventory result')
    roundoff = 50 * np.finfo(float).eps * (np.abs(initial) + harvested + needed + np.abs(stock))
    if (np.abs(ledger) > 20 * tolerance + roundoff).any():
        raise RuntimeError('Food inventory ledger did not close')
    periodic = np.abs(stock - initial)
    return FoodYear(initial, stock, peak, harvested, needed, consumed, unmet,
        spoiled, overflow, shortfall_days, ledger, periodic, periodic <= tolerance,
        None if stocks is None else np.stack(stocks),
        None if shortages is None else np.stack(shortages))


def food_year(harvest, need, capacity, *, initial_stock=0., loss_fraction_year=0., step_days=1., record=False):
    """One supplied year: harvest, immediate meals, capacity, then storage loss.

    Supply and demand are energies integrated over each step. ``step_days``
    controls storage decay and shortage-interval lengths, not energy units.
    Initial stock is an explicit input, never hidden food production.
    """
    return _year(initial_stock, _prepare(harvest, need, capacity, loss_fraction_year, step_days), record)


def periodic_food_year(harvest, need, capacity, *, loss_fraction_year=0., step_days=1., record=False):
    """Find the smallest repeating inventory for an identical repeated year.

    The nonexpansive annual stock map gives a monotone root bracket on
    [0,capacity]. Bisection avoids pretending a finite spin-up or a large
    inherited reserve is a sustainable food supply. Shortage years can also
    repeat; periodic convergence is separate from meeting food needs.
    """
    prepared = _prepare(harvest, need, capacity, loss_fraction_year, step_days)
    _, _, capacity, _, _, tolerance = prepared
    low = np.zeros_like(capacity); high = np.array(capacity, copy=True)
    starts_empty = _advance(low, prepared) <= tolerance
    for _ in range(96):
        mid = low + .5 * (high - low)
        drift = _advance(mid, prepared) - mid
        low = np.where(drift > 0, mid, low)
        high = np.where(drift <= 0, mid, high)
        if np.all((high - low <= tolerance) | starts_empty): break
    initial = np.where(starts_empty, 0., high)
    result = _year(initial, prepared, record)
    if not result.periodic_converged.all():
        raise RuntimeError('Repeating inventory did not meet its convergence criterion')
    return result


def minimum_zero_loss_capacity(harvest, need):
    """Minimum storage for a repeatable no-shortage year without spoilage.

    The largest cyclic cumulative energy deficit determines required storage.
    Insufficient annual production returns infinity, not a fictitious reserve.
    Meals can use a harvest immediately; capacity limits food held afterwards.
    """
    harvest, need = _series(harvest, need)
    deficit = need - harvest
    maximum = np.zeros(deficit.shape[1:]); minimum = maximum.copy()
    max_end = maximum.copy(); min_end = maximum.copy()
    for value in deficit:
        max_end = np.maximum(0., max_end + value)
        min_end = np.minimum(0., min_end + value)
        maximum = np.maximum(maximum, max_end); minimum = np.minimum(minimum, min_end)
    total = deficit.sum(0)
    capacity = np.maximum(maximum, total - minimum)
    tolerance = 1e-10 * np.maximum(1., np.maximum(harvest.sum(0), need.sum(0)))
    return np.where(total > tolerance, np.inf, np.maximum(capacity, 0.))
