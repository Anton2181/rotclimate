"""Matched pressure-geometry hypotheses, derived from the frozen upper-air closure.

Same four-layer rain/MSE algorithms and kinematic face fluxes. Both hypotheses
use spatial thermal reference, pressure-consistent mean heights and surface
pressure inferred from mean reference geopotential. This is NOT a coordinate
invariance test: fixed face fluxes imply different physical velocities. It
tests two atmospheric path assumptions, not a new momentum/radiation model.
"""
from dataclasses import dataclass
import numpy as np
from experiments import v10_column as base
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, interpolate_months, divergence

PROCESSES = ('horizontal', 'vertical', 'relaxation', 'evaporation', 'condensation')

P0 = 101325.
TRANSITION_PA = .6*P0


@dataclass
class Geometry:
    mass: np.ndarray
    surface_pressure: np.ndarray
    pressure: np.ndarray
    height_m: np.ndarray
    interfaces_pa: np.ndarray
    mode: str


def pressure_grid(surface_pressure, mode):
    ps = np.asarray(surface_pressure, float)
    if not np.isfinite(ps).all() or (ps <= 0).any():
        raise ValueError('Invalid surface pressure.')
    if mode == 'sigma':
        interfaces = np.array([1., .9, .75, .6, 0.])[:, None, None]*ps
    elif mode == 'hybrid':
        if (ps <= TRANSITION_PA).any():
            raise ValueError('Ground intersects fixed upper pressure interface.')
        eta = np.array([1., .75, .375, 0.])[:, None, None]
        lower = TRANSITION_PA+eta*(ps-TRANSITION_PA)
        interfaces = np.concatenate([lower, np.zeros((1,)+ps.shape)])
    else:
        raise ValueError('Unknown pressure geometry.')
    mass = (interfaces[:-1]-interfaces[1:])/base.G
    pressure = .5*(interfaces[:-1]+interfaces[1:])
    if (mass <= 0).any():
        raise ValueError('Nonpositive layer mass.')
    return mass, pressure, interfaces


def surface_pressure_from_heights(elevation, pressure_pa, heights):
    if heights.shape != (len(pressure_pa),)+elevation.shape or not np.isfinite(heights).all() or (np.diff(heights, axis=0) <= 0).any():
        raise ValueError('Reference heights must increase as pressure decreases.')
    if (np.diff(pressure_pa) >= 0).any() or (pressure_pa <= 0).any():
        raise ValueError('Invalid reference pressure axis.')
    ps = np.empty_like(elevation, dtype=float)
    logp = np.log(pressure_pa)
    for idx in np.ndindex(elevation.shape):
        h = heights[(slice(None),)+idx]
        k = int(np.clip(np.searchsorted(h, elevation[idx])-1, 0, len(h)-2))
        weight = (elevation[idx]-h[k])/(h[k+1]-h[k])
        ps[idx] = np.exp(logp[k]+weight*(logp[k+1]-logp[k]))
    return ps


def prepare_geometry(case, fields, mode):
    from experiments.v10_forcing_audit import at_pressure
    d = case.domain
    field = fields[d.name, 'hgt']
    iy = abs(field.latitude[:, None, None]-d.latitude).argmin(0)
    ix = abs((field.longitude[:, None, None]-case.longitude%360+180)%360-180).argmin(0)
    if (abs(field.latitude[iy]-d.latitude)>1.250001).any() or (abs((field.longitude[ix]-case.longitude+180)%360-180)>1.250001).any():
        raise ValueError('Location outside cached reference footprint.')
    heights = field.values.mean(0)[:, iy, ix]
    ps = surface_pressure_from_heights(d.elevation_m, field.pressure_hpa*100, heights)
    mass, pressure, interfaces = pressure_grid(ps, mode)
    air = []
    z = []
    for layer in range(4):
        sampled, _, _ = at_pressure(fields[d.name, 'air'], case.longitude, d.latitude, pressure[layer]/100)
        air.append(sampled)
        sampled, _, _ = at_pressure(field, case.longitude, d.latitude, pressure[layer]/100)
        z.append(sampled.mean(0))
    air, z = np.stack(air, axis=1), np.stack(z)
    if not np.isfinite(air).all() or not np.isfinite(z).all() or (np.diff(z, axis=0)<=0).any() or (z[0] <= d.elevation_m).any():
        raise ValueError('Invalid sampled coordinate column.')
    return Geometry(mass, ps, pressure, z, interfaces, mode), air


