"""Common-forcing manufactured transport comparisons; never an Earth year."""
from __future__ import annotations

import numpy as np
from experiments import v10_cloud_column_lab as original
from experiments import v10_flux_transport as candidate

lab = original.lab
base = lab.base
SCHEMES = ('upwind', 'coupled_fct')


def periodic(cells, scheme, case='contact', courant=.5, direction=1):
    if scheme not in SCHEMES or case not in ('contact', 'smooth') or courant not in (.25, .5):
        raise ValueError('Invalid fixed periodic comparison.')
    if case == 'contact' and cells % 2:
        raise ValueError('Contact requires an even cell count.')
    mesh = candidate.periodic_mesh(cells, direction)
    x = (np.arange(cells)+.5)/cells; p = np.full(cells, 90000.)
    pi = candidate.thermal.exner(p)
    if case == 'contact':
        temperature = np.where(x < .5, 20., 0.)
        q = base.saturation(temperature, p)
        theta = (temperature+273.15)/pi
    else:
        wave = np.sin(2*np.pi*x)*np.sinc(1/cells)
        theta = 300.+8.*wave; q = .004+.001*wave
    initial_theta = theta.copy(); initial_q = q.copy()
    initial_h = lab.enthalpy(theta*pi-273.15, q)
    c = np.array([theta, q]); rain = 0.; maximum_bound = 0.; steps = 2*cells if courant == .5 else 4*cells
    for _ in range(steps):
        if scheme == 'coupled_fct':
            c, _, info = candidate.transport(c, mesh, courant/cells)
            maximum_bound = max(maximum_bound, info['maximum_bound_error'])
        else:
            c = (1-courant)*c+courant*np.roll(c, direction, axis=1)
        if case == 'contact':
            h = lab.enthalpy(c[0]*pi-273.15, c[1])
            q, condensed, temperature = base.adjust(c[1], h, np.ones(cells), np.zeros(cells), p)
            rain += float(condensed.mean()); c = np.array([(temperature+273.15)/pi, q])
    final_h = lab.enthalpy(c[0]*pi-273.15, c[1])
    water_error = float(c[1].mean()+rain-initial_q.mean())
    heat_error = float(final_h.mean()-initial_h.mean())
    if abs(water_error)>1e-11 or abs(heat_error)>1e-6 or c[1].min()<0:
        raise FloatingPointError('Periodic comparison water/heat accounting failed.')
    return {'case': case, 'cells': cells, 'scheme': scheme, 'courant': courant, 'direction': direction,
        'steps': steps, 'circuits': 1., 'rain_g_per_kg': rain*1000.,
        'exact_rain_g_per_kg': 0., 'theta_mean_absolute_error_k': float(abs(c[0]-initial_theta).mean()),
        'vapor_mean_absolute_error_g_kg': float(abs(c[1]-initial_q).mean()*1000.),
        'water_error_kg_kg': water_error, 'enthalpy_error_j_kg': heat_error,
        'maximum_transport_bound_error': maximum_bound,
        'initial_theta_k': initial_theta, 'final_theta_k': c[0],
        'initial_vapor_ratio': initial_q, 'final_vapor_ratio': c[1]}


