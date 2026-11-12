"""One monthly staff-hour pool for fixed grain collection and secondary duties.

Failure refuses the fixed food/work case. It never reduces grain shipments and
then claims the unchanged residents remain fed, or infers political authority.
"""
from dataclasses import dataclass
import numpy as np

from .service_capacity import supported_staff_hours


def collection_trip_work(departures, outward_days, inward_days, accessible, *,
                         load_kcal, walking_hours_day=7., handling_hours=.25):
    food = np.asarray(departures, float)
    out, back = np.asarray(outward_days, float), np.asarray(inward_days, float)
    access = np.asarray(accessible)
    if food.ndim != 2 or food.shape[0] != 12 or any(a.shape != food.shape for a in (out, back, access)):
        raise ValueError('Twelve matching shipment/path/access bins per origin required')
    if access.dtype.kind != 'b' or not np.isfinite(food).all() or np.any(food < 0):
        raise ValueError('Nonnegative finite shipments and boolean access required')
    if any(np.isnan(a).any() or np.any(a < 0) for a in (out, back)):
        raise ValueError('Nonnegative directed travel times required')
    if not np.isfinite([load_kcal, walking_hours_day, handling_hours]).all() or min(load_kcal, walking_hours_day) <= 0 or handling_hours < 0:
        raise ValueError('Positive load/walking day and nonnegative handling scenario required')
    positive = food > 0
    if np.any(positive & (~access | ~np.isfinite(out) | ~np.isfinite(back))):
        raise ValueError('Shipment outside checked two-way collection access')
    trips = np.zeros_like(food)
    with np.errstate(over='ignore', under='ignore'):
        trips[positive] = np.maximum(1., np.ceil(food[positive] / load_kcal))
    if not np.isfinite(trips).all() or np.any(trips > 2 ** 53):
        raise ValueError('Collector trip count exceeds exact numerical range')
    hours = np.zeros_like(food)
    with np.errstate(over='ignore', under='ignore'):
        hours[positive] = trips[positive] * ((out[positive] + back[positive]) * walking_hours_day + handling_hours)
    if not np.isfinite(hours).all() or np.any(positive & (hours <= 0)):
        raise ValueError('Collection work exceeds numerical range or becomes free')
    return trips, hours


@dataclass
class MonthlyWork:
    gross_hours: np.ndarray
    required_collection_hours: np.ndarray
    fundable_collection_hours: np.ndarray
    collection_unmet_hours: np.ndarray
    qualified: np.ndarray
    secondary_served: np.ndarray
    secondary_unreachable: np.ndarray
    secondary_capacity_unmet: np.ndarray
    secondary_hours: np.ndarray
    unused_hours: np.ndarray
    invalid_reused_budget_hours: np.ndarray


def allocate_monthly_work(plan, collection_hours, requests, *, hours_per_staff_month,
                          source_supported, hours_per_request):
    """Reserve fixed collection; ration all remaining claims together per month.

    Qualification is whole-year: an unsupported source or one month of collection
    shortfall blocks every secondary duty at that site. The return is a fixed-plan
    audit, not a recomputed food equilibrium or realized patrol coverage.
    """
    staff = np.asarray(plan.institutional_people, float)
    shape = (12, len(staff))
    collection = np.asarray(collection_hours, float)
    demand = np.asarray(requests, float)
    source = np.asarray(source_supported)
    if collection.shape != shape or demand.ndim != 3 or demand.shape[1:] != shape or not demand.shape[0]:
        raise ValueError('Monthly collection and channel/month/site requests required')
    if source.shape != staff.shape or source.dtype.kind != 'b':
        raise ValueError('Explicit source-food support per site required')
    try:
        envelope = np.broadcast_to(np.asarray(hours_per_staff_month, float), shape)
        cost = np.broadcast_to(np.asarray(hours_per_request, float), demand.shape)
    except ValueError as error:
        raise ValueError('Aligned monthly work and request costs required') from error
    if any(not np.isfinite(a).all() or np.any(a < 0) for a in (collection, demand, envelope)):
        raise ValueError('Finite nonnegative collection/requests/work required')
    if not np.isfinite(cost).all() or np.any(cost <= 0):
        raise ValueError('Finite positive secondary work costs required')
    # Reuse resident/food validation; these annual hours are never a second pool.
    annual = supported_staff_hours(plan, hours_per_staff=envelope.sum(axis=0), committed_hours=0.)
    with np.errstate(over='ignore', under='ignore'):
        gross = staff[None, :] * envelope
        requested_hours = demand * cost
        total_requested = requested_hours.sum(axis=0)
    if (not np.isfinite(gross).all() or not np.isfinite(total_requested).all()
            or np.any((demand > 0) & (requested_hours == 0))
            or np.any((staff[None, :] > 0) & (envelope > 0) & (gross == 0))):
        raise ValueError('Monthly work exceeds numerical range')
    if not np.allclose(gross.sum(axis=0), annual.gross_hours, rtol=1e-12, atol=1e-8):
        raise RuntimeError('Monthly hours differ from the same annual cohort')
    funded = np.minimum(collection, gross)
    shortfall = collection - funded
    qualified = source & np.all(collection <= gross, axis=0)
    spare = np.maximum(gross - funded, 0.) * qualified[None, :]
    fraction = np.divide(spare, total_requested, out=np.ones_like(spare), where=total_requested > spare)
    fraction *= qualified[None, :]
    served = demand * fraction[None, :, :]
    unreachable = demand * (~qualified)[None, None, :]
    capacity_unmet = np.maximum(demand - served - unreachable, 0.)
    used = served * cost
    unused = np.maximum(gross - funded - used.sum(axis=0), 0.)
    # Deliberately invalid reference: each channel separately reuses all spare.
    naive = np.minimum(requested_hours, spare[None, :, :]).sum(axis=0)
    if (np.any(funded + used.sum(axis=0) > gross + 1e-9 * np.maximum(1., gross))
            or not np.allclose(served + unreachable + capacity_unmet, demand, rtol=1e-12, atol=1e-8)):
        raise RuntimeError('Shared monthly work/request ledger failed')
    return MonthlyWork(gross.copy(), collection.copy(), funded, shortfall, qualified,
                       served, unreachable, capacity_unmet, used, unused, naive)
