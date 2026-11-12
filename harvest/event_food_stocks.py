"""Destination-only food inventory with instantaneous supply and continuous meals.

This primitive assumes food is available at the destination at each supplied
event time. It does not model source availability, travel rations or diets.
"""
from dataclasses import dataclass
from math import exp, expm1, fsum, isfinite, log1p


@dataclass(frozen=True)
class EventFoodYear:
    initial_stock: float
    final_stock: float
    peak_stock: float
    harvested: float
    needed: float
    consumed: float
    unmet: float
    spoiled: float
    overflow: float
    shortfall_days: float
    ledger_residual: float
    periodic_residual: float


def _prepare(times, supplies, demand_rate, capacity, year_days, loss_fraction_year):
    times, supplies = tuple(times), tuple(supplies)
    if len(times) != len(supplies):
        raise ValueError('Each delivery needs a time and supply')
    if not all(isfinite(v) for v in (demand_rate, capacity, year_days, loss_fraction_year)) or demand_rate < 0 or capacity < 0 or year_days <= 0 or not 0 <= loss_fraction_year < 1:
        raise ValueError('Invalid inventory parameters')
    if any(not isfinite(t) or not 0 <= t < year_days for t in times) or any(not isfinite(q) or q < 0 for q in supplies):
        raise ValueError('Events need finite times inside the year and nonnegative cargo')
    groups = {}
    for t, q in zip(times, supplies):
        groups.setdefault(float(t), []).append(float(q))
    try:
        events = tuple((t, fsum(groups[t])) for t in sorted(groups))
        total = fsum(q for _, q in events)
    except OverflowError as error:
        raise ValueError('Annual energy must remain finite') from error
    if not all(isfinite(v) for v in (total, demand_rate * year_days, capacity + total)):
        raise ValueError('Annual energy must remain finite')
    return events, -log1p(-loss_fraction_year) / year_days


def _flow(stock, length, rate, hazard):
    """Return remaining, consumed, unmet, spoiled, empty-duration exactly."""
    if rate == 0:
        loss = stock * -expm1(-hazard * length)
        return stock - loss, 0., 0., loss, 0.
    depletion = (log1p(hazard * stock / rate) / hazard if hazard else stock / rate)
    fed = min(length, depletion)
    consumed = rate * fed
    remaining = (stock * exp(-hazard * fed) - rate * -expm1(-hazard * fed) / hazard if hazard else stock - consumed)
    remaining = max(0., remaining) if fed == length else 0.
    spoiled = max(0., stock - remaining - consumed)
    missing_days = max(0., length - fed)
    return remaining, consumed, rate * missing_days, spoiled, missing_days


def _run(events, rate, capacity, year_days, hazard, initial):
    stock = peak = initial; previous = 0.
    consumed = []; unmet = []; spoiled = []; overflow = []; empty = []
    for time, cargo in (*events, (year_days, 0.)):
        stock, eaten, missing, lost, duration = _flow(stock, time - previous, rate, hazard)
        consumed.append(eaten); unmet.append(missing); spoiled.append(lost); empty.append(duration)
        spilled = max(0., stock + cargo - capacity)
        overflow.append(spilled); stock = min(capacity, stock + cargo); peak = max(peak, stock)
        previous = time
    harvested = fsum(q for _, q in events)
    eaten, missing, lost, spilled = map(fsum, (consumed, unmet, spoiled, overflow))
    residual = fsum((initial, harvested, -eaten, -lost, -spilled, -stock))
    return EventFoodYear(initial, stock, peak, harvested, rate * year_days, eaten,
                         missing, lost, spilled, fsum(empty), residual, stock - initial)


def event_food_year(times, supplies, *, demand_rate, capacity, initial_stock=0., year_days=365., loss_fraction_year=.05):
    events, hazard = _prepare(times, supplies, demand_rate, capacity, year_days, loss_fraction_year)
    if not isfinite(initial_stock) or not 0 <= initial_stock <= capacity:
        raise ValueError('Initial stock must lie within capacity')
    return _run(events, demand_rate, capacity, year_days, hazard, initial_stock)


def periodic_event_food_year(times, supplies, *, demand_rate, capacity, year_days=365., loss_fraction_year=.05):
    """Smallest fixed point of the year's clamped affine inventory map.

    Every interval is a positive affine map clipped at zero; every pulse is
    addition clipped at capacity. Their composition is clip(A*s+B,F(0),F(cap)).
    With storage loss A<1, so its unique fixed point is clip(B/(1-A),F0,Fcap).
    At zero loss, B=0 gives a fixed interval; its lower end is the minimum.
    """
    events, hazard = _prepare(times, supplies, demand_rate, capacity, year_days, loss_fraction_year)
    low = _run(events, demand_rate, capacity, year_days, hazard, 0.).final_stock
    high = _run(events, demand_rate, capacity, year_days, hazard, capacity).final_stock
    if hazard:
        balance = fsum([q * exp(-hazard * (year_days - t)) for t, q in events] +
                       [-demand_rate * -expm1(-hazard * year_days) / hazard])
        initial = min(high, max(low, balance / -expm1(-hazard * year_days)))
    else:
        balance = fsum([q for _, q in events] + [-demand_rate * year_days])
        # fsum avoids cancellation from summing the supply then subtracting need.
        initial = high if balance > 0 else low
    result = _run(events, demand_rate, capacity, year_days, hazard, initial)
    tolerance = 1e-9 * max(1., result.harvested, result.needed, capacity)
    if abs(result.periodic_residual) > tolerance or abs(result.ledger_residual) > tolerance:
        raise ArithmeticError('Periodic inventory or food conservation failed')
    return result
