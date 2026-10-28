"""Stable hydrostatic lapse-rate troposphere and explicit isothermal cap.

Density, potential temperature, N² and pressure-column depth are derived from
temperature structure and physical constants, not independent circulation
knobs. This is a prescribed dry reference, not convection or radiative balance.
"""
from dataclasses import dataclass
import numpy as np
from .column_thermodynamics import CP,G,RD


@dataclass
class LapseReference:
    height_m: np.ndarray
    temperature_k: np.ndarray
    pressure_pa: np.ndarray
    density_kg_m3: np.ndarray
    potential_temperature_k: np.ndarray
    stability_s2: np.ndarray
    tropopause_height_m: float


def _parameters(surface_temperature_k,surface_pressure_pa,lapse_k_m,tropopause_temperature_k,reference_pressure_pa):
    ts,ps,gamma,tp,pref=map(float,[surface_temperature_k,surface_pressure_pa,lapse_k_m,tropopause_temperature_k,reference_pressure_pa])
    if (not np.isfinite([ts,ps,gamma,tp,pref]).all() or not 180<=ts<=330
            or not 40000<=ps<=110000 or not 150<=tp<=ts or pref<=0
            or not 0<=gamma<G/CP):
        raise ValueError('Need terrestrial positive reference scales and sub-dry-adiabatic nonnegative lapse')
    return ts,ps,gamma,tp,pref


def lapse_reference(height_m,*,surface_temperature_k=300.,surface_pressure_pa=101325.,
                    lapse_k_m=.006,tropopause_temperature_k=200.,reference_pressure_pa=100000.):
    """T=Ts-Gamma*z below the explicit isothermal tropopause, hydrostatic p.

N²=g/T*(g/cp-Gamma) below the cap and g²/(cp*Tcap) above. The cap is a
declared reference structure; it does not clip a diagnosed unstable atmosphere.
Gamma>=g/cp is rejected. Gamma0 is the exact isothermal analytic limit.
"""
    ts,ps,gamma,tp,pref=_parameters(surface_temperature_k,surface_pressure_pa,lapse_k_m,tropopause_temperature_k,reference_pressure_pa)
    z=np.asarray(height_m,float)
    if not np.isfinite(z).all() or np.any(z<0):raise ValueError('Need finite nonnegative height')
    if gamma==0:
        temp=np.full_like(z,ts);pressure=ps*np.exp(-G*z/(RD*ts));n2=np.full_like(z,G*G/(CP*ts));zt=np.inf
    else:
        zt=(ts-tp)/gamma
        below=z<zt
        temp=np.where(below,ts-gamma*z,tp)
        logp_t=np.log(ps)+G/(RD*gamma)*np.log(tp/ts)
        logp=np.where(below,np.log(ps)+G/(RD*gamma)*np.log(temp/ts),logp_t-G*(z-zt)/(RD*tp))
        pressure=np.exp(logp)
        n2=G/temp*(G/CP-np.where(below,gamma,0.))
    density=pressure/(RD*temp);theta=temp*(pref/pressure)**(RD/CP)
    if not all(np.isfinite(a).all() for a in [temp,pressure,density,theta,n2]) or np.any(pressure<=0):
        raise ValueError('Reference height exceeds finite positive hydrostatic domain')
    return LapseReference(z.copy(),temp,pressure,density,theta,n2,float(zt))


def height_at_pressure(pressure_pa,*,surface_temperature_k=300.,surface_pressure_pa=101325.,
                        lapse_k_m=.006,tropopause_temperature_k=200.,reference_pressure_pa=100000.):
    """Analytic inverse hydrostatic pressure, including intervals above the cap."""
    ts,ps,gamma,tp,_=_parameters(surface_temperature_k,surface_pressure_pa,lapse_k_m,tropopause_temperature_k,reference_pressure_pa)
    p=np.asarray(pressure_pa,float)
    if not np.isfinite(p).all() or np.any((p<=0)|(p>ps)):raise ValueError('Need positive pressure at/below the reference surface pressure')
    if gamma==0:return -RD*ts/G*np.log(p/ps)
    zt=(ts-tp)/gamma;pt=ps*(tp/ts)**(G/(RD*gamma))
    temperature=ts*(p/ps)**(RD*gamma/G)
    return np.where(p>=pt,(ts-temperature)/gamma,zt-RD*tp/G*np.log(p/pt))