def advance(state, domain, geometry, flow, dt, mode, physics=True):
    """Frozen toy cloud rules around the new transport; no cloud retuning."""
    if mode not in ('bulk', 'unmixed') or not np.isfinite(dt) or dt <= 0 or dt > base.stable_step(flow, geometry.mass, domain)*(1+1e-12):
        raise ValueError('Invalid manufactured transport comparison step.')
    g = geometry
    before_t = base.temperature(state.energy, g.mass, state.water, g.height_m)
    water, energy, _, _, work, changes, theta_error = candidate.thermal_transport(
        state, flow, dt, domain, g, before_t, np.zeros_like(g.mass))
    parcel = np.zeros_like(water); rain = np.zeros_like(water)
    if physics:
        if mode == 'unmixed':
            q = state.water[:-1]/g.mass[:-1]
            dry = (before_t[:-1]+273.15)*(g.pressure[1:]/g.pressure[:-1])**lab.KAPPA-273.15
            e = base.CP*(dry+273.15)+base.G*g.height_m[1:]+base.LV*q
            _, condensate, _ = base.adjust(q, e, np.ones_like(q), g.height_m[1:], g.pressure[1:])
            parcel[1:] = np.maximum(flow.vertical, 0.)*dt*condensate
            if (water-parcel).min() < 0:
                raise FloatingPointError('Frozen unmixed rule exceeds the new transported vapor; incompatible comparison, no clipping.')
            water -= parcel
        water, rain, after_t = base.adjust(water, energy, g.mass, g.height_m, g.pressure)
        rain += parcel
    else:
        after_t = base.temperature(energy, g.mass, water, g.height_m)
    thermal_error = float(abs(after_t-before_t-changes.sum(0)-base.LV*rain/(g.mass*base.CP)).max())
    water_error = float((water-state.water).sum(0).mean()+rain.sum(0).mean())
    energy_error = float((energy-state.energy).sum(0).mean()-work.sum(0).mean())
    if abs(water_error)>1e-10 or abs(energy_error)>1e-5 or abs(theta_error)>1e-7 or thermal_error>1e-9:
        raise FloatingPointError('Manufactured transport comparison accounting failed.')
    return base.State(water, energy, state.soil.copy()), rain, parcel, float(work.sum(0).mean()), thermal_error


def column(layers, mode, scheme, time_factor=1., vapor=True, physics=True):
    if scheme not in SCHEMES or time_factor not in (1., .5):
        raise ValueError('Invalid column transport comparison.')
    if scheme == 'upwind':
        return dict(original.run(layers, mode, time_factor, vapor, physics), scheme=scheme)
    d, g, initial, flow = original.fixture(layers, vapor)
    state = initial; times = np.linspace(0., original.TURNOVER_S, 17)
    rain = np.zeros_like(g.mass); parcel = rain.copy(); work = 0.; maximum_thermal = 0.; steps = 0; t = 0.
    total_rain = [0.]; parcel_rain = [0.]
    step_limit = min(60., base.stable_step(flow, g.mass, d))*time_factor
    for endpoint in times[1:]:
        while t < endpoint-1e-8:
            dt = min(step_limit, endpoint-t)
            state, amount, cloud, pressure_work, residual = advance(state, d, g, flow, dt, mode, physics)
            rain += amount; parcel += cloud; work += pressure_work; maximum_thermal = max(maximum_thermal, residual)
            t += dt; steps += 1
        total_rain.append(float(rain.sum(0).mean())); parcel_rain.append(float(parcel.sum(0).mean()))
    water_error = float((state.water-initial.water).sum(0).mean()+rain.sum(0).mean())
    energy_error = float((state.energy-initial.energy).sum(0).mean()-work)
    if abs(water_error)>1e-8 or abs(energy_error)>1e-3:
        raise FloatingPointError('Manufactured transport trajectory accounting failed.')
    return {'layers': layers, 'mode': mode, 'scheme': scheme, 'time_factor': time_factor, 'steps': steps,
        'duration_seconds': float(times[-1]), 'column_dry_mass_kg_m2': float(g.mass.sum(0).mean()),
        'initial_vapor_mm': float(initial.water.sum(0).mean()), 'initial_energy_j_m2': float(initial.energy.sum(0).mean()),
        'rain_mm': float(rain.sum(0).mean()), 'parcel_rain_mm': float(parcel.sum(0).mean()),
        'remaining_vapor_mm': float(state.water.sum(0).mean()), 'pressure_work_j_m2': work,
        'water_error_mm': water_error, 'energy_error_j_m2': energy_error, 'maximum_step_temperature_ledger_error_c': maximum_thermal,
        'times_seconds': times, 'rain_history_mm': np.array(total_rain), 'parcel_rain_history_mm': np.array(parcel_rain),
        'state': state, 'geometry': g, 'flow': flow}
