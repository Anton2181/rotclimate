"""Liquid/vapor phase equilibrium including heat capacities and rain enthalpy.

Fixed pressure and dry mass, no ice or gravitational work. Liquid enters at
its supplied temperature. Conserves cp_d Md(T-T0)+cp_v Wv(T-T0)+Lv0 Wv
+cp_l Wl(T-T0); constant heat capacities imply temperature-dependent Lv.
"""
from dataclasses import dataclass
import numpy as np

from .column_thermodynamics import CP,LV
from .phase_adjustment import _saturation

CP_VAPOR=1850.
CP_LIQUID=4186.
REFERENCE_K=273.15


def gas_enthalpy(temperature_k,vapor_kg_m2,dry_mass_kg_m2):
    return (CP*np.asarray(dry_mass_kg_m2)+CP_VAPOR*np.asarray(vapor_kg_m2))*(np.asarray(temperature_k)-REFERENCE_K)+LV*np.asarray(vapor_kg_m2)


def liquid_enthalpy(temperature_k,liquid_kg_m2):
    return CP_LIQUID*np.asarray(liquid_kg_m2)*(np.asarray(temperature_k)-REFERENCE_K)


@dataclass
class MoistPhase:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    liquid_kg_m2: np.ndarray
    condensation_kg_m2: np.ndarray
    evaporation_kg_m2: np.ndarray
    certificate: dict


@dataclass
class MoistRainColumn:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    condensation_kg_m2: np.ndarray
    rain_evaporation_kg_m2: np.ndarray
    dry_equivalent_heat_j_m2: np.ndarray
    gas_sensible_change_j_m2: np.ndarray
    certificate: dict


def equilibrate_moist(temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa,
                     liquid_kg_m2=0.,liquid_temperature_k=None):
    """Unique liquid equilibrium at fixed total water and stated moist enthalpy.

Liquid has the air temperature unless specified. This explicitly accounts for
cold falling rain mixing into warmer lower air before phase equilibrium.
"""
    if liquid_temperature_k is None:liquid_temperature_k=temperature_k
    t,w,m,p,l,tl=np.broadcast_arrays(*[np.asarray(a,float) for a in
        [temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa,liquid_kg_m2,liquid_temperature_k]])
    if (not all(np.isfinite(a).all() for a in [t,w,m,p,l,tl]) or np.any(m<=0)
            or np.any(w<0) or np.any(l<0) or np.any(w/m>.2)
            or np.any((t<180)|(t>330)) or np.any((tl<150)|(tl>370))
            or np.any((p<10000)|(p>110000)) or not np.isfinite(_saturation(t,p)).all()):
        raise ValueError("Need terrestrial temperature/pressure, positive dry mass and nonnegative dilute water")
    initial=gas_enthalpy(t,w,m)+liquid_enthalpy(tl,l)
    capacity=CP*m+CP_VAPOR*w+CP_LIQUID*l
    dc=CP_VAPOR-CP_LIQUID
    def temperature(x):
        return REFERENCE_K+(initial-LV*(w+x))/(capacity+dc*x)
    def x_at_temperature(target):
        d=target-REFERENCE_K
        return (initial-LV*w-capacity*d)/(LV+dc*d)
    lo=np.maximum(-w,x_at_temperature(370.));hi=np.minimum(l,x_at_temperature(150.))
    def residual(x):return w+x-m*_saturation(temperature(x),p)
    flo,fhi=residual(lo),residual(hi)
    if np.any(flo>1e-12) or np.any((fhi<0)&(hi<l)):
        raise ValueError("Moist phase equilibrium outside150–370K")
    all_evaporates=(fhi<=0)&(hi==l)
    for _ in range(64):
        mid=.5*(lo+hi);positive=residual(mid)>0
        hi=np.where(positive,mid,hi);lo=np.where(positive,lo,mid)
    change=np.where(all_evaporates,l,.5*(lo+hi))
    new_t,new_w,new_l=temperature(change),w+change,l-change
    final=gas_enthalpy(new_t,new_w,m)+liquid_enthalpy(new_t,new_l)
    energy_error=final-initial;water_error=new_w+new_l-w-l
    tolerance=100*np.finfo(float).eps*np.maximum(1.,np.abs(initial)+capacity*REFERENCE_K)
    if (not all(np.isfinite(a).all() for a in [new_t,new_w,new_l]) or np.any(new_w<0)
            or np.any(new_l<0) or np.any(np.abs(energy_error)>tolerance)):
        raise RuntimeError("Moist phase water/enthalpy bounds failed")
    sat=m*_saturation(new_t,p);den=np.maximum(sat,1e-12)
    saturation_error=np.maximum(np.maximum(new_w-sat,0),np.where(new_l>1e-12,np.abs(new_w-sat),0))/den
    if np.any(saturation_error>1e-9):raise RuntimeError("Moist equilibrium saturation failed")
    cert=dict(maximum_water_residual_kg_m2=float(np.abs(water_error).max()),
        maximum_moist_enthalpy_residual_j_m2=float(np.abs(energy_error).max()),
        maximum_saturation_error_fraction=float(saturation_error.max()),
        scope="Fixed-pressure liquid-only equilibrium with dry/vapor/liquid heat capacity; no ice or gravitational work")
    return MoistPhase(new_t,new_w,new_l,np.maximum(-change,0),np.maximum(change,0),cert)


