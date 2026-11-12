"""Reconstruct retained cargo and lagged destination times from collector IDs."""
import numpy as np


def trip_delivery_events(departures, trips, owners, qualified, origin, serial, site, end_hours, month,
                         *, load=120000., retention=.95, year_days=365., work_hours_day=7.):
    departures, trips, owners, qualified, origin, serial, site, end_hours = map(np.asarray,
        (departures, trips, owners, qualified, origin, serial, site, end_hours))
    if departures.ndim != 1 or trips.shape != departures.shape or owners.shape != departures.shape or qualified.ndim != 1:
        raise ValueError('Invalid source/provider shapes')
    if any(v.dtype.kind not in 'iu' for v in (trips, owners, origin, serial, site)) or qualified.dtype.kind != 'b':
        raise ValueError('IDs and trip counts must be integers; qualification must be boolean')
    if any(v.ndim != 1 or v.shape != origin.shape for v in (origin, serial, site, end_hours)):
        raise ValueError('Invalid trip record shapes')
    if not isinstance(month, int) or not 0 <= month < 12 or not np.isfinite([load, retention, year_days, work_hours_day]).all() or load <= 0 or not 0 <= retention <= 1 or year_days <= 0 or work_hours_day <= 0:
        raise ValueError('Invalid clock/cargo parameters')
    if not np.isfinite(departures).all() or (departures < 0).any() or (trips < 0).any() or (owners < 0).any() or (owners >= len(qualified)).any():
        raise ValueError('Invalid original cargo or ownership')
    if (origin < 0).any() or (origin >= len(owners)).any() or (site < 0).any() or (site >= len(qualified)).any() or (serial < 0).any():
        raise ValueError('Invalid recorded trip IDs')
    if not np.array_equal(owners[origin], site) or not qualified[site].all():
        raise ValueError('Trip provider must match its qualified original owner')
    phase = end_hours / work_hours_day
    if not np.isfinite(phase).all() or (phase < 0).any() or (end_hours >= year_days * work_hours_day / 12).any():
        raise ValueError('Return phase must stay inside its destination bin')
    expected = np.where(qualified[owners], trips, 0)
    if not np.array_equal(np.bincount(origin, minlength=len(owners)), expected):
        raise ValueError('Missing or excess original trip counts')
    order = np.lexsort((serial, origin)); sorted_origin, sorted_serial = origin[order], serial[order]
    offsets = np.cumsum(expected) - expected
    wanted = np.arange(len(origin)) - np.repeat(offsets, expected)
    if not np.array_equal(sorted_serial, wanted):
        raise ValueError('Missing or duplicate original trip serials')
    cargo = np.minimum(load, np.maximum(0., departures[origin] - load * serial))
    if (cargo <= 0).any():
        raise ValueError('Original trip has no cargo')
    original = np.bincount(origin, weights=cargo, minlength=len(owners))
    if not np.allclose(original, np.where(qualified[owners], departures, 0), rtol=1e-12, atol=1e-7):
        raise ValueError('Cargo does not reconstruct original departures')
    times = np.mod((month + 1) * year_days / 12 + phase, year_days)
    return times, cargo * retention
