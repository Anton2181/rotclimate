"""Seed the known staff-activation boundary without claiming global search."""
import numpy as np

from .settlement_dispatch import DispatchFeedback
from .settlement_residents import ResidentAllocation
from .settlement_support import SettlementPlan, permanent_food_ceiling


class ThresholdSeededDispatchFeedback(DispatchFeedback):
    def solve(self, *, scan_intervals=64, refinements=24):
        fine = super().solve(scan_intervals=scan_intervals, refinements=refinements)
        threshold = self.institutional_request + self.minimum_community
        eligible = self.upper >= threshold
        probe = self.evaluate(np.where(eligible, threshold, 0.))
        added = eligible & probe['feasible'] & (threshold > fine['total'])
        self.preseed_total = fine['total'].copy(); self.preseed_active = fine['active'].copy()
        self.threshold_feasible = eligible & probe['feasible']; self.threshold_seeded = added.copy()
        if not added.any():
            fine.update(threshold_seeded=added.copy(), threshold_feasible=self.threshold_feasible.copy(),
                preseed_total=self.preseed_total.copy(), preseed_active=self.preseed_active.copy())
            return fine
        lo = np.where(added, threshold, fine['total'])
        relative = np.divide(threshold, self.upper, out=np.zeros_like(self.upper), where=self.upper > 0)
        next_grid = self.upper * np.minimum(1., (np.floor(relative * scan_intervals) + 1) / scan_intervals)
        hi = np.where(added, np.maximum(threshold, next_grid), lo)
        refine = added & (hi > lo)
        for _ in range(refinements):
            mid = (lo + hi) / 2
            trial = self.evaluate(np.where(refine, mid, lo))
            lo = np.where(refine & trial['feasible'], mid, lo)
            hi = np.where(refine & ~trial['feasible'], mid, hi)
        final = self.evaluate(lo)
        if np.any((final['total'] > 0) & ~final['feasible']):
            raise RuntimeError('Merged threshold-seeded resident point lost its own feasibility')
        maximum = final['maximum_dispatch_scale']; reference_arrivals = final['flow']['arrivals']
        food_lo = np.zeros_like(maximum); food_hi = np.where(final['total'] > 0, 1., 0.)
        for _ in range(self.food_refinements):
            mid = (food_lo + food_hi) / 2
            food = self._food(reference_arrivals * mid[None, :], final['total'], record=False)
            supported = food.unmet <= 1e-10 * np.maximum(1., food.needed)
            food_hi = np.where(supported, mid, food_hi); food_lo = np.where(~supported, mid, food_lo)
        self._set_dispatch(final, maximum * food_hi, final=True)
        if np.any(final['town_food'].unmet > 1e-8 * np.maximum(1., final['town_food'].needed)):
            raise RuntimeError('Threshold-seeded final dispatch lost destination food')
        ceiling = permanent_food_ceiling(final['flow']['arrivals'], kcal_day=self.kcal_day, year_days=self.year_days,
            store_days=self.destination_store_days, loss_fraction_year=self.loss_fraction_year)
        plan = SettlementPlan(ceiling, final['civil'], final['staff'], final['total'], final['active'],
            final['civil'] >= self.minimum_community, final['town_food'])
        allocation = ResidentAllocation(plan, np.asarray(self.x.people).copy(), final['rural'], final['moved'],
            self.budget.copy(), np.asarray(self.x.owner).copy(), final['flow']['arrivals'].copy(),
            self.kcal_day, self.year_days, self.destination_store_days, self.loss_fraction_year)
        final.update(plan=plan, allocation=allocation, scan=fine['scan'],
            selected_fraction=np.divide(lo, self.upper, out=np.zeros_like(lo), where=self.upper > 0),
            refined_upper_fraction=np.where(added, np.divide(hi, self.upper, out=np.zeros_like(hi), where=self.upper > 0), fine['refined_upper_fraction']),
            sampled_support=fine['sampled_support'] | added, food_scalar_lower=maximum * food_lo,
            threshold_seeded=added.copy(), threshold_feasible=self.threshold_feasible.copy(),
            preseed_total=self.preseed_total.copy(), preseed_active=self.preseed_active.copy(),
            search_scope='Largest certified64-grid/bracket or known staff-threshold-seeded point;other feasible islands and better dispatch schedules can remain.')
        return final
