"""Accessibility diagnostics; these do not infer allegiance or military control."""
from dataclasses import dataclass
import numpy as np


@dataclass
class SeasonalAccess:
    access_mask: np.ndarray
    accessible_months: np.ndarray
    longest_isolation: np.ndarray
    effective_days: np.ndarray
    annual_threshold: np.ndarray


def cyclic_isolation(access):
    access=np.asarray(access)
    if access.dtype.kind!='b' or access.ndim<1 or not 0<len(access)<=12:
        raise ValueError('One to twelve boolean seasonal bins required')
    run=np.zeros(access.shape[1:],np.uint8);longest=run.copy()
    for period in np.concatenate([access,access]):
        run=np.where(period,0,np.minimum(run+1,len(access)))
        longest=np.maximum(longest,run)
    return longest


def seasonal_access(days,*,threshold=2.,decay_days=1.):
    days=np.asarray(days,float)
    if days.ndim<1 or not 0<len(days)<=12 or np.isnan(days).any() or np.any(days<0):
        raise ValueError('Nonnegative travel days or positive infinity required')
    if not np.isfinite(threshold) or threshold<=0 or not np.isfinite(decay_days) or decay_days<=0:
        raise ValueError('Positive finite travel threshold and decay scale required')
    access=days<=threshold;mask=np.zeros(days.shape[1:],np.uint16)
    for i,period in enumerate(access):mask|=period.astype(np.uint16)<<i
    with np.errstate(divide='ignore'):
        effective=-decay_days*np.log(np.mean(np.exp(-days/decay_days),axis=0))
    return SeasonalAccess(mask,access.sum(0).astype(np.uint8),cyclic_isolation(access),effective,effective<=threshold)
