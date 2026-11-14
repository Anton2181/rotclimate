"""Supplied FAO-style four-stage basal coefficients and exact time integrals.

This is a mathematical component. Stage lengths, local climatic adjustment and
the distinction between basal ET and root transpiration require separate inputs.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StageCurve:
    stage_days: tuple
    kcb_initial: float
    kcb_mid: float
    kcb_end: float

    def __post_init__(self):
        days = np.asarray(self.stage_days, dtype=float)
        if days.shape != (4,) or not np.isfinite(days).all() or np.any(days <= 0):
            raise ValueError('Four positive finite supplied stage durations required')
        if any(isinstance(v, (bool, np.bool_)) for v in self.stage_days):
            raise ValueError('Stage durations must be numbers, not booleans')
        coefficients = [self.kcb_initial, self.kcb_mid, self.kcb_end]
        if any(isinstance(v, (bool, np.bool_)) for v in coefficients) or not np.isfinite(coefficients).all() or np.any(np.asarray(coefficients) < 0):
            raise ValueError('Finite nonnegative supplied coefficients required')
        object.__setattr__(self, 'stage_days', tuple(float(v) for v in days))
        for name, value in zip(('kcb_initial', 'kcb_mid', 'kcb_end'), coefficients):
            object.__setattr__(self, name, float(value))

    @property
    def edges_days(self):
        return np.r_[0., np.cumsum(self.stage_days)]

    def _age(self, day):
        age = np.asarray(day, dtype=float)
        if not np.isfinite(age).all() or np.any(age < 0) or np.any(age > self.edges_days[-1]):
            raise ValueError('Finite crop age within the supplied growing period required')
        return age

    def value(self, day):
        age = self._age(day)
        edges = self.edges_days
        initial, mid, end = self.kcb_initial, self.kcb_mid, self.kcb_end
        return np.select(
            [age < edges[1], age < edges[2], age < edges[3]],
            [initial, initial + (age - edges[1]) * (mid - initial) / self.stage_days[1], mid],
            default=mid + (age - edges[3]) * (end - mid) / self.stage_days[3],
        )

    def integral(self, start_day, end_day):
        """Coefficient-days over a supplied closed interval; zero length allowed."""
        a, b = np.broadcast_arrays(self._age(start_day), self._age(end_day))
        if np.any(b < a):
            raise ValueError('Ordered crop-age interval required')
        result = np.zeros_like(a)
        levels = [self.kcb_initial, self.kcb_initial, self.kcb_mid, self.kcb_mid]
        slopes = [0., (self.kcb_mid-self.kcb_initial)/self.stage_days[1], 0., (self.kcb_end-self.kcb_mid)/self.stage_days[3]]
        for origin, length, level, slope in zip(self.edges_days[:-1], self.stage_days, levels, slopes):
            left, right = np.clip(a-origin, 0., length), np.clip(b-origin, 0., length)
            result += (right-left) * (level + slope*(right+left)/2)
        return result

    def mean(self, start_day, end_day):
        """Exact coefficient mean for a positive actual step duration."""
        a, b = np.broadcast_arrays(self._age(start_day), self._age(end_day))
        if np.any(b <= a):
            raise ValueError('Positive crop-age interval required for a mean')
        return self.integral(a,b)/(b-a)
