"""Water + approximate moist static energy in the frozen two-layer circulation.

Diagnostic closure, not a radiation/momentum model. h = cp*T_K + g*z + Lv*r
per kg dry air; water heat capacity, rain sensible enthalpy, ice and kinetic
energy are neglected. Geopotential heights use the frozen 8400 m scale height.
The same finite-volume dry-air fluxes transport both water and energy. Constant
Lv saturation adjustment converts latent to sensible energy internally.
"""
from __future__ import annotations
from dataclasses import dataclass,replace
import numpy as np

from rotclimate_v10.core import (Config,Domain,State,DAY,EDGES,advance as transport_water,
    air_masses,capacities,initial_state as initial_water,interpolate_months,stable_step,tracer_flux,divergence)
from rotclimate_v10.weather import catalogue,flow_at

CP = 1004.;LV = 2.5e6;G = 9.80665


@dataclass(frozen=True)
class Closure:
    relaxation_days: float = 5.
    terrain_drag: bool = True

    def validate(self):
        if not np.isfinite(self.relaxation_days) or self.relaxation_days<=0:
            raise ValueError('Temperature relaxation must be finite and positive.')


@dataclass
class ThermalState:
    water: State
    lower_energy: np.ndarray  # J/m², dry-air mass times approximate MSE
    upper_energy: np.ndarray


@dataclass
class ThermalYear:
    state: ThermalState
    rain_mm: np.ndarray
    lower_temperature_c: np.ndarray  # time-weighted monthly means
    upper_temperature_c: np.ndarray
    reference_temperature_c: np.ndarray
    budget: dict


def levels(domain,config):
    return (domain.elevation_m-8400.*np.log(config.lower_pressure_fraction),
            domain.elevation_m-8400.*np.log(config.upper_pressure_fraction))


def temperature(energy,mass,water,z):
    return (energy/mass-G*z-LV*water/mass)/CP-273.15


def saturation(t,pressure,derivative=False):
    """Liquid-water approximation; fail on unsupported states, never clip T."""
    if not np.isfinite(t).all() or np.min(t)<-123.15 or np.max(t)>96.85:
        raise FloatingPointError('Thermodynamic state outside supported 150–370 K range.')
    es = 611.2*np.exp(17.67*t/(t+243.5))
    # Near boiling is outside this regional pilot, not a hidden humidity cap.
    if (es>=.95*pressure).any():
        raise FloatingPointError('Near-boiling thermodynamic state; inspect the kinematic forcing.')
    qs = .622*es/(pressure-es)
    if not derivative:return qs
    des = es*17.67*243.5/(t+243.5)**2
    return qs,.622*pressure*des/(pressure-es)**2


def adjust(water,energy,mass,z,pressure):
    """Saturate while retaining latent heating; energy is unchanged by rain-out."""
    raw = temperature(energy,mass,water,z)
    q = water/mass;qs = saturation(raw,pressure)
    active = q>qs
    if not active.any():return water.copy(),np.zeros_like(water),raw
    # Solve in condensed mixing ratio. Bracket the latent warming, not a fixed T.
    lower = np.zeros_like(q);upper = q.copy();c = np.maximum(q-qs,0)/(1+LV/CP*saturation(raw,pressure,True)[1])
    converged = False
    for _ in range(32):
        t = raw+LV/CP*c
        sat,dsat = saturation(t,pressure,True)
        f = c+sat-q
        error = np.where(active,abs(f),0)
        if error.max()<1e-12:
            converged = True;break
        upper = np.where(active&(f>0),c,upper)
        lower = np.where(active&(f<=0),c,lower)
        newton = c-f/(1+LV/CP*dsat)
        c = np.where(active,np.where((newton>lower)&(newton<upper),newton,.5*(lower+upper)),0)
    if not converged:raise FloatingPointError('Energy-coupled saturation adjustment did not converge.')
    condensate = np.where(active,c*mass,0.)
    remaining = water-condensate
    final_t = temperature(energy,mass,remaining,z)
    if (remaining < -1e-12).any() or (remaining/mass-saturation(final_t,pressure)>2e-12).any():
        raise FloatingPointError('Invalid saturated water store.')
    return remaining,condensate,final_t


