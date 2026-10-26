"""Pressure-integrated terrestrial saturation columns, with explicit profiles.

No observed rain or location coefficients. This is a diagnostic thermal-profile
closure, not prognostic convection, radiation or latent-heat feedback. Liquid
Bolton vapor pressure, constant cp/Lv and dry ideal-gas thermodynamics are used.
Water above100hPa is omitted; its dry air remains in the upper mass fraction.
"""
from dataclasses import dataclass
import numpy as np

G=9.80665
RD=287.05
CP=1004.
LV=2.5e6
EPSILON=.622
TOP_PRESSURE_PA=10000.
TROPOPAUSE_K=200.


@dataclass
class SaturationColumn:
    water_mm: np.ndarray  # lower/upper, then input shape; kg/m² = mm
    air_mass_kg_m2: np.ndarray  # full column mass; upper includes dry air above100hPa
    interface_temperature_k: np.ndarray  # surface,0.75ps,100hPa

    @property
    def total_mm(self):return self.water_mm.sum(0)

    @property
    def lower_water_fraction(self):return self.water_mm[0]/self.total_mm

    @property
    def upper_lower_q_ratio(self):
        q=self.water_mm/self.air_mass_kg_m2
        return q[1]/q[0]


def specific_saturation(temperature_k,pressure_pa):
    t,p=np.broadcast_arrays(np.asarray(temperature_k,float),np.asarray(pressure_pa,float))
    if (not np.isfinite(t).all() or not np.isfinite(p).all() or (p<=0).any()
            or (t<150).any() or (t>370).any()):raise ValueError('Need finite150–370K temperatures and positive pressures')
    c=t-273.15;es=611.2*np.exp(17.67*c/(c+243.5))
    if (es>=.95*p).any():raise ValueError('Near-boiling saturation column is unsupported')
    return EPSILON*es/(p-(1-EPSILON)*es)


def saturation_column(temperature_c,surface_pressure_pa,*,profile='moist',lapse_k_km=6.,steps=64):
    """Integrate q_sat dp/g using RK4 in log pressure in each air layer.

    Lower dry-air fraction is0.25; the remaining0.75 includes negligible-water
    stratospheric air above100hPa. A200K isothermal stratosphere is a prescribed
    Earth-like boundary assumption (surface colder than this stays isothermal).
    ``moist`` uses the saturated pseudoadiabatic dry-gas approximation;
    ``lapse`` follows the given environmental lapse with hydrostatic pressure;
    ``isothermal`` is an analytic verification limit, not a model option.
    Surface pressure follows the caller's mass basis; this helper does not fit
    altitude, boundary humidity or planetary parameters.
    """
    ts,ps=np.broadcast_arrays(np.asarray(temperature_c,float)+273.15,np.asarray(surface_pressure_pa,float))
    edges=np.stack([ps,.75*ps,np.full_like(ps,TOP_PRESSURE_PA)])
    water,temperatures=integrate_saturation_profile(temperature_c,ps,edges,
        profile=profile,lapse_k_km=lapse_k_km,steps=steps)
    return SaturationColumn(water,np.stack([.25*ps/G,.75*ps/G]),temperatures)


def integrate_saturation_profile(temperature_c,surface_pressure_pa,pressure_edges_pa,*,profile='moist',lapse_k_km=6.,steps=64):
    """Integrate arbitrary descending pressure intervals, starting at surface.

    Returns water per interval and temperature at interfaces. This supports
    reference comparisons over exactly matched pressure ranges without
    extrapolating below-ground or beyond the observed humidity column.
    """
    ts,ps=np.broadcast_arrays(np.asarray(temperature_c,float)+273.15,np.asarray(surface_pressure_pa,float))
    if (not np.isfinite(ts).all() or not np.isfinite(ps).all() or (ts<170).any() or (ts>330).any()
            or (ps<40000).any() or (ps>110000).any()):raise ValueError('Need terrestrial170–330K surfaces and40–110kPa pressure')
    pressure_edges=np.asarray(pressure_edges_pa,float)
    if (pressure_edges.ndim!=ps.ndim+1 or pressure_edges.shape[1:]!=ps.shape or pressure_edges.shape[0]<2
            or not np.isfinite(pressure_edges).all() or (pressure_edges<10000).any()
            or not np.array_equal(pressure_edges[0],ps) or not (np.diff(pressure_edges,axis=0)<0).all()):
        raise ValueError('Pressure edges must descend from the matched surface to at least100hPa')
    if profile not in ('moist','lapse','isothermal'):raise ValueError('Unknown column thermal profile')
    if (not np.isfinite(lapse_k_km) or not 0<lapse_k_km<=10
            or not isinstance(steps,int) or isinstance(steps,bool) or steps<8):raise ValueError('Need positive lapse<=10K/km and at least8 RK4 steps per layer')
    specific_saturation(ts,ps)
    floor=np.minimum(ts,TROPOPAUSE_K);temperature=ts.copy();water=[];interfaces=[ts.copy()]
    def derivative(x,t):
        pressure=ps*np.exp(-x);t=np.maximum(t,floor)
        q=specific_saturation(t,pressure)
        if profile=='isothermal':cooling=np.zeros_like(t)
        elif profile=='lapse':cooling=RD*(lapse_k_km/1000)/G*t
        else:
            r=q/(1-q)
            cooling=RD/CP*t*(1+LV*r/(RD*t))/(1+LV*LV*r*EPSILON/(CP*RD*t*t))
        cooling=np.where(t>floor,cooling,0.)
        return -cooling,q*pressure/G
    edges=np.log(ps[None]/pressure_edges)
    for start,end in zip(edges[:-1],edges[1:]):
        h=(end-start)/steps;amount=np.zeros_like(ps)
        for i in range(steps):
            x=start+i*h
            k1,w1=derivative(x,temperature)
            k2,w2=derivative(x+h/2,temperature+h*k1/2)
            k3,w3=derivative(x+h/2,temperature+h*k2/2)
            k4,w4=derivative(x+h,temperature+h*k3)
            temperature=np.maximum(temperature+h*(k1+2*k2+2*k3+k4)/6,floor)
            amount+=h*(w1+2*w2+2*w3+w4)/6
        water.append(amount);interfaces.append(temperature.copy())
    water=np.stack(water)
    if not np.isfinite(water).all() or (water<=0).any():raise FloatingPointError('Invalid pressure-integrated saturation column')
    return water,np.stack(interfaces)
