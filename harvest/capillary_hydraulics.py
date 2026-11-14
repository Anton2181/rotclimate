"""Supplied-soil hydraulic relations and stationary capillary head profiles.

The profile relates a prescribed flux to pressure/height. It creates no water
and is not a groundwater supply, aquifer store or crop-uptake model.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class HydraulicSoil:
    theta_residual: float
    theta_saturated: float
    ksat_cm_day: float
    alpha_cm_inv: float
    connectivity: float
    n: float

    def __post_init__(self):
        names=tuple(self.__dataclass_fields__)
        values=[getattr(self,name) for name in names]
        if any(isinstance(v,(bool,np.bool_)) for v in values) or not np.isfinite(values).all():
            raise ValueError('Finite scalar hydraulic parameters required')
        residual,saturated,ksat,alpha,connectivity,n=map(float,values)
        if not 0<=residual<saturated<=1 or ksat<=0 or alpha<=0 or n<=1:
            raise ValueError('Ordered water contents, positive Ksat/alpha and n>1 required')
        for name,value in zip(names,[residual,saturated,ksat,alpha,connectivity,n]):object.__setattr__(self,name,value)

    def _log_saturation(self,suction_cm):
        h=np.asarray(suction_cm,float)
        if not np.isfinite(h).all() or np.any(h<0):raise ValueError('Finite nonnegative suction magnitude in cm required')
        m=1-1/self.n
        with np.errstate(divide='ignore',over='ignore',invalid='ignore'):
            exponent=self.n*(np.log(self.alpha_cm_inv)+np.log(h))
            log_term=np.logaddexp(0.,exponent)
        if not np.isfinite(log_term).all():raise ValueError('Hydraulic parameter/head overflow')
        return -m*log_term,log_term

    def water_content(self,suction_cm):
        log_saturation,_=self._log_saturation(suction_cm)
        return np.clip(self.theta_residual+(self.theta_saturated-self.theta_residual)*np.exp(log_saturation),self.theta_residual,self.theta_saturated)

    def conductivity_cm_day(self,suction_cm):
        log_saturation,log_term=self._log_saturation(suction_cm);m=1-1/self.n
        with np.errstate(divide='ignore',over='ignore',invalid='ignore'):
            bracket=-np.expm1(m*np.log1p(-np.exp(-log_term)))
            result=np.exp(np.log(self.ksat_cm_day)+self.connectivity*log_saturation+2*np.log(bracket))
        if not np.isfinite(result).all():raise ValueError('Conductivity overflow or undefined parameters')
        return result


def stationary_profile_cm(soil,suction_edges_cm,upward_flux_mm_day):
    """FAO61 Eq6 midpoint recurrence; output shape flux.shape + (head edges,).

    Suction is the nonnegative magnitude of negative pressure head. Height is
    positive above the water table. Flux mm/day is converted to cm/day once.
    The caller must separately qualify and pay any actual supplied water.
    """
    h=np.asarray(suction_edges_cm,float);q=np.asarray(upward_flux_mm_day,float)
    if h.ndim!=1 or len(h)<2 or not np.isfinite(h).all() or h[0]!=0 or np.any(np.diff(h)<=0):
        raise ValueError('Ordered finite suction edges starting zero required')
    if not np.isfinite(q).all() or np.any(q<0):raise ValueError('Finite nonnegative prescribed upward flux required')
    conductivity=np.asarray(soil.conductivity_cm_day((h[:-1]+h[1:])/2))
    if not np.isfinite(conductivity).all() or np.any(conductivity<0):raise ValueError('Finite nonnegative midpoint conductivity required')
    flux=q[...,None]/10
    conductivity,flux=np.broadcast_arrays(conductivity,flux)
    ratio=np.divide(conductivity,conductivity+flux,out=np.ones_like(conductivity),where=flux>0)
    increments=np.diff(h)*ratio
    result=np.concatenate([np.zeros(increments.shape[:-1]+(1,)),np.cumsum(increments,axis=-1)],axis=-1)
    return np.where(q[...,None]==0,h,result)
