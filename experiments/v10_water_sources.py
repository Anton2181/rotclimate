"""Passive last-vapor-source tags around the frozen pressure-law step.

Tags never feed back into water, energy, evaporation, rain, soil or circulation.
Land evaporation receives a new land tag: this is last entry to atmospheric
vapor, not original molecular ancestry through soil recycling.
"""
from dataclasses import dataclass
import numpy as np
from experiments import v10_pressure_thermo as model
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, interpolate_months, divergence
base = model.base
SOURCES = ('initial', 'boundary', 'ocean_evaporation', 'land_recycling')
TAG_KEYS = ('import_mm', 'export_mm', 'evaporation_mm', 'rain_mm', 'numerical_adjustment_mm')


@dataclass
class State:
    water: np.ndarray
    energy: np.ndarray
    soil: np.ndarray
    tags: np.ndarray  # source, layer, y, x; mm


def initial_state(domain, profile, settings, geometry, local_air):
    physical = model.initial_state(domain, profile, settings, geometry, local_air)
    tags = np.zeros((len(SOURCES),)+physical.water.shape)
    tags[0] = physical.water
    return State(physical.water, physical.energy, physical.soil, tags)


def validate_tags(state):
    if state.tags.shape != (len(SOURCES),)+state.water.shape or not np.isfinite(state.tags).all() or state.tags.min() < 0:
        raise ValueError('Invalid vapor-source stores.')
    if abs(state.tags.sum(0)-state.water).max() > 1e-9:
        raise ValueError('Vapor sources do not sum to physical water.')


def face_transfers(fx, fy, dt, domain):
    """Gross boundary inputs/outputs in domain-mean atmospheric mm."""
    ny, nx = domain.land.shape
    signed = (fx[..., 0]/domain.dx, -fx[..., -1]/domain.dx,
        fy[..., 0, :]/domain.dy, -fy[..., -1, :]/domain.dy)
    incoming = dt*sum(np.maximum(a, 0).sum() for a in signed)/(ny*nx)
    outgoing = dt*sum(np.maximum(-a, 0).sum() for a in signed)/(ny*nx)
    return float(incoming), float(outgoing)


def advance(state, domain, profile, settings, flow, dt, time_s, local_air,
            geometry, physics=True):
    validate_tags(state)
    physical = model.advance(state, domain, profile, settings, flow, dt, time_s,
        local_air, physics=physics, geometry=geometry)
    new, rain, temperature, target, budget, by_layer, changes, residual = physical
    bq = np.broadcast_to(interpolate_months(profile.mixing_ratio, time_s)[:, None, None]*settings.humidity_scale, target.shape)
    bq = np.minimum(bq, base.saturation(target, geometry.pressure)*.95)
    tags = np.empty_like(state.tags)
    ledger = {key: np.zeros(len(SOURCES)) for key in TAG_KEYS}
    for source in range(len(SOURCES)):
        boundary = bq if source == 1 else np.zeros_like(bq)
        fx, fy = base.flux(state.tags[source], geometry.mass, flow.x, flow.y, boundary)
        div = divergence(fx, fy, domain.dx, domain.dy)
        ratio = state.tags[source]/geometry.mass
        exchange = flow.vertical*np.where(flow.vertical >= 0, ratio[:-1], ratio[1:])
        div += model.coordinates.vertical_divergence(exchange, geometry.mass.shape)
        moved = state.tags[source]-dt*div
        if moved.min() < -1e-11:
            raise FloatingPointError('Negative transported source tracer.')
        tags[source] = np.maximum(moved, 0.)
        ledger['numerical_adjustment_mm'][source] += float((tags[source]-moved).sum(0).mean())
        ledger['import_mm'][source], ledger['export_mm'][source] = face_transfers(fx, fy, dt, domain)
    # Infer the unchanged step's vapor injection before its proportional rainout.
    # Only the lowest layer receives evaporation in the frozen implementation.
    available = new.water+by_layer
    injection = available-tags.sum(0)
    if abs(injection[1:]).max() > 1e-9 or injection[0].min() < -1e-9:
        raise FloatingPointError('Source tags cannot explain the physical vapor injection.')
    evaporation = np.maximum(injection[0], 0.)
    ocean = np.where(~domain.land, evaporation, 0.)
    land = np.where(domain.land, evaporation, 0.)
    for source, values, name in ((2, ocean, 'ocean_evaporation_mm'), (3, land, 'land_evaporation_mm')):
        ledger['evaporation_mm'][source] = float(values.mean())
        if abs(values.mean()-budget[name]) > 1e-9:
            raise FloatingPointError('Inferred evaporation disagrees with the unchanged physical budget.')
        tags[source, 0] += values
    # Roundoff reconciliation is explicit and bounded, never fed to the model.
    before = tags.copy()
    total = tags.sum(0)
    scale = np.divide(available, total, out=np.zeros_like(total), where=total > 0)
    tags *= scale[None]
    empty = total == 0
    tags[0, empty] = available[empty]
    adjustment = tags-before
    if abs(adjustment).max() > 1e-9:
        raise FloatingPointError('Source reconciliation exceeds the roundoff allowance.')
    ledger['numerical_adjustment_mm'] += adjustment.sum(axis=(1, 2, 3))/(domain.land.size)
    fraction = np.divide(tags, available[None], out=np.zeros_like(tags), where=available[None] > 0)
    tagged_rain = fraction*by_layer[None]
    tags = fraction*new.water[None]
    ledger['rain_mm'] = tagged_rain.sum(axis=(1, 2, 3))/domain.land.size
    delta = (tags-state.tags).sum(axis=(1, 2, 3))/domain.land.size
    errors = delta-(ledger['import_mm']-ledger['export_mm']+ledger['evaporation_mm']-
        ledger['rain_mm']+ledger['numerical_adjustment_mm'])
    if abs(errors).max() > 1e-9 or abs(tagged_rain.sum(0)-by_layer).max() > 1e-9:
        raise FloatingPointError('Per-source atmospheric water ledger failed.')
    tagged = State(new.water, new.energy, new.soil, tags)
    validate_tags(tagged)
    ledger['max_step_source_error_mm'] = float(abs(errors).max())
    ledger['max_step_reconciliation_mm'] = float(abs(adjustment).max())
    return (tagged, rain, temperature, target, budget, by_layer, changes, residual,
        tagged_rain.sum(1), ledger)