def initial_state(domain, profile, settings, geometry, local_air):
    mass, ps, p, z = geometry.mass, geometry.surface_pressure, geometry.pressure, geometry.height_m
    t, _ = targets(domain, profile, settings, 0., local_air)
    q = np.broadcast_to(interpolate_months(profile.mixing_ratio, 0.)[:, None, None]*settings.humidity_scale, t.shape)
    water = mass*np.minimum(q, .6*base.saturation(t, p))
    return base.State(water, mass*(base.CP*(t+273.15)+base.G*z)+base.LV*water,
        np.where(domain.land, 75., 0.))



def targets(domain, profile, settings, time_s, local_air=None):
    if local_air is None or not settings.observed_temperature or not settings.observed_humidity:
        raise ValueError('Coordinate experiment requires spatial thermal reference and observed humidity.')
    return interpolate_months(local_air, time_s), interpolate_months(domain.temperature_c, time_s)


def vertical_divergence(exchange, shape):
    out = np.zeros(shape)
    out[:-1] += exchange
    out[1:] -= exchange
    return out


def advance(state, domain, profile, settings, flow, dt, time_s, local_air=None,
            physics=True, geometry=None):
    if geometry is None:
        raise ValueError('Explicit coordinate geometry required.')
    mass, ps, p, z = geometry.mass, geometry.surface_pressure, geometry.pressure, geometry.height_m
    if dt <= 0 or dt > base.stable_step(flow, mass, domain)*(1+1e-12):
        raise ValueError('Column CFL exceeded.')
    if not all(np.isfinite(a).all() for a in (state.water, state.energy, state.soil)) or min(state.water.min(), state.soil.min()) < 0:
        raise ValueError('Invalid column state.')
    target, surface = targets(domain, profile, settings, time_s, local_air)
    if local_air is None:
        bq = base.boundary(domain, profile, settings, time_s, p)
    else:
        bq = np.broadcast_to(interpolate_months(profile.mixing_ratio, time_s)[:, None, None]*settings.humidity_scale, target.shape)
        bq = np.minimum(bq, base.saturation(target, p)*.95)
    be = base.CP*(target+273.15)+base.G*z+base.LV*bq
    wx, wy = base.flux(state.water, mass, flow.x, flow.y, bq)
    ex, ey = base.flux(state.energy, mass, flow.x, flow.y, be)
    wd = divergence(wx, wy, domain.dx, domain.dy)
    ed = divergence(ex, ey, domain.dx, domain.dy)
    wv = vertical_divergence(flow.vertical*np.where(flow.vertical >= 0,
        state.water[:-1]/mass[:-1], state.water[1:]/mass[1:]), mass.shape)
    ev = vertical_divergence(flow.vertical*np.where(flow.vertical >= 0,
        state.energy[:-1]/mass[:-1], state.energy[1:]/mass[1:]), mass.shape)
    water = state.water-dt*(wd+wv)
    energy = state.energy-dt*(ed+ev)
    if water.min() < -1e-11:
        raise FloatingPointError('Negative transported water.')
    correction = np.maximum(-water, 0)
    water += correction
    energy += base.LV*correction
    changes = np.zeros((len(PROCESSES),)+mass.shape)
    changes[0] = -dt*(ed-base.LV*wd)/(mass*base.CP)
    changes[1] = -dt*(ev-base.LV*wv)/(mass*base.CP)
    initial_t = base.temperature(state.energy, mass, state.water, z)
    t = base.temperature(energy, mass, water, z)
    soil = state.soil.copy()
    evap_ocean = np.zeros_like(soil)
    evap_land = np.zeros_like(soil)
    runoff = np.zeros_like(soil)
    rain = np.zeros_like(water)
    relax = np.zeros_like(energy)
    if physics:
        tau = np.array([settings.relaxation_lower_days]*2+[settings.relaxation_upper_days]*2)[:, None, None]*DAY
        relax = mass*base.CP*(-np.expm1(-dt/tau))*(target-t)
        energy += relax
        changes[2] = relax/(mass*base.CP)
        t = base.temperature(energy, mass, water, z)
        speed = np.sqrt((.5*(flow.x[0, :, 1:]+flow.x[0, :, :-1])/mass[0])**2
            +(.5*(flow.y[0, 1:]+flow.y[0, :-1])/mass[0])**2+4)
        deficit = np.maximum(base.saturation(surface, ps)-water[0]/mass[0], 0)
        evap_ocean = np.where(~domain.land, np.minimum(1.2*.0012*speed*deficit*dt, 5*dt/DAY), 0.)
        winter = np.cos(2*np.pi*(time_s/DAY-15)/365)
        demand = 3*(1-.5*winter)*np.clip((surface+5)/25, 0, 1)*dt/DAY
        demand *= soil/150*np.clip(1-water[0]/np.maximum(mass[0]*base.saturation(t[0], p[0]), 1e-12), 0, 1)
        evap_land = np.where(domain.land, np.minimum(soil, demand), 0)
        soil -= evap_land
        water[0] += evap_ocean+evap_land
        energy[0] += base.LV*(evap_ocean+evap_land)
        # Evaporation adds latent energy and vapor together, no direct sensible T change.
        water, rain, t = base.adjust(water, energy, mass, z, p)
        changes[4] = base.LV*rain/(mass*base.CP)
        soil += np.where(domain.land, rain.sum(0), 0)
        runoff = np.maximum(soil-150, 0)
        soil -= runoff
    closure = float(abs(t-initial_t-changes.sum(0)).max())
    if closure > 1e-9:
        raise FloatingPointError('Signed temperature-change ledger failed.')
    boundary_water = float(dt*wd.sum(0).mean())
    boundary_energy = float(dt*ed.sum(0).mean())
    water_change = float((water.sum(0)+soil-state.water.sum(0)-state.soil).mean())
    energy_change = float((energy-state.energy).sum(0).mean())
    ocean_rain = float(np.where(~domain.land, rain.sum(0), 0).mean())
    rw = float(correction.sum(0).mean())
    latent = float(base.LV*(evap_ocean+evap_land).mean())
    heating = float(relax.sum(0).mean())
    budget = {'ocean_evaporation_mm': float(evap_ocean.mean()),
        'land_evaporation_mm': float(evap_land.mean()), 'rain_mm': float(rain.sum(0).mean()),
        'ocean_rain_mm': ocean_rain, 'runoff_mm': float(runoff.mean()),
        'boundary_export_mm': boundary_water, 'roundoff_correction_mm': rw,
        'surface_latent_input_j_m2': latent, 'temperature_relaxation_j_m2': heating,
        'energy_boundary_export_j_m2': boundary_energy, 'roundoff_energy_j_m2': base.LV*rw,
        'water_error_mm': water_change-(float(evap_ocean.mean())-ocean_rain-float(runoff.mean())-boundary_water+rw),
        'energy_error_j_m2': energy_change-(latent+heating-boundary_energy+base.LV*rw)}
    if not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm']) > 1e-9 or abs(budget['energy_error_j_m2']) > 1e-5:
        raise FloatingPointError('Column water/static-energy budget failed.')
    base.saturation(t, p)
    return base.State(water, energy, soil), rain.sum(0), t, target, budget, rain, changes, closure


