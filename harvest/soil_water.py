"""Continuous fixed-root-zone water ledger, FAO56 equations 81–88.

Inputs are daily water depths, reference ET and supplied crop coefficients.
Harvest/sowing do not reset storage. Irrigation is net infiltrating water
limited by an explicit field supply; this is not a river/allocation model.
Reference: https://www.fao.org/4/x0490e/x0490e0e.htm .
"""
from dataclasses import dataclass

import numpy as np


@dataclass
class SoilWaterYear:
    initial_stored: np.ndarray
    final_stored: np.ndarray
    evapotranspiration: np.ndarray
    potential_evapotranspiration: np.ndarray
    irrigation_applied: np.ndarray
    irrigation_unmet: np.ndarray
    runoff: np.ndarray
    drainage: np.ndarray
    ledger_residual: np.ndarray
    periodic_residual: np.ndarray
    depletion_path: np.ndarray | None = None
    stress_path: np.ndarray | None = None
    et_path: np.ndarray | None = None
    irrigation_path: np.ndarray | None = None


def available_water(field_capacity,wilting_point,root_depth):
    """Eq82, volumetric fractions and metres -> millimetres of available water."""
    fc,wp,depth=np.broadcast_arrays(np.asarray(field_capacity,float),np.asarray(wilting_point,float),np.asarray(root_depth,float))
    if not all(np.isfinite(a).all() for a in (fc,wp,depth)) or np.any((wp<0)|(fc>1)|(fc<=wp)|(depth<=0)):
        raise ValueError('Valid field capacity, wilting point and root depth required')
    return 1000*(fc-wp)*depth


def stress_coefficient(depletion,total_available,depletion_fraction):
    """Eq84: full ET until RAW=p*TAW, then linearly reduced root extraction."""
    return np.clip((total_available-depletion)/((1-depletion_fraction)*total_available),0,1)


def _prepare(rain,reference_et,crop_coefficient,total_available,depletion_fraction,
             runoff,irrigation_request,irrigation_supply,capillary_rise,adjust_depletion):
    series=np.broadcast_arrays(*(np.asarray(a,float) for a in [rain,reference_et,crop_coefficient,
        depletion_fraction,runoff,irrigation_request,irrigation_supply,capillary_rise]))
    if series[0].ndim<1 or not len(series[0]) or not all(np.isfinite(a).all() for a in series):
        raise ValueError('Finite nonempty daily fields required')
    r,et0,kc,p,ro,request,supply,cr=series
    if any(np.any(a<0) for a in [r,et0,kc,ro,request,supply,cr]) or np.any(ro>r) or np.any((p<=0)|(p>=1)):
        raise ValueError('Nonnegative depths/ET/coefficient, runoff<=rain and 0<p<1 required')
    taw=np.broadcast_to(np.asarray(total_available,float),r.shape[1:])
    if not np.isfinite(taw).all() or np.any(taw<=0):raise ValueError('Fixed positive TAW required')
    potential=et0*kc
    if not np.isfinite(potential).all():raise ValueError('Potential ET must remain finite')
    if adjust_depletion:p=np.clip(p+.04*(5-potential),.1,.8)
    irrigation=np.minimum(request,supply)
    return r,potential,p,ro,irrigation,request-irrigation,cr,taw


def _advance(initial,prepared,record):
    rain,potential,p,runoff,irrigation,unmet,capillary,taw=prepared
    stock=np.broadcast_to(np.asarray(initial,float),taw.shape).copy()
    if not np.isfinite(stock).all() or np.any((stock<0)|(stock>taw)):
        raise ValueError('Initial storage must be within 0..TAW')
    initial=stock.copy();et=np.zeros_like(stock);drainage=et.copy()
    depletion=[taw-stock] if record else None;stresses=[] if record else None;ets=[] if record else None
    for rain_day,demand,fraction,ro,ir,cr in zip(rain,potential,p,runoff,irrigation,capillary):
        # Rain and net irrigation can relieve stress this day. Water above
        # field capacity drains after this day's ET (FAO56 daily convention).
        available=stock+rain_day-ro+ir+cr
        stress=stress_coefficient(np.maximum(taw-available,0),taw,fraction)
        actual=np.minimum(demand*stress,available)
        after=available-actual;drained=np.maximum(after-taw,0)
        stock=np.minimum(after,taw)
        et+=actual;drainage+=drained
        if record:depletion.append(taw-stock);stresses.append(stress);ets.append(actual)
    ledger=initial+rain.sum(0)+irrigation.sum(0)+capillary.sum(0)-runoff.sum(0)-et-drainage-stock
    scale=np.maximum(1,initial+rain.sum(0)+irrigation.sum(0)+capillary.sum(0))
    if not np.isfinite(ledger).all() or np.any(np.abs(ledger)>1e-9*scale):
        raise RuntimeError('Soil water ledger did not close')
    return SoilWaterYear(initial,stock,et,potential.sum(0),irrigation.sum(0),unmet.sum(0),runoff.sum(0),
        drainage,ledger,np.abs(stock-initial),None if not record else np.stack(depletion),
        None if not record else np.stack(stresses),None if not record else np.stack(ets),
        None if not record else irrigation.copy())


def soil_water_year(rain,reference_et,crop_coefficient,*,total_available,
                    depletion_fraction,initial_stored,runoff=0.,irrigation_request=0.,
                    irrigation_supply=0.,capillary_rise=0.,adjust_depletion=False,record=False):
    """One daily sequence. Coefficient and depletion fraction can change by crop.

    Fixed TAW persists across the sequence. Depth growth, snow/frozen soil,
    dual-coefficient evaporation, ponded rice and groundwater routing are not
    represented. Initial storage is explicit; no free refill at harvest.
    """
    return _advance(initial_stored,_prepare(rain,reference_et,crop_coefficient,total_available,
        depletion_fraction,runoff,irrigation_request,irrigation_supply,capillary_rise,adjust_depletion),record)


def periodic_soil_water(rain,reference_et,crop_coefficient,*,total_available,
                       depletion_fraction,runoff=0.,irrigation_request=0.,irrigation_supply=0.,
                       capillary_rise=0.,adjust_depletion=False,record=False):
    """Smallest repeating soil-water state for the identical supplied year.

    Bisection of the nonexpansive annual storage map avoids an arbitrary
    two-year spin-up or inherited full soil profile. Periodic storage does
    not mean water demand is met. No yield or rainfall-risk inference.
    """
    prepared=_prepare(rain,reference_et,crop_coefficient,total_available,depletion_fraction,
        runoff,irrigation_request,irrigation_supply,capillary_rise,adjust_depletion)
    taw=prepared[-1];low=np.zeros_like(taw);high=np.array(taw,copy=True)
    tolerance=1e-9*np.maximum(1,taw)
    empty_fixed=_advance(low,prepared,False).final_stored<=tolerance
    for _ in range(80):
        mid=low+.5*(high-low)
        drift=_advance(mid,prepared,False).final_stored-mid
        low=np.where(drift>0,mid,low);high=np.where(drift<=0,mid,high)
        if np.all((high-low<=tolerance)|empty_fixed):break
    result=_advance(np.where(empty_fixed,0.,high),prepared,record)
    if np.any(result.periodic_residual>tolerance):raise RuntimeError('Repeating soil water did not converge')
    return result
