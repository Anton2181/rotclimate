"""Stable prescribed wind-temperature profile with two horizontal patterns.

Diagnostic closure only, not a vertical energy or convective-adjustment model.
A is a modeled common-pressure surface reference; B is a modeled zonal/free-air
reference. Neither is observed forcing. All derivatives are at fixed pressure.
"""
from functools import lru_cache
import numpy as np
from .thermal_layer_winds import (DRY_AIR_GAS_CONSTANT as RD,EQUATORIAL_F,
    LOWER_CENTROID_SIGMA,UPPER_CENTROID_SIGMA,LOWER_MASS_FRACTION)

G=9.80665
CP=1004.
P0=101325.
FLOOR=200.
DECAY_EXPONENT=1/(-np.log(1-LOWER_MASS_FRACTION))


def parameters(surface,background,lapse_k_km=6.):
    a,b=np.broadcast_arrays(np.asarray(surface,float),np.asarray(background,float))
    if (a.ndim!=2 or min(a.shape)<3 or not np.isfinite(a).all() or not np.isfinite(b).all()
            or (a<=0).any() or (b<=0).any() or not np.isfinite(lapse_k_km)
            or not 0<=lapse_k_km<G/CP*1000):
        raise ValueError('Need matching positive2D common-reference temperatures and a dry-stable environmental lapse')
    k=RD*lapse_k_km/1000/G;delta=a-b
    cap=np.divide((RD/CP-k)*a,delta,out=np.full_like(a,np.inf),where=delta>0)
    limited=cap<DECAY_EXPONENT;exponent=np.where(limited,cap,DECAY_EXPONENT)
    da=np.divide(-(RD/CP-k)*b,delta**2,out=np.zeros_like(a),where=limited)
    db=np.divide((RD/CP-k)*a,delta**2,out=np.zeros_like(a),where=limited)
    return a,b,k,exponent,da,db,limited


def raw_profile(log_sigma,par):
    a,b,k,exponent,da,db,_=par
    fade=np.exp(exponent*log_sigma);base=b+(a-b)*fade;power=np.exp(k*log_sigma)
    raw=base*power
    partial_a=power*(fade+(a-b)*fade*log_sigma*da)
    partial_b=power*(1-fade+(a-b)*fade*log_sigma*db)
    effective_kappa=k+exponent*(a-b)*fade/base
    return raw,partial_a,partial_b,effective_kappa


def profile(surface,background,pressure_pa,*,lapse_k_km=6.):
    """T, dT/dA, dT/dB, effective lapse at fixed absolute pressure.

    T=max([B+(A-B)*sigma**a]*sigma**k,200K). Nominal anomaly e-folding
    pressure depth equals the existing lower dry-mass layer. For warm anomalies,
    a<= (Rd/cp-k)*A/(A-B) guarantees dlnT/dlnp<=Rd/cp at every p<=p0.
    This prescribes a stable shape; it adds no claim of energy adjustment.
    """
    pressure=np.asarray(pressure_pa,float)
    if not np.isfinite(pressure).all() or (pressure<=0).any() or (pressure>P0).any():
        raise ValueError('Need finite pressure in(0,101325]Pa')
    raw,da,db,kappa=raw_profile(np.log(pressure/P0),parameters(surface,background,lapse_k_km))
    active=raw>FLOOR
    return np.maximum(raw,FLOOR),np.where(active,da,0.),np.where(active,db,0.),np.where(active,kappa*G/RD*1000,0.)


def active_interval(top,bottom,par):
    """Find the above-floor interval; a stable cold inversion can have2roots."""
    a,b,k,exponent,*_=par;delta=a-b
    peak=bottom.copy()
    if k==0:peak=np.where(delta<0,top,peak)
    else:
        ratio=np.divide(k*b,-(k+exponent)*delta,out=np.ones_like(a),where=delta<0)
        peak=np.where(delta<0,np.log(ratio)/exponent,peak)
    peak=np.clip(peak,top,bottom);hot=raw_profile(peak,par)[0]>FLOOR
    start=top.copy();end=bottom.copy()
    for upper in (True,False):
        edge=top if upper else bottom
        root=hot&(raw_profile(edge,par)[0]<=FLOOR)
        if not root.any():continue
        lo=top.copy() if upper else peak.copy();hi=peak.copy() if upper else bottom.copy()
        for _ in range(42):
            mid=(lo+hi)/2;warm=raw_profile(mid,par)[0]>FLOOR
            if upper:lo=np.where(warm,lo,mid);hi=np.where(warm,mid,hi)
            else:lo=np.where(warm,mid,lo);hi=np.where(warm,hi,mid)
        if upper:start=np.where(root,(lo+hi)/2,start)
        else:end=np.where(root,(lo+hi)/2,end)
    return start,np.where(hot,end,start)


@lru_cache(maxsize=1)
def quadrature():return np.polynomial.legendre.leggauss(16)


def separated_thermal_shear(surface,background,surface_pressure_pa,cell_m,coriolis,*,lapse_k_km=6.):
    """Integrate grad_p(T) BEFORE the terrain-dependent pressure bounds."""
    par=parameters(surface,background,lapse_k_km);a,b,k,exponent,_,_,limited=par
    ps=np.asarray(surface_pressure_pa,float);f=np.broadcast_to(np.asarray(coriolis,float),a.shape)
    if (ps.shape!=a.shape or not np.isfinite(ps).all() or (ps<=0).any() or (ps>P0).any()
            or not np.isfinite(cell_m) or cell_m<=0 or not np.isfinite(f).all()):
        raise ValueError('Need matching physical surface pressure, spacing and Coriolis field')
    top,bottom=active_interval(np.log(UPPER_CENTROID_SIGMA*ps/P0),np.log(LOWER_CENTROID_SIGMA*ps/P0),par)
    nodes,weights=quadrature();width=bottom-top;x=top[None]+(nodes[:,None,None]+1)*width[None]/2
    _,da,db,_=raw_profile(x,par)
    integral_a=np.sum(weights[:,None,None]*da,axis=0)*width/2
    integral_b=np.sum(weights[:,None,None]*db,axis=0)*width/2
    east=(integral_a*np.gradient(a,axis=1)+integral_b*np.gradient(b,axis=1))/cell_m
    north=-(integral_a*np.gradient(a,axis=0)+integral_b*np.gradient(b,axis=0))/cell_m
    coefficient=RD*f/(f*f+EQUATORIAL_F**2)
    maximum_kappa=k+exponent*np.maximum(a-b,0)/a
    return (-coefficient*north,coefficient*east),dict(
        temperature_coordinate='two common101325Pa references; fixed-pressure gradients before moving-bound integration',
        thermal_profile='stable-separated',thermal_lapse_k_km=float(lapse_k_km),thermal_floor_k=FLOOR,
        reference_pressure_pa=P0,nominal_anomaly_decay_exponent=float(DECAY_EXPONENT),
        minimum_anomaly_decay_exponent=float(exponent.min()),maximum_anomaly_decay_exponent=float(exponent.max()),
        stability_limited_cells=int(limited.sum()),maximum_possible_lapse_k_km=float(maximum_kappa.max()*G/RD*1000),
        dry_adiabatic_limit_k_km=G/CP*1000,
        minimum_reference_temperature_k=float(a.min()),maximum_reference_temperature_k=float(a.max()),
        minimum_background_temperature_k=float(b.min()),maximum_background_temperature_k=float(b.max()),
        fully_floor_limited_cells=int((width==0).sum()),quadrature_nodes=16)
