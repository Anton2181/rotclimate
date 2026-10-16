"""Dry-potential-temperature transport with explicit prescribed-flow work.

Pressure and mass are fixed. Moisture/condensation retain the frozen closure.
State.energy keeps the old m(cp*T+gz)+Lv*water representation for accounting;
it is no longer assumed to be passively conserved by prescribed circulation.
The diagnosed energy exchange includes pressure/geopotential effects and
discretisation; without momentum this is not total-energy closure of a GCM.
"""
import numpy as np
from experiments import v10_spatial_wind as winds
from experiments import v10_coordinates as coordinates
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, interpolate_months, divergence
base = winds.base
initial_state = winds.initial_state
ColumnProjection = winds.ColumnProjection
nested_events = winds.nested_events
RD = 287.05
P_REF = 100000.
KAPPA = RD/base.CP
PROCESSES = ('horizontal_advection', 'vertical_advection', 'pressure_expansion',
    'relaxation', 'evaporation', 'condensation')


def exner(pressure):
    if not np.isfinite(pressure).all() or (pressure <= 0).any():
        raise ValueError('Positive pressure required for dry-potential-temperature transport.')
    return (pressure/P_REF)**KAPPA


def flow_at(domain, profile, settings, storms, time_s, geometry, local_wind,
            projector=None, wind_mode='spatial'):
    if wind_mode == 'spatial':
        return winds.flow_at(domain, profile, settings, storms, time_s, geometry, local_wind, projector)
    if wind_mode == 'uniform':
        return winds.mass_model.flow_at(domain, profile, settings, storms, time_s, geometry, projector)
    raise ValueError('Unknown mean-wind control.')


def thermal_transport(state, flow, dt, domain, geometry, target, boundary_q):
    """Transport theta with the same dry flux as water; derive energy exchange."""
    mass, pressure, z = geometry.mass, geometry.pressure, geometry.height_m
    pi = exner(pressure)
    temperature_k = base.temperature(state.energy, mass, state.water, z)+273.15
    theta = temperature_k/pi
    if (theta <= 0).any() or not np.isfinite(theta).all():
        raise ValueError('Positive finite potential temperature required.')
    boundary_t = target+273.15
    fx, fy = base.flux(mass*theta, mass, flow.x, flow.y, boundary_t/pi)
    horizontal = divergence(fx, fy, domain.dx, domain.dy)
    vertical = coordinates.vertical_divergence(flow.vertical*np.where(flow.vertical >= 0, theta[:-1], theta[1:]), mass.shape)
    new_theta = theta-dt*(horizontal+vertical)/mass
    if new_theta.min() <= 0:
        raise FloatingPointError('Negative advected potential temperature.')
    wx, wy = base.flux(state.water, mass, flow.x, flow.y, boundary_q)
    wd = divergence(wx, wy, domain.dx, domain.dy)
    wv = coordinates.vertical_divergence(flow.vertical*np.where(flow.vertical >= 0,
        state.water[:-1]/mass[:-1], state.water[1:]/mass[1:]), mass.shape)
    water = state.water-dt*(wd+wv)
    boundary_e = base.CP*boundary_t+base.G*z+base.LV*boundary_q
    ex, ey = base.flux(state.energy, mass, flow.x, flow.y, boundary_e)
    ed = divergence(ex, ey, domain.dx, domain.dy)
    ev = coordinates.vertical_divergence(flow.vertical*np.where(flow.vertical >= 0,
        state.energy[:-1]/mass[:-1], state.energy[1:]/mass[1:]), mass.shape)
    energy = mass*(base.CP*pi*new_theta+base.G*z)+base.LV*water
    frozen_energy = state.energy-dt*(ed+ev)
    work = energy-frozen_energy
    # Advective T changes use donor-minus-local anomalies. Constant offsets do
    # not create large opposing horizontal/vertical 'heating' contributions.
    tx, ty = base.flux(mass*temperature_k, mass, flow.x, flow.y, boundary_t)
    td = divergence(tx, ty, domain.dx, domain.dy)
    tv = coordinates.vertical_divergence(flow.vertical*np.where(flow.vertical >= 0,
        temperature_k[:-1], temperature_k[1:]), mass.shape)
    md = divergence(flow.x, flow.y, domain.dx, domain.dy)
    mv = coordinates.vertical_divergence(flow.vertical, mass.shape)
    changes = np.zeros((len(PROCESSES),)+mass.shape)
    changes[0] = -dt*(td-temperature_k*md)/mass
    changes[1] = -dt*(tv-temperature_k*mv)/mass
    changes[2] = pi*new_theta-temperature_k-changes[0]-changes[1]
    theta_error = float((mass*(new_theta-theta)).sum(0).mean()+dt*horizontal.sum(0).mean())
    return water, energy, wd, ed, work, changes, theta_error


