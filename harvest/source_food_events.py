"""Physical rural and export stores with explicit raw pickup requests.

Harvests fill the rural store first. Only its overflow quota enters the export
store. Pickups never take rural grain and no transport retention is applied.
Times, capacities and harvests are supplied scenarios, not inferred dates.
"""
from dataclasses import dataclass
from math import exp, expm1, fsum, isfinite
from numbers import Integral

from harvest.event_food_stocks import (
    EventFoodYear, _flow, _prepare, event_food_year, periodic_event_food_year,
)


@dataclass(frozen=True)
class ExportAccount:
    initial_stock: float
    final_stock: float
    peak_stock: float
    quota_input: float
    requested: float
    withdrawn: float
    unfilled: float
    spoiled: float
    overflow: float
    ledger_residual: float
    periodic_residual: float


@dataclass(frozen=True)
class SourceFoodYear:
    rural: EventFoodYear
    export: ExportAccount
    uncollected: float
    total_ledger_residual: float
    quota_times: tuple
    quota_cargo: tuple
    pickup_ids: tuple
    pickup_times: tuple
    pickup_requested: tuple
    pickup_withdrawn: tuple
    pickup_unfilled: tuple


def _requests(times, cargo, ids, year_days):
    times, cargo, ids = tuple(times), tuple(cargo), tuple(ids)
    if not len(times) == len(cargo) == len(ids):
        raise ValueError('Every pickup needs a time, raw request and unique ID')
    if any(not isinstance(i, Integral) or isinstance(i, bool) or i < 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Pickup IDs must be unique nonnegative integers')
    if any(not isfinite(t) or not 0 <= t < year_days for t in times) or any(not isfinite(q) or q < 0 for q in cargo):
        raise ValueError('Pickups need finite in-year times and nonnegative raw cargo')
    try:
        total = fsum(cargo)
    except OverflowError as error:
        raise ValueError('Annual pickup requests must remain finite') from error
    if not isfinite(total):
        raise ValueError('Annual pickup requests must remain finite')
    return tuple(map(float, times)), tuple(map(float, cargo)), tuple(map(int, ids))


def _quota(events, rural, rate, capacity, year_days, hazard, fraction):
    stock, clock = rural.initial_stock, 0.
    times, supplies = [], []
    for time, cargo in events:
        stock = _flow(stock, time-clock, rate, hazard)[0]
        overflow = max(0., stock+cargo-capacity)
        stock = min(capacity, stock+cargo)
        times.append(time)
        supplies.append(overflow*fraction)
        clock = time
    stock = _flow(stock, year_days-clock, rate, hazard)[0]
    scale = max(1., rural.harvested, rural.needed, capacity)
    if abs(stock-rural.final_stock) > 1e-10*scale or abs(fsum(supplies)-rural.overflow*fraction) > 1e-10*scale:
        raise ArithmeticError('Rural replay and overflow quota disagree')
    return tuple(times), tuple(supplies)


def _export_run(quota_times, quota, times, requests, ids, capacity, initial, year_days, hazard):
    # A supply clips to capacity before same-time pickups. Smaller supplied IDs
    # receive first access at an equal time, independent of input row order.
    events = [(t, 0, -1, q) for t, q in zip(quota_times, quota)]
    events += [(t, 1, i, q) for i, (t, q) in enumerate(zip(times, requests))]
    events.sort(key=lambda e: (e[0], e[1], ids[e[2]] if e[1] else -1))
    stock = peak = initial
    clock = 0.
    losses, overflow = [], []
    withdrawn = [0.]*len(requests)
    for time, kind, index, cargo in events:
        loss = stock * -expm1(-hazard*(time-clock))
        stock -= loss
        losses.append(loss)
        if kind == 0:
            overflow.append(max(0., stock+cargo-capacity))
            stock = min(capacity, stock+cargo)
            peak = max(peak, stock)
        else:
            amount = min(stock, cargo)
            withdrawn[index] = amount
            stock -= amount
        clock = time
    loss = stock * -expm1(-hazard*(year_days-clock))
    stock -= loss
    losses.append(loss)
    supplied, requested, taken, spoiled, spilled = map(fsum, (quota, requests, withdrawn, losses, overflow))
    missing = tuple(q-taken for q, taken in zip(requests, withdrawn))
    account = ExportAccount(initial, stock, peak, supplied, requested, taken, fsum(missing), spoiled, spilled,
        fsum((initial, supplied, -stock, -taken, -spoiled, -spilled)), stock-initial)
    return account, tuple(withdrawn), missing


def _inputs(harvest_times, harvest_cargo, pickup_times, pickup_cargo, pickup_ids, demand_rate, rural_capacity, export_capacity, quota_fraction, year_days, loss_fraction_year):
    events, hazard = _prepare(harvest_times, harvest_cargo, demand_rate, rural_capacity, year_days, loss_fraction_year)
    if not isfinite(export_capacity) or export_capacity < 0 or not isfinite(quota_fraction) or not 0 <= quota_fraction <= 1:
        raise ValueError('Nonnegative export capacity and quota fraction in [0,1] required')
    times, requests, ids = _requests(pickup_times, pickup_cargo, pickup_ids, year_days)
    if not isfinite(export_capacity+fsum(q for _, q in events)):
        raise ValueError('Source energies must remain finite')
    return events, hazard, times, requests, ids


def _result(events, rural, times, requests, ids, demand_rate, rural_capacity, export_capacity, fraction, year_days, hazard, initial_export, periodic):
    qt, quota = _quota(events, rural, demand_rate, rural_capacity, year_days, hazard, fraction)
    def run(stock):
        return _export_run(qt, quota, times, requests, ids, export_capacity, stock, year_days, hazard)
    if periodic:
        low = run(0.)[0].final_stock
        high = run(export_capacity)[0].final_stock
        balance = fsum([q*exp(-hazard*(year_days-t)) for t, q in zip(qt, quota)] +
                       [-q*exp(-hazard*(year_days-t)) for t, q in zip(times, requests)])
        initial_export = min(high, max(low, balance / -expm1(-hazard*year_days))) if hazard else (high if balance > 0 else low)
    account, withdrawn, missing = run(initial_export)
    uncollected = fsum((rural.overflow*(1-fraction), account.overflow))
    total = fsum((rural.initial_stock, account.initial_stock, rural.harvested, -rural.final_stock,
        -account.final_stock, -rural.consumed, -rural.spoiled, -account.spoiled, -account.withdrawn, -uncollected))
    scale = max(1., rural.harvested, rural.needed, account.requested, rural_capacity, export_capacity)
    if any(abs(v) > 1e-9*scale for v in (rural.ledger_residual, account.ledger_residual, total)):
        raise ArithmeticError('Source stores do not conserve raw grain')
    if periodic and any(abs(v) > 1e-9*scale for v in (rural.periodic_residual, account.periodic_residual)):
        raise ArithmeticError('Source stores do not repeat')
    return SourceFoodYear(rural, account, uncollected, total, qt, quota, ids, times, requests, withdrawn, missing)


def source_food_year(harvest_times, harvest_cargo, pickup_times, pickup_cargo, pickup_ids, *, demand_rate, rural_capacity,
                     export_capacity, quota_fraction=.1, initial_rural_stock=0., initial_export_stock=0., year_days=365., loss_fraction_year=.05):
    """Replay supplied initial stores; equal-time harvest precedes pickup IDs."""
    e, h, t, q, ids = _inputs(harvest_times, harvest_cargo, pickup_times, pickup_cargo, pickup_ids,
        demand_rate, rural_capacity, export_capacity, quota_fraction, year_days, loss_fraction_year)
    if not isfinite(initial_export_stock) or not 0 <= initial_export_stock <= export_capacity:
        raise ValueError('Initial export stock must fit its physical capacity')
    rural = event_food_year([t for t, _ in e], [q for _, q in e], demand_rate=demand_rate, capacity=rural_capacity,
        initial_stock=initial_rural_stock, year_days=year_days, loss_fraction_year=loss_fraction_year)
    return _result(e, rural, t, q, ids, demand_rate, rural_capacity, export_capacity, quota_fraction, year_days, h, initial_export_stock, False)


def periodic_source_food_year(harvest_times, harvest_cargo, pickup_times, pickup_cargo, pickup_ids, *, demand_rate, rural_capacity,
                              export_capacity, quota_fraction=.1, year_days=365., loss_fraction_year=.05):
    """Minimum repeating rural stock, then minimum repeating export stock."""
    e, h, t, q, ids = _inputs(harvest_times, harvest_cargo, pickup_times, pickup_cargo, pickup_ids,
        demand_rate, rural_capacity, export_capacity, quota_fraction, year_days, loss_fraction_year)
    rural = periodic_event_food_year([t for t, _ in e], [q for _, q in e], demand_rate=demand_rate,
        capacity=rural_capacity, year_days=year_days, loss_fraction_year=loss_fraction_year)
    return _result(e, rural, t, q, ids, demand_rate, rural_capacity, export_capacity, quota_fraction, year_days, h, 0., True)
