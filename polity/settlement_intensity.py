"""Experimental relative centre intensity and symmetric, locally varying spacing.

This allocates locations under a supplied count. It is not an occupation-age,
population-growth, food-supply or political-authority model. The original frozen
fixed-spacing allocator is retained unchanged for exact study replay.
"""
from __future__ import annotations

from numbers import Integral
import numpy as np
from scipy.special import logsumexp

from polity.settlement_locations import Placement


def intensity_fields(score, eligible, count, cell_km, *, history=None,
                     coefficient=0.35, maximum_spacing_km=45.):
    """Return target centres/km² and desired pair spacing, not people/km².

    Integrating target intensity over eligible cells gives the requested count. Positive
    rescaling of suitability or prior changes neither field. Expected site count
    is distinct from the eventual realization; exclusions can cause a shortfall.
    Inhibition and fixed-count truncation change spatial inclusion probabilities,
    so this field is not the exact expectation of the resulting point process.
    """
    score,eligible=np.asarray(score,float),np.asarray(eligible,bool)
    if score.ndim!=2 or eligible.shape!=score.shape:
        raise ValueError('Score and eligibility must be matching2D grids')
    if isinstance(count,bool) or not isinstance(count,Integral) or count<0:
        raise ValueError('Count must be a nonnegative integer')
    if not np.isfinite(cell_km) or cell_km<=0:
        raise ValueError('Cell size must be positive and finite')
    if not np.isfinite(coefficient) or coefficient<0 or not np.isfinite(maximum_spacing_km) or maximum_spacing_km<0:
        raise ValueError('Spacing parameters must be nonnegative and finite')
    if np.any(~np.isfinite(score[eligible])) or np.any(score[eligible]<0):
        raise ValueError('Eligible scores must be finite and nonnegative')
    positive=eligible&(score>0)
    logw=np.full(score.shape,-np.inf)
    logw[positive]=np.log(score[positive])
    if history is not None:
        history=np.asarray(history,float)
        if history.shape!=score.shape or np.any(~np.isfinite(history[eligible])) or np.any(history[eligible]<0):
            raise ValueError('History must match the grid and be finite and nonnegative')
        positive &= history>0
        logw[~positive]=-np.inf
        logw[positive]+=np.log(history[positive])
    intensity=np.zeros(score.shape);spacing=np.zeros(score.shape)
    if count and positive.any():
        intensity[positive]=count*np.exp(logw[positive]-logsumexp(logw[positive]))/cell_km**2
        spacing[positive]=np.minimum(coefficient/np.sqrt(np.maximum(intensity[positive],np.finfo(float).tiny)),maximum_spacing_km)
    return intensity,spacing


def adaptive_count_sites(score,eligible,count,cell_km,*,history=None,coefficient=.35,
                         maximum_spacing_km=45.,seed=1,stochastic=False):
    """Accept pairs only beyond half the sum of their local separation fields.

    Pair compatibility is symmetric even at a boundary between low and high
    intensity. No9km lower cutoff is imposed; one proposal per raster cell still
    prevents duplicates. The input grids, population and count are never modified.
    """
    intensity,spacing=intensity_fields(score,eligible,count,cell_km,history=history,
        coefficient=coefficient,maximum_spacing_km=maximum_spacing_km)
    candidates=np.flatnonzero(intensity>0)
    if not count or not len(candidates):
        return Placement((),int(count),len(candidates))
    rank=np.log(intensity.ravel()[candidates])
    if stochastic:rank+=np.random.default_rng(seed).gumbel(size=len(candidates))
    order=np.argsort(-rank,kind='stable')
    h,w=intensity.shape;blocked=np.zeros((h,w),bool);towns=[]
    maximum=float(spacing.max())
    for index in candidates[order]:
        y,x=divmod(int(index),w)
        if blocked[y,x]:continue
        towns.append((y,x))
        if len(towns)==count:break
        # Include every candidate whose pair-specific separation could conflict.
        radius=int(np.ceil((spacing[y,x]+maximum)/(2*cell_km)))
        y0,y1=max(0,y-radius),min(h,y+radius+1)
        x0,x1=max(0,x-radius),min(w,x+radius+1)
        yy,xx=np.ogrid[y0:y1,x0:x1]
        threshold=.5*(spacing[y,x]+spacing[y0:y1,x0:x1])
        blocked[y0:y1,x0:x1]|=((yy-y)**2+(xx-x)**2)*cell_km**2<=threshold**2
    return Placement(tuple(towns),int(count),len(candidates))
