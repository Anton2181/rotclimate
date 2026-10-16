"""Spatial monthly reference winds, with frozen mass projection/thermodynamics.

Only the mean wind field changes. Boundary humidity remains the same offshore
profile; synthetic storms do not acquire observed heat/moisture covariance.
This is an Earth circulation mechanism test, not fantasy forcing.
"""
import numpy as np
from dataclasses import replace
from experiments import v10_mass_projection as mass_model
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, interpolate_months
base = mass_model.base
advance = mass_model.advance
initial_state = mass_model.initial_state
PROCESSES = mass_model.PROCESSES
ColumnProjection = mass_model.ColumnProjection
nested_events = mass_model.nested_events


def sample_bilinear(field, longitude, latitude, pressure_hpa):
    """Bilinear horizontal / log-pressure sampling; no edge extrapolation.

    Unwrap longitude around the target domain, handling the Iberia zero meridian.
    Smooth horizontal interpolation avoids steps at nearest-native-cell borders.
    It adds no resolved information to the coarse pressure-level reference.
    """
    lon, lat = np.asarray(longitude), np.asarray(latitude)
    pressure = np.broadcast_to(pressure_hpa, lon.shape)
    if lon.shape != lat.shape or not all(np.isfinite(a).all() for a in (lon, lat, pressure)):
        raise ValueError('Invalid sampling coordinates.')
    center = float(np.median(lon))
    unwrap = lambda a: center+(a-center+180)%360-180
    native_lon = unwrap(field.longitude)
    order = np.argsort(native_lon)
    xs = native_lon[order];ys = field.latitude[::-1]
    x = unwrap(lon);y = lat
    levels = np.log(field.pressure_hpa[::-1]);p = np.log(pressure)
    if (np.diff(xs) <= 0).any() or (np.diff(ys) <= 0).any() or (np.diff(levels) <= 0).any():
        raise ValueError('Invalid ordered reference axes.')
    if x.min() < xs[0] or x.max() > xs[-1] or y.min() < ys[0] or y.max() > ys[-1] or p.min() < levels[0] or p.max() > levels[-1]:
        raise ValueError('Spatial reference does not cover the requested coordinates/pressure.')
    ix = np.clip(np.searchsorted(xs, x)-1, 0, len(xs)-2)
    iy = np.clip(np.searchsorted(ys, y)-1, 0, len(ys)-2)
    ip = np.clip(np.searchsorted(levels, p)-1, 0, len(levels)-2)
    fx = (x-xs[ix])/(xs[ix+1]-xs[ix])
    fy = (y-ys[iy])/(ys[iy+1]-ys[iy])
    fp = (p-levels[ip])/(levels[ip+1]-levels[ip])
    values = field.values[:, ::-1, ::-1, :][..., order]
    result = np.zeros((values.shape[0],)+lon.shape)
    for dy, wy in ((0, 1-fy), (1, fy)):
        for dx, wx in ((0, 1-fx), (1, fx)):
            lower = values[:, ip, iy+dy, ix+dx]
            upper = values[:, ip+1, iy+dy, ix+dx]
            result += wx*wy*((1-fp)*lower+fp*upper)
    if not np.isfinite(result).all():
        raise ValueError('Missing spatial pressure-level reference.')
    return result


def prepare_wind(case, geometry, fields):
    components = []
    for variable in ('uwnd', 'vwnd'):
        components.append(np.stack([sample_bilinear(fields[case.domain.name, variable],
            case.longitude, case.domain.latitude, pressure/100) for pressure in geometry.pressure], axis=1))
    return np.stack(components, axis=1)  # month, east/north component, layer, y, x


def flow_at(domain, profile, settings, storms, time_s, geometry, local_wind, projector=None):
    if not settings.observed_wind or local_wind.shape != (12, 2, 4)+domain.land.shape or not np.isfinite(local_wind).all():
        raise ValueError('Spatial-wind experiment requires finite monthly reference winds.')
    if projector is None:
        projector = ColumnProjection(domain, geometry)
    u, north = interpolate_months(local_wind, time_s)
    uf, _ = mass_model.face_masses(u)
    _, vf = mass_model.face_masses(-north)
    reference_mass = (base.FRACTIONS*mass_model.coordinates.P0/base.G)[:, None, None]
    x = uf*reference_mass;y = vf*reference_mass
    # Same finite-depth terrain response as the paired uniform-wind controls.
    if settings.terrain != 'none':
        drag = 1/(1+(np.maximum(domain.elevation_m, 0)/settings.terrain_drag_height_m)**2)
        dragx = np.pad(.5*(drag[:, :-1]+drag[:, 1:]), ((0, 0), (1, 1)), mode='edge')
        dragy = np.pad(.5*(drag[:-1]+drag[1:]), ((1, 1), (0, 0)), mode='edge')
        dx = x[0]*(dragx-1);dy = y[0]*(dragy-1)
        destination = 1 if settings.terrain == 'shallow' else 3
        x[0] += dx;y[0] += dy;x[destination] -= dx;y[destination] -= dy
    # Reuse the exact frozen storm-only flux construction and event catalogue.
    zero_mean = replace(profile, eastward=np.zeros_like(profile.eastward), northward=np.zeros_like(profile.northward))
    transient = base.flow_at(domain, zero_mean, settings, storms, time_s)
    raw_x = (x+transient.x)/reference_mass*projector.mx
    raw_y = (y+transient.y)/reference_mass*projector.my
    return projector.project(raw_x, raw_y)


# Seasonal accounting copied from the frozen mass-projection experiment; only
# the explicitly passed mean-wind field in flow_at changes. No monkey-patching.
def year(domain, profile, settings, seed, state, local_air, mask, geometry, local_wind, checkpoint=None,
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
                flow = flow_at(domain, profile, settings, storms, tick, geometry, local_wind, projector)
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
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2'])
    if abs(we) > 1e-6 or abs(ee) > 1:
        raise FloatingPointError('Annual column budgets failed.')
    info['budget'] = dict(totals, annual_water_error_mm=we, annual_energy_error_j_m2=ee,
        max_step_water_error_mm=maxw, max_step_energy_error_j_m2=maxe,
        max_air_continuity_kg_m2_s=continuity, steps=steps)
    return state, rain, temp, refs, info
