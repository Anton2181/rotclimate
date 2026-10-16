"""Passive measurements of the frozen ascending-parcel cloud rule.

No alternate condensation is applied. In particular, saturation at the actual
layer face is a path diagnostic, not a substitute precipitation calculation.
"""
from __future__ import annotations

import numpy as np
from experiments import v10_cloud_sources as physical

physics = physical.physics
base = physics.base
METRICS = ('upward_dry_mass_kg_m2', 'upward_vapor_mm', 'parcel_rain_mm',
           'parcel_rain_first_saturation_above_face_mm',
           'parcel_rain_recipient_pre_step_RH_below_70_mm',
           'rain_weighted_midpoint_pressure_gap_pa_mm',
           'vapor_weighted_donor_RH_mm',
           'parcel_rain_colder_than_pre_step_recipient_mm')


class Collector:
    def __init__(self, domain, geometry, settings, profile, local_air, saved=None, edges=None):
        self.domain = domain; self.g = geometry; self.settings = settings
        self.profile = profile; self.local_air = local_air
        self.edges = np.array(physical.EDGES if edges is None else edges, float)
        shape = domain.land.shape
        if len(geometry.mass) != 5 or self.edges.shape != (13,) or (np.diff(self.edges) <= 0).any():
            raise ValueError('Cloud geometry requires five layers and twelve months.')
        expected = {'metrics': (12, len(METRICS), 3)+shape, 'layer_rain': (12, 5)+shape, 'time_seconds': (12,)}
        if saved is not None and set(saved) != set(expected):
            raise ValueError('Cloud geometry checkpoint fields changed.')
        self.arrays = {name: np.zeros(size) if saved is None else np.array(saved[name], dtype=float, copy=True) for name, size in expected.items()}
        for name, size in expected.items():
            a = self.arrays[name]
            if a.shape != size or not np.isfinite(a).all() or (a < 0).any():
                raise ValueError('Invalid cloud geometry checkpoint.')
        # Every diagnosed interface lies strictly between its cell midpoints.
        if not ((geometry.pressure[:3] > geometry.interfaces_pa[1:4]) & (geometry.interfaces_pa[1:4] > geometry.pressure[1:4])).all():
            raise ValueError('Cloud geometry has an invalid ascending pressure path.')

    def add(self, before, after, layer_rain, parcel_rain, flow, boundary, budget, dt, time_s):
        month = int(np.searchsorted(self.edges, time_s, side='right')-1)
        if not 0 <= month < 12 or dt <= 0 or time_s+dt > self.edges[month+1]+1e-6:
            raise ValueError('Cloud geometry step crosses its month.')
        g = self.g; count = 3
        t = base.temperature(before.energy, g.mass, before.water, g.height_m)
        target, _ = physics.coordinates.targets(self.domain, self.profile, self.settings, time_s, self.local_air)
        donor_q = before.water[:count]/g.mass[:count]
        pressure = g.pressure[1:count+1]; height = g.height_m[1:count+1]
        dry_t = (t[:count]+273.15)*(pressure/g.pressure[:count])**(287.05/base.CP)-273.15
        tau = np.where(np.arange(1, count+1)<2, self.settings.relaxation_lower_days, self.settings.relaxation_upper_days)[:, None, None]*base.DAY
        parcel_t = dry_t+(-np.expm1(-dt/tau))*(target[1:count+1]-dry_t)
        energy = base.CP*(parcel_t+273.15)+base.G*height+base.LV*donor_q
        _, condensed, cloud_t = base.adjust(donor_q, energy, np.ones_like(donor_q), height, pressure)
        mass = np.maximum(flow.vertical[:count], 0.)*dt
        actual = parcel_rain[1:4]
        if not np.array_equal(mass*condensed, actual) or parcel_rain[0].any() or parcel_rain[-1].any():
            raise ValueError('Passive cloud geometry does not reconstruct actual lower-interface condensate.')
        # Invert the existing tiny relaxation shift to a potential-temperature
        # path. This reproduces the endpoint exactly; it is not a separately
        # prognosed parcel or observed cloud-base measurement.
        face = g.interfaces_pa[1:4]
        face_t = (parcel_t+273.15)*(face/pressure)**(287.05/base.CP)-273.15
        late = donor_q <= base.saturation(face_t, face)
        recipient_rh = before.water[1:4]/g.mass[1:4]/base.saturation(t[1:4], pressure)
        donor_rh = donor_q/base.saturation(t[:3], g.pressure[:3])
        values = np.stack((mass, mass*donor_q, actual, actual*late,
            actual*(recipient_rh<.7), actual*(g.pressure[:3]-pressure),
            mass*donor_q*donor_rh, actual*(cloud_t<t[1:4])))
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError('Invalid passive cloud geometry tendency.')
        self.arrays['metrics'][month] += values
        self.arrays['layer_rain'][month] += layer_rain
        self.arrays['time_seconds'][month] += dt

    def validate_months(self, month, water, rain):
        durations = np.diff(self.edges)
        if not 0 <= month <= 12 or not np.allclose(self.arrays['time_seconds'][:month], durations[:month], atol=1e-5, rtol=0) or self.arrays['time_seconds'][month:].any():
            raise ValueError('Cloud geometry month coverage disagrees with physical checkpoint.')
        layers = self.arrays['layer_rain']; metrics = self.arrays['metrics']
        if layers[month:].any() or metrics[month:].any() or not np.allclose(layers.sum(1), rain, atol=1e-9, rtol=0):
            raise ValueError('Cloud geometry rain disagrees with physical monthly fields.')
        if (metrics[:, 2]-layers[:, 1:4]>1e-9).any() or (metrics[:, 2]-metrics[:, 1]>1e-9).any():
            raise ValueError('Parcel rain exceeds actual rain or carried vapor.')
        if any((metrics[:, i]-metrics[:, 2]>1e-9).any() for i in (3, 4, 7)):
            raise ValueError('Cloud geometry subset exceeds parcel rain.')

    def summary(self, masks, winter, summer):
        rows = {}
        for name, mask in masks.items():
            if not mask.any():
                continue
            values = self.arrays['metrics'][:, :, :, mask].mean(-1)
            row = {'cells': int(mask.sum()), 'monthly_by_interface': {metric: values[:, i].tolist() for i, metric in enumerate(METRICS)}}
            for season, months in (('winter', winter), ('summer', summer)):
                totals = values[months].sum(0)
                rain = float(totals[2].sum()); vapor = float(totals[1].sum())
                ratio = lambda n, d: float(n/d) if d>0 else None
                row[season] = {
                    'by_interface': {metric: totals[i].tolist() for i, metric in enumerate(METRICS)},
                    'total_rain_mm': float(self.arrays['layer_rain'][months][:, :, mask].sum((0, 1)).mean()),
                    'parcel_rain_mm': rain, 'upward_vapor_sum_mm': vapor,
                    'parcel_rain_over_upward_vapor': ratio(rain, vapor),
                    'parcel_rain_first_saturation_above_face_fraction': ratio(totals[3].sum(), rain),
                    'parcel_rain_dry_pre_step_recipient_fraction': ratio(totals[4].sum(), rain),
                    'rain_weighted_midpoint_pressure_gap_hpa': ratio(totals[5].sum()/100., rain),
                    'vapor_weighted_donor_RH': ratio(totals[6].sum(), vapor),
                    'parcel_rain_colder_than_pre_step_recipient_fraction': ratio(totals[7].sum(), rain)}
            rows[name] = row
        return {'regions': rows, 'metrics': list(METRICS),
            'interpretation': 'Actual parcel-rain subsets on the unchanged trajectory. Above-face onset follows the existing relaxed dry-theta path; it is not proof that cell-midpoint transport is wrong. Recipient RH/T are pre-step environmental values. Summed upward vapor can revisit interfaces/cells; it is not unique supply or a bound on possible climate rainfall. No alternate rain, entrainment or evaporation is applied.'}
