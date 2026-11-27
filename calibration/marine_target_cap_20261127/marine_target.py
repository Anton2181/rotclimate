"""Experimental marine-equilibrium ceiling; no fitted constants or observations."""
import numpy as np


def capped_marine_target(ocean_target, land_saturation, ocean, nearest, rh, land_rate):
    ocean = np.asarray(ocean, bool)
    if any(np.shape(a) != ocean.shape for a in [ocean_target, land_saturation, land_rate]):
        raise ValueError('Marine target fields must share the grid shape')
    if not np.isfinite(rh) or rh < 0:
        raise ValueError('Nonnegative finite humidity fraction required')
    if not ocean.any():
        # EDT has no valid sea index on all-land domains: no marine exchange.
        return np.zeros_like(land_saturation), np.zeros_like(land_rate)
    if (not np.isfinite(ocean_target[ocean]).all() or (ocean_target[ocean] < 0).any()
            or not np.isfinite(land_saturation).all() or (land_saturation < 0).any()
            or not np.isfinite(land_rate).all() or (land_rate < 0).any()):
        raise ValueError('Invalid marine equilibrium, saturation or rate')
    if ocean.all():
        return ocean_target.copy(), land_rate
    if len(nearest) != 2 or any(np.shape(a) != ocean.shape for a in nearest):
        raise ValueError('Invalid nearest-sea indices')
    if any((a < 0).any() or (a >= ocean.shape[k]).any() for k, a in enumerate(nearest)):
        raise ValueError('Nearest-sea index outside the grid')
    if not ocean[nearest].all():
        raise ValueError('Nearest source must be an actual sea cell')
    bounded = np.minimum(rh * land_saturation, ocean_target[nearest])
    return np.where(ocean, ocean_target, bounded), land_rate
