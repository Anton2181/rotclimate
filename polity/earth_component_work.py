"""Isolated component crop tasks sharing one physical rural workforce.

Potential grain is an input. Positive component activities keep a common
retention fraction; the single annual budget and each harvest-bin peak budget
apply to their sum. No seasonal food or demographic calculation occurs here.
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class ComponentWork:
    active_area: np.ndarray
    required_listed: np.ndarray
    required_reaping: np.ndarray
    monthly_peak_required: np.ndarray
    workers: np.ndarray
    annual_available: np.ndarray
    peak_available: np.ndarray
    annual_fraction: np.ndarray
    peak_fraction: np.ndarray
    retained: np.ndarray
    produced_components: np.ndarray
    produced_total: np.ndarray
    annual_used: np.ndarray
    monthly_peak_used: np.ndarray


def component_work(potential,area,listed_per_ha,reaping_per_ha,boundary,rural,*,hours):
    potential,area,listed,reaping=[np.asarray(v,float) for v in [potential,area,listed_per_ha,reaping_per_ha]]
    boundary=np.asarray(boundary);rural=np.asarray(rural,float)
    if potential.ndim!=2 or any(v.shape!=potential.shape for v in [area,listed,reaping,boundary]) or rural.shape!=potential.shape[1:]:
        raise ValueError('Aligned component×source arrays and one rural population per physical source required')
    if hours not in [600,300]:raise ValueError('Only the declared600h primary and300h stress are supported')
    if not all(np.isfinite(v).all() for v in [potential,area,listed,reaping,rural]) or any(np.any(v<0) for v in [potential,area,listed,reaping,rural]):
        raise ValueError('Finite nonnegative physical inputs required')
    positive=potential>0
    if boundary.dtype.kind not in 'iu' or np.any(positive&((boundary<0)|(boundary>=12))) or np.any(positive&((area<=0)|(listed<=0)|(reaping<=0))) or np.any(reaping>listed):
        raise ValueError('Positive crop activities require area,complete work and a valid harvest boundary')
    active_area=np.where(positive,area,0.)
    required_listed=active_area*listed;required_reaping=active_area*reaping
    peak_required=np.zeros((12,len(rural)))
    for component in range(len(potential)):
        ok=positive[component];source=np.flatnonzero(ok)
        np.add.at(peak_required,(boundary[component,ok],source),required_reaping[component,ok])
    workers=rural*.4
    annual_available=workers*hours;peak_available=np.minimum(annual_available,workers*30*8)
    annual_required=required_listed.sum(0);peak_maximum=peak_required.max(0)
    annual_fraction=np.divide(annual_available,annual_required,out=np.ones_like(rural),where=annual_required>0)
    peak_fraction=np.divide(peak_available,peak_maximum,out=np.ones_like(rural),where=peak_maximum>0)
    retained=np.minimum(1,np.minimum(annual_fraction,peak_fraction))
    retained=np.where(positive.any(0),retained,0.)
    produced=potential*retained
    return ComponentWork(active_area,required_listed,required_reaping,peak_required,workers,
        annual_available,peak_available,annual_fraction,peak_fraction,retained,produced,produced.sum(0),
        annual_required*retained,peak_required*retained)
