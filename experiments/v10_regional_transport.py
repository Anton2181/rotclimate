"""Separate regional transport candidate; frozen clouds and upwind delegation.

The FCT advance body is copied from v10_parcel_condensation.advance, changing
only the transport call. Instantaneous rain/soil, heat exchange, cloud dose,
boundary caps and physical guards remain the original controls. Upwind calls
the original function directly. No regional integration at import time.
"""
from __future__ import annotations
import numpy as np
from experiments import v10_parcel_condensation as original
from experiments import v10_boundary_transport as transport
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES
base=original.base
core=original.core
coordinates=original.coordinates
MODES=original.MODES
PROCESSES=original.PROCESSES
ascending_condensate=original.ascending_condensate


def advance(state, domain, profile, settings, flow, dt, time_s, local_air=None,
            physics=True, geometry=None, boundary=None, condensation_mode="bulk", transport_scheme="coupled_fct"):
    if transport_scheme == "upwind":
        return original.advance(state, domain, profile, settings, flow, dt, time_s, local_air,
            physics=physics, geometry=geometry, boundary=boundary, condensation_mode=condensation_mode)
    if transport_scheme != "coupled_fct":
        raise ValueError("Unknown transport scheme.")
    if condensation_mode not in MODES:raise ValueError("Unknown parcel condensation mode.")
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
    if boundary is None or boundary.shape != mass.shape or not np.isfinite(boundary).all() or (boundary < 0).any():
        raise ValueError('Explicit finite nonnegative boundary humidity required.')
    if (boundary > .95*base.saturation(target, p)+1e-14).any():
        raise ValueError('Prepared boundary exceeds the local saturation cap.')
    bq = boundary
    initial_t = base.temperature(state.energy, mass, state.water, z)
    water, energy, wd, ed, work, changes, theta_error = transport.thermal_transport(
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
    parcel_rain = np.zeros_like(water)
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
        if condensation_mode != 'bulk':
            parcel_rain = ascending_condensate(state,settings,flow,dt,geometry,target,condensation_mode)
            if (water-parcel_rain).min()<0:
                raise FloatingPointError('Ascending parcel condensate exceeds transported water.')
            water = water-parcel_rain
        water, rain, t = base.adjust(water, energy, mass, z, p)
        rain = rain+parcel_rain
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
        incoming, outgoing = core.gross_boundary_transfers(state, flow, dt, domain, geometry, bq)
        if abs(outgoing-incoming-boundary_water) > 1e-9:
            raise FloatingPointError('Gross boundary fluxes disagree with net water transport.')
        budget.update(boundary_import_gross_mm=incoming, boundary_export_gross_mm=outgoing)
    if not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm']) > 1e-9 or abs(budget['energy_error_j_m2']) > 1e-5 or abs(theta_error) > 1e-7:
        raise FloatingPointError('Column water/static-energy budget failed.')
    base.saturation(t, p)
    return base.State(water, energy, soil), rain.sum(0), t, target, budget, rain, changes, closure, parcel_rain



def year(domain, profile, settings, state, local_air, mask, geometry, driver,
         checkpoint=None, save_month=None, should_stop=lambda: False, condensation_mode="bulk", time_factor=1., transport_scheme="coupled_fct"):
    """Frozen physical accounting with prepared piecewise-constant boundary water."""
    if transport_scheme == "upwind":
        return original.year(domain, profile, settings, state, local_air, mask, geometry, driver,
            checkpoint=checkpoint, save_month=save_month, should_stop=should_stop,
            condensation_mode=condensation_mode, time_factor=time_factor)
    if transport_scheme != "coupled_fct":
        raise ValueError("Unknown transport scheme.")
    if condensation_mode not in MODES or time_factor not in (1.,.5):raise ValueError('Invalid parcel mode/time factor.')
    parcel_totals = np.zeros((12,len(geometry.mass))) if checkpoint is None else np.array(checkpoint[-1]['parcel_rain_scored_land_mm'])
    if parcel_totals.shape != (12,len(geometry.mass)) or not np.isfinite(parcel_totals).all() or (parcel_totals<0).any():raise ValueError('Invalid parcel checkpoint.')
    shape = domain.land.shape;count = len(geometry.mass)
    if local_air.shape != (12, count)+shape or not np.isfinite(local_air).all() or mask.shape != shape or not mask.any():
        raise ValueError('Invalid event-forcing air input or diagnostic mask.')
    if checkpoint is None:
        rain = np.zeros((12,)+shape);temp = np.zeros((12, count)+shape);refs = np.zeros_like(temp)
        totals = {};start_month = 0;steps = 0
        initial_water = float((state.water.sum(0)+state.soil).mean());initial_energy = float(state.energy.sum(0).mean())
        maxw = maxe = continuity = ledger_error = 0.
        max_adjustment = max_raw_divergence = 0.
        layer_rain = np.zeros((12, count));thermal = np.zeros((12, len(PROCESSES), count))
        imports = np.zeros(12)
    else:
        state, rain, temp, refs, info = checkpoint
        totals = info['totals'].copy();start_month = info['month']
        initial_water,initial_energy = info['initial_water'],info['initial_energy']
        maxw,maxe,continuity,steps = (info[k] for k in ('maxw', 'maxe', 'continuity', 'steps'))
        d = info['diagnostics'];layer_rain = np.array(d['layer_rain_scored_land_mm']);thermal = np.array(d['temperature_changes_scored_land_c'])
        imports = np.array(d['monthly_boundary_import_gross_mm'], float)
        ledger_error = d['max_step_temperature_ledger_error_c'];max_adjustment = d['max_projection_adjustment_m_s']
        max_raw_divergence = d['max_raw_column_divergence_kg_m2_s']
        if imports.shape != (12,) or not np.isfinite(imports).all() or (imports < 0).any() or not np.allclose(imports[:start_month], driver.monthly_targets[:start_month], atol=1e-7, rtol=0):
            raise ValueError('Resumed monthly import control failed.')
    for month in range(start_month, 12):
        t = float(EDGES[month]);flow = None;next_forcing = t
        while t < EDGES[month+1]-1e-6:
            if steps % 32 == 0 and should_stop():
                raise base.BudgetStop()
            if flow is None or t >= next_forcing-1e-6:
                flow,boundary,next_forcing = driver.at(t)
                limit = base.stable_step(flow, geometry.mass, domain)
                max_adjustment = max(max_adjustment, driver.last_info['barotropic_velocity_adjustment_max_m_s'])
                max_raw_divergence = max(max_raw_divergence, driver.last_info['raw_column_divergence_max_kg_m2_s'])
            dt = step_length(t, limit*time_factor, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded event-forcing step count exceeded.')
            state,p,temperature,target,b,by_layer,changes,residual,parcel_rain = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry=geometry, boundary=boundary, condensation_mode=condensation_mode)
            parcel_totals[month] += parcel_rain[:,mask].mean(1)
            rain[month] += p;temp[month] += temperature*dt;refs[month] += target*dt
            layer_rain[month] += by_layer[:, mask].mean(1);thermal[month] += changes[:, :, mask].mean(2)
            imports[month] += b['boundary_import_gross_mm']
            for key,value in b.items():
                if key not in ('water_error_mm', 'energy_error_j_m2'):
                    totals[key] = totals.get(key, 0.)+value
            maxw = max(maxw, abs(b['water_error_mm']));maxe = max(maxe, abs(b['energy_error_j_m2']))
            continuity = max(continuity, flow.continuity);ledger_error = max(ledger_error, residual)
            t += dt;steps += 1
        if abs(imports[month]-driver.monthly_targets[month]) > 1e-7:
            raise FloatingPointError('Actual integrated monthly gross import differs from its fixed target.')
        duration = EDGES[month+1]-EDGES[month];temp[month] /= duration;refs[month] /= duration
        info = dict(month=month+1, totals=totals, initial_water=initial_water, initial_energy=initial_energy,
            maxw=maxw, maxe=maxe, continuity=continuity, steps=steps,
            diagnostics={'processes': list(PROCESSES), 'layer_rain_scored_land_mm': layer_rain.tolist(),
                'temperature_changes_scored_land_c': thermal.tolist(), 'max_step_temperature_ledger_error_c': ledger_error,
                'max_projection_adjustment_m_s': max_adjustment, 'max_raw_column_divergence_kg_m2_s': max_raw_divergence,
                'monthly_boundary_import_gross_mm': imports.tolist(), 'monthly_boundary_import_target_mm': driver.monthly_targets.tolist(),
                'note': 'Signed thermal changes are cumulative, not temperature error. Projection diagnostics refer to the original projected components; centered event anomalies remain column-balanced. Gross import is verified at every month boundary.'})
        info['parcel_rain_scored_land_mm'] = parcel_totals.tolist()
        if save_month:
            save_month(state, rain, temp, refs, info)
    wf = float((state.water.sum(0)+state.soil).mean());ef = float(state.energy.sum(0).mean())
    we = wf-initial_water-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2']+totals['prescribed_flow_work_j_m2'])
    if abs(we) > 1e-6 or abs(ee) > 1:
        raise FloatingPointError('Annual event-forcing budgets failed.')
    info['budget'] = dict(totals, annual_water_error_mm=we, annual_energy_error_j_m2=ee,
        max_step_water_error_mm=maxw, max_step_energy_error_j_m2=maxe, max_air_continuity_kg_m2_s=continuity, steps=steps)
    return state, rain, temp, refs, info