# Non-transport microphysics copied unchanged from the frozen coordinate step.
def advance(state, domain, profile, settings, flow, dt, time_s, local_air=None,
            physics=True, geometry=None):
    if geometry is None:
        raise ValueError('Explicit coordinate geometry required.')
    mass, ps, p, z = geometry.mass, geometry.surface_pressure, geometry.pressure, geometry.height_m
    if dt <= 0 or dt > base.stable_step(flow, mass, domain)*(1+1e-12):
        raise ValueError('Column CFL exceeded.')
    if not all(np.isfinite(a).all() for a in (state.water, state.energy, state.soil)) or min(state.water.min(), state.soil.min()) < 0:
        raise ValueError('Invalid column state.')
    target, surface = coordinates.targets(domain, profile, settings, time_s, local_air)
    if local_air is None:
        bq = base.boundary(domain, profile, settings, time_s, p)
    else:
        bq = np.broadcast_to(interpolate_months(profile.mixing_ratio, time_s)[:, None, None]*settings.humidity_scale, target.shape)
        bq = np.minimum(bq, base.saturation(target, p)*.95)
    initial_t = base.temperature(state.energy, mass, state.water, z)
    water, energy, wd, ed, work, changes, theta_error = thermal_transport(
        state, flow, dt, domain, geometry, target, bq)
    if water.min() < -1e-11:
        raise FloatingPointError('Negative transported water.')
    correction = np.maximum(-water, 0)
    water += correction
    energy += base.LV*correction
    t = base.temperature(energy, mass, water, z)
    flow_work = float(work.sum(0).mean())
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
        changes[3] = relax/(mass*base.CP)
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
        changes[5] = base.LV*rain/(mass*base.CP)
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
        'prescribed_flow_work_j_m2': flow_work, 'theta_transport_error_kg_k_m2': theta_error,
        'water_error_mm': water_change-(float(evap_ocean.mean())-ocean_rain-float(runoff.mean())-boundary_water+rw),
        'energy_error_j_m2': energy_change-(latent+heating-boundary_energy+base.LV*rw+flow_work)}
    if not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm']) > 1e-9 or abs(budget['energy_error_j_m2']) > 1e-5 or abs(theta_error) > 1e-7:
        raise FloatingPointError('Column water/static-energy budget failed.')
    base.saturation(t, p)
    return base.State(water, energy, soil), rain.sum(0), t, target, budget, rain, changes, closure


# Separate seasonal ledger: adds the explicitly diagnosed prescribed-flow work.
def year(domain, profile, settings, seed, state, local_air, mask, geometry, local_wind, checkpoint=None,
         save_month=None, should_stop=lambda: False, wind_mode='spatial'):
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
        max_adjustment = max_raw_divergence = 0.
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
        max_adjustment = info['diagnostics']['max_projection_adjustment_m_s']
        max_raw_divergence = info['diagnostics']['max_raw_column_divergence_kg_m2_s']
        if layer_rain.shape != (12, 4) or thermal.shape != (12, len(PROCESSES), 4) or not np.isfinite(layer_rain).all() or not np.isfinite(thermal).all():
            raise ValueError('Invalid resumed process diagnostics.')
    storms = nested_events(domain, settings, seed, profile.storm_domain_width_m)
    projector = ColumnProjection(domain, geometry)
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
                flow = flow_at(domain, profile, settings, storms, tick, geometry, local_wind, projector, wind_mode=wind_mode)
                max_adjustment = max(max_adjustment, projector.last_info['barotropic_velocity_adjustment_max_m_s'])
                max_raw_divergence = max(max_raw_divergence, projector.last_info['raw_column_divergence_max_kg_m2_s'])
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
                'max_projection_adjustment_m_s': max_adjustment,
                'max_raw_column_divergence_kg_m2_s': max_raw_divergence,
                'note': 'Cumulative signed temperature changes per month, not net heating or temperature error. Divide by month length for K/day.'})
        if save_month:
            save_month(state, rain, temp, refs, info)
    wf = float((state.water.sum(0)+state.soil).mean())
    ef = float(state.energy.sum(0).mean())
    we = wf-initial_water-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2']+totals['prescribed_flow_work_j_m2'])
    if abs(we) > 1e-6 or abs(ee) > 1:
        raise FloatingPointError('Annual column budgets failed.')
    info['budget'] = dict(totals, annual_water_error_mm=we, annual_energy_error_j_m2=ee,
        max_step_water_error_mm=maxw, max_step_energy_error_j_m2=maxe,
        max_air_continuity_kg_m2_s=continuity, steps=steps)
    return state, rain, temp, refs, info
