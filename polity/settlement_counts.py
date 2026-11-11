"""Role-specific aggregate count models; never interpret a seat as residents."""
import numpy as np


def count_exposure(area_km2, population, beta):
    area, people = np.asarray(area_km2, float), np.asarray(population, float)
    if area.shape != people.shape or np.any(~np.isfinite(area)) or np.any(~np.isfinite(people)):
        raise ValueError('Matching finite exposure and population required')
    if np.any(area<=0) or np.any(people<0) or not np.isfinite(beta) or beta<0:
        raise ValueError('Positive land area, nonnegative people and exponent required')
    # beta=0 is area-only, including genuinely zero-population blocks.
    return area * (people / area)**beta


def fit_scale(exposure, counts):
    exposure, counts = np.asarray(exposure, float), np.asarray(counts, float)
    if exposure.shape!=counts.shape or np.any(~np.isfinite(exposure)) or np.any(exposure<0) or np.any(~np.isfinite(counts)) or np.any(counts<0):
        raise ValueError('Matching finite nonnegative exposures and counts required')
    if exposure.sum()==0:
        return 0. if counts.sum()==0 else None
    return float(counts.sum()/exposure.sum())


def poisson_deviance(observed, predicted):
    observed, predicted = np.broadcast_arrays(np.asarray(observed,float),np.asarray(predicted,float))
    if np.any(~np.isfinite(observed)) or np.any(~np.isfinite(predicted)) or np.any(observed<0) or np.any(predicted<0):
        raise ValueError('Finite nonnegative counts required')
    if np.any((observed>0)&(predicted==0)):
        return float('inf')
    terms=predicted-observed
    positive=observed>0
    terms[positive]+=observed[positive]*np.log(observed[positive]/predicted[positive])
    return float(2*np.sum(terms))
