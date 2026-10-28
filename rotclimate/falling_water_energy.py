"""Phase/rain step including vapor potential energy and local fall dissipation.

Liquid-only, fixed levels/pressure, instantaneous terminal fall. All released
gravitational potential becomes local air heat; precipitation kinetic storage
and surface impact are neglected. This composes with moist-static-energy
transport without silently losing falling-water energy.
"""
from dataclasses import dataclass
import numpy as np

from .column_thermodynamics import CP,G,LV
from .moist_enthalpy import CP_VAPOR,CP_LIQUID,REFERENCE_K,gas_enthalpy,liquid_enthalpy
from .phase_adjustment import _saturation


@dataclass
class FallingWaterState:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    condensation_kg_m2: np.ndarray
    evaporation_kg_m2: np.ndarray
    fall_dissipation_j_m2: np.ndarray
    certificate: dict


def _equilibrium(t,w,m,p,l,liquid_t,*,extra_heat,feedback_per_vapor_change):
    """Solve Hfinal=Hinitial+extra_heat-beta*x, x=change in vapor.

Upper beta encodes heat released by newly produced falling condensate;
lower extra/beta encodes heat from incoming rain and its surviving descent.
Rain liquid and air end in equilibrium at a common temperature.
"""
    initial=gas_enthalpy(t,w,m)+liquid_enthalpy(liquid_t,l)
    capacity=CP*m+CP_VAPOR*w+CP_LIQUID*l
    dc=CP_VAPOR-CP_LIQUID;beta=feedback_per_vapor_change
    def temperature(x):
        return REFERENCE_K+(initial+extra_heat-LV*w-(LV+beta)*x)/(capacity+dc*x)
    def x_at(target):
        d=target-REFERENCE_K
        return (initial+extra_heat-LV*w-capacity*d)/(LV+beta+dc*d)
    lo=np.maximum(-w,x_at(370.));hi=np.minimum(l,x_at(150.))
    def residual(x):return w+x-m*_saturation(temperature(x),p)
    flo,fhi=residual(lo),residual(hi)
    if np.any(flo>1e-12) or np.any((fhi<0)&(hi<l)):
        raise ValueError('Falling-water equilibrium lies outside150–370K')
    all_evaporates=(fhi<=0)&(hi==l)
    for _ in range(64):
        mid=.5*(lo+hi);positive=residual(mid)>0
        hi=np.where(positive,mid,hi);lo=np.where(positive,lo,mid)
    x=np.where(all_evaporates,l,.5*(lo+hi));new_t=temperature(x)
    vapor,liquid=w+x,l-x
    final=gas_enthalpy(new_t,vapor,m)+liquid_enthalpy(new_t,liquid)
    budget=final-initial-extra_heat+beta*x
    scale=np.abs(initial)+capacity*REFERENCE_K+np.abs(extra_heat)
    if np.any(np.abs(budget)>200*np.finfo(float).eps*np.maximum(scale,1.)):
        raise RuntimeError('Falling-water phase enthalpy/root feedback budget failed')
    sat=m*_saturation(new_t,p);den=np.maximum(sat,1e-12)
    error=np.maximum(np.maximum(vapor-sat,0),np.where(liquid>1e-12,np.abs(vapor-sat),0))/den
    if (not all(np.isfinite(a).all() for a in [new_t,vapor,liquid]) or np.any(vapor<0)
            or np.any(liquid<0) or np.any(error>1e-9)):
        raise RuntimeError('Falling-water phase positivity/saturation failed')
    return new_t,vapor,liquid,x,float(np.abs(budget).max())


