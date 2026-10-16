"""Fixed-monthly-circulation, matched-gross-import event sensitivity.

Synthetic mechanism test, not observed storm statistics or a complete front.
Frozen sources stay intact. Boundary water is held over each forcing interval;
thermal targets retain their original interpolation and diagnosed flow work.
"""
from __future__ import annotations
from dataclasses import replace
import numpy as np
from experiments import v10_split_column as core
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, CENTERS
base = core.base
coordinates = core.coordinates
PROCESSES = core.PROCESSES
INTERVAL = 10800.
AMPLITUDES = (1., 16.)
TIMINGS = ('steady', 'aligned', 'shifted')
PULSE_AMPLITUDE = .4


def boundary_mask(shape):
    mask = np.zeros(shape, bool)
    mask[[0, -1]] = True;mask[:, [0, -1]] = True
    return mask


def incoming_coefficients(flow, domain):
    """Gross incoming dry-air flux per unique boundary cell; corners add faces."""
    values = np.zeros((len(flow.x),)+domain.land.shape)
    values[..., 0] += np.maximum(flow.x[..., 0], 0)/domain.dx
    values[..., -1] += np.maximum(-flow.x[..., -1], 0)/domain.dx
    values[..., 0, :] += np.maximum(flow.y[..., 0, :], 0)/domain.dy
    values[..., -1, :] += np.maximum(-flow.y[..., -1, :], 0)/domain.dy
    return values[:, boundary_mask(domain.land.shape)]/domain.land.size


def centered_flow(full, convergence, mean_x, mean_y, amplitude, domain):
    if amplitude == 1.:
        return full
    if not np.isfinite(amplitude) or amplitude < 1:
        raise ValueError('Event amplitude must be finite and at least one.')
    x = full.x+(amplitude-1)*(convergence.x-mean_x)
    y = full.y+(amplitude-1)*(convergence.y-mean_y)
    return base.balanced(x, y, domain.dx, domain.dy)


