"""Conservative liquid-only phase adjustment, isolated from the Earth model.

Fixed pressure/dry mass, constant dry cp and Lv; water vapor/liquid heat
capacities, ice, precipitation enthalpy and gravitational work are omitted.
Conserves the stated dilute enthalpy cp*Md*T + Lv*Wv, not full moist energy.
"""
from dataclasses import dataclass

import numpy as np

from .column_thermodynamics import CP, EPSILON, LV


@dataclass
class PhaseState:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    liquid_kg_m2: np.ndarray
    condensed_kg_m2: np.ndarray
    evaporated_kg_m2: np.ndarray
    sensible_heat_j_m2: np.ndarray
    certificate: dict


@dataclass
class RainColumn:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    surface_rain_kg_m2: np.ndarray
    condensation_kg_m2: np.ndarray
    rain_evaporation_kg_m2: np.ndarray
    sensible_heat_j_m2: np.ndarray
    certificate: dict


def _saturation(temperature, pressure):
    """Dry-air mixing ratio, including an infinite near-boiling bracket limit."""
    es = 611.2 * np.exp(17.67*(temperature-273.15)/(temperature-29.65))
    return np.divide(EPSILON*es, pressure-es, out=np.full_like(es,np.inf), where=es<pressure)


def saturation_vapor_mass(temperature_k, dry_mass_kg_m2, pressure_pa):
    t,m,p = np.broadcast_arrays(np.asarray(temperature_k,float),
                               np.asarray(dry_mass_kg_m2,float),np.asarray(pressure_pa,float))
    if (not all(np.isfinite(a).all() for a in [t,m,p]) or np.any(m<=0)
            or np.any((t<150)|(t>370)) or np.any(p<=0)):
        raise ValueError("Need finite150–370K temperature, positive dry mass and pressure")
    r = _saturation(t,p)
    if not np.isfinite(r).all():
        raise ValueError("Saturation at or above boiling is unsupported")
    # r=Wv/Mdry, whereas the older column helper integrates specific humidity.
    return m*r


def equilibrate_liquid(temperature_k, vapor_kg_m2, dry_mass_kg_m2, pressure_pa,
                       liquid_kg_m2=0.):
    """Find vapor/liquid equilibrium without losing water or inventing heat.

For vapor change x, Tnew=Told-Lv*x/(cp*Md), liquid_new=liquid_old-x.
The saturation equation is strictly increasing in x, so a bracketed solution
is unique. All liquid evaporates if that remains undersaturated. Initial
supersaturation condenses even with no incoming liquid. Incoming rain may
evaporate only as far as the cooling-adjusted saturation state permits.
"""
    t,w,m,p,l = np.broadcast_arrays(*[np.asarray(a,float) for a in
        [temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa,liquid_kg_m2]])
    if (not all(np.isfinite(a).all() for a in [t,w,m,p,l]) or np.any(m<=0)
            or np.any(w<0) or np.any(l<0) or np.any((t<180)|(t>330))
            or np.any((p<10000)|(p>110000)) or np.any(w/m>.2)):
        raise ValueError("Need terrestrial180–330K,10–110kPa, positive dry mass and nonnegative dilute water")
    saturation_vapor_mass(t,m,p)
    alpha = LV/(CP*m)
    # Bounds preserve water exactly; thermal bounds avoid extrapolating the
    # liquid saturation formula outside its supported diagnostic domain.
    lo = np.maximum(-w,(t-370.)/alpha)
    hi = np.minimum(l,(t-150.)/alpha)
    def residual(x):
        return w+x-m*_saturation(t-alpha*x,p)
    flo,fhi = residual(lo),residual(hi)
    if np.any(flo>1e-12) or np.any((fhi<0)&(hi<l)):
        raise ValueError("Phase equilibrium lies outside150–370K")
    all_evaporates = (fhi<=0)&(hi==l)
    for _ in range(64):
        mid = .5*(lo+hi)
        positive = residual(mid)>0
        hi = np.where(positive,mid,hi)
        lo = np.where(positive,lo,mid)
    change = np.where(all_evaporates,l,.5*(lo+hi))
    new_t,new_w,new_l = t-alpha*change,w+change,l-change
    heat = -LV*change
    # Use actual state differences, not the algebraically identical assigned
    # heat, to expose floating-point conservation errors independently.
    energy_error = CP*m*(new_t-t)+LV*(new_w-w)
    water_error = new_w+new_l-w-l
    roundoff = 100*np.finfo(float).eps*CP*m*np.maximum(t,new_t)
    if (not all(np.isfinite(a).all() for a in [new_t,new_w,new_l]) or np.any(new_w<0)
            or np.any(new_l<0) or np.any(np.abs(energy_error)>roundoff)):
        raise RuntimeError("Liquid phase adjustment failed its physical bounds or enthalpy check")
    sat = saturation_vapor_mass(new_t,m,p)
    scale = np.maximum(sat,1e-12)
    excess = float(np.max(np.maximum(new_w-sat,0)/scale))
    equilibrium = float(np.max(np.where(new_l>1e-12,np.abs(new_w-sat)/scale,0)))
    if max(excess,equilibrium)>1e-9:
        raise RuntimeError("Phase equilibrium failed its actual saturation check")
    certificate = dict(maximum_water_residual_kg_m2=float(np.abs(water_error).max()),
        maximum_dilute_enthalpy_residual_j_m2=float(np.abs(energy_error).max()),
        maximum_saturation_excess_fraction=excess,maximum_liquid_equilibrium_error_fraction=equilibrium,
        scope="Liquid-only fixed-pressure dilute cp*Md*T+Lv*Wv adjustment; no ice or liquid/vapor heat capacity")
    return PhaseState(new_t,new_w,new_l,np.maximum(-change,0),np.maximum(change,0),heat,certificate)


