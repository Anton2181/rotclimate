"""Conditional no-loss reserve bounds across optimal annual crop calendars.

This is a mathematical food-ledger scenario, not a granary-capacity estimate.
Food arrives in pulses at rounded climate-bin maturity boundaries. Annual
food need equals annual edible harvest, spread uniformly through the year.
No storage-loss coefficient, famine probability or population is inferred.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np

from .crop_sequences import BINS, sequence_candidates


@dataclass
class CalendarStocks:
    minimum_days: np.ndarray
    maximum_days: np.ndarray
    annual_schedules: np.ndarray
    perennial_timing_unknown: np.ndarray


def _clock(year_steps, year_days):
    if isinstance(year_steps, bool) or not isinstance(year_steps, Integral) or year_steps < BINS:
        raise ValueError('At least twelve integer inventory steps required')
    if not np.isfinite(year_days) or year_days <= 0:
        raise ValueError('Year length must be positive and finite')
    return year_days / year_steps


def two_pulse_capacity(first_boundary, second_boundary, first_share, *, year_steps=73, year_days=365.):
    """Exact no-loss storage in days of uniform need for this pulse scenario.

    With balanced annual supply, the largest cyclic deficit is the maximum
    of either harvest and either inter-harvest gap's demand, less one step's
    immediate meals. This matches food_stocks' harvest-before-meals ledger.
    Inputs are bin boundaries and the first harvest's share of annual energy.
    """
    step_days = _clock(year_steps, year_days)
    if any(isinstance(b, bool) or not isinstance(b, Integral) or not 0 <= b < BINS for b in (first_boundary, second_boundary)):
        raise ValueError('Maturity boundaries must be climate-bin indices')
    share = np.asarray(first_share, float)
    if not np.isfinite(share).all() or np.any((share < 0) | (share > 1)):
        raise ValueError('Harvest shares must be in [0,1]')
    clock = lambda boundary: int(np.floor(boundary * year_steps / BINS + .5)) % year_steps
    gap = ((clock(second_boundary) - clock(first_boundary)) % year_steps) * step_days
    largest = np.maximum(np.maximum(share * year_days, (1 - share) * year_days), max(gap, year_days - gap))
    return np.maximum(largest - step_days, 0.)


def calendar_stock_bounds(catalogue, sequence, can_double, *, year_steps=73, year_days=365., **policy):
    """Bounds over all tied-optimal annual schedules under the supplied policy.

    Perennial timing stays unknown even if an equally optimal annual schedule
    exists. NaN means no timed annual schedule was available, not zero storage.
    The method verifies that the policy reproduces the supplied optimum/count.
    """
    step_days = _clock(year_steps, year_days)
    low = np.full(sequence.energy.shape, np.inf)
    high = np.full(sequence.energy.shape, -np.inf)
    count = np.zeros(sequence.energy.shape, np.uint32)
    unknown = np.zeros(sequence.energy.shape, bool)
    secondary = policy.get('secondary_weight', .5)
    for i, j, energy in sequence_candidates(catalogue, can_double, **policy):
        tolerance = 1e-7 + 1e-12 * np.abs(sequence.energy)
        if np.any(energy > sequence.energy + tolerance):
            raise ValueError('Stock policy does not reproduce the supplied optimum')
        tied = (energy > 0) & np.isclose(energy, sequence.energy, rtol=1e-12, atol=1e-7)
        if i == -2:
            unknown |= tied
            continue
        if not tied.any():
            continue
        if j < 0:
            capacity = year_days - step_days
        else:
            first_energy = catalogue.energy[i]
            total = first_energy + secondary * catalogue.energy[j]
            share = np.divide(first_energy, total, out=np.zeros_like(total, dtype=float), where=total > 0)
            capacity = two_pulse_capacity(catalogue.windows[i].harvest_boundary,
                catalogue.windows[j].harvest_boundary, share, year_steps=year_steps, year_days=year_days)
        low = np.where(tied, np.minimum(low, capacity), low)
        high = np.where(tied, np.maximum(high, capacity), high)
        count += tied
    if not np.array_equal(count + unknown.astype(np.uint32), sequence.optimal_count):
        raise ValueError('Stock policy/catalogue differs from the supplied optimal schedules')
    return CalendarStocks(np.where(count > 0, low, np.nan), np.where(count > 0, high, np.nan),count,unknown)
