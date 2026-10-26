"""Isolated liquid pseudoadiabatic parcel; never used as climate forcing.

Dry ideal-gas pressure work, constant dry cp and latent heat. Condensed water
leaves the parcel immediately. Use mixing ratio per kg DRY air for its water
ledger, rather than subtracting specific humidities on a changing wet mass.
No entrainment, ice, fallout evaporation, radiation or environmental heating.
"""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import brentq
from rotclimate.column_thermodynamics import RD,CP,LV,EPSILON,specific_saturation


def vapor_pressure(temperature_k):
    c=np.asarray(temperature_k,float)-273.15
    return 611.2*np.exp(17.67*c/(c+243.5))


def specific_from_relative_humidity(temperature_k,pressure_pa,rh):
    """RH means actual/saturated vapor pressure, not q/q_sat."""
    specific_saturation(temperature_k,pressure_pa)  # identical validity checks
    if not np.isfinite(rh) or not 0<=rh<=1:raise ValueError('Need relative humidity in[0,1]')
    e=rh*vapor_pressure(temperature_k)
    return EPSILON*e/(pressure_pa-(1-EPSILON)*e)


def moist_derivatives(temperature_k,pressure_pa):
    """dT/dx and dry-gas work per dx, x=log(p_initial/p).

    Differentiate the actual Bolton saturation law used by this model, so
    cp*dT + Rd*T*dx + Lv*dr =0 uses consistent thermodynamics. Replacing its
    derivative with a different constant-Lv vapor-pressure law would leave
    an avoidable first-law mismatch.
    """
    q=float(specific_saturation(temperature_k,pressure_pa));r=q/(1-q)
    c=temperature_k-273.15
    dlog_es_dt=17.67*243.5/(c+243.5)**2
    pressure_factor=r*(1+r/EPSILON)
    cooling=-(RD*temperature_k+LV*pressure_factor)/(CP+LV*pressure_factor*dlog_es_dt)
    return cooling,RD*temperature_k


@dataclass
class Parcel:
    pressure_pa: np.ndarray
    temperature_k: np.ndarray
    vapor_kg_kg_dry: np.ndarray
    condensed_kg_kg_dry: np.ndarray
    pressure_work_j_kg_dry: np.ndarray
    lcl_pressure_pa: float | None
    first_law_residual_j_kg_dry: np.ndarray


def ascend(temperature_k,pressure_pa,specific_humidity,end_pressure_pa,*,steps=256):
    """Lift one parcel dry to its LCL, then liquid pseudoadiabatically.

    The exact dry segment and root-located LCL avoid grid-dependent early
    condensation. RK4 integrates saturated temperature AND pressure work.
    Supported bounded research domain: terrestrial starts270–320K,40–110kPa,
    upward endpoint at least300hPa. No prescribed stratospheric temperature.
    """
    t,p,q,pe=map(float,(temperature_k,pressure_pa,specific_humidity,end_pressure_pa))
    if (not np.isfinite([t,p,q,pe]).all() or not 270<=t<=320 or not 40000<=p<=110000
            or not 30000<=pe<=p or not 0<=q<1 or not isinstance(steps,int)
            or isinstance(steps,bool) or steps<16):
        raise ValueError('Need a bounded terrestrial upward parcel and at least16steps')
    saturation=float(specific_saturation(t,p))
    if q>saturation:raise ValueError('Initial supersaturation is unsupported')
    r0=q/(1-q);end=np.log(p/pe);kappa=RD/CP
    def dry_saturation(x):
        qs=float(specific_saturation(t*np.exp(-kappa*x),p*np.exp(-x)))
        return qs/(1-qs)
    if q==0 or dry_saturation(end)>=r0:lcl=None
    elif q==saturation:lcl=0.
    else:lcl=brentq(lambda x:dry_saturation(x)-r0,0,end,xtol=1e-14)
    x=np.unique(np.r_[np.linspace(0,end,steps+1),[] if lcl is None else [lcl]])
    temperature=np.zeros(len(x));work=np.zeros(len(x));vapor=np.full(len(x),r0)
    temperature[0]=t
    for i in range(1,len(x)):
        a,b=x[i-1:i+1];h=b-a
        if lcl is None or b<=lcl:
            temperature[i]=t*np.exp(-kappa*b)
            work[i]=CP*(t-temperature[i])
        else:
            y=temperature[i-1]
            f=lambda xx,tt:moist_derivatives(tt,p*np.exp(-xx))
            k1,w1=f(a,y);k2,w2=f(a+h/2,y+h*k1/2)
            k3,w3=f(a+h/2,y+h*k2/2);k4,w4=f(b,y+h*k3)
            temperature[i]=y+h*(k1+2*k2+2*k3+k4)/6
            work[i]=work[i-1]+h*(w1+2*w2+2*w3+w4)/6
            qs=float(specific_saturation(temperature[i],p*np.exp(-b)))
            vapor[i]=qs/(1-qs)
    condensed=r0-vapor
    energy=CP*(temperature-t)+work+LV*(vapor-r0)
    if (not np.isfinite(energy).all() or (condensed < -1e-12).any()
            or (np.diff(vapor)>1e-12).any()):raise FloatingPointError('Invalid parcel water/energy path')
    return Parcel(p*np.exp(-x),temperature,vapor,condensed,work,
        None if lcl is None else float(p*np.exp(-lcl)),energy)
