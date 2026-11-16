"""Declared fixed-infrastructure storage/loss sensitivity, isolated from the pilot.

Five-percent stocks retain the qualified analytic adapter verbatim. Zero-loss
stocks use the clipped annual map's endpoints at the original tolerance.
Commercial capacities are supplied absolute energies, never scenario output.
"""
import numpy as np

from harvest.field_support import FixedRuralFood
from harvest.food_stocks import food_year
from .seasonal_settlement_network import food_year as original_year, route_sources
from .wide_supply import ship

KCAL = 912500.


def inventory(harvest, need, capacity, loss):
    if loss == .05:
        return original_year(harvest, need, capacity)
    if loss != 0:
        raise ValueError('Only declared zero/five-percent losses supported')
    # At zero loss the annual map is clip(s+B, lower, upper). Its lower
    # endpoint is T(0); if that endpoint repeats at the original tolerance,
    # it is the smallest sustainable reserve under that criterion. Otherwise
    # positive annual drift makes the upper endpoint T(cap) the fixed point.
    # Testing the lower endpoint first avoids floating balanced-year drift
    # choosing an arbitrary large root from an interval of repeating stocks.
    kwargs = dict(loss_fraction_year=0., step_days=365/12, record=True)
    empty = food_year(harvest, need, capacity, **kwargs)
    tol = 1e-10 * np.maximum(1., np.maximum(empty.harvested, empty.needed))
    lower = np.where(empty.final_stock <= tol, 0., empty.final_stock)
    low_year = food_year(harvest, need, capacity, initial_stock=lower, **kwargs)
    if low_year.periodic_converged.all():
        return low_year
    upper = food_year(harvest, need, capacity, initial_stock=capacity, **kwargs).final_stock
    initial = np.where(low_year.periodic_converged, lower, upper)
    result = food_year(harvest, need, capacity, initial_stock=initial, **kwargs)
    if not result.periodic_converged.all():
        raise RuntimeError('Zero-loss endpoint inventory did not repeat at original tolerance')
    return result


def commercial_capacity(reference_market, days):
    reference = np.asarray(reference_market, float)
    if days not in (365, 90) or not np.isfinite(reference).all() or (reference < 0).any():
        raise ValueError('Nonnegative baseline reference and declared capacity required')
    return reference.copy() if days == 365 else reference * 90 / 365


def fixed_storage_food(produced, boundary, rural, request, owner, retention, between,
                       *, marketed_share, reference_market, commercial_days, loss):
    produced = np.asarray(produced, float); boundary = np.asarray(boundary)
    rural = np.asarray(rural, float); request = np.asarray(request, float)
    owner = np.asarray(owner); retention = np.asarray(retention, float); between = np.asarray(between, float)
    if produced.ndim != 2 or boundary.shape != produced.shape or rural.shape != produced.shape[1:]:
        raise ValueError('Aligned component production/calendars and rural population required')
    if request.ndim != 1 or owner.shape != (4, len(rural)) or retention.shape != owner.shape or between.shape != (4, len(request), len(request)):
        raise ValueError('Four route snapshots and fixed requests required')
    if not all(np.isfinite(v).all() for v in (produced, rural, request, retention, between)) or any((v < 0).any() for v in (produced, rural, request)):
        raise ValueError('Finite nonnegative physical inputs required')
    if not 0 <= marketed_share <= 1 or ((retention < 0) | (retention > 1)).any() or ((between < 0) | (between > 1)).any():
        raise ValueError('Grain fractions must lie in zero to one')
    positive = produced > 0
    if boundary.dtype.kind not in 'iu' or (positive & ((boundary < 0) | (boundary >= 12))).any():
        raise ValueError('Positive grain requires a monthly harvest boundary')
    if owner.dtype.kind not in 'iu' or ((owner < -1) | (owner >= len(request))).any():
        raise ValueError('Valid source route owners required')
    capacity = commercial_capacity(reference_market, commercial_days)
    if capacity.shape != rural.shape:
        raise ValueError('One fixed commercial reference per physical origin required')
    harvest = np.zeros((12, len(rural)))
    for component in range(len(produced)):
        valid = positive[component]; source = np.flatnonzero(valid)
        np.add.at(harvest, (boundary[component, valid], source), produced[component, valid])
    need = rural * KCAL; monthly_need = np.broadcast_to(need / 12, harvest.shape)
    rural_food = FixedRuralFood(harvest, inventory(harvest, monthly_need, need, loss), monthly_need, 365., 365.)
    marketed = rural_food.exportable * marketed_share
    annual_market = marketed.sum(0); dispatch = np.broadcast_to(annual_market / 12, marketed.shape).copy()
    for month in range(12):
        dispatch[month] *= (owner[month // 3] >= 0) & (retention[month // 3] > 0)
    export_food = inventory(marketed, dispatch, capacity, loss)
    departures = dispatch - export_food.unmet_path
    direct = route_sources(departures, owner, retention, len(request))
    town_need = np.broadcast_to(request * KCAL / 12, direct.shape); town_capacity = request * 2500. * 90
    local = inventory(direct, town_need, town_capacity, loss)
    protected = (request > 0) & (local.unmet <= 1e-8 * np.maximum(1, local.needed))
    overflow = np.maximum(local.stock_path[:-1] + direct - town_need - town_capacity, 0) * protected
    received = np.zeros_like(direct); exported = np.zeros_like(direct); moves = []
    for month in range(12):
        nxt = (month + 1) % 12
        flows, got = ship(overflow[month], local.unmet_path[nxt], between[month // 3])
        received[nxt] += got
        for (i, j), value in flows.items():
            exported[month, i] += value
            moves.append((month, i, j, value, value * between[month // 3, i, j]))
    final = inventory(direct + received, town_need, town_capacity, loss)
    return dict(harvest=harvest, rural_food=rural_food.year, marketed=marketed, dispatch=dispatch,
                export_food=export_food, departures=departures, direct=direct, direct_food=local,
                town_food=final, inter_received=received, inter_exported=exported,
                shipments=np.array(moves, float).reshape(-1, 5), arrivals=direct + received,
                protected_exporters=protected)
