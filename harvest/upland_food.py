"""Conditional upland harvests from one continuous daily field-water ledger.

Supplied crop windows must already be judged physiologically feasible; this
adapter does not choose sowing dates or validate cultivar maturity. Potential
food is net of seed/processing. No arbitrary secondary-crop discount is added.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np

from .soil_water import periodic_soil_water


@dataclass(frozen=True)
class UplandSeason:
    crop: str
    start: int
    duration: int
    potential_net_energy: float
    coefficient: float
    yield_response: float
    depletion_fraction: float


@dataclass
class UplandFood:
    harvest: np.ndarray
    seasons: list[dict]
    water: object
    coefficients: np.ndarray


def upland_food_year(rain,reference_et,seasons,*,total_available,fallow_coefficient,
                    fallow_depletion_fraction,minimum_et_ratio,
                    irrigation_request=0.,irrigation_supply=0.):
    """Apply a supplied seasonal FAO33 Ky response to FAO56 actual crop ET.

    ``minimum_et_ratio`` is an explicit analysis guard, not a fitted universal
    biological threshold. Below it this simple yield inference is refused;
    extreme drought requires a validated growth/failure model. Ponded rice and
    perennials are excluded. Off-season Kc/p and fixed root depth are scenario
    assumptions, not a full dual-coefficient soil-evaporation model.
    """
    rain,et0=np.broadcast_arrays(np.asarray(rain,float),np.asarray(reference_et,float))
    if rain.ndim!=1 or not len(rain):raise ValueError('One daily field required')
    days=len(rain)
    if not np.isfinite(minimum_et_ratio) or not 0<minimum_et_ratio<=1:
        raise ValueError('Explicit positive yield-inference guard required')
    kc=np.full(days,fallow_coefficient,float);p=np.full(days,fallow_depletion_fraction,float)
    owner=np.full(days,-1,int);seasons=tuple(seasons)
    for i,s in enumerate(seasons):
        if s.crop not in ('wheat','barley','millet') or any(isinstance(v,bool) or not isinstance(v,Integral) for v in [s.start,s.duration]):
            raise ValueError('Named upland crop and integer daily windows required')
        if not 0<=s.start<days or not 1<=s.duration<=days:
            raise ValueError('Invalid season window')
        if not np.isfinite(s.potential_net_energy) or s.potential_net_energy<0 or not np.isfinite(s.yield_response) or s.yield_response<0:
            raise ValueError('Finite nonnegative net potential food and Ky required')
        idx=(s.start+np.arange(s.duration))%days
        if np.any(owner[idx]>=0):raise ValueError('Crop seasons overlap on the same field')
        owner[idx]=i;kc[idx]=s.coefficient;p[idx]=s.depletion_fraction
    water=periodic_soil_water(rain,et0,kc,total_available=total_available,depletion_fraction=p,
        irrigation_request=irrigation_request,irrigation_supply=irrigation_supply,record=True)
    harvest=np.zeros(days);results=[]
    for i,s in enumerate(seasons):
        idx=owner==i;potential=float(np.sum(et0[idx]*kc[idx]));actual=float(np.sum(water.et_path[idx]))
        ratio=1. if potential==0 else min(actual/potential,1.)
        if ratio<minimum_et_ratio:
            raise ValueError(f'{s.crop}: ET ratio {ratio:.3f} lies outside the declared simple-yield analysis domain')
        factor=float(np.clip(1-s.yield_response*(1-ratio),0,1))
        food=s.potential_net_energy*factor;boundary=(s.start+s.duration)%days
        harvest[boundary]+=food
        results.append(dict(crop=s.crop,start=s.start,duration=s.duration,harvest_boundary=boundary,
            potential_net_energy=s.potential_net_energy,relative_yield=factor,net_harvest_energy=food,
            potential_et_mm=potential,actual_et_mm=actual,et_ratio=ratio))
    return UplandFood(harvest,results,water,kc)
