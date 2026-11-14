"""Independent FAO56 scalar reference: stdlib solar angles and Decimal algebra.

Used by preflight/review, never by the weather producer or harvest component.
"""
from decimal import Decimal,localcontext
import math


def scalar_reference(tmean,tmin,tmax,ea,u2,pressure,solar,latitude,day,elevation):
    phi=math.radians(latitude);angle=2*math.pi*day/365
    declination=.409*math.sin(angle-1.39);distance=1+.033*math.cos(angle)
    sunset=math.acos(max(-1.,min(1.,-math.tan(phi)*math.tan(declination))))
    ra=max(0.,1440/math.pi*.0820*distance*(sunset*math.sin(phi)*math.sin(declination)+math.cos(phi)*math.cos(declination)*math.sin(sunset)))
    with localcontext() as context:
        context.prec=40
        D=lambda value:Decimal(str(value))
        t,lo,hi,vap,wind,p,rs,z=map(D,[tmean,tmin,tmax,ea,u2,pressure,solar,elevation])
        def saturation(temp):return D('.6108')*(D('17.27')*temp/(temp+D('237.3'))).exp()
        es=(saturation(lo)+saturation(hi))/2
        delta=D(4098)*saturation(t)/(t+D('237.3'))**2
        gamma=D('.000665')*p
        rso=(D('.75')+D('.00002')*z)*D(ra)
        ratio=rs/rso;used=max(D('.3'),min(D(1),ratio))
        rns=D('.77')*rs
        rnl=D('4.903e-9')*((hi+D('273.16'))**4+(lo+D('273.16'))**4)/2*(D('.34')-D('.14')*vap.sqrt())*(D('1.35')*used-D('.35'))
        rn=rns-rnl;denominator=delta+gamma*(1+D('.34')*wind)
        radiation=D('.408')*delta*rn/denominator
        aerodynamic=gamma*900/(t+273)*wind*(es-vap)/denominator
        raw=radiation+aerodynamic
        har=D('.0023')*max(t+D('17.8'),D(0))*(hi-lo).sqrt()*D('.408')*D(ra)
        result=dict(ra_mj_m2_day=ra,daylight_hours=24/math.pi*sunset,rso_mj_m2_day=rso,rs_ratio_raw=ratio,rs_ratio_used=used,rns_mj_m2_day=rns,rnl_mj_m2_day=rnl,rn_mj_m2_day=rn,es_kpa=es,ea_kpa=vap,vpd_kpa=es-vap,delta_kpa_c=delta,gamma_kpa_c=gamma,pm_radiation_mm_day=radiation,pm_aerodynamic_mm_day=aerodynamic,pm_raw_mm_day=raw,pm_mm_day=max(raw,D(0)),hargreaves_mm_day=har)
        return {name:float(value) for name,value in result.items()}


def dewpoint_pressure(dewpoint):
    with localcontext() as context:
        context.prec=40
        t=Decimal(str(dewpoint))
        return float(Decimal('.6108')*(Decimal('17.27')*t/(t+Decimal('237.3'))).exp())
