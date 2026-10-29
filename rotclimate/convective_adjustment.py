"""Experimental conservative adjacent-layer convective adjustment.

Dry-unstable pairs, or near-saturated lower cells whose saturated parcel is
warmer than the upper cell, mix vapor and redistribute heat toward a neutral
parcel lapse. Each pair retains water/gas enthalpy. Actual liquid phase then
exports rain enthalpy. This instantaneous local closure omits entrainment,
convective momentum transport and explicit turbulent kinetic energy.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import CP,RD,LV
from .moist_enthalpy import CP_VAPOR,REFERENCE_K
from .phase_adjustment import saturation_vapor_mass
from .pressure_moist import enthalpy_phase,gas_energy,PressureMoistState
from .parcel_stability import _saturated_derivative
from .multilevel_transport import _field


def _saturated_lift(t,lower_pressure,upper_pressure):
    value=np.asarray(t,float).copy();start,end=np.log(lower_pressure),np.log(upper_pressure)
    count=max(1,int(np.ceil((start-end)/.04)));h=(end-start)/count
    for j in range(count):
        x=start+j*h;k1=_saturated_derivative(value,x);k2=_saturated_derivative(value+.5*h*k1,x+.5*h)
        k3=_saturated_derivative(value+.5*h*k2,x+.5*h);k4=_saturated_derivative(value+h*k3,x+h)
        value+=h*(k1+2*k2+2*k3+k4)/6
    return value


def _flags(t,w,m,p,tolerance):
    q=w/m;dry=t[:-1]*(p[1:]/p[:-1]).reshape((-1,)+(1,)*(t.ndim-1))**(RD/(CP+CP_VAPOR*q[:-1]))
    saturation=saturation_vapor_mass(t[:-1],m[:-1],p[:-1].reshape((-1,)+(1,)*(t.ndim-1)))
    near_saturated=w[:-1]>=saturation*(1-1e-8)
    flags=dry>t[1:]+tolerance
    for k in range(len(p)-1):
        if np.any(near_saturated[k]):flags[k]|=near_saturated[k]&(_saturated_lift(t[k],p[k],p[k+1])>t[k+1]+tolerance)
    return flags


@dataclass
class ConvectiveAdjustment:
    temperature_k: np.ndarray
    vapor_kg_m2: np.ndarray
    ground_rain_kg_m2: np.ndarray
    ground_rain_enthalpy_j_m2: np.ndarray
    certificate: dict


def adjust_convection(temperature_k,vapor_kg_m2,cell_mass_kg_m2,pressure_pa,*,neutral_tolerance_k=.01,max_sweeps=64):
    t,w,m=map(lambda a:np.asarray(a,float),[temperature_k,vapor_kg_m2,cell_mass_kg_m2]);p=np.asarray(pressure_pa,float)
    if (t.ndim<1 or len(t)<2 or w.shape!=t.shape or m.shape!=t.shape or p.shape!=(len(t),)
            or not all(np.isfinite(a).all() for a in [t,w,m,p]) or np.any((t<180)|(t>330))
            or np.any(m<=0) or np.any((w<0)|(w/m>.2)) or np.any(np.diff(p)>=0)
            or np.any((p<10000)|(p>110000)) or not np.isfinite(neutral_tolerance_k) or neutral_tolerance_k<=0
            or not isinstance(max_sweeps,int) or max_sweeps<1):raise ValueError('Need supported thermal states, descending pressures and positive adjustment controls')
    before=gas_energy(t,w,m);water0=w.sum(0);pp=np.broadcast_to(p.reshape((-1,)+(1,)*(t.ndim-1)),t.shape)
    t,w,rain,rain_h=enthalpy_phase(t,w,m,pp);t=t.copy();w=w.copy();rain=rain.copy();rain_h=rain_h.copy()
    pair_count=0;max_pair_error=0.;sweeps=0
    for sweep in range(1,max_sweeps+1):
        moved=False
        for k in range(len(p)-1):
            q0=w[k]/m[k];sat=saturation_vapor_mass(t[k],m[k],p[k]);wet=w[k]>=sat*(1-1e-8)
            dry_ratio=(p[k+1]/p[k])**(RD/(CP+CP_VAPOR*q0));dry_unstable=t[k]*dry_ratio>t[k+1]+neutral_tolerance_k
            wet_unstable=wet&(_saturated_lift(t[k],p[k],p[k+1])>t[k+1]+neutral_tolerance_k) if np.any(wet) else np.zeros_like(wet)
            active=dry_unstable|wet_unstable
            if not np.any(active):continue
            moved=True;pair_count+=int(np.count_nonzero(active))
            old_energy=gas_energy(t[k],w[k],m[k])+gas_energy(t[k+1],w[k+1],m[k+1])
            qbar=(w[k]+w[k+1])/(m[k]+m[k+1]);capacity=CP+CP_VAPOR*qbar
            sensible=(CP*m[k]+CP_VAPOR*w[k])*t[k]+(CP*m[k+1]+CP_VAPOR*w[k+1])*t[k+1]
            ratio=(p[k+1]/p[k])**(RD/capacity);lower=sensible/(capacity*(m[k]+m[k+1]*ratio))
            for _ in range(8):
                if np.any(wet_unstable):ratio=np.where(wet_unstable,_saturated_lift(lower,p[k],p[k+1])/lower,ratio)
                updated=sensible/(capacity*(m[k]+m[k+1]*ratio))
                if np.max(abs(updated[active]-lower[active]))<1e-9:lower=updated;break
                lower=updated
            upper=(sensible/capacity-m[k]*lower)/m[k+1]
            t[k]=np.where(active,lower,t[k]);t[k+1]=np.where(active,upper,t[k+1])
            w[k]=np.where(active,m[k]*qbar,w[k]);w[k+1]=np.where(active,m[k+1]*qbar,w[k+1])
            actual=gas_energy(t[k],w[k],m[k])+gas_energy(t[k+1],w[k+1],m[k+1])
            max_pair_error=max(max_pair_error,float(np.max(abs(actual-old_energy))))
        sweeps=sweep
        if moved:
            t,w,new_rain,new_h=enthalpy_phase(t,w,m,pp);rain+=new_rain;rain_h+=new_h
        remaining=_flags(t,w,m,p,neutral_tolerance_k)
        if not np.any(remaining):break
    converged=not bool(np.any(remaining));after=gas_energy(t,w,m)
    energy_error=after.sum(0)+rain_h-before.sum(0);water_error=w.sum(0)+rain-water0
    relative=float(np.max(abs(energy_error))/max(float(np.max(np.sum(abs(before),axis=0))),1.))
    water_relative=float(np.max(abs(water_error))/max(float(np.max(water0)),1.))
    if max(relative,water_relative)>1e-11:raise RuntimeError('Convective mixing/phase actual water/enthalpy budget failed')
    if np.any((t<180)|(t>330)) or np.any(w<0):raise ValueError('Adjustment leaves supported state')
    return ConvectiveAdjustment(t,w,rain,rain_h,dict(converged=converged,sweeps=sweeps,adjusted_pairs=pair_count,
        remaining_active_interfaces=int(np.count_nonzero(remaining)),neutral_tolerance_k=neutral_tolerance_k,
        maximum_pair_gas_enthalpy_error_j_m2=max_pair_error,maximum_column_energy_rain_error_j_m2=float(np.max(abs(energy_error))),
        maximum_column_water_rain_error_kg_m2=float(np.max(abs(water_error))),relative_column_energy_error=relative,
        relative_column_water_error=water_relative,
        scope='Instantaneous adjacent mixing: dry instability or saturated conditional instability, common vapor ratio and neutral parcel lapse, conservative liquid phase. No entrainment, convective momentum or explicit turbulence energy.'))


def advance_with_convection(model,state,dt_s,*,neutral_tolerance_k=.01,max_sweeps=64,relaxation_s=0.,**kwargs):
    """First-order split dynamics/transport/phase then conservative adjustment.

    The nested dynamical certificate applies before the adjustment. Final
    pressure responds on the next timestep; no final midpoint claim is made.
    """
    if not np.isfinite(relaxation_s) or relaxation_s<0:raise ValueError('Need finite nonnegative convective relaxation time')
    dynamic=model.advance(state,dt_s,**kwargs)
    closure=adjust_convection(dynamic.temperature_k,dynamic.vapor_kg_m2,model.mass,model.column.centers_pa,
        neutral_tolerance_k=neutral_tolerance_k,max_sweeps=max_sweeps)
    if not closure.certificate['converged']:raise RuntimeError('Convective adjustment did not converge; no step accepted')
    fraction=1. if relaxation_s==0 else float(-np.expm1(-dt_s/relaxation_s))
    if fraction==1.:
        final_t,final_w=closure.temperature_k,closure.vapor_kg_m2;extra_rain=closure.ground_rain_kg_m2;extra_h=closure.ground_rain_enthalpy_j_m2
    else:
        # Relax water and gas enthalpy, not temperature. The target's actual
        # exported rain is included in the same convex budget. Homogenizing
        # this mixture can change saturation, so book its phase explicitly.
        final_w=dynamic.vapor_kg_m2+fraction*(closure.vapor_kg_m2-dynamic.vapor_kg_m2)
        h0=gas_energy(dynamic.temperature_k,dynamic.vapor_kg_m2,model.mass)
        h1=gas_energy(closure.temperature_k,closure.vapor_kg_m2,model.mass)
        mixed_h=h0+fraction*(h1-h0)
        mixed_t=(mixed_h-(LV-CP_VAPOR*REFERENCE_K)*final_w)/(CP*model.mass+CP_VAPOR*final_w)
        final_t,final_w,mixed_rain,mixed_rain_h=enthalpy_phase(mixed_t,final_w,model.mass,model.pressure)
        extra_rain=fraction*closure.ground_rain_kg_m2+mixed_rain;extra_h=fraction*closure.ground_rain_enthalpy_j_m2+mixed_rain_h
    rain=dynamic.ground_rain_kg_m2+extra_rain;rain_h=dynamic.ground_rain_enthalpy_j_m2+extra_h
    face_mass=model.mass[:,0,0,None,None]
    kinetic=lambda s:.5*(np.sum(face_mass*s.u_east[:,:,1:-1]**2)+np.sum(face_mass*s.v_south[:,1:-1]**2))
    old=gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+kinetic(state)
    new=gas_energy(final_t,final_w,model.mass).sum()+kinetic(dynamic)
    energy_error=float(new+rain_h.sum()-old-dt_s*dynamic.certificate['external_power_w_m2']*model.n)
    evap=_field(kwargs.get('evaporation_kg_m2_s',0.),model.mass.shape,'water source',minimum=0.)
    water_error=float(final_w.sum()+rain.sum()-state.vapor_kg_m2.sum()-dt_s*evap.sum())
    if abs(energy_error)>2000*np.finfo(float).eps*max(abs(old),1.) or abs(water_error)>1e-9*max(float(state.vapor_kg_m2.sum()),1.):
        raise RuntimeError('Split coupled convection actual total budget failed')
    cert=dict(dynamics_before_adjustment=dynamic.certificate,convective_adjustment=closure.certificate,
        relaxation_s=relaxation_s,adjusted_fraction=fraction,
        actual_remaining_active_interfaces=int(np.count_nonzero(_flags(final_t,final_w,model.mass,model.column.centers_pa,neutral_tolerance_k))),
        actual_combined_energy_rain_source_residual_j_m2=energy_error/model.n,
        actual_combined_water_rain_source_residual_kg_m2=water_error/model.n,
        gas_enthalpy_plus_kinetic_energy_j_m2=float(new/model.n),kinetic_energy_j_m2=float(kinetic(dynamic)/model.n),
        scope='First-order split repeated pressure-coordinate dynamics and conservative local convective adjustment; final pressure responds next step, no Earth adoption')
    return PressureMoistState(final_t,final_w,dynamic.u_east,dynamic.v_south,rain,rain_h,cert)