def adjust_falling_water(temperature_k,vapor_kg_m2,layer_mass_kg_m2,pressure_pa,
                         height_m,interface_height_m):
    """Conserve gas moist static energy plus exported rain sensible energy.

Box heights are ordered0<=zlower<zinterface<zupper. Condensate drops from
zupper to zlower. Uniform drag per fall distance deposits fraction
(zupper-zinterface)/(zupper-zlower) in upper air and the remainder below.
Surviving rain drops from zlower to ground0, depositing that energy below.
Upper dissipation feeds back on condensation; lower dissipation feeds back on
evaporation/survival. Ground rain leaves with its actual lower temperature.
"""
    t,w,m,p,z=[np.asarray(a,float) for a in
                [temperature_k,vapor_kg_m2,layer_mass_kg_m2,pressure_pa,height_m]]
    if t.ndim<1 or t.shape[0]!=2 or any(a.shape!=t.shape for a in [w,m,p,z]):
        raise ValueError('Need matching lower/upper T,water,mass,pressure,height')
    interface=np.broadcast_to(np.asarray(interface_height_m,float),t.shape[1:])
    if (not all(np.isfinite(a).all() for a in [t,w,m,p,z,interface]) or np.any(m<=0)
            or np.any(w<0) or np.any(w/m>.2) or np.any((t<180)|(t>330))
            or np.any((p<10000)|(p>110000)) or np.any(p[0]<=p[1])
            or np.any(z[0]<0) or np.any(interface<=z[0]) or np.any(interface>=z[1])
            or not np.isfinite(_saturation(t,p)).all()):
        raise ValueError('Need terrestrial dilute states and lower<interface<upper heights above ground')
    drop=z[1]-z[0];fraction=(z[1]-interface)/drop
    tu,wu,condensed,xu,erru=_equilibrium(t[1],w[1],m[1],p[1],np.zeros_like(w[1]),t[1],
        extra_heat=np.zeros_like(w[1]),feedback_per_vapor_change=fraction*G*drop)
    # Incoming rain supplies sensible enthalpy AND dissipated gravitational
    # energy. Additional surviving descent is g*zlower*(incoming-xlower).
    constant=((1-fraction)*G*drop+G*z[0])*condensed
    tl,wl,rain,xl,errl=_equilibrium(t[0],w[0],m[0],p[0],condensed,tu,
        extra_heat=constant,feedback_per_vapor_change=G*z[0])
    new_t,new_w=np.stack([tl,tu]),np.stack([wl,wu])
    heat_upper=fraction*G*drop*condensed
    heat_lower=(1-fraction)*G*drop*condensed+G*z[0]*rain
    dissipation=np.stack([heat_lower,heat_upper]);rain_h=liquid_enthalpy(tl,rain)
    before=gas_enthalpy(t,w,m)+G*(m+w)*z
    after=gas_enthalpy(new_t,new_w,m)+G*(m+new_w)*z
    water_error=w.sum(0)-new_w.sum(0)-rain
    energy_error=after.sum(0)+rain_h-before.sum(0)
    release=G*(condensed*drop+rain*z[0])
    if np.any(np.abs(energy_error)>400*np.finfo(float).eps*np.maximum(np.abs(before).sum(0)+CP*m.sum(0)*REFERENCE_K,1.)):
        raise RuntimeError('Gas static energy plus ground precipitation enthalpy failed')
    cert=dict(maximum_column_water_residual_kg_m2=float(np.abs(water_error).max()),
        maximum_static_energy_plus_rain_residual_j_m2=float(np.abs(energy_error).max()),
        maximum_fall_heat_minus_potential_release_residual_j_m2=float(np.abs(dissipation.sum(0)-release).max()),
        maximum_upper_phase_feedback_residual_j_m2=erru,maximum_lower_phase_feedback_residual_j_m2=errl,
        scope='Liquid-only instantaneous terminal fall with uniform drag heating per distance; no precipitation kinetic storage, ice or prognostic momentum')
    return FallingWaterState(new_t,new_w,rain,rain_h,np.stack([np.maximum(-xl,0),np.maximum(-xu,0)]),
                             np.stack([np.maximum(xl,0),np.maximum(xu,0)]),dissipation,cert)
