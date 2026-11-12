"""Declared location-intensity hypotheses, independent of resident population.

These transformations never change eligibility, people, food or the count budget.
The density exponent acts only on the legacy smoothed-density score factor.
"""
import numpy as np
from scipy import ndimage as ndi


def density_score(score, density, land, eligible, power):
    score, density = np.asarray(score, float), np.asarray(density)
    land, eligible = np.asarray(land, bool), np.asarray(eligible, bool)
    if score.ndim != 2 or any(a.shape != score.shape for a in (density, land, eligible)):
        raise ValueError('Matching two-dimensional score, density and masks required')
    if not np.isfinite(power) or power <= 0:
        raise ValueError('Positive finite density exponent required')
    if np.any(~np.isfinite(density[land])) or np.any(density[land] < 0):
        raise ValueError('Land density must be finite and nonnegative')
    # Preserve the source dtype during smoothing, exactly as settle.site_score.
    smooth = ndi.gaussian_filter(np.where(land, density, 0.), 1.)
    if np.any(smooth[eligible] <= 0) or np.any(~np.isfinite(score[eligible])) or np.any(score[eligible] < 0):
        raise ValueError('Eligible scores need positive smoothed density and finite nonnegative scores')
    result = np.zeros_like(score)
    result[eligible] = score[eligible] * smooth[eligible] ** (power - 1.)
    if not np.isfinite(result).all():
        raise ValueError('Transformed score overflow')
    return result


def history_prior(distance_km, scale_km, floor):
    distance = np.asarray(distance_km, float)
    if np.any(np.isnan(distance)) or np.any(distance < 0):
        raise ValueError('Nonnegative distances required; infinity denotes unsupported cells')
    if not np.isfinite(scale_km) or scale_km <= 0 or not np.isfinite(floor) or not 0 <= floor <= 1:
        raise ValueError('Positive history scale and floor in [0,1] required')
    return floor + (1. - floor) * np.exp(-distance / scale_km)


def variants():
    """The 21 unique variants committed in the 11 November protocol."""
    for power in (.5, .7, 1.):
        for scale in (450, 800):
            for floor in (0., .1, .3, 1.):
                if floor == 1 and scale == 800:
                    continue
                yield dict(variant=f'b{power:g}_L{scale}_f{floor:g}', power=power,
                           scale_km=scale, floor=floor)
