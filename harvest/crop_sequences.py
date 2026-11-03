"""Experimental annual crop windows and compatible one/two-crop sequences.

This preserves the production crop response, but retains every growing window.
It does not replace production Harvest outputs. Timing is in twelve climate
bins, not observed sowing dates; perennial harvest timing is deliberately absent.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np

from scripts.land_people import CROPS, DAYS, smoothstep

BINS = 12


@dataclass(frozen=True)
class CropWindow:
    crop: str
    start: int
    length: int

    def __post_init__(self):
        if not isinstance(self.crop, str) or not self.crop or any(isinstance(v, bool) or not isinstance(v, Integral) for v in (self.start, self.length)):
            raise ValueError('Named crop and integer climate-bin window required')
        if int(self.start) != self.start or int(self.length) != self.length or not 0 <= self.start < BINS or not 1 <= self.length <= BINS:
            raise ValueError('Window must start in [0,11] and occupy 1–12 bins')

    @property
    def harvest_boundary(self):
        return (self.start + self.length) % BINS

    def occupied(self, turnaround=0):
        return sum(1 << ((self.start + k) % BINS) for k in range(min(BINS, self.length + turnaround)))


@dataclass
class CropCatalogue:
    windows: tuple[CropWindow, ...]
    energy: np.ndarray  # option, then cell axes; net edible kcal/ha/year

    def __post_init__(self):
        self.windows = tuple(self.windows)
        self.energy = np.asarray(self.energy)
        if not self.windows or self.energy.ndim < 1 or len(self.windows) != self.energy.shape[0]:
            raise ValueError('One energy field per crop window required')
        if not all(isinstance(w, CropWindow) for w in self.windows):
            raise ValueError('CropWindow entries required')
        if len(set(self.windows)) != len(self.windows):
            raise ValueError('Duplicate crop windows would inflate schedule counts')
        if not np.isfinite(self.energy).all() or np.any(self.energy < 0):
            raise ValueError('Crop energy must be finite and nonnegative')


@dataclass
class CropSequence:
    energy: np.ndarray
    first: np.ndarray  # catalogue index; -1 no crop, -2 perennial-only
    second: np.ndarray  # catalogue index or -1
    optimal_count: np.ndarray  # alternative ordered primary/secondary schedules
    harvest_boundaries_possible: np.ndarray  # union, not independent probabilities
    perennial_possible: np.ndarray


def crop_windows(T, P, PET, S0, irr, *, rain_keep=None, keep=None, crops=None):
    """Enumerate windows using the existing Harvest crop-yield response.

    The mirrored response is checked against production on every sample in
    the review driver. No new crop coefficient or water-supply rule is fitted.
    Soil states are the existing reference bucket, not a sequential crop-water
    ledger; compatible occupancy alone does not establish agronomic viability.
    """
    T, P, PET, S0 = (np.asarray(a) for a in (T, P, PET, S0))
    if T.ndim < 1 or T.shape[0] != BINS or any(a.shape != T.shape for a in (P, PET, S0)):
        raise ValueError('Matching twelve-bin climate and soil arrays required')
    if not all(np.isfinite(a).all() for a in (T, P, PET, S0)) or any(np.any(a < 0) for a in (P, PET, S0)):
        raise ValueError('Finite climate, nonnegative rain/evaporation/soil required')
    irr = np.broadcast_to(np.asarray(irr), T.shape[1:])
    for factor in (irr, rain_keep, keep):
        if factor is not None and (not np.isfinite(factor).all() or np.any((np.asarray(factor) < 0) | (np.asarray(factor) > 1))):
            raise ValueError('Irrigation and reliability factors must be in [0,1]')
    windows, energies = [], []
    for name, c in (CROPS if crops is None else crops).items():
        if name == 'dates':
            raise ValueError('Perennial dates need separate harvest timing')
        lo, hi = c['window']
        for length in range(c['months'][0], c['months'][1] + 1):
            for start in range(BINS):
                window = CropWindow(name, start, length)
                idx = [(start + k) % BINS for k in range(length)]
                Ts, Ps, Es = T[idx], P[idx], PET[idx]
                ok = np.all((Ts >= lo) & (Ts <= hi), axis=0) & (Ts.max(0) >= c['need_warm'])
                heat = np.sum(np.maximum(Ts - c['base'], 0.), axis=0) * DAYS
                ok &= heat >= c['heat']
                etc = c['kc'] * Es.sum(0) + c.get('flood_mm', 0.)
                supply = .8 * Ps.sum(0) + S0[idx[0]]
                fw = np.clip(supply / np.maximum(etc, 1.), 0., 1.)
                yf = np.clip(1. - c['ky'] * (1. - fw), 0., 1.) * smoothstep(fw, .3, .5)
                if rain_keep is not None:
                    yf = yf * rain_keep
                yf = irr + (1. - irr) * yf
                if keep is not None:
                    yf = yf * keep
                energy = np.where(ok, yf, 0.) * c['grain'] * 1000. * c['edible'] * c['kcal'] * (1 - c['seed'])
                windows.append(window); energies.append(energy)
    return CropCatalogue(tuple(windows), np.stack(energies))


def sequence_candidates(catalogue, can_double, *, secondary_weight=.5, turnaround=0,
                        allow_same_crop=False, perennial_energy=None):
    """Yield (primary index, secondary index, energy) for permitted schedules.

    Turnaround reserves whole climate bins *after both* crops, including at
    the year boundary. Same-crop repetition defaults off, matching production.
    Ordered roles retain the inherited half-weight secondary-crop assumption.
    """
    if isinstance(turnaround, bool) or not isinstance(turnaround, Integral) or not 0 <= turnaround <= BINS:
        raise ValueError('Turnaround must be an integer number of climate bins')
    if not np.isfinite(secondary_weight) or not 0 < secondary_weight <= 1:
        raise ValueError('Secondary weight must be in (0,1]')
    shape = catalogue.energy.shape[1:]
    can_double = np.broadcast_to(np.asarray(can_double, bool), shape)
    for i, energy in enumerate(catalogue.energy):
        yield i, -1, energy
    if perennial_energy is not None:
        perennial = np.broadcast_to(np.asarray(perennial_energy), shape)
        if not np.isfinite(perennial).all() or np.any(perennial < 0):
            raise ValueError('Perennial output must be finite and nonnegative')
        yield -2, -1, perennial
    if not can_double.any():
        return
    windows = catalogue.windows
    for i, a in enumerate(windows):
        for j in range(i + 1, len(windows)):
            b = windows[j]
            if (a.crop == b.crop and not allow_same_crop) or a.occupied(turnaround) & b.occupied() or b.occupied(turnaround) & a.occupied():
                continue
            x, y = catalogue.energy[i], catalogue.energy[j]
            allowed = can_double & (x > 0) & (y > 0)
            # Failed/ineligible pairs have zero energy and never count as
            # optimal productive schedules. Singles are always available.
            yield i, j, np.where(allowed, x + secondary_weight*y, 0.)
            if secondary_weight != 1:
                yield j, i, np.where(allowed, y + secondary_weight*x, 0.)


def optimize_sequences(catalogue, can_double, **policy):
    """Maximize annual energy and retain ambiguity of equally good schedules.

    The returned first/second choice is only a deterministic example. The
    optimal count and harvest-boundary union preserve ties within a relative
    1e-12/absolute 1e-7 kcal tolerance; they are not timing probabilities.
    A second pass compares every candidate with the final maximum, preventing
    tie counting from depending on candidate enumeration order.
    """
    best = np.zeros(catalogue.energy.shape[1:])
    first = np.full(best.shape, -1, int); second = first.copy()
    for i, j, energy in sequence_candidates(catalogue, can_double, **policy):
        better = energy > best
        first = np.where(better, i, first); second = np.where(better, j, second)
        best = np.maximum(best, energy)
    count = np.zeros(best.shape, np.uint32)
    possible = np.zeros((BINS,) + best.shape, bool)
    perennial = np.zeros(best.shape, bool)
    for i, j, energy in sequence_candidates(catalogue, can_double, **policy):
        tied = (energy > 0) & np.isclose(energy, best, rtol=1e-12, atol=1e-7)
        count += tied
        if i == -2:
            perennial |= tied
        else:
            possible[catalogue.windows[i].harvest_boundary] |= tied
        if j >= 0:
            possible[catalogue.windows[j].harvest_boundary] |= tied
    return CropSequence(best, first, second, count, possible, perennial)
