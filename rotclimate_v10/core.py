"""Conservative two-layer, kinematically forced atmospheric water prototype.

Dry-air masses are fixed. The column flux must be divergence-free; an upper
return flow and diagnosed vertical flux balance the lower flow cell by cell.
Water is a mixing ratio transported by those SAME dry-air fluxes. Temperature
is prescribed, not predicted. All water stores and external fluxes are counted.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

DAY = 86400.
MONTH_DAYS = np.array([31,28,31,30,31,30,31,31,30,31,30,31])
EDGES = np.r_[0,np.cumsum(MONTH_DAYS)] * DAY
CENTERS = (np.cumsum(MONTH_DAYS) - .5*MONTH_DAYS) * DAY


@dataclass(frozen=True)
class Config:
    lower_fraction: float = .25
    cfl: float = .6
    max_step_s: float = 3600.
    forcing_interval_s: float = 10800.
    lower_temperature_offset_c: float = -3.
    upper_temperature_offset_c: float = -35.
    lower_pressure_fraction: float = .875
    upper_pressure_fraction: float = .375
    ocean_boundary_rh: float = .8
    land_boundary_rh: float = .4
    upper_boundary_rh: float = .2
    initial_lower_rh: float = .6
    soil_capacity_mm: float = 150.
    initial_soil_fraction: float = .5
    ocean_evap_max_mm_day: float = 5.
    land_pet_mm_day: float = 3.
    bulk_exchange_coefficient: float = .0012
    gust_ms: float = 2.
    background_wind_ms: float = 6.
    storm_rate_month: float = 4.
    storm_seasonality: float = .75
    storm_rotation_ms: float = 12.
    storm_convergence_ms: float = 1.
    storm_radius_km: float = 350.
    storm_lifetime_days: float = 2.
    storm_translation_ms: float = 7.
    winter_track_lat: float = 37.
    summer_track_lat: float = 47.
    terrain_drag_height_m: float = 1800.
    seed: int = 41
    rotation_sign: int = 1

    def validate(self):
        values = vars(self)
        if not all(np.isfinite(v) for v in values.values()):
            raise ValueError('All configuration values must be finite.')
        if not 0 < self.lower_fraction < 1 or not 0 < self.cfl < 1:
            raise ValueError('Layer fraction and CFL must lie strictly between zero and one.')
        positive = ('max_step_s','forcing_interval_s','soil_capacity_mm','terrain_drag_height_m',
                    'storm_radius_km','storm_lifetime_days','lower_pressure_fraction','upper_pressure_fraction')
        if any(values[k] <= 0 for k in positive) or self.rotation_sign not in (-1,1):
            raise ValueError('Invalid physical scale or rotation sign.')
        if not 0 <= self.storm_seasonality <= 1 or not 0 <= self.initial_soil_fraction <= 1:
            raise ValueError('Invalid seasonal contrast or initial soil fraction.')
        for key in ('ocean_boundary_rh','land_boundary_rh','upper_boundary_rh','initial_lower_rh'):
            if not 0 <= values[key] <= 1:
                raise ValueError('Relative humidities must be between zero and one.')
        for key in ('ocean_evap_max_mm_day','land_pet_mm_day','bulk_exchange_coefficient','gust_ms',
                    'background_wind_ms','storm_rate_month','storm_rotation_ms','storm_convergence_ms','storm_translation_ms'):
            if values[key] < 0:
                raise ValueError('Rates and speed magnitudes must be nonnegative.')


@dataclass
class Domain:
    name: str
    land: np.ndarray
    elevation_m: np.ndarray
    latitude: np.ndarray
    temperature_c: np.ndarray  # twelve observed/prescribed surface-temperature fields
    dx: float
    dy: float

    def validate(self):
        shape = self.land.shape
        if len(shape) != 2 or min(shape) < 2 or self.land.dtype != bool:
            raise ValueError('Need a two-dimensional Boolean land mask with at least two cells per axis.')
        if self.temperature_c.shape != (12,)+shape or self.elevation_m.shape != shape or self.latitude.shape != shape:
            raise ValueError('Incompatible domain fields.')
        if self.dx <= 0 or self.dy <= 0 or not np.isfinite([self.dx,self.dy]).all():
            raise ValueError('Cell dimensions must be finite and positive.')
        if not all(np.isfinite(a).all() for a in (self.temperature_c,self.elevation_m,self.latitude)):
            raise ValueError('Forcing must be finite; prepare missing data explicitly.')
        if (self.latitude <= 0).any() or (self.latitude >= 90).any():
            raise ValueError('This pilot supports Northern Hemisphere regional domains only.')


@dataclass
class State:
    lower: np.ndarray  # kg water/m2 = mm
    upper: np.ndarray
    soil: np.ndarray

    def copy(self):
        return State(*(a.copy() for a in (self.lower,self.upper,self.soil)))


@dataclass
class AirFlow:
    lower_x: np.ndarray  # kg dry air / (m s) on vertical faces
    lower_y: np.ndarray  # map-down positive, on horizontal faces
    upper_x: np.ndarray
    upper_y: np.ndarray
    vertical: np.ndarray  # lower -> upper, kg dry air/(m2 s)
    continuity_error: float


def divergence(fx,fy,dx,dy):
    return np.diff(fx,axis=-1)/dx + np.diff(fy,axis=-2)/dy


def balanced_flow(lower_x,lower_y,column_x,column_y,dx,dy):
    """Diagnose an upper return and vertical flow from a divergence-free column."""
    arrays = [np.asarray(a,float) for a in (lower_x,lower_y,column_x,column_y)]
    lx,ly,cx,cy = arrays
    if lx.shape != cx.shape or ly.shape != cy.shape or lx.shape[0]+1 != ly.shape[0] or lx.shape[1] != ly.shape[1]+1:
        raise ValueError('Incompatible dry-air face fields.')
    if dx <= 0 or dy <= 0 or not all(np.isfinite(a).all() for a in arrays):
        raise ValueError('Invalid face fields or spacing.')
    error = float(abs(divergence(cx,cy,dx,dy)).max())
    if error > 1e-10:
        raise ValueError(f'Column dry-air continuity failed: {error:g} kg/m2/s.')
    return AirFlow(lx,ly,cx-lx,cy-ly,-divergence(lx,ly,dx,dy),error)


def saturation_ratio(temperature,pressure):
    """Saturation water/dry-air mixing ratio, not specific humidity."""
    t = np.clip(temperature,-80.,50.)
    es = 611.2*np.exp(17.67*t/(t+243.5))
    return .622*es/np.maximum(np.asarray(pressure)-es,100.)


def air_masses(domain,config):
    ps = 101325.*np.exp(-np.maximum(domain.elevation_m,-400.)/8400.)
    total = ps/9.80665
    return total*config.lower_fraction,total*(1-config.lower_fraction),ps


def interpolate_months(values,time_s):
    t = time_s % (365*DAY)
    centers = np.r_[CENTERS[-1]-365*DAY,CENTERS,CENTERS[0]+365*DAY]
    k = int(np.searchsorted(centers,t,side='right')-1)
    f = (t-centers[k])/(centers[k+1]-centers[k])
    return (1-f)*values[(k-1)%12] + f*values[k%12]


def capacities(domain,config,time_s):
    ml,mu,ps = air_masses(domain,config)
    t = interpolate_months(domain.temperature_c,time_s)
    ql = saturation_ratio(t+config.lower_temperature_offset_c,ps*config.lower_pressure_fraction)
    qu = saturation_ratio(t+config.upper_temperature_offset_c,ps*config.upper_pressure_fraction)
    return ml*ql,mu*qu,t,ps


def initial_state(domain,config):
    domain.validate();config.validate()
    wl,wu,_,_ = capacities(domain,config,0.)
    return State(wl*config.initial_lower_rh,wu*config.upper_boundary_rh,
                 np.where(domain.land,config.soil_capacity_mm*config.initial_soil_fraction,0.))


def tracer_flux(water,mass,fx,fy,boundary_q):
    q = water/mass
    x,y = np.empty_like(fx),np.empty_like(fy)
    x[:,1:-1] = fx[:,1:-1]*np.where(fx[:,1:-1]>=0,q[:,:-1],q[:,1:])
    y[1:-1,:] = fy[1:-1,:]*np.where(fy[1:-1,:]>=0,q[:-1,:],q[1:,:])
    x[:,0] = fx[:,0]*np.where(fx[:,0]>=0,boundary_q[:,0],q[:,0])
    x[:,-1] = fx[:,-1]*np.where(fx[:,-1]>=0,q[:,-1],boundary_q[:,-1])
    y[0,:] = fy[0,:]*np.where(fy[0,:]>=0,boundary_q[0,:],q[0,:])
    y[-1,:] = fy[-1,:]*np.where(fy[-1,:]>=0,q[-1,:],boundary_q[-1,:])
    return x,y


def outgoing(fx,fy,vertical,dx,dy):
    return ((np.maximum(fx[:,1:],0)+np.maximum(-fx[:,:-1],0))/dx
            +(np.maximum(fy[1:,:],0)+np.maximum(-fy[:-1,:],0))/dy+np.maximum(vertical,0))


def stable_step(flow,ml,mu,dx,dy,config):
    rate = max(float((outgoing(flow.lower_x,flow.lower_y,flow.vertical,dx,dy)/ml).max()),
               float((outgoing(flow.upper_x,flow.upper_y,-flow.vertical,dx,dy)/mu).max()))
    return min(config.max_step_s,config.cfl/rate) if rate > 0 else config.max_step_s


def advance(state,domain,config,flow,dt,time_s,physics=True):
    """One positivity-limited donor-cell step; return state, rain and budget.

    Budget units are domain-mean mm. Boundary export is positive outward.
    Combined inventory = atmospheric vapour + land soil water.
    """
    ml,mu,_ = air_masses(domain,config)
    if not np.isfinite(dt) or dt <= 0 or dt > stable_step(flow,ml,mu,domain.dx,domain.dy,config)*(1+1e-12):
        raise ValueError('Step exceeds the declared positivity/CFL limit.')
    for a in (state.lower,state.upper,state.soil):
        if a.shape != domain.land.shape or not np.isfinite(a).all() or a.min() < 0:
            raise ValueError('Invalid water store.')
    capl,capu,t,ps = capacities(domain,config,time_s)
    bql = capl/ml*np.where(domain.land,config.land_boundary_rh,config.ocean_boundary_rh)
    bqu = capu/mu*config.upper_boundary_rh
    fx,fy = tracer_flux(state.lower,ml,flow.lower_x,flow.lower_y,bql)
    ux,uy = tracer_flux(state.upper,mu,flow.upper_x,flow.upper_y,bqu)
    vertical = flow.vertical*np.where(flow.vertical>=0,state.lower/ml,state.upper/mu)
    lower = state.lower-dt*(divergence(fx,fy,domain.dx,domain.dy)+vertical)
    upper = state.upper-dt*(divergence(ux,uy,domain.dx,domain.dy)-vertical)
    boundary = float((divergence(fx+ux,fy+uy,domain.dx,domain.dy)*dt).mean())
    if min(float(lower.min()),float(upper.min())) < -1e-11:
        raise FloatingPointError('Conservative transport produced a negative water store.')
    correction = float((-np.minimum(lower,0)-np.minimum(upper,0)).mean())
    lower,upper = np.maximum(lower,0),np.maximum(upper,0)
    soil = state.soil.copy()
    ocean_evap = np.zeros_like(lower);land_evap = np.zeros_like(lower)
    rain = np.zeros_like(lower);runoff = np.zeros_like(lower)
    if physics:
        # Cell-centred lower wind inferred from the dry-air flux on each face.
        speed = np.sqrt((.5*(flow.lower_x[:,1:]+flow.lower_x[:,:-1])/ml)**2
                        +(.5*(flow.lower_y[1:,:]+flow.lower_y[:-1,:])/ml)**2+config.gust_ms**2)
        deficit = np.maximum(saturation_ratio(t,ps)-lower/ml,0)
        ocean_evap = np.where(~domain.land,np.minimum(1.2*config.bulk_exchange_coefficient*speed*deficit*dt,
                              config.ocean_evap_max_mm_day*dt/DAY),0.)
        winter = np.cos(2*np.pi*(time_s/DAY-15)/365.)
        demand = config.land_pet_mm_day*(1-.5*winter)*np.clip((t+5)/25,0,1)*dt/DAY
        demand *= soil/config.soil_capacity_mm*np.clip(1-lower/np.maximum(capl,1e-12),0,1)
        land_evap = np.where(domain.land,np.minimum(soil,demand),0.)
        soil -= land_evap
        lower += ocean_evap+land_evap
        pl,pu = np.maximum(lower-capl,0),np.maximum(upper-capu,0)
        lower -= pl;upper -= pu;rain = pl+pu
        soil += np.where(domain.land,rain,0.)
        runoff = np.maximum(soil-config.soil_capacity_mm,0.)
        soil -= runoff
    new = State(lower,upper,soil)
    inventory = float((lower+upper+soil-state.lower-state.upper-state.soil).mean())
    ocean_rain = float(np.where(~domain.land,rain,0.).mean())
    budget = dict(inventory_change_mm=inventory,ocean_evaporation_mm=float(ocean_evap.mean()),
                  land_evaporation_mm=float(land_evap.mean()),rain_mm=float(rain.mean()),
                  ocean_rain_mm=ocean_rain,runoff_mm=float(runoff.mean()),boundary_export_mm=boundary,
                  roundoff_correction_mm=correction,air_continuity_max_kg_m2_s=flow.continuity_error)
    budget['water_error_mm'] = inventory-(budget['ocean_evaporation_mm']-ocean_rain-budget['runoff_mm']-boundary+correction)
    if not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm']) > 1e-9:
        raise FloatingPointError('Water budget failed.')
    return new,rain,budget
