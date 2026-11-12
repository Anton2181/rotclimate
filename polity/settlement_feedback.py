"""Cell people -> remaining workers -> grain -> rural meals -> town residents.

An isolated, partial cereal scenario using the existing work and food solvers.
No population is inferred from grain; no food deficit cell exports its meals.
Transfer feasibility can be nonmonotone because workers move with residents.
"""
from dataclasses import dataclass

import numpy as np

from harvest.field_support import field_support, fixed_rural_food
from harvest.food_stocks import periodic_food_year
from .settlement_support import SettlementPlan, permanent_food_ceiling
from .settlement_residents import ResidentAllocation


def collect_origins(overflow, owner, accessible, sites, *, fraction, freight_capacity,
                    retention, delay_bins, store_days, loss_fraction_year, year_days):
    """The stored_collection rule, retaining the underlying origin inventories.

    owner is zero-indexed here. The legacy rule uses one-indexed catchments;
    all origins supplied to this function have a destination.
    """
    food = np.asarray(overflow, float); ids = np.asarray(owner)
    access = np.asarray(accessible, bool)
    if food.ndim != 2 or food.shape[0] != 12 or ids.shape != (food.shape[1],) or access.shape != food.shape:
        raise ValueError('Twelve food/access bins and one owner per origin required')
    if ids.dtype.kind not in 'iu' or np.any((ids < 0) | (ids >= sites)):
        raise ValueError('Valid zero-indexed owner required')
    if (not np.isfinite(food).all() or np.any(food < 0) or not np.isfinite([fraction, retention, store_days, year_days]).all()
            or not 0 <= fraction <= 1 or not 0 <= retention <= 1 or store_days < 0 or year_days <= 0):
        raise ValueError('Finite nonnegative food/stores and fractional collection/retention required')
    if isinstance(delay_bins, bool) or not isinstance(delay_bins, (int, np.integer)) or not 0 <= delay_bins < 12:
        raise ValueError('Integer delivery delay below a year required')
    cap = np.broadcast_to(np.asarray(freight_capacity, float), (12, sites))
    if not np.isfinite(cap).all() or np.any(cap < 0):
        raise ValueError('Finite nonnegative freight capacities required')
    production = food * fraction
    annual = production.sum(0)
    total = np.bincount(ids, weights=annual, minlength=sites)
    share = np.divide(annual, total[ids], out=np.zeros_like(annual), where=total[ids] > 0)
    need = np.minimum(cap[:, ids] * share, annual / 12) * access
    year = periodic_food_year(production, need, annual * store_days / year_days,
        loss_fraction_year=loss_fraction_year, step_days=year_days / 12, record=True)
    taken = need - year.unmet_path
    departures = np.stack([np.bincount(ids, weights=t, minlength=sites) for t in taken])
    if np.any(departures > cap + 1e-7 * np.maximum(1, cap)):
        raise RuntimeError('Origin export stores exceeded the supplied freight slots')
    return dict(origin_departures=taken, departures=departures,
        arrivals=np.roll(departures, delay_bins, axis=0) * retention,
        transport_loss=float(departures.sum() * (1 - retention)),
        export_year=year, export_capacity=annual * store_days / year_days,
        uncollected=float(food.sum() - production.sum() + year.overflow.sum()))


@dataclass
class FeedbackInputs:
    people: np.ndarray
    owner: np.ndarray
    potential_kcal: np.ndarray
    boundaries: np.ndarray
    listed_hours: np.ndarray
    reaping_hours: np.ndarray
    access: np.ndarray
    civilian_request: np.ndarray
    affiliated: np.ndarray
    freight_capacity: np.ndarray


