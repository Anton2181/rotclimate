"""Daily FAO56 grass-reference evaporation, with explicit radiation units.

This is a reference calculation, not measured evapotranspiration. It does not
select a crop coefficient or change the atlas's existing evaporation forcing.
"""
import numpy as np


def _arrays(*values):
    arrays=np.broadcast_arrays(*[np.asarray(v,dtype=float) for v in values])
    if not all(np.isfinite(v).all() for v in arrays):
        raise ValueError('Finite reference-weather inputs required')
    return arrays


def saturation_vapour_pressure(temperature_c):
    t,=_arrays(temperature_c)
    if np.any((t<=-237.3)|(t>100)):
        raise ValueError('Temperature outside saturation-pressure domain')
    return .6108*np.exp(17.27*t/(t+237.3))


def pressure_at_elevation(elevation_m):
    z,=_arrays(elevation_m)
    if np.any((z<-500)|(z>10000)):
        raise ValueError('Terrestrial reference elevation required')
    return 101.3*((293-.0065*z)/293)**5.26


def wind_at_2m(wind_ms,height_m):
    wind,height=_arrays(wind_ms,height_m)
    if np.any(wind<0) or np.any((height<.1)|(height>100)):
        raise ValueError('Nonnegative wind and height in 0.1..100 m required')
    return wind*4.87/np.log(67.8*height-5.42)


def extraterrestrial_radiation(latitude_deg,day_of_year):
    """FAO56 equations21–25; MJ/m²/day and hours, including distance factor."""
    latitude,day=_arrays(latitude_deg,day_of_year)
    if np.any(np.abs(latitude)>90) or np.any((day<1)|(day>366)|(day!=np.floor(day))):
        raise ValueError('Latitude within poles and Gregorian integer day 1..366 required')
    phi=np.deg2rad(latitude);angle=2*np.pi*day/365.
    distance=1+.033*np.cos(angle)
    declination=.409*np.sin(angle-1.39)
    sunset=np.arccos(np.clip(-np.tan(phi)*np.tan(declination),-1,1))
    radiation=24*60/np.pi*.0820*distance*(sunset*np.sin(phi)*np.sin(declination)+np.cos(phi)*np.cos(declination)*np.sin(sunset))
    return dict(ra_mj_m2_day=np.maximum(radiation,0.),daylight_hours=24/np.pi*sunset)


def penman_monteith(tmean_c,es_kpa,ea_kpa,wind2m_ms,pressure_kpa,net_radiation_mj_m2_day):
    """Equation6, grass reference, daily G=0; retain signed raw ETo."""
    t,es,ea,u,p,rn=_arrays(tmean_c,es_kpa,ea_kpa,wind2m_ms,pressure_kpa,net_radiation_mj_m2_day)
    saturation=saturation_vapour_pressure(t)
    if np.any((t<=-100)|(t>70)) or np.any(es<0) or np.any(ea<0) or np.any(ea>es+1e-10) or np.any(u<0) or np.any(p<=0):
        raise ValueError('Physical grass-reference weather required')
    delta=4098*saturation/(t+237.3)**2
    gamma=.000665*p
    denominator=delta+gamma*(1+.34*u)
    radiation=.408*delta*rn/denominator
    aerodynamic=gamma*900/(t+273)*u*(es-ea)/denominator
    raw=radiation+aerodynamic
    return dict(es_kpa=es,ea_kpa=ea,vpd_kpa=es-ea,delta_kpa_c=delta,gamma_kpa_c=gamma,pm_radiation_mm_day=radiation,pm_aerodynamic_mm_day=aerodynamic,pm_raw_mm_day=raw,pm_mm_day=np.maximum(raw,0.))


def daily_reference(tmean_c,tmin_c,tmax_c,ea_kpa,wind2m_ms,pressure_kpa,solar_mj_m2_day,latitude_deg,day_of_year,elevation_m):
    """Daily radiation and both reference methods on identical supplied weather.

    Cloudiness Rs/Rso is explicitly clipped to0.3..1 for the empirical longwave
    term. The unbounded ratio and raw signed ETo remain in the diagnostics.
    Polar-night longwave estimation is outside this component's supplied domain.
    """
    t,lo,hi,ea,u,p,rs,latitude,day,z=_arrays(tmean_c,tmin_c,tmax_c,ea_kpa,wind2m_ms,pressure_kpa,solar_mj_m2_day,latitude_deg,day_of_year,elevation_m)
    if np.any(lo>t) or np.any(t>hi) or np.any(rs<0):
        raise ValueError('Ordered temperatures and nonnegative daily radiation required')
    pressure_at_elevation(z)  # validate the Rso elevation domain; use supplied p below
    solar=extraterrestrial_radiation(latitude,day)
    ra=solar['ra_mj_m2_day'];rso=(.75+2e-5*z)*ra
    if np.any(rso<=0):
        raise ValueError('Positive clear-sky radiation required; no polar-night adapter')
    ratio=rs/rso;used=np.clip(ratio,.3,1.)
    if np.any(ea<0):raise ValueError('Nonnegative actual vapour pressure required')
    rns=.77*rs
    rnl=4.903e-9*((hi+273.16)**4+(lo+273.16)**4)/2*(.34-.14*np.sqrt(ea))*(1.35*used-.35)
    rn=rns-rnl
    es=(saturation_vapour_pressure(lo)+saturation_vapour_pressure(hi))/2
    pm=penman_monteith(t,es,ea,u,p,rn)
    hargreaves=.0023*np.maximum(t+17.8,0)*np.sqrt(hi-lo)*(.408*ra)
    return dict(**solar,rso_mj_m2_day=rso,rs_ratio_raw=ratio,rs_ratio_used=used,rns_mj_m2_day=rns,rnl_mj_m2_day=rnl,rn_mj_m2_day=rn,**pm,hargreaves_mm_day=hargreaves)
