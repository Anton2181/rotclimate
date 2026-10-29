"""Safeguarded liquid-enthalpy root for the pressure-coordinate prototype.

The same liquid-only equilibrium, no gravity feedback or extra heat. Clear
all-evaporated cells need no root search. Saturated cells use an analytic
Newton derivative inside the original bracket, with the frozen bisection
solver as a fallback. This module is not yet an adopted dynamical backend.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import CP,LV,EPSILON
from .moist_enthalpy import CP_VAPOR,CP_LIQUID,REFERENCE_K,gas_enthalpy,liquid_enthalpy
from .phase_adjustment import _saturation
from .falling_water_energy import _equilibrium


@dataclass
class LiquidEquilibrium:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    liquid_kg_m2: np.ndarray
    vapor_change_kg_m2: np.ndarray
    certificate: dict


def equilibrium_enthalpy(temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa,liquid_kg_m2=0.,liquid_temperature_k=None,*,maximum_newton_iterations=32):
    if not isinstance(maximum_newton_iterations,int) or isinstance(maximum_newton_iterations,bool) or maximum_newton_iterations<0:raise ValueError('Need a nonnegative Newton iteration budget; zero uses reference fallback')
    if liquid_temperature_k is None:liquid_temperature_k=temperature_k
    t,w,m,p,l,tl=np.broadcast_arrays(*[np.asarray(a,float) for a in [temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa,liquid_kg_m2,liquid_temperature_k]])
    if (not all(np.isfinite(a).all() for a in [t,w,m,p,l,tl]) or np.any(m<=0) or np.any((w<0)|(l<0)|(w/m>.2))
            or np.any((t<180)|(t>330)|(tl<150)|(tl>370)|(p<10000)|(p>110000))):raise ValueError('Need supported dry/dilute liquid equilibrium inputs')
    initial=gas_enthalpy(t,w,m)+liquid_enthalpy(tl,l);capacity=CP*m+CP_VAPOR*w+CP_LIQUID*l;dc=CP_VAPOR-CP_LIQUID
    def temperature(x):return REFERENCE_K+(initial-LV*w-LV*x)/(capacity+dc*x)
    def x_at(target):
        d=target-REFERENCE_K
        return (initial-LV*w-capacity*d)/(LV+dc*d)
    lo=np.maximum(-w,x_at(370.));hi=np.minimum(l,x_at(150.))
    flo=w+lo-m*_saturation(temperature(lo),p);fhi=w+hi-m*_saturation(temperature(hi),p)
    if np.any(flo>1e-12) or np.any((fhi<0)&(hi<l)):raise ValueError('Liquid equilibrium lies outside150–370K')
    clear=(fhi<=0)&(hi==l);active=np.flatnonzero(~clear.ravel());x=l.copy();iterations=0;fallback=np.array([],dtype=int)
    if len(active):
        ww,mm,pp,ll,tt,ttl,hh,cc=[a.ravel()[active] for a in [w,m,p,l,t,tl,initial,capacity]]
        low,high=lo.ravel()[active].copy(),hi.ravel()[active].copy();root=high.copy();done=np.zeros(len(root),bool)
        derivative_numerator=-LV*cc-dc*(hh-LV*ww)
        for iterations in range(1,maximum_newton_iterations+1):
            den=cc+dc*root;temp=REFERENCE_K+(hh-LV*ww-LV*root)/den
            es=611.2*np.exp(17.67*(temp-273.15)/(temp-29.65));valid=es<pp
            qs=np.divide(EPSILON*es,pp-es,out=np.full_like(es,np.inf),where=valid);sat=mm*qs;f=ww+root-sat
            # Infinite near-boiling saturation is only a bracket limit;
            # inf <= inf must never mark a saturated root as solved.
            done|=np.isfinite(f)&np.isfinite(sat)&(abs(f)<=1e-12*np.maximum(sat,1e-12))
            if np.all(done):break
            positive=f>0;high=np.where(~done&positive,root,high);low=np.where(~done&~positive,root,low)
            des=es*(17.67*243.5)/(temp-29.65)**2
            dqs=np.divide(EPSILON*pp*des,(pp-es)**2,out=np.full_like(es,np.inf),where=valid)
            derivative=1-mm*dqs*derivative_numerator/den**2
            correction=np.divide(f,derivative,out=np.zeros_like(f),where=np.isfinite(f)&np.isfinite(derivative)&(derivative>0))
            proposal=root-correction
            allowed=np.isfinite(f)&np.isfinite(proposal)&(proposal>low)&(proposal<high)
            proposal=np.where(allowed,proposal,.5*(low+high));root=np.where(done,root,proposal)
        if not np.all(done):
            fallback=active[~done]
            old=_equilibrium(t.ravel()[fallback],w.ravel()[fallback],m.ravel()[fallback],p.ravel()[fallback],l.ravel()[fallback],tl.ravel()[fallback],extra_heat=0.,feedback_per_vapor_change=0.)
            root[~done]=old[3]
        x.flat[active]=root
    new_t,new_w,new_l=[np.array(a,copy=True) for a in [temperature(x),w+x,l-x]]
    # Preserve the trusted fallback's exact rounded state, rather than
    # recomputing it through a differently shaped vector expression.
    if len(fallback):new_t.flat[fallback]=old[0];new_w.flat[fallback]=old[1];new_l.flat[fallback]=old[2]
    final=gas_enthalpy(new_t,new_w,m)+liquid_enthalpy(new_t,new_l);budget=final-initial
    scale=abs(initial)+capacity*REFERENCE_K
    if np.any(abs(budget)>200*np.finfo(float).eps*np.maximum(scale,1.)):raise RuntimeError('Fast liquid phase actual enthalpy budget failed')
    sat=m*_saturation(new_t,p);error=np.maximum(np.maximum(new_w-sat,0),np.where(new_l>1e-12,abs(new_w-sat),0))/np.maximum(sat,1e-12)
    if not all(np.isfinite(a).all() for a in [new_t,new_w,new_l,error]) or np.any(new_w<0) or np.any(new_l<0) or np.any(error>1e-9):raise RuntimeError('Fast liquid phase positivity/saturation failed')
    return LiquidEquilibrium(new_t,new_w,new_l,x,dict(cells=t.size,root_cells=len(active),all_evaporated_cells=int(clear.sum()),maximum_newton_iterations=iterations,
        bisection_fallback_cells=len(fallback),maximum_actual_enthalpy_residual_j_m2=float(abs(budget).max()),maximum_saturation_error_fraction=float(error.max()),
        scope='Same fixed-pressure enthalpy liquid equilibrium; no extra/gravity heat. Safeguarded Newton within original bracket, trusted bisection fallback; physical checks unchanged.'))


def enthalpy_phase_fast(temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa):
    """Same top-down enthalpy-only rain interface as the frozen prototype."""
    t,w,m,p=np.broadcast_arrays(*[np.asarray(a,float) for a in [temperature_k,vapor_kg_m2,dry_mass_kg_m2,pressure_pa]])
    if t.ndim<1 or len(t)<1:raise ValueError('Need a vertical pressure-cell axis')
    nt,nw=np.empty_like(t),np.empty_like(w);incoming=np.zeros_like(t[0]);liquid_t=t[-1]
    for k in range(len(t)-1,-1,-1):
        r=equilibrium_enthalpy(t[k],w[k],m[k],p[k],incoming,liquid_t);nt[k]=r.temperature_k;nw[k]=r.vapor_kg_m2;incoming=r.liquid_kg_m2;liquid_t=nt[k]
    return nt,nw,incoming,liquid_enthalpy(nt[0],incoming)
