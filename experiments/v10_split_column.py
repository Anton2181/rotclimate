"""Controlled five-layer split of the frozen upper 607.95–0 hPa cell.

Temperature/height targets follow the new pressures. Old upper horizontal mass
flux is partitioned by layer mass; lower flows and aggregate upper flow stay
paired. This tests vertical structure under the old coarse circulation, not
new observed winds at the two upper pressures. No reference q above 300 hPa
exists in the cache: dry and retained-300-hPa-RH lids are explicit assumptions.
"""
from dataclasses import dataclass
import numpy as np
from experiments import v10_pressure_thermo as core, v10_forcing_audit as atmosphere
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, interpolate_months
base = core.base
coordinates = core.coordinates
thermal_transport = core.thermal_transport
ColumnProjection = core.ColumnProjection
nested_events = core.nested_events
PROCESSES = core.PROCESSES
SPLIT_PA = 30000.


def validate_geometry(geometry, shape):
    count = len(geometry.mass)
    arrays = (geometry.mass, geometry.pressure, geometry.height_m)
    if count not in (4, 5) or any(a.shape != (count,)+shape or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Invalid layer geometry shape/values.')
    if geometry.interfaces_pa.shape != (count+1,)+shape or geometry.surface_pressure.shape != shape or not np.isfinite(geometry.interfaces_pa).all():
        raise ValueError('Invalid layer interface shapes/values.')
    if (geometry.mass <= 0).any() or (geometry.pressure <= 0).any() or (np.diff(geometry.interfaces_pa, axis=0) >= 0).any():
        raise ValueError('Nonpositive/reversed pressure layers.')
    if not np.allclose(geometry.mass, -np.diff(geometry.interfaces_pa, axis=0)/base.G, atol=1e-10, rtol=0) or not np.allclose(geometry.pressure, .5*(geometry.interfaces_pa[:-1]+geometry.interfaces_pa[1:]), atol=1e-10, rtol=0):
        raise ValueError('Layer pressure/mass rules disagree.')


@dataclass
class Profile:
    offsets: np.ndarray
    mixing_ratio: np.ndarray
    eastward: np.ndarray
    northward: np.ndarray
    height_m: np.ndarray
    storm_domain_width_m: float | None = None

    def validate(self):
        count = len(self.height_m)
        if count not in (4, 5) or any(a.shape != (12, count) or not np.isfinite(a).all() for a in (self.offsets, self.mixing_ratio, self.eastward, self.northward)):
            raise ValueError('Invalid split-column profile.')
        if (self.mixing_ratio < 0).any() or (self.mixing_ratio > .1).any() or not np.isfinite(self.height_m).all() or (np.diff(self.height_m) <= 0).any():
            raise ValueError('Invalid split-column moisture/heights.')


def prepare_geometry(case, original, original_air, fields):
    if original.mass.shape[0] != 4 or not np.allclose(original.interfaces_pa[3], coordinates.TRANSITION_PA):
        raise ValueError('Need the original four-layer hybrid geometry.')
    interfaces = np.concatenate([original.interfaces_pa[:4],
        np.full((1,)+case.domain.land.shape, SPLIT_PA), np.zeros((1,)+case.domain.land.shape)])
    mass = -np.diff(interfaces, axis=0)/base.G
    pressure = .5*(interfaces[:-1]+interfaces[1:])
    heights = [original.height_m[k] for k in range(3)]
    air = [original_air[:, k] for k in range(3)]
    for p in pressure[3:]:
        a, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'air'], case.longitude, case.domain.latitude, p/100)
        z, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'hgt'], case.longitude, case.domain.latitude, p/100)
        air.append(a);heights.append(z.mean(0))
    geometry = coordinates.Geometry(mass, original.surface_pressure.copy(), pressure,
        np.stack(heights), interfaces, 'hybrid_split300')
    air = np.stack(air, axis=1)
    if not np.array_equal(mass[:3], original.mass[:3]) or not np.allclose(mass.sum(0), original.mass.sum(0), atol=1e-10, rtol=0):
        raise ValueError('Split changed lower masses or total column mass.')
    if (mass <= 0).any() or not np.isfinite(air).all() or (np.diff(geometry.height_m, axis=0) <= 0).any():
        raise ValueError('Invalid new pressure/thermal geometry.')
    return geometry, air