def initial_state(domain,config):
    water = initial_water(domain,config)
    ml,mu,_ = air_masses(domain,config);zl,zu = levels(domain,config)
    surface = interpolate_months(domain.temperature_c,0.)
    el = ml*(CP*(surface+config.lower_temperature_offset_c+273.15)+G*zl)+LV*water.lower
    eu = mu*(CP*(surface+config.upper_temperature_offset_c+273.15)+G*zu)+LV*water.upper
    return ThermalState(water,el,eu)


def boundary_energy(domain,config,time_s):
    ml,mu,ps = air_masses(domain,config);zl,zu = levels(domain,config)
    t = interpolate_months(domain.temperature_c,time_s)
    tl,tu = t+config.lower_temperature_offset_c,t+config.upper_temperature_offset_c
    ql = saturation(tl,ps*config.lower_pressure_fraction)*np.where(domain.land,config.land_boundary_rh,config.ocean_boundary_rh)
    qu = saturation(tu,ps*config.upper_pressure_fraction)*config.upper_boundary_rh
    return CP*(tl+273.15)+G*zl+LV*ql,CP*(tu+273.15)+G*zu+LV*qu


def advance(state,domain,config,closure,flow,dt,time_s,physics=True):
    ml,mu,ps = air_masses(domain,config);zl,zu = levels(domain,config)
    for a in (state.lower_energy,state.upper_energy):
        if a.shape!=domain.land.shape or not np.isfinite(a).all():raise ValueError('Invalid energy store.')
    # The frozen routine handles positive conservative water transport only.
    water,_,water_budget = transport_water(state.water,domain,config,flow,dt,time_s,physics=False)
    bl,bu = boundary_energy(domain,config,time_s)
    lx,ly = tracer_flux(state.lower_energy,ml,flow.lower_x,flow.lower_y,bl)
    ux,uy = tracer_flux(state.upper_energy,mu,flow.upper_x,flow.upper_y,bu)
    vz = flow.vertical*np.where(flow.vertical>=0,state.lower_energy/ml,state.upper_energy/mu)
    el = state.lower_energy-dt*(divergence(lx,ly,domain.dx,domain.dy)+vz)
    eu = state.upper_energy-dt*(divergence(ux,uy,domain.dx,domain.dy)-vz)
    boundary = float((divergence(lx+ux,ly+uy,domain.dx,domain.dy)*dt).mean())
    # Any tiny positivity correction carries latent energy and is explicitly external.
    corrected = water_budget['roundoff_correction_mm']*LV
    if corrected:
        # Reconstruct the frozen transport's rare per-cell positivity correction.
        capl,capu,_,_ = capacities(domain,config,time_s)
        ql = capl/ml*np.where(domain.land,config.land_boundary_rh,config.ocean_boundary_rh)
        qu = capu/mu*config.upper_boundary_rh
        wx,wy = tracer_flux(state.water.lower,ml,flow.lower_x,flow.lower_y,ql)
        vx,vy = tracer_flux(state.water.upper,mu,flow.upper_x,flow.upper_y,qu)
        exchange = flow.vertical*np.where(flow.vertical>=0,state.water.lower/ml,state.water.upper/mu)
        raw_l = state.water.lower-dt*(divergence(wx,wy,domain.dx,domain.dy)+exchange)
        raw_u = state.water.upper-dt*(divergence(vx,vy,domain.dx,domain.dy)-exchange)
        el += LV*np.maximum(-raw_l,0);eu += LV*np.maximum(-raw_u,0)
    tl = temperature(el,ml,water.lower,zl);tu = temperature(eu,mu,water.upper,zu)
    surface = interpolate_months(domain.temperature_c,time_s)
    rain = np.zeros_like(ml);runoff = np.zeros_like(ml);ocean_evap = np.zeros_like(ml);land_evap = np.zeros_like(ml)
    relaxation = np.zeros_like(ml);pl = np.zeros_like(ml);pu = np.zeros_like(ml)
    if physics:
        # Relax sensible temperature, not humidity or MSE, toward the same reference.
        fraction = -np.expm1(-dt/(closure.relaxation_days*DAY))
        dl = ml*CP*fraction*(surface+config.lower_temperature_offset_c-tl)
        du = mu*CP*fraction*(surface+config.upper_temperature_offset_c-tu)
        el += dl;eu += du;relaxation = dl+du
        tl = temperature(el,ml,water.lower,zl)
        speed = np.sqrt((.5*(flow.lower_x[:,1:]+flow.lower_x[:,:-1])/ml)**2
                        +(.5*(flow.lower_y[1:,:]+flow.lower_y[:-1,:])/ml)**2+config.gust_ms**2)
        deficit = np.maximum(saturation(surface,ps)-water.lower/ml,0)
        ocean_evap = np.where(~domain.land,np.minimum(1.2*config.bulk_exchange_coefficient*speed*deficit*dt,
                              config.ocean_evap_max_mm_day*dt/DAY),0.)
        winter = np.cos(2*np.pi*(time_s/DAY-15)/365.)
        capl = ml*saturation(tl,ps*config.lower_pressure_fraction)
        demand = config.land_pet_mm_day*(1-.5*winter)*np.clip((surface+5)/25,0,1)*dt/DAY
        demand *= water.soil/config.soil_capacity_mm*np.clip(1-water.lower/np.maximum(capl,1e-12),0,1)
        land_evap = np.where(domain.land,np.minimum(water.soil,demand),0)
        water.soil -= land_evap;water.lower += ocean_evap+land_evap
        # Surface heat reservoir supplies evaporation's latent enthalpy, logged below.
        el += LV*(ocean_evap+land_evap)
        water.lower,pl,tl = adjust(water.lower,el,ml,zl,ps*config.lower_pressure_fraction)
        water.upper,pu,tu = adjust(water.upper,eu,mu,zu,ps*config.upper_pressure_fraction)
        rain = pl+pu;water.soil += np.where(domain.land,rain,0)
        runoff = np.maximum(water.soil-config.soil_capacity_mm,0);water.soil -= runoff
    water_delta = float((water.lower+water.upper+water.soil-state.water.lower-state.water.upper-state.water.soil).mean())
    ocean_rain = float(np.where(~domain.land,rain,0).mean())
    water_expected = float(ocean_evap.mean())-ocean_rain-float(runoff.mean())-water_budget['boundary_export_mm']+water_budget['roundoff_correction_mm']
    energy_delta = float((el+eu-state.lower_energy-state.upper_energy).mean())
    latent = float((LV*(ocean_evap+land_evap)).mean());relax = float(relaxation.mean())
    energy_error = energy_delta-(latent+relax-boundary+corrected)
    budget = {'water_error_mm':water_delta-water_expected,'inventory_change_mm':water_delta,
        'ocean_evaporation_mm':float(ocean_evap.mean()),'land_evaporation_mm':float(land_evap.mean()),
        'rain_mm':float(rain.mean()),'lower_rain_mm':float(pl.mean()),'upper_rain_mm':float(pu.mean()),
        'ocean_rain_mm':ocean_rain,'runoff_mm':float(runoff.mean()),
        'boundary_export_mm':water_budget['boundary_export_mm'],'roundoff_correction_mm':water_budget['roundoff_correction_mm'],
        'energy_inventory_change_j_m2':energy_delta,'surface_latent_input_j_m2':latent,
        'temperature_relaxation_j_m2':relax,'energy_boundary_export_j_m2':boundary,'roundoff_energy_j_m2':corrected,
        'energy_error_j_m2':energy_error,'air_continuity_max_kg_m2_s':flow.continuity_error}
    if (not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm'])>1e-9 or abs(energy_error)>1e-5):
        raise FloatingPointError('Coupled water/static-energy budget failed.')
    saturation(tl,ps*config.lower_pressure_fraction);saturation(tu,ps*config.upper_pressure_fraction)
    return ThermalState(water,el,eu),rain,tl,tu,budget


def integrate_year(domain,config,closure,state,storms=True,progress=None):
    domain.validate();config.validate();closure.validate()
    events = catalogue(domain,config)
    forcing = domain if closure.terrain_drag else replace(domain,elevation_m=np.zeros_like(domain.elevation_m))
    ml,mu,_ = air_masses(domain,config)
    rain = np.zeros((12,)+domain.land.shape);tl_sum = np.zeros_like(rain);tu_sum = np.zeros_like(rain);ref_sum = np.zeros_like(rain)
    water_initial = float((state.water.lower+state.water.upper+state.water.soil).mean())
    energy_initial = float((state.lower_energy+state.upper_energy).mean())
    totals = {};t = 0.;steps = 0;flow = None;next_forcing = 0;max_water = 0.;max_energy = 0.;continuity = 0.;minimum = float('inf')
    for month in range(12):
        while t<EDGES[month+1]-1e-6:
            if flow is None or t>=next_forcing-1e-6:
                flow = flow_at(forcing,config,events,t,storms=storms)
                dt_limit = stable_step(flow,ml,mu,domain.dx,domain.dy,config)
                next_forcing = min(t+config.forcing_interval_s,EDGES[-1])
            dt = min(dt_limit,next_forcing-t,EDGES[month+1]-t)
            if dt<.01 or steps>=500000:raise RuntimeError('Bounded step count exceeded.')
            state,p,tl,tu,b = advance(state,domain,config,closure,flow,dt,t)
            rain[month] += p;tl_sum[month] += tl*dt;tu_sum[month] += tu*dt
            ref_sum[month] += interpolate_months(domain.temperature_c,t)*dt
            for key,value in b.items():
                if key not in ('water_error_mm','energy_error_j_m2','air_continuity_max_kg_m2_s'):
                    totals[key] = totals.get(key,0.)+value
            max_water = max(max_water,abs(b['water_error_mm']));max_energy = max(max_energy,abs(b['energy_error_j_m2']))
            continuity = max(continuity,b['air_continuity_max_kg_m2_s'])
            minimum = min(minimum,float(state.water.lower.min()),float(state.water.upper.min()),float(state.water.soil.min()))
            t += dt;steps += 1
        t = float(EDGES[month+1]);duration = EDGES[month+1]-EDGES[month]
        tl_sum[month] /= duration;tu_sum[month] /= duration;ref_sum[month] /= duration
        if progress:progress(month+1,steps)
    final_water = float((state.water.lower+state.water.upper+state.water.soil).mean())
    final_energy = float((state.lower_energy+state.upper_energy).mean())
    water_error = final_water-water_initial-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    energy_error = final_energy-energy_initial-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2'])
    if abs(water_error)>1e-6 or abs(energy_error)>1.:
        raise FloatingPointError('Annual water/static-energy closure failed.')
    totals.update(initial_inventory_mm=water_initial,final_inventory_mm=final_water,
        initial_energy_j_m2=energy_initial,final_energy_j_m2=final_energy,annual_water_error_mm=water_error,
        annual_energy_error_j_m2=energy_error,max_step_water_error_mm=max_water,max_step_energy_error_j_m2=max_energy,
        max_air_continuity_kg_m2_s=continuity,min_store_mm=minimum,steps=steps,
        temperature_relaxation_mean_w_m2=totals['temperature_relaxation_j_m2']/(365*DAY))
    return ThermalYear(state,rain,tl_sum,tu_sum,ref_sum,totals)