def falling_rain_column(temperature_k, vapor_kg_m2, dry_mass_kg_m2, pressure_pa):
    """Two well-mixed layers, lower first; upper condensate falls into lower.

Upper condensate warms above. Rain then evaporates into and cools unsaturated
lower air, or lower supersaturation produces more rain. All surviving liquid
leaves the ground. There is no finite fall time, cloud storage, ice or convection.
"""
    t,w,m,p = [np.asarray(a,float) for a in
               [temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa]]
    if (t.ndim<1 or t.shape[0]!=2 or any(a.shape!=t.shape for a in [w,m,p])
            or not np.all(p[0]>p[1])):
        raise ValueError("Need matching lower/upper two-layer arrays with descending representative pressures")
    upper = equilibrate_liquid(t[1],w[1],m[1],p[1])
    lower = equilibrate_liquid(t[0],w[0],m[0],p[0],upper.liquid_kg_m2)
    new_t = np.stack([lower.temperature_k,upper.temperature_k])
    new_w = np.stack([lower.vapor_kg_m2,upper.vapor_kg_m2])
    condensation = np.stack([lower.condensed_kg_m2,upper.condensed_kg_m2])
    evaporation = np.stack([lower.evaporated_kg_m2,upper.evaporated_kg_m2])
    heat = np.stack([lower.sensible_heat_j_m2,upper.sensible_heat_j_m2])
    rain = lower.liquid_kg_m2
    water_error = w.sum(axis=0)-new_w.sum(axis=0)-rain
    energy_error = np.sum(CP*m*(new_t-t)+LV*(new_w-w),axis=0)
    cert = dict(maximum_column_water_residual_kg_m2=float(np.abs(water_error).max()),
        maximum_column_dilute_enthalpy_residual_j_m2=float(np.abs(energy_error).max()),
        maximum_heat_minus_net_rain_latent_residual_j_m2=float(np.abs(heat.sum(axis=0)-LV*rain).max()),
        lower=lower.certificate,upper=upper.certificate,
        scope="Isolated two-layer instantaneous liquid rain/reevaporation; no convective transport or climate coupling")
    return RainColumn(new_t,new_w,rain,condensation,evaporation,heat,cert)
