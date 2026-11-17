"""Isolated quota-reference control of the qualified storage/loss adapter.

The physical ledger and operation order are copied from earth_storage_loss;
only the annual dispatch reference can change. None means the original
own-scenario quota for exact controls. Explicit references never resize stores.
"""
import numpy as np

from harvest.field_support import FixedRuralFood
from .earth_storage_loss import inventory, commercial_capacity, KCAL
from .seasonal_settlement_network import route_sources
from .wide_supply import ship


def fixed_dispatch_food(produced, boundary, rural, request, owner, retention, between,
                       *, marketed_share, reference_market, commercial_days, loss, dispatch_reference=None):
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
    annual_market = marketed.sum(0) if dispatch_reference is None else np.asarray(dispatch_reference, float)
    if annual_market.shape != rural.shape or not np.isfinite(annual_market).all() or (annual_market < 0).any():
        raise ValueError('One finite nonnegative annual dispatch reference per origin required')
    dispatch = np.broadcast_to(annual_market / 12, marketed.shape).copy()
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