def physical_record(record):
    return (*record[:4], record[-1])


def year(domain, profile, settings, seed, state, local_air, mask, geometry, local_wind,
         checkpoint=None, save_month=None, should_stop=lambda: False, wind_mode='spatial'):
    """Frozen annual time/physics order with additional passive diagnostics."""
    shape = domain.land.shape
    if local_air.shape != (12, 4)+shape or not np.isfinite(local_air).all() or mask.shape != shape or not mask.any():
        raise ValueError('Invalid source experiment inputs.')
    if checkpoint is None:
        rain = np.zeros((12,)+shape);temp = np.zeros((12, 4)+shape);refs = np.zeros_like(temp)
        tagged_rain = np.zeros((12, len(SOURCES))+shape)
        totals = {};start_month = 0
        initial_water = float((state.water.sum(0)+state.soil).mean())
        initial_energy = float(state.energy.sum(0).mean())
        maxw = maxe = continuity = ledger_error = 0.;steps = 0
        max_adjustment = max_raw_divergence = 0.
        layer_rain = np.zeros((12, 4));thermal = np.zeros((12, len(model.PROCESSES), 4))
        tag_totals = {key: np.zeros(len(SOURCES)) for key in TAG_KEYS}
        initial_tags = state.tags.sum(axis=(1, 2, 3))/domain.land.size
        max_tag_error = max_reconciliation = 0.
    else:
        state, rain, temp, refs, tagged_rain, info = checkpoint
        totals = info['totals'].copy();start_month = info['month']
        initial_water, initial_energy = info['initial_water'], info['initial_energy']
        maxw, maxe, continuity, steps = (info[k] for k in ('maxw', 'maxe', 'continuity', 'steps'))
        layer_rain = np.array(info['diagnostics']['layer_rain_scored_land_mm'])
        thermal = np.array(info['diagnostics']['temperature_changes_scored_land_c'])
        ledger_error = info['diagnostics']['max_step_temperature_ledger_error_c']
        max_adjustment = info['diagnostics']['max_projection_adjustment_m_s']
        max_raw_divergence = info['diagnostics']['max_raw_column_divergence_kg_m2_s']
        tag_totals = {key: np.array(info['sources']['totals'][key]) for key in TAG_KEYS}
        initial_tags = np.array(info['sources']['initial_store_mm'])
        max_tag_error = info['sources']['max_step_error_mm']
        max_reconciliation = info['sources']['max_step_reconciliation_mm']
    validate_tags(state)
    storms = model.nested_events(domain, settings, seed, profile.storm_domain_width_m)
    projector = model.ColumnProjection(domain, geometry);mass = geometry.mass
    for month in range(start_month, 12):
        t = float(EDGES[month]);flow = None;next_forcing = t
        while t < EDGES[month+1]-1e-6:
            if steps % 32 == 0 and should_stop():
                raise base.BudgetStop()
            if flow is None or t >= next_forcing-1e-6:
                tick = np.floor((t+1e-6)/10800.)*10800.;next_forcing = tick+10800.
                flow = model.flow_at(domain, profile, settings, storms, tick, geometry,
                    local_wind, projector, wind_mode=wind_mode)
                max_adjustment = max(max_adjustment, projector.last_info['barotropic_velocity_adjustment_max_m_s'])
                max_raw_divergence = max(max_raw_divergence, projector.last_info['raw_column_divergence_max_kg_m2_s'])
                limit = base.stable_step(flow, mass, domain)
            dt = step_length(t, limit, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded column step count exceeded.')
            state, p, temperature, target, b, by_layer, changes, residual, pr, tags = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry)
            rain[month] += p;temp[month] += temperature*dt;refs[month] += target*dt
            tagged_rain[month] += pr
            layer_rain[month] += by_layer[:, mask].mean(1)
            thermal[month] += changes[:, :, mask].mean(2)
            for key, value in b.items():
                if key not in ('water_error_mm', 'energy_error_j_m2'):
                    totals[key] = totals.get(key, 0.)+value
            for key in TAG_KEYS:
                tag_totals[key] += tags[key]
            max_tag_error = max(max_tag_error, tags['max_step_source_error_mm'])
            max_reconciliation = max(max_reconciliation, tags['max_step_reconciliation_mm'])
            maxw = max(maxw, abs(b['water_error_mm']));maxe = max(maxe, abs(b['energy_error_j_m2']))
            continuity = max(continuity, flow.continuity);ledger_error = max(ledger_error, residual)
            t += dt;steps += 1
        duration = EDGES[month+1]-EDGES[month]
        temp[month] /= duration;refs[month] /= duration
        source_info = {'names': list(SOURCES), 'totals': {k:v.tolist() for k,v in tag_totals.items()},
            'initial_store_mm': initial_tags.tolist(), 'max_step_error_mm': max_tag_error,
            'max_step_reconciliation_mm': max_reconciliation}
        info = dict(month=month+1, totals=totals, initial_water=initial_water, initial_energy=initial_energy,
            maxw=maxw, maxe=maxe, continuity=continuity, steps=steps, sources=source_info,
            diagnostics={'processes': list(model.PROCESSES), 'layer_rain_scored_land_mm': layer_rain.tolist(),
            'temperature_changes_scored_land_c': thermal.tolist(), 'max_step_temperature_ledger_error_c': ledger_error,
            'max_projection_adjustment_m_s': max_adjustment,
            'max_raw_column_divergence_kg_m2_s': max_raw_divergence})
        if save_month:
            save_month(state, rain, temp, refs, tagged_rain, info)
    wf = float((state.water.sum(0)+state.soil).mean());ef = float(state.energy.sum(0).mean())
    we = wf-initial_water-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2']+totals['prescribed_flow_work_j_m2'])
    end_tags = state.tags.sum(axis=(1, 2, 3))/domain.land.size
    error = end_tags-initial_tags-(tag_totals['import_mm']-tag_totals['export_mm']+
        tag_totals['evaporation_mm']-tag_totals['rain_mm']+tag_totals['numerical_adjustment_mm'])
    if abs(we) > 1e-6 or abs(ee) > 1 or abs(error).max() > 1e-6:
        raise FloatingPointError('Annual physical/source budgets failed.')
    info['sources'].update(end_store_mm=end_tags.tolist(), annual_error_mm=error.tolist())
    info['budget'] = dict(totals, annual_water_error_mm=we, annual_energy_error_j_m2=ee,
        max_step_water_error_mm=maxw, max_step_energy_error_j_m2=maxe,
        max_air_continuity_kg_m2_s=continuity, steps=steps)
    return state, rain, temp, refs, tagged_rain, info