def pulse_pair(score, amplitude=PULSE_AMPLITUDE):
    score = np.asarray(score, float)
    if score.ndim not in (1,2) or score.shape[0] == 0 or not np.isfinite(score).all() or (score < 0).any() or not 0 <= amplitude < 1:
        raise ValueError('Need a finite nonnegative event signal and bounded amplitude.')
    centered = score-score.mean(axis=0,keepdims=True)
    scale = np.max(abs(centered),axis=0,keepdims=True)
    normalized = np.divide(centered,scale,out=np.zeros_like(centered),where=scale > 1e-20)
    aligned = 1+amplitude*normalized
    return aligned, np.roll(aligned, len(aligned)//2,axis=0)


def match_import(raw, caps, coefficients, interval_s, target):
    """Capped monotone solve, matching monthly gross import, not concentration."""
    if raw.shape != caps.shape or coefficients.shape != raw.shape or not all(np.isfinite(a).all() for a in (raw, caps, coefficients)):
        raise ValueError('Invalid boundary dose arrays.')
    if min(raw.min(), caps.min(), coefficients.min(), target) < 0 or not np.isfinite(target) or not np.isfinite(interval_s) or interval_s <= 0:
        raise ValueError('Invalid boundary dose values.')
    def dose(value):
        return float(np.sum(coefficients*value)*interval_s)
    ceiling = np.where(raw > 0, caps, 0.)
    maximum = dose(ceiling)
    tolerance = max(1e-10, target*1e-12)
    if target > maximum+tolerance:
        raise ValueError('Monthly gross-import target is infeasible under local saturation caps.')
    if target == 0:
        return np.zeros_like(raw), 0.
    if abs(dose(np.minimum(raw, caps))-target) <= tolerance:
        return np.minimum(raw, caps), 1.
    lo,hi = 0.,1.
    while dose(np.minimum(hi*raw, caps)) < target:
        hi *= 2
        if hi > 1e8:
            raise ValueError('Cannot bracket a feasible boundary dose.')
    for _ in range(70):
        mid = .5*(lo+hi)
        if dose(np.minimum(mid*raw, caps)) < target:
            lo = mid
        else:
            hi = mid
    value = np.minimum(.5*(lo+hi)*raw, caps)
    if abs(dose(value)-target) > tolerance:
        raise ValueError('Gross-import normalization failed.')
    return value, .5*(lo+hi)


def native_flows(case, profile, settings, geometry, circulation, events, projector, time_s):
    kwargs = dict(projector=projector, wind_mode='spatial', circulation=circulation)
    full = core.flow_at(case.domain, profile, settings, events, time_s, geometry, circulation[3], **kwargs)
    info = projector.last_info.copy()
    no_convergence = core.flow_at(case.domain, profile, replace(settings, storm_convergence_ms=0.), events,
        time_s, geometry, circulation[3], **kwargs)
    convergence = base.balanced(full.x-no_convergence.x, full.y-no_convergence.y, case.domain.dx, case.domain.dy)
    return full, convergence, info


def variant_key(amplitude, timing):
    return f'lift{int(amplitude)}_{timing}'


def build_calendar(domain, geometry, flows, ratios, safe_caps, coast_mask, edges=EDGES, interval=INTERVAL):
    """Independent circulation/boundary queries only; never advances a state."""
    if len(edges) != 13 or edges[0] != 0 or (np.diff(edges) <= 0).any() or not np.allclose(np.diff(edges)/interval, np.round(np.diff(edges)/interval)):
        raise ValueError('Monthly edges must align with the forcing clock.')
    if coast_mask.shape != domain.land.shape or not coast_mask.any():
        raise ValueError('Need a geographic coastal mask, independent of observed rain.')
    mask = boundary_mask(domain.land.shape);times = np.arange(0., edges[-1], interval)
    month_index = np.searchsorted(edges[1:], times, side='right')
    samples = np.bincount(month_index, minlength=12)
    xshape = (len(geometry.mass), domain.land.shape[0], domain.land.shape[1]+1)
    yshape = (len(geometry.mass), domain.land.shape[0]+1, domain.land.shape[1])
    mean_x = np.zeros((12,)+xshape);mean_y = np.zeros((12,)+yshape)
    shape = (len(times), len(geometry.mass), int(mask.sum()))
    raw = np.empty(shape);caps = np.empty(shape);coefficients = {a:np.empty(shape) for a in AMPLITUDES}
    score = np.zeros((len(times),int(mask.sum())));maximum_continuity = 0.
    for i,t in enumerate(times):
        full, conv, _ = flows(t);month = month_index[i]
        mean_x[month] += conv.x;mean_y[month] += conv.y
        score[i] = np.maximum(conv.vertical[2,mask],0)
        caps[i] = safe_caps(t, t+interval)[:, mask]
        raw[i] = np.minimum(ratios(t+.5*interval)[:, mask], caps[i])
        coefficients[1.][i] = incoming_coefficients(full, domain)
        maximum_continuity = max(maximum_continuity, full.continuity, conv.continuity)
    mean_x /= samples[:, None, None, None];mean_y /= samples[:, None, None, None]
    mean_difference_x = np.zeros_like(mean_x);mean_difference_y = np.zeros_like(mean_y)
    from experiments.v10_mass_projection import face_masses
    mx,my = face_masses(geometry.mass)
    signed = {a: np.zeros(12) for a in AMPLITUDES};positive = {a: np.zeros(12) for a in AMPLITUDES}
    ascent_trace = {a: np.zeros(len(times)) for a in AMPLITUDES}
    maximum_speed = {a: 0. for a in AMPLITUDES};minimum_step = {a: float('inf') for a in AMPLITUDES}
    for i,t in enumerate(times):
        full, conv, _ = flows(t);month = month_index[i]
        enhanced = centered_flow(full, conv, mean_x[month], mean_y[month], AMPLITUDES[1], domain)
        coefficients[AMPLITUDES[1]][i] = incoming_coefficients(enhanced, domain)
        mean_difference_x[month] += enhanced.x-full.x;mean_difference_y[month] += enhanced.y-full.y
        for a,f in ((1., full), (AMPLITUDES[1], enhanced)):
            w = base.G*f.vertical[2, coast_mask]
            signed[a][month] += w.mean();positive[a][month] += np.maximum(w, 0).mean()
            ascent_trace[a][i] = np.maximum(w, 0).mean()
            maximum_speed[a] = max(maximum_speed[a], float(np.max(abs(f.x/mx))), float(np.max(abs(f.y/my))))
            minimum_step[a] = min(minimum_step[a], base.stable_step(f, geometry.mass, domain))
            maximum_continuity = max(maximum_continuity, f.continuity)
    mean_velocity_error = max(float(abs(mean_difference_x/samples[:, None, None, None]/mx).max()),
        float(abs(mean_difference_y/samples[:, None, None, None]/my).max()))
    if mean_velocity_error > 1e-10:
        raise ValueError('Monthly dry-circulation mean changed.')
    arrays = dict(times=times, edges=np.array(edges), mean_convergence_x=mean_x, mean_convergence_y=mean_y,
        boundary_mask=mask, pulse_score=score)
    stats = {};targets = np.zeros(12);pulse_aligned = np.ones_like(score);pulse_shifted = np.ones_like(score)
    for month in range(12):
        selected = month_index == month
        targets[month] = np.sum(coefficients[1.][selected]*raw[selected])*interval
        pulse_aligned[selected],pulse_shifted[selected] = pulse_pair(score[selected])
    arrays.update(monthly_import_target_mm=targets, pulse_aligned=pulse_aligned, pulse_shifted=pulse_shifted)
    arrays.update({f'coastal_positive_ascent_lift{int(a)}_pa_s':values for a,values in ascent_trace.items()})
    max_match_error = 0.
    for amplitude in AMPLITUDES:
        for timing in TIMINGS:
            key = variant_key(amplitude, timing);values = np.empty(shape);scales = [];means = [];variances = [];clipped = [];correlations = []
            pattern = np.ones_like(score) if timing == 'steady' else arrays['pulse_'+timing]
            for month in range(12):
                selected = month_index == month;requested = raw[selected]*pattern[selected, None, :]
                q,scale = match_import(requested, caps[selected], coefficients[amplitude][selected], interval, targets[month])
                values[selected] = q;scales.append(scale)
                means.append(q.mean(axis=(0, 2)).tolist());variances.append(q.var(axis=(0, 2)).tolist())
                clipped.append(float(((scale*requested > caps[selected]+1e-15) & (requested > 0)).mean()))
                incoming_rate = np.sum(coefficients[amplitude][selected]*q,axis=(1,2))
                ascent = ascent_trace[amplitude][selected]
                correlations.append(float(np.corrcoef(incoming_rate,ascent)[0,1]) if incoming_rate.std() > 1e-15 and ascent.std() > 1e-15 else None)
                max_match_error = max(max_match_error, abs(np.sum(coefficients[amplitude][selected]*q)*interval-targets[month]))
            arrays['boundary_'+key] = values
            stats[key] = {'monthly_normalization_scale': scales, 'monthly_boundary_mean_r_by_layer': means,
                'monthly_boundary_variance_r_by_layer': variances, 'monthly_capped_fraction': clipped,
                'monthly_import_rate_vs_coastal_positive_ascent_correlation': correlations,
                'maximum_face_component_speed_m_s': maximum_speed[amplitude], 'minimum_stable_step_s': minimum_step[amplitude],
                'monthly_coastal_signed_ascent_pa_s': (signed[amplitude]/samples).tolist(),
                'monthly_coastal_positive_ascent_pa_s': (positive[amplitude]/samples).tolist()}
    return arrays, {'variants': stats, 'maximum_monthly_import_error_mm': max_match_error,
        'maximum_monthly_mean_face_velocity_change_m_s': mean_velocity_error,
        'maximum_air_continuity_kg_m2_s': maximum_continuity,
        'monthly_import_target_mm': targets.tolist(), 'forcing_ticks': len(times), 'state_advances': 0,
        'humidity_control': 'Same integrated monthly gross boundary import. At each boundary cell, a nominal moisture pulse follows the positive convergence-only storm ascent there; its timing control permutes identical pulse values within the month. Actual capped/normalized humidity means and variance are diagnosed, not claimed equal.',
        'circulation_control': 'Amplify convergence-only fluctuations about their exact discrete monthly face mean. Rotation, event catalogue and monthly mean full circulation retained.'}


def prepare_calendar(case, profile, setting, geometry, air, circulation):
    projector = core.ColumnProjection(case.domain, circulation[0])
    events = core.nested_events(case.domain, setting, 41, profile.storm_domain_width_m)
    def flows(t):
        return native_flows(case, profile, setting, geometry, circulation, events, projector, t)
    def ratios(t):
        return core.boundary_ratio(case.domain, profile, setting, geometry, air, t)
    def caps(start, end):
        # T is piecewise linear between monthly centers; saturation is monotone.
        # Include every interpolation knot, including the periodic year boundary.
        knots = CENTERS[(CENTERS > start) & (CENTERS < end)]
        targets = [core.coordinates.targets(case.domain, profile, setting, t, air)[0] for t in (start, *knots, end)]
        return .95*base.saturation(np.min(targets, axis=0), geometry.pressure)
    coast = case.domain.land & (case.coast_distance_km < 150.)
    arrays, diagnostics = build_calendar(case.domain, geometry, flows, ratios, caps, coast)
    diagnostics['event_count'] = len(events)
    return arrays, diagnostics


class Driver:
    def __init__(self, arrays, case, profile, setting, geometry, air, circulation, amplitude, timing):
        self.arrays = arrays;self.case = case;self.profile = profile;self.setting = setting
        self.geometry = geometry;self.air = air;self.circulation = circulation
        self.amplitude = amplitude;self.timing = timing
        self.boundary_values = arrays['boundary_'+variant_key(amplitude, timing)]
        self.monthly_targets = arrays['monthly_import_target_mm']
        self.projector = core.ColumnProjection(case.domain, circulation[0])
        self.events = core.nested_events(case.domain, setting, 41, profile.storm_domain_width_m)
        self.last_info = {}

    def at(self, time_s):
        index = int(np.floor((time_s+1e-6)/INTERVAL))
        if not 0 <= index < len(self.arrays['times']):
            raise ValueError('Forcing time outside the prepared calendar.')
        tick = self.arrays['times'][index];month = np.searchsorted(self.arrays['edges'][1:], tick, side='right')
        if self.amplitude == 1.:
            flow = core.flow_at(self.case.domain, self.profile, self.setting, self.events, tick,
                self.geometry, self.circulation[3], self.projector, wind_mode='spatial', circulation=self.circulation)
            self.last_info = self.projector.last_info.copy()
        else:
            full, conv, self.last_info = native_flows(self.case, self.profile, self.setting,
                self.geometry, self.circulation, self.events, self.projector, tick)
            flow = centered_flow(full, conv, self.arrays['mean_convergence_x'][month],
                self.arrays['mean_convergence_y'][month], self.amplitude, self.case.domain)
        boundary = np.zeros_like(self.geometry.mass)
        boundary[:, self.arrays['boundary_mask']] = self.boundary_values[index]
        return flow, boundary, tick+INTERVAL


# Static copy of the frozen step, with an explicit prepared boundary argument.
def advance(state, domain, profile, settings, flow, dt, time_s, local_air=None,
            physics=True, geometry=None, boundary=None):
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
    water, energy, wd, ed, work, changes, theta_error = core.thermal_transport(
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
        incoming, outgoing = core.gross_boundary_transfers(state, flow, dt, domain, geometry, bq)
        if abs(outgoing-incoming-boundary_water) > 1e-9:
            raise FloatingPointError('Gross boundary fluxes disagree with net water transport.')
        budget.update(boundary_import_gross_mm=incoming, boundary_export_gross_mm=outgoing)
    if not np.isfinite(list(budget.values())).all() or abs(budget['water_error_mm']) > 1e-9 or abs(budget['energy_error_j_m2']) > 1e-5 or abs(theta_error) > 1e-7:
        raise FloatingPointError('Column water/static-energy budget failed.')
    base.saturation(t, p)
    return base.State(water, energy, soil), rain.sum(0), t, target, budget, rain, changes, closure


def year(domain, profile, settings, state, local_air, mask, geometry, driver,
         checkpoint=None, save_month=None, should_stop=lambda: False):
    """Frozen physical accounting with prepared piecewise-constant boundary water."""
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
            dt = step_length(t, limit, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded event-forcing step count exceeded.')
            state,p,temperature,target,b,by_layer,changes,residual = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry=geometry, boundary=boundary)
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
