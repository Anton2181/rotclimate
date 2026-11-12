"""Finite origin residents feeding the existing seasonal-food SettlementPlan.

An explicit caller-supplied population is partitioned, never added to a rural
total. Catchments and transfer shares are inputs, not inferred migration or
calibrated urban shares. Food production must already reflect available labour.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np

from harvest.food_stocks import periodic_food_year
from .settlement_support import allocate_settlement, permanent_food_ceiling


@dataclass
class ResidentAllocation:
    settlement: object
    origin_people: np.ndarray
    rural_people: np.ndarray
    transferred_people: np.ndarray
    destination_budget: np.ndarray
    owner: np.ndarray  # one destination per origin, -1 explicitly unassigned
    arrivals: np.ndarray
    kcal_day: float
    year_days: float
    store_days: float
    loss_fraction_year: float


def allocate_residents(arrivals, origin_people, owner, civilian_request, affiliated, *, transfer_fraction,
                       institutional_request=100., minimum_community=50., kcal_day=2500.,
                       year_days=365., store_days=90., loss_fraction_year=.05):
    """Cap civilian AND institutional residents by one finite origin budget.

    Population not transferred stays rural, including unreachable origins and
    unused transfer allowances. No minimum community/cohort can create people.
    Transfers within a catchment are proportional to the supplied allowances.
    The ordinary food allocator is reused unchanged; production defaults and
    historical benchmark producers retain their exact identities.

    This alone certifies population and destination food. Call audit_origin_food
    before treating shipments/rural meals as one feasible food ledger. It must
    consume the returned rural_people, rather than an unchanged rural food claim.
    """
    population = np.asarray(origin_people, float)
    ids = np.asarray(owner); request = np.asarray(civilian_request, float)
    affiliation = np.asarray(affiliated, bool); food = np.asarray(arrivals, float)
    if population.ndim != 1 or ids.shape != population.shape or ids.dtype.kind not in 'iu':
        raise ValueError('One finite origin vector and one integer owner per origin required')
    if request.ndim != 1 or affiliation.shape != request.shape or food.shape != (12, len(request)):
        raise ValueError('Twelve arrivals and civilian/affiliation records per destination required')
    if not len(request) or np.any((ids < -1) | (ids >= len(request))):
        raise ValueError('Owner must be -1 or a valid destination index')
    if not np.isfinite(population).all() or np.any(population < 0):
        raise ValueError('Finite nonnegative origin people required')
    with np.errstate(over='ignore'):
        if not np.isfinite(population.sum()):
            raise ValueError('Total population exceeds numerical range')
    if not np.isfinite(request).all() or np.any(request < 0):
        raise ValueError('Finite nonnegative civilian requests required')
    if not np.isfinite([institutional_request, minimum_community]).all() or institutional_request <= 0 or minimum_community < 0:
        raise ValueError('Positive cohort and nonnegative community threshold required')
    fraction = np.broadcast_to(np.asarray(transfer_fraction, float), population.shape)
    if not np.isfinite(fraction).all() or np.any((fraction < 0) | (fraction > 1)):
        raise ValueError('Explicit origin transfer fractions in [0,1] required')
    reached = ids >= 0
    allowance = np.where(reached, population * fraction, 0.)
    budget = np.bincount(ids[reached], weights=allowance[reached], minlength=len(request))
    if not np.isfinite(budget).all():
        raise ValueError('Population budget exceeds numerical range')
    food_ceiling = permanent_food_ceiling(food, kcal_day=kcal_day, year_days=year_days,
        store_days=store_days, loss_fraction_year=loss_fraction_year)
    active = affiliation & (request >= minimum_community) & (
        np.minimum(budget, food_ceiling) >= institutional_request + minimum_community)
    capped_request = np.minimum(request, np.maximum(budget - np.where(active, institutional_request, 0.), 0.))
    plan = allocate_settlement(food, capped_request, active, institutional_request=institutional_request,
        minimum_community=minimum_community, kcal_day=kcal_day, year_days=year_days,
        store_days=store_days, loss_fraction_year=loss_fraction_year)
    fraction_used = np.divide(plan.total_people, budget, out=np.zeros_like(budget), where=budget > 0)
    moved = np.zeros_like(population)
    moved[reached] = allowance[reached] * fraction_used[ids[reached]]
    rural = population - moved
    settled = np.bincount(ids[reached], weights=moved[reached], minlength=len(request))
    if (np.any(plan.total_people > budget + 1e-8) or np.any(rural < -1e-8)
            or not np.allclose(settled, plan.total_people, rtol=1e-11, atol=1e-8)
            or not np.isclose(rural.sum() + plan.total_people.sum(), population.sum(), rtol=1e-11, atol=1e-8)):
        raise RuntimeError('Origin/rural/settlement population partition failed')
    return ResidentAllocation(plan, population.copy(), rural, moved, budget, ids.copy(), food.copy(),
                              float(kcal_day), float(year_days), float(store_days), float(loss_fraction_year))


def audit_origin_food(allocation, harvest, departures, *, origin_capacity_kcal,
                      retention, delay_bins, loss_fraction_year=.05):
    """Gate supplied shipments against remaining rural meals and the SAME grain.

    Harvest/departures are twelve bins per origin of already-edible food. Each
    origin exports only to its one supplied owner. No routes, capacity, permission,
    staff recruitment or production labour are invented. This homogeneous food
    pool supplies the same explicit ration to rural and settlement residents.
    Failure blocks treating the destination plan as a coupled feasible result.
    """
    if not isinstance(allocation, ResidentAllocation):
        raise ValueError('A finite ResidentAllocation is required')
    plan = allocation.settlement
    pop, rural, moved, ids = (np.asarray(a) for a in (allocation.origin_people,
        allocation.rural_people, allocation.transferred_people, allocation.owner))
    if (pop.ndim != 1 or any(a.shape != pop.shape for a in (rural, moved, ids)) or ids.dtype.kind not in 'iu'
            or np.any((ids < -1) | (ids >= len(plan.total_people)))
            or any(not np.isfinite(a).all() or np.any(a < 0) for a in (pop, rural, moved))
            or not np.allclose(rural + moved, pop, rtol=1e-11, atol=1e-8)
            or np.any(moved[ids < 0] > 0)):
        raise ValueError('Origin population partition changed or is invalid')
    reached = ids >= 0
    relocated = np.bincount(ids[reached], weights=moved[reached], minlength=len(plan.total_people))
    if (not np.allclose(relocated, plan.total_people, rtol=1e-11, atol=1e-8)
            or not np.allclose(plan.civilian_people + plan.institutional_people, plan.total_people, rtol=1e-11, atol=1e-8)
            or np.any(plan.total_people > allocation.destination_budget + 1e-8)):
        raise ValueError('Destination residents differ from conserved origin transfers')
    need = np.broadcast_to(plan.total_people * allocation.kcal_day * allocation.year_days / 12, allocation.arrivals.shape)
    destination = periodic_food_year(allocation.arrivals, need,
        plan.total_people * allocation.kcal_day * allocation.store_days,
        loss_fraction_year=allocation.loss_fraction_year, step_days=allocation.year_days / 12, record=True)
    for field in ('harvested', 'needed', 'consumed', 'unmet', 'spoiled', 'overflow'):
        if not np.allclose(getattr(destination, field), getattr(plan.food_year, field), rtol=1e-11, atol=1e-7):
            raise ValueError('Destination food record changed: ' + field)
    if np.any(destination.unmet > 1e-8 * np.maximum(1., destination.needed)):
        raise ValueError('Destination residents lack seasonal food support')
    supply, shipped = np.asarray(harvest, float), np.asarray(departures, float)
    shape = (12, len(allocation.origin_people))
    if supply.shape != shape or shipped.shape != shape:
        raise ValueError('Twelve harvest/departure bins per population origin required')
    if any(not np.isfinite(a).all() or np.any(a < 0) for a in (supply, shipped)):
        raise ValueError('Finite nonnegative source harvest and departures required')
    if not np.isfinite(retention) or not 0 <= retention <= 1:
        raise ValueError('Transport retention in [0,1] required')
    if isinstance(delay_bins, bool) or not isinstance(delay_bins, Integral) or not 0 <= delay_bins < 12:
        raise ValueError('Integer delivery delay in [0,11] required')
    if np.any(shipped[:, ~reached] > 0):
        raise ValueError('Unassigned origins cannot export to an invented destination')
    site_departures = np.stack([np.bincount(ids[reached], weights=s[reached],
        minlength=len(allocation.destination_budget)) for s in shipped])
    expected = np.roll(site_departures, delay_bins, axis=0) * retention
    if not np.allclose(expected, allocation.arrivals, rtol=1e-11, atol=1e-7):
        raise ValueError('Destination arrivals do not match the declared origin shipments')
    rural_need = np.broadcast_to(allocation.rural_people * allocation.kcal_day * allocation.year_days / 12, shape)
    combined_need = rural_need + shipped
    if not np.allclose(combined_need - shipped, rural_need, rtol=1e-10, atol=1e-7):
        raise ValueError('Rural meals are lost at the numerical range of the declared exports')
    year = periodic_food_year(supply, combined_need, origin_capacity_kcal,
        loss_fraction_year=loss_fraction_year, step_days=allocation.year_days / 12, record=True)
    # Large export volumes must not relax protection of a small rural cohort.
    if np.any(year.unmet > 1e-8 * np.maximum(1., rural_need.sum(0))):
        raise ValueError('Remaining rural meals and declared exports cannot coexist on the origin food budget')
    transport_loss = float(shipped.sum() * (1 - retention))
    rural_consumed = float(year.consumed.sum() - shipped.sum())
    stock_change = float((year.final_stock - year.initial_stock).sum()
                         + (destination.final_stock - destination.initial_stock).sum())
    residual = float(supply.sum() - rural_consumed - year.spoiled.sum() - year.overflow.sum()
        - transport_loss - destination.consumed.sum() - destination.spoiled.sum() - destination.overflow.sum())
    residual -= stock_change
    if abs(residual) > 1e-7 * max(1., supply.sum()):
        raise RuntimeError('Combined rural/transport/settlement grain ledger failed')
    return dict(status='passed', source_food_feasible=True, population_conserved=True,
        origin_food_year=year, rural_meals_kcal=rural_consumed, rural_need_kcal=float(rural_need.sum()),
        rural_unmet_kcal=float(year.unmet.sum()),
        rural_people=float(allocation.rural_people.sum()),
        settlement_people=float(allocation.settlement.total_people.sum()),
        origin_harvest_kcal=float(supply.sum()), origin_spoilage_kcal=float(year.spoiled.sum()),
        origin_unused_kcal=float(year.overflow.sum()), departed_kcal=float(shipped.sum()),
        transport_loss_kcal=transport_loss, destination_meals_kcal=float(destination.consumed.sum()),
        destination_spoilage_kcal=float(destination.spoiled.sum()),
        destination_unused_kcal=float(destination.overflow.sum()), periodic_stock_change_kcal=stock_change,
        joint_residual_kcal=residual)
