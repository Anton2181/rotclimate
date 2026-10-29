"""Partial-column pseudoadiabatic parcel stability for the dry/dilute model.

Unsaturated ascent retains parcel vapor; saturated ascent removes liquid at
the actual temperature. The lapse uses the same temperature-dependent phase
enthalpies and liquid saturation curve as the model. Positive/negative
buoyancy integrals are partial-column diagnostics, not whole-atmosphere CAPE
or a convection closure. Virtual-temperature diagnostics are explicit opt-in.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import CP,RD,G,EPSILON,LV
from .moist_enthalpy import CP_VAPOR,CP_LIQUID,REFERENCE_K


def _saturation(t,p):
    es=611.2*np.exp(17.67*(t-273.15)/(t-29.65))
    if np.any(es>=.95*p):raise ValueError('Unsupported near-boiling parcel')
    r=EPSILON*es/(p-es)
    dr_dt=r*p/(p-es)*(17.67*243.5/(t-29.65)**2)
    dr_dlnp=-r*p/(p-es)
    return r,dr_dt,dr_dlnp


def _saturated_derivative(t,logp):
    p=np.exp(logp);sat,dr_dt,dr_dlnp=_saturation(t,p)
    latent=LV+(CP_VAPOR-CP_LIQUID)*(t-REFERENCE_K)
    return (RD*t-latent*dr_dlnp)/(CP+CP_VAPOR*sat+latent*dr_dt)


@dataclass
class ParcelProfile:
    temperature_k: np.ndarray
    vapor_mixing_ratio: np.ndarray
    lifting_condensation_pressure_pa: np.ndarray
    lcl_in_column: np.ndarray
    maximum_initial_roundoff_saturation_excess: float


def parcel_profile(pressure_pa,source_temperature_k,source_vapor_mixing_ratio,*,max_log_pressure_step=.01):
    p=np.asarray(pressure_pa,float);t,r=np.broadcast_arrays(np.asarray(source_temperature_k,float),np.asarray(source_vapor_mixing_ratio,float))
    if (p.ndim!=1 or len(p)<2 or not np.isfinite(p).all() or np.any(np.diff(p)>=0)
            or np.any((p<10000)|(p>110000)) or not np.isfinite(t).all() or not np.isfinite(r).all()
            or np.any((t<150)|(t>370)) or np.any((r<0)|(r>.2))
            or not np.isfinite(max_log_pressure_step) or max_log_pressure_step<=0):
        raise ValueError('Need descending terrestrial pressures and finite supported parcel state/step')
    t0=t.copy();sat=_saturation(t,p[0])[0];excess=np.maximum(r-sat,0.)
    if np.any(excess>1e-9*np.maximum(sat,1e-12)):raise ValueError('Phase-adjust supersaturated source before parcel diagnosis')
    r0=np.minimum(r,sat);out_t=[t.copy()];out_r=[r0.copy()]
    # Locate cloud base before integrating. Switching a nonsmooth dry/moist
    # derivative inside RK stages (even at a saturated source by roundoff)
    # produces a first-order temperature error. Split exactly at the LCL.
    exponent=RD/(CP+CP_VAPOR*r0)
    def lcl_residual(logp):return _saturation(t0*np.exp(exponent*(logp-np.log(p[0]))),np.exp(logp))[0]-r0
    in_column=lcl_residual(np.log(p[-1]))<=0
    lo=np.full(t0.shape,np.log(p[-1]));hi=np.full(t0.shape,np.log(p[0]))
    for _ in range(48):
        mid=.5*(lo+hi);positive=lcl_residual(mid)>0;hi=np.where(positive,mid,hi);lo=np.where(positive,lo,mid)
    loglcl=.5*(lo+hi);lcl=np.where(in_column,np.exp(loglcl),0.)
    for bottom,top in zip(p[:-1],p[1:]):
        start,end=np.log(bottom),np.log(top);steps=max(1,int(np.ceil((start-end)/max_log_pressure_step)));h=(end-start)/steps
        for j in range(steps):
            x=start+j*h;next_x=x+h;wet=in_column&(next_x<loglcl)
            wet_start=np.where(wet,np.minimum(x,loglcl),x)
            wet_t=np.where(wet&(x>=loglcl),t0*np.exp(exponent*(wet_start-np.log(p[0]))),t)
            hw=np.where(wet,next_x-wet_start,0.)
            k1=_saturated_derivative(wet_t,wet_start);k2=_saturated_derivative(wet_t+.5*hw*k1,wet_start+.5*hw)
            k3=_saturated_derivative(wet_t+.5*hw*k2,wet_start+.5*hw);k4=_saturated_derivative(wet_t+hw*k3,wet_start+hw)
            integrated=wet_t+hw*(k1+2*k2+2*k3+k4)/6
            t=np.where(wet,integrated,t0*np.exp(exponent*(next_x-np.log(p[0]))))
        if not np.isfinite(t).all() or np.any((t<150)|(t>370)):raise ValueError('Parcel leaves supported150–370K diagnostic domain')
        out_t.append(t.copy());out_r.append(np.minimum(r0,_saturation(t,top)[0]))
    return ParcelProfile(np.stack(out_t),np.stack(out_r),lcl,in_column,float(np.max(excess)))


def _positive_linear_integral(left,right,width):
    both=(left>=0)&(right>=0)
    same=.5*(left+right)*width
    a=np.where(left>0,left,0.);b=np.where(right>0,right,0.)
    crossing=np.divide(.5*(a*a+b*b),abs(right-left),out=np.zeros_like(a),where=(left*right<0))*width
    return np.where(both,same,np.where((left>0)|(right>0),crossing,0.))


@dataclass
class ParcelStability:
    pressure_pa: np.ndarray
    parcel: ParcelProfile
    buoyancy_ms2: np.ndarray
    positive_buoyancy_energy_j_kg: np.ndarray
    negative_buoyancy_energy_j_kg: np.ndarray
    certificate: dict


def diagnose_parcel(pressure_pa,environment_temperature_k,environment_vapor_mixing_ratio,*,source_index=0,
                    virtual_temperature=False,max_log_pressure_step=.01):
    p=np.asarray(pressure_pa,float);env=np.asarray(environment_temperature_k,float);r=np.asarray(environment_vapor_mixing_ratio,float)
    if (p.ndim!=1 or len(p)<2 or env.ndim<1 or env.shape[0]!=len(p) or r.shape!=env.shape or not np.isfinite(env).all()
            or not np.isfinite(r).all() or np.any((env<150)|(env>370)) or np.any((r<0)|(r>.2))
            or not isinstance(source_index,int) or isinstance(source_index,bool) or not 0<=source_index<len(p)-1):
        raise ValueError('Need matching environmental states and a source below the top cell')
    env,r,p=env[source_index:],r[source_index:],p[source_index:]
    # Resolve the unsaturated segment/LCL and sign crossings inside model
    # pressure cells. Using only coarse endpoints can miss inhibition entirely.
    sample_p=[p[0]];sample_t=[env[0]];sample_r=[r[0]]
    if not np.isfinite(max_log_pressure_step) or max_log_pressure_step<=0:raise ValueError('Need positive pressure integration step')
    if not np.isfinite(p).all() or np.any(np.diff(p)>=0):raise ValueError('Need descending finite pressures')
    for k in range(len(p)-1):
        count=max(1,int(np.ceil(np.log(p[k]/p[k+1])/max_log_pressure_step)))
        for j in range(1,count+1):
            fraction=j/count;sample_p.append(np.exp((1-fraction)*np.log(p[k])+fraction*np.log(p[k+1])))
            sample_t.append(np.exp((1-fraction)*np.log(env[k])+fraction*np.log(env[k+1])))
            sample_r.append((1-fraction)*r[k]+fraction*r[k+1])
    p,env,r=np.array(sample_p),np.stack(sample_t),np.stack(sample_r)
    parcel=parcel_profile(p,env[0],r[0],max_log_pressure_step=max_log_pressure_step)
    if virtual_temperature:
        observed=env*(1+r/EPSILON)/(1+r)
        predicted=parcel.temperature_k*(1+parcel.vapor_mixing_ratio/EPSILON)/(1+parcel.vapor_mixing_ratio)
    else:observed,predicted=env,parcel.temperature_k
    difference=predicted-observed;dx=np.log(p[:-1]/p[1:]).reshape((-1,)+(1,)*(env.ndim-1))
    positive=RD*np.sum(_positive_linear_integral(difference[:-1],difference[1:],dx),axis=0)
    negative=RD*np.sum(_positive_linear_integral(-difference[:-1],-difference[1:],dx),axis=0)
    return ParcelStability(p,parcel,G*difference/observed,positive,negative,
        dict(source_pressure_pa=float(p[0]),top_pressure_pa=float(p[-1]),source_index=source_index,
            virtual_temperature=bool(virtual_temperature),max_log_pressure_step=max_log_pressure_step,
            pressure_integration_samples=len(p),environment_interpolation='log T and linear mixing ratio in log pressure',
            scope='Lowest-selected-model-cell pseudoadiabatic parcel; positive and negative linear-segment buoyancy integrals over supplied partial pressure column. Not whole-atmosphere CAPE/CIN or a convection closure.'))