def prepare_profile(case, original, geometry, air, fields, lid):
    if lid not in ('dry', 'rh300'):
        raise ValueError('Unknown unobserved-upper-humidity assumption.')
    mask = atmosphere.offshore_mask(case)
    ratio = np.zeros((12, 5));ratio[:, :3] = original.mixing_ratio[:, :3]
    sampled, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'shum'], case.longitude,
        case.domain.latitude, geometry.pressure[3]/100)
    ratio[:, 3] = sampled[:, mask].mean(1)
    if lid == 'rh300':
        r, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'shum'], case.longitude, case.domain.latitude, 300.)
        t, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'air'], case.longitude, case.domain.latitude, 300.)
        rh = np.clip((r/base.saturation(t, SPLIT_PA))[:, mask].mean(1), 0., .95)
        ratio[:, 4] = rh*base.saturation(air[:, 4, mask].mean(1), geometry.pressure[4, mask].mean())
    surface = case.domain.temperature_c[:, mask].mean(1)
    offsets = air[:, :, mask].mean(2)-surface[:, None]
    u = np.concatenate([original.eastward[:, :3], np.repeat(original.eastward[:, 3:], 2, axis=1)], axis=1)
    v = np.concatenate([original.northward[:, :3], np.repeat(original.northward[:, 3:], 2, axis=1)], axis=1)
    profile = Profile(offsets, ratio, u, v, geometry.height_m[:, mask].mean(1), original.storm_domain_width_m)
    profile.validate()
    return profile


def split_flow(flow, old_geometry, geometry, domain):
    if geometry.mass.shape[0] != 5 or not np.array_equal(geometry.mass[:3], old_geometry.mass[:3]):
        raise ValueError('Need matching lower layers for the controlled circulation split.')
    weights = geometry.mass[3:, 0, 0]/old_geometry.mass[3, 0, 0]
    if not np.allclose(geometry.mass[3:], weights[:, None, None]*old_geometry.mass[3], atol=1e-10, rtol=0) or abs(weights.sum()-1) > 1e-12:
        raise ValueError('Upper mass partition is not spatially uniform/conservative.')
    x = np.concatenate([flow.x[:3], weights[:, None, None]*flow.x[3]], axis=0)
    y = np.concatenate([flow.y[:3], weights[:, None, None]*flow.y[3]], axis=0)
    return base.balanced(x, y, domain.dx, domain.dy)


def flow_at(domain, profile, settings, storms, time_s, geometry, local_wind,
            projector=None, wind_mode='spatial', circulation=None):
    if circulation is None:
        if geometry.mass.shape[0] != 4:
            raise ValueError('Five layers require the explicit saved coarse circulation.')
        return core.flow_at(domain, profile, settings, storms, time_s, geometry, local_wind, projector, wind_mode)
    old_g, old_profile, _, old_wind = circulation
    coarse = core.flow_at(domain, old_profile, settings, storms, time_s, old_g, old_wind, projector, wind_mode)
    return split_flow(coarse, old_g, geometry, domain)


def boundary_ratio(domain, profile, settings, geometry, local_air, time_s,
                   boundary_mode='reference', circulation=None):
    target, _ = coordinates.targets(domain, profile, settings, time_s, local_air)
    r = np.broadcast_to(interpolate_months(profile.mixing_ratio, time_s)[:, None, None]*settings.humidity_scale, target.shape)
    r = np.minimum(r, .95*base.saturation(target, geometry.pressure))
    if boundary_mode == 'reference':
        return r
    if boundary_mode != 'column_matched' or circulation is None:
        raise ValueError('Unknown boundary control or missing original inputs.')
    old_g, old_profile, old_air, _ = circulation
    old_t, _ = coordinates.targets(domain, old_profile, settings, time_s, old_air)
    old_r = interpolate_months(old_profile.mixing_ratio, time_s)[:, None, None]*settings.humidity_scale
    old_r = np.minimum(old_r, .95*base.saturation(old_t, old_g.pressure))
    requested = (old_g.mass*old_r).sum(0);available = (geometry.mass*r).sum(0)
    if (requested > available+1e-10).any():
        raise ValueError('Column-matched control needs upward scaling; inspect instead of adding supersaturated vapor.')
    factor = np.divide(requested, available, out=np.zeros_like(requested), where=available > 0)
    return r*np.minimum(factor, 1.)[None]


def initial_state(domain, profile, settings, geometry, local_air,
                  boundary_mode='reference', circulation=None):
    domain.validate();profile.validate();settings.validate()
    validate_geometry(geometry, domain.land.shape)
    target, _ = coordinates.targets(domain, profile, settings, 0., local_air)
    r = boundary_ratio(domain, profile, settings, geometry, local_air, 0., boundary_mode, circulation)
    water = geometry.mass*np.minimum(r, .6*base.saturation(target, geometry.pressure))
    energy = geometry.mass*(base.CP*(target+273.15)+base.G*geometry.height_m)+base.LV*water
    return base.State(water, energy, np.where(domain.land, 75., 0.))