def year(domain, profile, settings, seed, state, local_air, mask, geometry, checkpoint=None,
         save_month=None, should_stop=lambda: False):
    shape = domain.land.shape
    if local_air.shape != (12, 4)+shape or not np.isfinite(local_air).all() or mask.shape != shape or not mask.any():
        raise ValueError('Invalid local-air input or diagnostic mask.')
    if checkpoint is None:
        rain = np.zeros((12,)+shape)
        temp = np.zeros((12, 4)+shape)
        refs = np.zeros_like(temp)
        totals = {}
        start_month = 0
        initial_water = float((state.water.sum(0)+state.soil).mean())
        initial_energy = float(state.energy.sum(0).mean())
        maxw = maxe = continuity = ledger_error = 0.
        steps = 0
        layer_rain = np.zeros((12, 4))
        thermal = np.zeros((12, len(PROCESSES), 4))
    else:
        state, rain, temp, refs, info = checkpoint
        totals = info['totals'].copy()
        start_month = info['month']
        initial_water, initial_energy = info['initial_water'], info['initial_energy']
        maxw, maxe, continuity, steps = (info[k] for k in ('maxw', 'maxe', 'continuity', 'steps'))
        layer_rain = np.array(info['diagnostics']['layer_rain_scored_land_mm'])
        thermal = np.array(info['diagnostics']['temperature_changes_scored_land_c'])
        ledger_error = info['diagnostics']['max_step_temperature_ledger_error_c']
        if layer_rain.shape != (12, 4) or thermal.shape != (12, len(PROCESSES), 4) or not np.isfinite(layer_rain).all() or not np.isfinite(thermal).all():
            raise ValueError('Invalid resumed process diagnostics.')
    storms = base.events(domain, settings, seed, profile.storm_domain_width_m)
    mass = geometry.mass
    for month in range(start_month, 12):
        t = float(EDGES[month])
        flow = None
        next_forcing = t
        while t < EDGES[month+1]-1e-6:
            if steps % 32 == 0 and should_stop():
                raise base.BudgetStop()
            if flow is None or t >= next_forcing-1e-6:
                tick = np.floor((t+1e-6)/10800.)*10800.
                next_forcing = tick+10800.
                flow = base.flow_at(domain, profile, settings, storms, tick)
                limit = base.stable_step(flow, mass, domain)
            dt = step_length(t, limit, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded column step count exceeded.')
            state, p, temperature, target, b, by_layer, changes, residual = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry=geometry)
            rain[month] += p
            temp[month] += temperature*dt
            refs[month] += target*dt
            layer_rain[month] += by_layer[:, mask].mean(1)
            thermal[month] += changes[:, :, mask].mean(2)
            for key, value in b.items():
                if key not in ('water_error_mm', 'energy_error_j_m2'):
                    totals[key] = totals.get(key, 0.)+value
            maxw = max(maxw, abs(b['water_error_mm']))
            maxe = max(maxe, abs(b['energy_error_j_m2']))
            continuity = max(continuity, flow.continuity)
            ledger_error = max(ledger_error, residual)
            t += dt
            steps += 1
        duration = EDGES[month+1]-EDGES[month]
        temp[month] /= duration
        refs[month] /= duration
        info = dict(month=month+1, totals=totals, initial_water=initial_water,
            initial_energy=initial_energy, maxw=maxw, maxe=maxe, continuity=continuity,
            steps=steps, diagnostics={'processes': list(PROCESSES),
                'layer_rain_scored_land_mm': layer_rain.tolist(),
                'temperature_changes_scored_land_c': thermal.tolist(),
                'max_step_temperature_ledger_error_c': ledger_error,
                'note': 'Cumulative signed temperature changes per month, not net heating or temperature error. Divide by month length for K/day.'})
        if save_month:
            save_month(state, rain, temp, refs, info)
    wf = float((state.water.sum(0)+state.soil).mean())
    ef = float(state.energy.sum(0).mean())
    we = wf-initial_water-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2'])
    if abs(we) > 1e-6 or abs(ee) > 1:
        raise FloatingPointError('Annual column budgets failed.')
    info['budget'] = dict(totals, annual_water_error_mm=we, annual_energy_error_j_m2=ee,
        max_step_water_error_mm=maxw, max_step_energy_error_j_m2=maxe,
        max_air_continuity_kg_m2_s=continuity, steps=steps)
    return state, rain, temp, refs, info