def moist_falling_rain(temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa):
    """Upper rain carries its actual sensible enthalpy into the lower box."""
    t,w,m,p=[np.asarray(a,float) for a in [temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa]]
    if (t.ndim<1 or t.shape[0]!=2 or any(a.shape!=t.shape for a in [w,m,p]) or not np.all(p[0]>p[1])):
        raise ValueError("Need matching lower/upper arrays with descending representative pressures")
    upper=equilibrate_moist(t[1],w[1],m[1],p[1])
    lower=equilibrate_moist(t[0],w[0],m[0],p[0],upper.liquid_kg_m2,upper.temperature_k)
    new_t=np.stack([lower.temperature_k,upper.temperature_k]);new_w=np.stack([lower.vapor_kg_m2,upper.vapor_kg_m2])
    rain=lower.liquid_kg_m2;rain_h=liquid_enthalpy(lower.temperature_k,rain)
    before=gas_enthalpy(t,w,m);after=gas_enthalpy(new_t,new_w,m)
    water_error=w.sum(0)-new_w.sum(0)-rain
    energy_error=after.sum(0)+rain_h-before.sum(0)
    scale=np.sum(np.abs(before)+CP*m*REFERENCE_K,axis=0)
    if np.any(np.abs(energy_error)>200*np.finfo(float).eps*np.maximum(scale,1.)):
        raise RuntimeError("Falling rain failed column moist enthalpy plus exported rain energy")
    condensation=np.stack([lower.condensation_kg_m2,upper.condensation_kg_m2])
    evaporation=np.stack([lower.evaporation_kg_m2,upper.evaporation_kg_m2])
    sensible=(after-LV*new_w)-(before-LV*w)
    cert=dict(maximum_column_water_residual_kg_m2=float(np.abs(water_error).max()),
        maximum_column_moist_enthalpy_residual_j_m2=float(np.abs(energy_error).max()),
        maximum_sensible_plus_rain_minus_latent_residual_j_m2=float(np.abs(sensible.sum(0)+rain_h-LV*rain).max()),
        upper=upper.certificate,lower=lower.certificate,
        scope="Isolated liquid-only two-layer phase/rain transfer with heat capacities and precipitation enthalpy; no ice, convection, mechanical/gravitational energy or climate coupling")
    return MoistRainColumn(new_t,new_w,rain,rain_h,condensation,evaporation,
        CP*m*(new_t-t),sensible,cert)