def gross_boundary_transfers(state, flow, dt, domain, geometry, boundary):
    r = state.water/geometry.mass
    west = flow.x[..., 0]*np.where(flow.x[..., 0] >= 0, boundary[..., 0], r[..., 0])/domain.dx
    east = -flow.x[..., -1]*np.where(flow.x[..., -1] >= 0, r[..., -1], boundary[..., -1])/domain.dx
    north = flow.y[..., 0, :]*np.where(flow.y[..., 0, :] >= 0, boundary[..., 0, :], r[..., 0, :])/domain.dy
    south = -flow.y[..., -1, :]*np.where(flow.y[..., -1, :] >= 0, r[..., -1, :], boundary[..., -1, :])/domain.dy
    incoming = dt*sum(np.maximum(a, 0).sum() for a in (west, east, north, south))/domain.land.size
    outgoing = dt*sum(np.maximum(-a, 0).sum() for a in (west, east, north, south))/domain.land.size
    return float(incoming), float(outgoing)


# Separate static copies of the frozen advance/year, generalized for layer count
# and explicit boundary controls. Original modules remain unchanged.
def advance(state, domain, profile, settings, flow, dt, time_s, local_air=None,
            physics=True, geometry=None, boundary_mode='reference', circulation=None):
    if geometry is None:
        raise ValueError('Explicit coordinate geometry required.')
    mass, ps, p, z = geometry.mass, geometry.surface_pressure, geometry.pressure, geometry.height_m
    if len(mass) not in (4, 5) or state.water.shape != mass.shape or state.energy.shape != mass.shape or local_air is None or local_air.shape != (12,)+mass.shape:
        raise ValueError('Invalid resolved-layer state or thermal shape.')
    if dt <= 0 or dt > base.stable_step(flow, mass, domain)*(1+1e-12):
        raise ValueError('Column CFL exceeded.')
    if not all(np.isfinite(a).all() for a in (state.water, state.energy, state.soil)) or min(state.water.min(), state.soil.min()) < 0:
        raise ValueError('Invalid column state.')
    target, surface = coordinates.targets(domain, profile, settings, time_s, local_air)
    if local_air is None:
        raise ValueError('Explicit local thermal reference required.')
    bq = boundary_ratio(domain, profile, settings, geometry, local_air,
        time_s, boundary_mode, circulation)
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
        tau = np.where(np.arange(len(mass)) < 2, settings.relaxation_lower_days, settings.relaxation_upper_days)[:, None, None]*DAY
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
    if len(mass) == 5:
        incoming, outgoing = gross_boundary_transfers(state, flow, dt, domain, geometry, bq)
        if abs(outgoing-incoming-boundary_water) > 1e-9:
            raise FloatingPointError('Gross boundary fluxes disagree with net water transport.')
        budget.update(boundary_import_gross_mm=incoming, boundary_export_gross_mm=outgoing)
    if not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm']) > 1e-9 or abs(budget['energy_error_j_m2']) > 1e-5 or abs(theta_error) > 1e-7:
        raise FloatingPointError('Column water/static-energy budget failed.')
    base.saturation(t, p)
    return base.State(water, energy, soil), rain.sum(0), t, target, budget, rain, changes, closure

def year(domain, profile, settings, seed, state, local_air, mask, geometry, local_wind, checkpoint=None,
         save_month=None, should_stop=lambda: False, wind_mode='spatial', boundary_mode='reference', circulation=None):
    shape = domain.land.shape
    count = len(geometry.mass)
    if local_air.shape != (12, count)+shape or not np.isfinite(local_air).all() or mask.shape != shape or not mask.any():
        raise ValueError('Invalid local-air input or diagnostic mask.')
    if checkpoint is None:
        rain = np.zeros((12,)+shape)
        temp = np.zeros((12, count)+shape)
        refs = np.zeros_like(temp)
        totals = {}
        start_month = 0
        initial_water = float((state.water.sum(0)+state.soil).mean())
        initial_energy = float(state.energy.sum(0).mean())
        maxw = maxe = continuity = ledger_error = 0.
        steps = 0
        max_adjustment = max_raw_divergence = 0.
        layer_rain = np.zeros((12, count))
        thermal = np.zeros((12, len(PROCESSES), count))
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
        if layer_rain.shape != (12, count) or thermal.shape != (12, len(PROCESSES), count) or not np.isfinite(layer_rain).all() or not np.isfinite(thermal).all():
            raise ValueError('Invalid resumed process diagnostics.')
    storms = nested_events(domain, settings, seed, profile.storm_domain_width_m)
    projector = ColumnProjection(domain, geometry if circulation is None else circulation[0])
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
                flow = flow_at(domain, profile, settings, storms, tick, geometry, local_wind, projector, wind_mode=wind_mode, circulation=circulation)
                max_adjustment = max(max_adjustment, projector.last_info['barotropic_velocity_adjustment_max_m_s'])
                max_raw_divergence = max(max_raw_divergence, projector.last_info['raw_column_divergence_max_kg_m2_s'])
                limit = base.stable_step(flow, mass, domain)
            dt = step_length(t, limit, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded column step count exceeded.')
            state, p, temperature, target, b, by_layer, changes, residual = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry=geometry, boundary_mode=boundary_mode, circulation=circulation)
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
