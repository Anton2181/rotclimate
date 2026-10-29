"""Explicit conservative radiation and neutral surface-exchange interfaces.

These are flux kernels, not tuned Earth radiation, a coupled surface model or
an implicit full-atmosphere boundary. Opacities, incoming top radiation,
surface state and roughness must be declared by the caller.
"""
import numpy as np
from .column_thermodynamics import CP,RD,LV,EPSILON
from .moist_enthalpy import CP_VAPOR,CP_LIQUID,REFERENCE_K

STEFAN_BOLTZMANN=5.670374419e-8


def _broadcast(value,shape,name,minimum=None,maximum=None):
    a=np.asarray(value,float)
    if a.ndim==1 and len(shape)>1 and a.shape[0]==shape[0]:a=a.reshape((len(a),)+(1,)*(len(shape)-1))
    try:a=np.broadcast_to(a,shape).copy()
    except ValueError as exc:raise ValueError('Need matching '+name) from exc
    if not np.isfinite(a).all() or (minimum is not None and np.any(a<minimum)) or (maximum is not None and np.any(a>maximum)):
        raise ValueError('Invalid '+name)
    return a


def two_stream_radiation(temperature_k,surface_temperature_k,longwave_optical_depth,shortwave_optical_depth,*,
                         solar_in_w_m2=0.,longwave_in_w_m2=0.,surface_albedo=.2,surface_emissivity=1.):
    """Pure absorption/emission two-stream fluxes, cell0 nearest the surface.

    Longwave emissivity equals absorptivity; surface longwave reflection is
    1-emissivity. Shortwave has surface reflection, two-way atmospheric
    absorption and no thermal emission/scattering. Optical depths are effective
    stream optical depths (a beam-path factor must be supplied by the caller).
    The top is the caller's declared boundary, not automatically the TOA.
    """
    t=np.asarray(temperature_k,float)
    if t.ndim<1 or len(t)<1 or not np.isfinite(t).all() or np.any((t<150)|(t>350)):raise ValueError('Need terrestrial layer temperatures')
    shape=t.shape[1:];ts=_broadcast(surface_temperature_k,shape,'surface temperature',150,350)
    tau_lw=_broadcast(longwave_optical_depth,t.shape,'longwave depth',0);tau_sw=_broadcast(shortwave_optical_depth,t.shape,'shortwave depth',0)
    solar=_broadcast(solar_in_w_m2,shape,'incoming solar',0);top_lw=_broadcast(longwave_in_w_m2,shape,'incoming longwave',0)
    albedo=_broadcast(surface_albedo,shape,'albedo',0,1);emissivity=_broadcast(surface_emissivity,shape,'surface emissivity',0,1)
    transmission=np.exp(-tau_lw);absorption=-np.expm1(-tau_lw);emission=absorption*STEFAN_BOLTZMANN*t**4
    down=np.empty((len(t)+1,)+shape);up=np.empty_like(down);down[-1]=top_lw
    for k in range(len(t)-1,-1,-1):down[k]=transmission[k]*down[k+1]+emission[k]
    up[0]=emissivity*STEFAN_BOLTZMANN*ts**4+(1-emissivity)*down[0]
    for k in range(len(t)):up[k+1]=transmission[k]*up[k]+emission[k]
    longwave_heat=-np.diff(up-down,axis=0);surface_lw=down[0]-up[0]
    sw_t=np.exp(-tau_sw);sw_down=np.empty_like(down);sw_up=np.empty_like(up);sw_down[-1]=solar
    for k in range(len(t)-1,-1,-1):sw_down[k]=sw_t[k]*sw_down[k+1]
    sw_up[0]=albedo*sw_down[0]
    for k in range(len(t)):sw_up[k+1]=sw_t[k]*sw_up[k]
    shortwave_heat=np.diff(sw_down-sw_up,axis=0);surface_sw=sw_down[0]-sw_up[0]
    atmospheric=longwave_heat+shortwave_heat;surface=surface_lw+surface_sw
    top=top_lw-up[-1]+solar-sw_up[-1];error=atmospheric.sum(0)+surface-top
    scale=np.maximum(abs(atmospheric).sum(0)+abs(surface)+abs(top),1.)
    if np.any(abs(error)>200*np.finfo(float).eps*scale):raise RuntimeError('Actual column radiation flux budget failed')
    return dict(atmospheric_heating_w_m2=atmospheric,surface_heating_w_m2=surface,net_top_incoming_w_m2=top,
        atmospheric_longwave_heating_w_m2=longwave_heat,atmospheric_shortwave_heating_w_m2=shortwave_heat,
        surface_longwave_heating_w_m2=surface_lw,surface_shortwave_heating_w_m2=surface_sw,
        longwave_up_w_m2=up,longwave_down_w_m2=down,shortwave_up_w_m2=sw_up,shortwave_down_w_m2=sw_down,
        maximum_actual_energy_residual_w_m2=float(abs(error).max()),
        scope='Declared grey stream depths, Kirchhoff emission and surface reflection; no spectral/cloud/scattering physics, automatic opacity fit or TOA assumption.')


