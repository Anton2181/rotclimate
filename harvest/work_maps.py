"""Partial cereal field-work scenarios from published atlas crop energies.

Columella work counts concern listed tasks to the threshing floor. Neither
these ratios nor their inverse estimate total subsistence labour/population.
Calendar masks retain all tied best windows, never probabilities or dates.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class CerealWork:
    hours: np.ndarray
    land: np.ndarray
    reaping: np.ndarray
    crop: np.ndarray  # 0 unavailable, 1 wheat, 2 barley; ties prefer wheat


def cereal_work(energy,listed_hours,reaping_hours,*,food_target):
    """Choose the least listed field work among supplied single cereals.

    Energy shape: two crops (wheat, barley), then cell axes; kcal per cropped
    hectare, already net of seed/edible processing fractions. No second seed,
    occupation, arable, fallow or malaria deduction. Land is the requirement
    of that WORK-efficient cereal, not an independent minimum-land solution.
    Zero output stays unavailable (NaN), rather than zero work.
    """
    energy=np.asarray(energy,float);hours=np.asarray(listed_hours,float);reap=np.asarray(reaping_hours,float)
    if energy.ndim<1 or energy.shape[0]!=2 or hours.shape!=(2,) or reap.shape!=(2,):
        raise ValueError('Two cereal energies and aligned per-hectare work counts required')
    if not np.isfinite(energy).all() or np.any(energy<0) or not np.isfinite(hours).all() or np.any(hours<=0):
        raise ValueError('Finite nonnegative energy and positive work required')
    if not np.isfinite(reap).all() or np.any((reap<=0)|(reap>hours)) or not np.isfinite(food_target) or food_target<=0:
        raise ValueError('Positive food target and reaping work within total work required')
    expansion=(slice(None),)+(None,)*(energy.ndim-1)
    area=np.divide(food_target,energy,out=np.full_like(energy,np.inf),where=energy>0)
    work=area*hours[expansion];choice=np.argmin(work,axis=0)
    gather=lambda array:np.take_along_axis(array,choice[None],axis=0)[0]
    best=gather(work);valid=np.isfinite(best)
    return CerealWork(np.where(valid,best,np.nan),np.where(valid,gather(area),np.nan),
        np.where(valid,gather(area*reap[expansion]),np.nan),np.where(valid,choice+1,0).astype('u1'))


def tied_harvest_boundaries(catalogue):
    """Bitmask of all maturity boundaries of equal maximum positive energy."""
    best=catalogue.energy.max(axis=0);mask=np.zeros(best.shape,np.uint16)
    for window,energy in zip(catalogue.windows,catalogue.energy):
        tied=(best>0)&np.isclose(energy,best,rtol=1e-12,atol=1e-7)
        mask|=np.where(tied,1<<window.harvest_boundary,0).astype(np.uint16)
    return best,mask


def boundary_count(mask):
    mask=np.asarray(mask)
    if mask.dtype.kind not in 'ui' or np.any((mask<0)|(mask>4095)):raise ValueError('Twelve-bin unsigned masks required')
    return sum(((mask>>i)&1).astype(np.uint8) for i in range(12))