class CerealFeedback:
    def __init__(self, inputs, *, transfer_fraction, hours_worker_year, worker_fraction=.4,
                 harvest_days=30., hours_worker_day=8., kcal_day=2500., year_days=365.,
                 rural_store_days=365., export_store_days=365., destination_store_days=90.,
                 loss_fraction_year=.05, collection_fraction=.1, retention=.95, delay_bins=1,
                 institutional_request=100., minimum_community=50.):
        self.x = inputs; x = inputs
        p = np.asarray(x.people, float); ids = np.asarray(x.owner)
        n = len(x.civilian_request)
        if p.ndim != 1 or not len(p) or not n or ids.shape != p.shape or ids.dtype.kind not in 'iu':
            raise ValueError('Nonempty origin people and integer owner vectors required')
        if not np.isfinite(p).all() or np.any(p < 0) or np.any((ids < 0) | (ids >= n)):
            raise ValueError('Finite nonnegative people and valid owners required')
        for a in [x.potential_kcal, x.boundaries, x.listed_hours, x.reaping_hours]:
            if np.asarray(a).shape != p.shape:
                raise ValueError('Crop/work/calendar fields must match population origins')
        if np.asarray(x.access).shape != (12, len(p)) or np.asarray(x.affiliated).shape != (n,):
            raise ValueError('Aligned seasonal access and destination affiliations required')
        request = np.asarray(x.civilian_request, float)
        if not np.isfinite(request).all() or np.any(request < 0):
            raise ValueError('Finite nonnegative civilian requests required')
        if not np.isfinite(transfer_fraction) or not 0 <= transfer_fraction <= 1:
            raise ValueError('Transfer fraction must be in [0,1]')
        if not np.isfinite([institutional_request, minimum_community]).all() or institutional_request <= 0 or minimum_community < 0:
            raise ValueError('Positive institutional request and nonnegative civilian minimum required')
        self.kcal_day, self.year_days = kcal_day, year_days
        self.rural_store_days, self.destination_store_days = rural_store_days, destination_store_days
        self.loss_fraction_year = loss_fraction_year
        self.institutional_request, self.minimum_community = institutional_request, minimum_community
        self.work_options = dict(worker_fraction=worker_fraction, hours_worker_year=hours_worker_year,
            harvest_days=harvest_days, hours_worker_day=hours_worker_day, ration_kcal_day=kcal_day, year_days=year_days)
        self.collection_options = dict(fraction=collection_fraction, freight_capacity=x.freight_capacity,
            retention=retention, delay_bins=delay_bins, store_days=export_store_days,
            loss_fraction_year=loss_fraction_year, year_days=year_days)
        self.allowance = p * transfer_fraction
        self.budget = np.bincount(ids, weights=self.allowance, minlength=n)
        # Some total-resident requests lie in a gap between a civilian-only
        # community and one able to coexist with the reserved cohort.
        can_staff = np.asarray(x.affiliated, bool) & (request >= minimum_community) & (
            self.budget >= institutional_request + minimum_community)
        self.upper = np.minimum(self.budget, request + np.where(can_staff, institutional_request, 0.))

    def evaluate(self, total):
        x = self.x; target = np.asarray(total, float); n = len(self.budget)
        if target.shape != (n,) or not np.isfinite(target).all() or np.any(target < 0) or np.any(target > self.upper + 1e-8):
            raise ValueError('Trial residents must fit the original finite population/request bound')
        ratio = np.divide(target, self.budget, out=np.zeros_like(target), where=self.budget > 0)
        moved = self.allowance * ratio[x.owner]
        rural = np.asarray(x.people) - moved
        annual_need = rural * self.kcal_day * self.year_days
        work = field_support(x.potential_kcal, x.listed_hours, x.reaping_hours,
            rural_need_kcal=annual_need, **self.work_options)
        food = fixed_rural_food(work.produced_kcal, x.boundaries, annual_need,
            reserve_days=self.rural_store_days, loss_fraction_year=self.loss_fraction_year, year_days=self.year_days)
        overflow = food.exportable
        flow = collect_origins(overflow, x.owner, x.access, n, **self.collection_options)
        need = np.broadcast_to(target * self.kcal_day * self.year_days / 12, (12, n))
        town_food = periodic_food_year(flow['arrivals'], need, target * self.kcal_day * self.destination_store_days,
            loss_fraction_year=self.loss_fraction_year, step_days=self.year_days / 12, record=True)
        bad_origin = food.year.unmet > 1e-8 * np.maximum(1, annual_need)
        bad_count = np.bincount(x.owner, weights=bad_origin, minlength=n)
        active = np.asarray(x.affiliated, bool) & (target >= self.institutional_request + self.minimum_community) & (
            np.asarray(x.civilian_request) >= self.minimum_community)
        staff = np.where(active, self.institutional_request, 0.)
        civil = target - staff
        admissible = (civil >= 0) & (civil <= np.asarray(x.civilian_request) + 1e-8)
        feasible = (bad_count == 0) & admissible & (town_food.unmet <= 1e-8 * np.maximum(1, town_food.needed))
        return dict(total=target.copy(), moved=moved, rural=rural, work=work, rural_food=food,
            flow=flow, town_food=town_food, staff=staff, civil=civil, active=active,
            source_supported=bad_count == 0, source_deficit_origins=bad_count.astype(int),
            feasible=feasible, admissible=admissible)

    def solve(self, *, scan_intervals=32, refinements=24):
        if isinstance(scan_intervals, bool) or not isinstance(scan_intervals, int) or scan_intervals < 1:
            raise ValueError('Positive integer scan intervals required')
        if isinstance(refinements, bool) or not isinstance(refinements, int) or refinements < 0:
            raise ValueError('Nonnegative integer bracket refinements required')
        n = len(self.budget); lo = np.zeros(n); chosen = np.full(n, -1, int)
        scan = []
        for i in range(scan_intervals + 1):
            fraction = i / scan_intervals
            trial = self.evaluate(self.upper * fraction)
            good = trial['feasible'] & (trial['total'] > 0)
            lo = np.where(good, fraction, lo); chosen = np.where(good, i, chosen)
            scan.append(dict(fraction=fraction, feasible=trial['feasible'].copy(),
                source_supported=trial['source_supported'].copy(),
                destination_unmet=trial['town_food'].unmet.copy()))
        refine = (chosen >= 0) & (chosen < scan_intervals)
        hi = np.minimum(1., lo + 1 / scan_intervals)
        for _ in range(refinements):
            mid = (lo + hi) / 2
            trial = self.evaluate(self.upper * np.where(refine, mid, lo))
            lo = np.where(refine & trial['feasible'], mid, lo)
            hi = np.where(refine & ~trial['feasible'], mid, hi)
        final = self.evaluate(self.upper * lo)
        if np.any((final['total'] > 0) & ~final['feasible']):
            raise RuntimeError('Final positive settlement did not reproduce its coupled feasibility')
        ceiling = permanent_food_ceiling(final['flow']['arrivals'], kcal_day=self.kcal_day, year_days=self.year_days,
            store_days=self.destination_store_days, loss_fraction_year=self.loss_fraction_year)
        plan = SettlementPlan(ceiling, final['civil'], final['staff'], final['total'], final['active'],
            final['civil'] >= self.minimum_community, final['town_food'])
        allocation = ResidentAllocation(plan, np.asarray(self.x.people).copy(), final['rural'], final['moved'],
            self.budget.copy(), np.asarray(self.x.owner).copy(), final['flow']['arrivals'],
            self.kcal_day, self.year_days, self.destination_store_days, self.loss_fraction_year)
        final.update(plan=plan, allocation=allocation, scan=scan, selected_fraction=lo,
            refined_upper_fraction=hi, sampled_support=chosen >= 0,
            search_scope='Largest certified scanned/bracketed point; feasible islands can be missed, no global optimum claim.')
        return final