def bulk_surface_exchange(surface_temperature_k,air_temperature_k,air_mixing_ratio,surface_pressure_pa,reference_pressure_pa,
                          wind_speed_ms,reference_height_m,roughness_m,*,scalar_roughness_m=None,water_availability=1.,von_karman=.4):
    """Neutral log-law fluxes, positive upward; dew remains signed and visible.

    Air temperature is dry-adiabatically referred to surface pressure before
    the neutral potential-temperature difference is evaluated. This is not
    a stable/unstable Monin-Obukhov correction. Caller supplies actual reference
    height and roughness, avoiding a10m coefficient applied to a deep cell.
    Water availability limits evaporation only; it does not suppress dew.
    """
    if scalar_roughness_m is None:scalar_roughness_m=roughness_m
    try:ts,ta,q,ps,pa,speed,z,z0m,z0h,wet=np.broadcast_arrays(*[np.asarray(a,float) for a in [surface_temperature_k,air_temperature_k,air_mixing_ratio,surface_pressure_pa,reference_pressure_pa,wind_speed_ms,reference_height_m,roughness_m,scalar_roughness_m,water_availability]])
    except ValueError as exc:raise ValueError('Need matching surface-exchange fields') from exc
    if (not all(np.isfinite(a).all() for a in [ts,ta,q,ps,pa,speed,z,z0m,z0h,wet]) or not np.isfinite(von_karman) or von_karman<=0
            or np.any((ts<180)|(ts>330)|(ta<180)|(ta>330)|(q<0)|(q>.2)|(ps<50000)|(ps>110000)|(pa<=0)|(pa>ps)
                |(speed<0)|(z0m<=0)|(z0h<=0)|(z<=z0m)|(z<=z0h)|(wet<0)|(wet>1))):raise ValueError('Invalid terrestrial neutral-exchange input')
    air_surface=ta*(ps/pa)**(RD/CP)
    if np.any((air_surface<180)|(air_surface>350)):raise ValueError('Dry-referred air temperature outside supported domain')
    es=611.2*np.exp(17.67*(ts-273.15)/(ts-29.65))
    if np.any(es>=ps):raise ValueError('Surface saturation pressure exceeds air pressure')
    qsat=EPSILON*es/(ps-es);eair=q*ps/(EPSILON+q);dry_density=(ps-eair)/(RD*air_surface)
    coefficient=von_karman**2/(np.log(z/z0m)*np.log(z/z0h))
    conductance=dry_density*coefficient*speed
    raw_vapor=conductance*(qsat-q);vapor=np.where(raw_vapor>0,wet*raw_vapor,raw_vapor)
    sensible=conductance*(CP+CP_VAPOR*q)*(ts-air_surface)
    # Vapor uses the donor temperature. Condensing vapor comes from the air,
    # while evaporating vapor leaves the surface liquid reservoir.
    donor_t=np.where(vapor>=0,ts,air_surface)
    hv=LV+CP_VAPOR*(donor_t-REFERENCE_K);hl=CP_LIQUID*(ts-REFERENCE_K)
    return dict(vapor_flux_kg_m2_s=vapor,sensible_heat_w_m2=sensible,vapor_enthalpy_flux_w_m2=vapor*hv,
        phase_heat_flux_w_m2=vapor*(hv-hl),liquid_enthalpy_transport_w_m2=vapor*hl,
        air_referred_to_surface_k=air_surface,vapor_donor_temperature_k=donor_t,exchange_coefficient=coefficient,
        scope='Neutral bulk exchange, explicit reference pressure/height/roughness; liquid saturation only, signed dew, no stability/gust closure, no state integration or Earth calibration.')
