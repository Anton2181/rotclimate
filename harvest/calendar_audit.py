"""Observe calendar tie-breaking without changing the production crop model.

Roll the *same* 12 input bins together, retain all chosen masks after mapping
them back to their original bins, and try the resulting tied-best calendars.
This is an attainable alternative, not exhaustive calendar optimization, an
observed harvest date, or a new double-cropping policy.
"""
from dataclasses import dataclass

import numpy as np

from scripts.land_people import CROPS, best_crop_mix, crop_yield


@dataclass
class CalendarAudit:
    original_total: np.ndarray
    rotation_minimum: np.ndarray
    rotation_maximum: np.ndarray
    attainable_tied_total: np.ndarray
    crop_mask_varies: dict[str, np.ndarray]
    maximum_crop_yield_drift: float


def calendar_origin_audit(T, P, PET, S0, irr, can_double, *, rain_keep=None,
                          keep=None, perennial_kcal=None, crops=None):
    """Test annual kcal/ha and tied season masks under twelve relabellings.

The soil-water states are rolled, not spun up again. Perennial output is
held fixed and cannot enter a second-crop pair. Same-crop second harvests
remain excluded, and the existing half-weight second crop and water gate
are retained. Only masks selected by the original model are considered.
"""
    # Preserve production dtypes: in particular 1 - a float32 irrigation
    # share must not silently become a different float64 expression.
    T, P, PET, S0 = (np.asarray(a) for a in (T, P, PET, S0))
    if T.ndim < 1 or T.shape[0] != 12 or any(a.shape != T.shape for a in (P, PET, S0)):
        raise ValueError('Matching twelve-bin climate and soil-water arrays required')
    if not all(np.isfinite(a).all() for a in (T, P, PET, S0)):
        raise ValueError('Audit inputs must be finite')
    shape = T.shape[1:]
    irr = np.broadcast_to(np.asarray(irr), shape)
    can_double = np.broadcast_to(np.asarray(can_double, bool), shape)
    if not np.isfinite(irr).all() or np.any((irr < 0) | (irr > 1)):
        raise ValueError('Irrigation shares must be between zero and one')
    specs = CROPS if crops is None else crops
    if not specs or 'dates' in specs:
        raise ValueError('Annual crop definitions required; dates are separate')
    all_masks = {name: [] for name in specs}
    reference = None
    minimum = maximum = original = None
    drift = 0.
    for shift in range(12):
        climate = [np.roll(a, shift, axis=0) for a in (T, P, PET, S0)]
        kcal, masks = {}, {}
        for name, crop in specs.items():
            kcal[name], mask = crop_yield(*climate, irr, crop, rain_keep, keep)
            masks[name] = np.roll(mask, -shift, axis=0)
            all_masks[name].append(masks[name])
        if perennial_kcal is not None:
            kcal['dates'] = np.broadcast_to(np.asarray(perennial_kcal, float), shape)
            if not np.isfinite(kcal['dates']).all() or np.any(kcal['dates'] < 0):
                raise ValueError('Perennial calories must be finite and nonnegative')
            masks['dates'] = np.zeros(T.shape, bool)
        if reference is None:
            reference = {k: v.copy() for k, v in kcal.items()}
        else:
            for name in specs:
                delta = np.abs(kcal[name] - reference[name])
                drift = max(drift, float(np.max(delta)))
                if not np.allclose(kcal[name], reference[name], rtol=1e-12, atol=1e-7):
                    raise ValueError('Relabelling changed an annual crop yield')
        total, _, _ = best_crop_mix(kcal, masks, can_double)
        if original is None:
            original = total.copy(); minimum = total.copy(); maximum = total.copy()
        else:
            minimum = np.minimum(minimum, total); maximum = np.maximum(maximum, total)
    attainable = original.copy()
    names = list(specs)
    # Every mask is a feasible individually optimal season returned by the
    # unchanged model. Combining origins tests missed choices among those ties.
    for i, a in enumerate(names):
        for b in names[i+1:]:
            pair = np.maximum(reference[a] + .5*reference[b], reference[b] + .5*reference[a])
            for ma in all_masks[a]:
                for mb in all_masks[b]:
                    allowed = can_double & (reference[a] > 0) & (reference[b] > 0) & ~np.any(ma & mb, axis=0)
                    attainable = np.where(allowed, np.maximum(attainable, pair), attainable)
    varies = {name: np.any(np.stack(masks) != masks[0], axis=(0, 1)) for name, masks in all_masks.items()}
    return CalendarAudit(original, minimum, maximum, attainable, varies, drift)
