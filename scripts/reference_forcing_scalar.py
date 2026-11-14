"""Independent Decimal reference using caller-supplied world radiation."""
from decimal import Decimal,localcontext


def supplied_radiation_reference(tmean,tmin,tmax,ea,u2,pressure,solar,ra,elevation):
    with localcontext() as context:
        context.prec=40
        D=lambda x:Decimal(str(x))
        t,lo,hi,vap,wind,p,rs,radiation,z=map(D,[tmean,tmin,tmax,ea,u2,pressure,solar,ra,elevation])
        def saturation(temp):return D('.6108')*(D('17.27')*temp/(temp+D('237.3'))).exp()
        es=(saturation(lo)+saturation(hi))/2
        delta=4098*saturation(t)/(t+D('237.3'))**2;gamma=D('.000665')*p
        rso=(D('.75')+D('.00002')*z)*radiation
        ratio=rs/rso;bounded=max(D('.3'),min(D(1),ratio))
        rns=D('.77')*rs
        rnl=D('4.903e-9')*((hi+D('273.16'))**4+(lo+D('273.16'))**4)/2*(D('.34')-D('.14')*vap.sqrt())*(D('1.35')*bounded-D('.35'))
        rn=rns-rnl;divisor=delta+gamma*(1+D('.34')*wind)
        radiative=D('.408')*delta*rn/divisor
        aerodynamic=gamma*900/(t+273)*wind*(es-vap)/divisor
        raw=radiative+aerodynamic
        har=D('.0023')*max(t+D('17.8'),D(0))*(hi-lo).sqrt()*D('.408')*radiation
        return {key:float(value) for key,value in dict(ra_mj_m2_day=radiation,rso_mj_m2_day=rso,rs_ratio_raw=ratio,rs_ratio_used=bounded,rns_mj_m2_day=rns,rnl_mj_m2_day=rnl,rn_mj_m2_day=rn,es_kpa=es,ea_kpa=vap,vpd_kpa=es-vap,delta_kpa_c=delta,gamma_kpa_c=gamma,pm_radiation_mm_day=radiative,pm_aerodynamic_mm_day=aerodynamic,pm_raw_mm_day=raw,pm_mm_day=max(raw,D(0)),hargreaves_mm_day=har).items()}
