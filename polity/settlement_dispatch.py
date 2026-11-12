"""Work-bounded proportional dispatch inside finite resident/food feedback.

The catchment has one common dispatch scalar across its available origins and
months. This certifies an examined family, not globally optimal logistics.
"""
import numpy as np

from harvest.food_stocks import periodic_food_year
from .monthly_work import collection_trip_work
from .settlement_feedback import CerealFeedback
from .settlement_support import permanent_food_ceiling


class DispatchFeedback(CerealFeedback):
    def __init__(self, inputs, *, outward_days, inward_days, load_kcal,
                 monthly_open, staff_hours_year=600., walking_hours_day=7., handling_hours=.25,
                 work_refinements=40, food_refinements=40, **options):
        super().__init__(inputs, **options)
        shape = np.asarray(inputs.access).shape
        self.outward = np.asarray(outward_days, float).copy()
        self.inward = np.asarray(inward_days, float).copy()
        opened = np.asarray(monthly_open)
        if self.outward.shape != shape or self.inward.shape != shape or opened.shape != (12,) or opened.dtype.kind != 'b':
            raise ValueError('Aligned directed paths and twelve explicit monthly availability flags required')
        if not np.isfinite(staff_hours_year) or staff_hours_year < 0:
            raise ValueError('Finite nonnegative supplied staff hours required')
        for count in (work_refinements, food_refinements):
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError('Positive integer dispatch refinement counts required')
        # Existing trip validation covers finite positive loads, directed times,
        # work units and closed paths, without manufacturing any shipments.
        collection_trip_work(np.zeros(shape), self.outward, self.inward, inputs.access,
            load_kcal=load_kcal, walking_hours_day=walking_hours_day, handling_hours=handling_hours)
        self.load_kcal = float(load_kcal); self.walking_hours_day = float(walking_hours_day)
        self.handling_hours = float(handling_hours); self.opened = opened.copy()
        self.hour_envelope = opened[:, None] * (staff_hours_year / 12)
        self.work_refinements = work_refinements; self.food_refinements = food_refinements
        self.trip_cost = np.where(np.asarray(inputs.access, bool),
            (self.outward + self.inward) * walking_hours_day + handling_hours, 0.)

    def _site_sum(self, value):
        return np.stack([np.bincount(self.x.owner, weights=v, minlength=len(self.budget)) for v in value])

    def _hours(self, departures):
        trips = np.where(departures > 0, np.maximum(1., np.ceil(departures / self.load_kcal)), 0.)
        return trips, self._site_sum(trips * self.trip_cost)

    def _food(self, arrivals, target, *, record):
        return periodic_food_year(arrivals, np.broadcast_to(target * self.kcal_day * self.year_days / 12, arrivals.shape),
            target * self.kcal_day * self.destination_store_days, loss_fraction_year=self.loss_fraction_year,
            step_days=self.year_days / 12, record=record)

    def _set_dispatch(self, trial, scale, *, final):
        origin = trial['reference_origin_departures'] * self.opened[:, None] * scale[self.x.owner][None, :]
        site_departures = self._site_sum(origin)
        arrivals = np.roll(site_departures, self.collection_options['delay_bins'], axis=0) * self.collection_options['retention']
        trips, hours = self._hours(origin)
        gross = trial['staff'][None, :] * self.hour_envelope
        if np.any(hours > gross):
            raise RuntimeError('Selected dispatch exceeds its own monthly staff hours')
        food = self._food(arrivals, trial['total'], record=True)
        flow = dict(origin_departures=origin, departures=site_departures, arrivals=arrivals,
            export_capacity=trial['reference_export_capacity'],
            transport_loss=float(site_departures.sum() * (1 - self.collection_options['retention'])))
        if final:
            production = trial['rural_food'].exportable * self.collection_options['fraction']
            export = periodic_food_year(production, origin, flow['export_capacity'],
                loss_fraction_year=self.loss_fraction_year, step_days=self.year_days / 12, record=True)
            if np.any(export.unmet > 1e-8 * np.maximum(1., production.sum(axis=0))):
                raise RuntimeError('Reduced dispatch did not retain source inventory feasibility')
            flow.update(export_year=export, uncollected=float(trial['rural_food'].exportable.sum()
                - production.sum() + export.overflow.sum()))
            checked_trips, checked_hours = collection_trip_work(origin, self.outward, self.inward, self.x.access,
                load_kcal=self.load_kcal, walking_hours_day=self.walking_hours_day, handling_hours=self.handling_hours)
            np.testing.assert_array_equal(trips, checked_trips)
            np.testing.assert_allclose(hours, self._site_sum(checked_hours), rtol=1e-12, atol=1e-8)
        trial.update(flow=flow, town_food=food, dispatch_scale=scale.copy(), origin_trips=trips,
                     collection_hours=hours, staff_gross_hours=gross)

    def evaluate(self, total):
        trial = super().evaluate(total)
        reference = trial['flow']; target = trial['total']; owner = self.x.owner
        trial['reference_origin_departures'] = reference['origin_departures']
        trial['reference_export_capacity'] = reference['export_capacity']
        base = reference['origin_departures'] * self.opened[:, None]
        gross = trial['staff'][None, :] * self.hour_envelope
        _, full = self._hours(base)
        full_ok = np.all(full <= gross, axis=0) & (target > 0) & (trial['staff'] > 0)
        lo = np.where(full_ok, 1., 0.); hi = np.where(trial['staff'] > 0, 1., 0.)
        refine = ~full_ok & (hi > 0) & (target > 0)
        for _ in range(self.work_refinements):
            mid = (lo + hi) / 2
            _, used = self._hours(base * np.where(refine, mid, lo)[owner][None, :])
            fits = np.all(used <= gross, axis=0)
            lo = np.where(refine & fits, mid, lo); hi = np.where(refine & ~fits, mid, hi)
        self._set_dispatch(trial, lo, final=False)
        trial['maximum_dispatch_scale'] = lo.copy()
        trial['dispatch_scale_upper'] = hi.copy()
        trial['feasible'] = trial['source_supported'] & trial['admissible'] & (
            trial['town_food'].unmet <= 1e-10 * np.maximum(1., trial['town_food'].needed))
        return trial

    def solve(self, *, scan_intervals=32, refinements=24):
        result = super().solve(scan_intervals=scan_intervals, refinements=refinements)
        maximum = result['maximum_dispatch_scale']; reference_arrivals = result['flow']['arrivals']
        lo = np.zeros_like(maximum); hi = np.where(result['total'] > 0, 1., 0.)
        for _ in range(self.food_refinements):
            mid = (lo + hi) / 2
            food = self._food(reference_arrivals * mid[None, :], result['total'], record=False)
            supported = food.unmet <= 1e-10 * np.maximum(1., food.needed)
            hi = np.where(supported, mid, hi); lo = np.where(~supported, mid, lo)
        self._set_dispatch(result, maximum * hi, final=True)
        if np.any((result['total'] > 0) & (result['town_food'].unmet > 1e-8 * np.maximum(1., result['town_food'].needed))):
            raise RuntimeError('Final reduced dispatch lost seasonal food support')
        plan = result['plan']; allocation = result['allocation']
        plan.food_ceiling_people = permanent_food_ceiling(result['flow']['arrivals'], kcal_day=self.kcal_day,
            year_days=self.year_days, store_days=self.destination_store_days, loss_fraction_year=self.loss_fraction_year)
        plan.food_year = result['town_food']; allocation.arrivals = result['flow']['arrivals'].copy()
        result['food_scalar_lower'] = maximum * lo
        result['search_scope'] = ('Largest certified scanned/bracketed resident point within a uniform catchment dispatch family; '
            'neither global logistics optimality nor proof all other schedules fail.')
        return result
