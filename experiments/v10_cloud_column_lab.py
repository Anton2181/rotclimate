"""Manufactured closed two-column vertical-grid comparison, not an Earth run.

Both columns share a neutral dry-potential-temperature hydrostatic profile.
An analytic circulation rises in one and descends in the other. Its smooth
pressure-face flux, column mass, initial vapor and enthalpy integrals are
preserved across grids. No boundaries, evaporation, relaxation, terrain,
momentum feedback or new water sources are added.
"""
from __future__ import annotations

from types import SimpleNamespace
import numpy as np
from experiments import v10_cloud_lab as lab

base = lab.base
coordinates = lab.frozen.coordinates
TOP = 50000.
BOTTOM = 100000.
THETA = 300.
FLUX = .2
TURNOVER_S = (BOTTOM-TOP)/base.G/FLUX


def fixture(layers, vapor=True):
    if isinstance(layers, bool) or not isinstance(layers, (int, np.integer)) or not 4 <= layers <= 256 or layers % 4:
        raise ValueError('Use 4–256 layers divisible by four for aligned moisture zones.')
    edges = np.linspace(BOTTOM, TOP, layers+1); dp = edges[:-1]-edges[1:]
    # Pressure quadrature preserves the integral of this analytic dry profile.
    pi = (edges[:-1]**(1+lab.KAPPA)-edges[1:]**(1+lab.KAPPA))/((1+lab.KAPPA)*dp*BOTTOM**lab.KAPPA)
    p = BOTTOM*pi**(1/lab.KAPPA)
    z = base.CP*THETA/base.G*(1-pi)  # hydrostatic dry-adiabatic profile
    expand = lambda array: np.broadcast_to(np.asarray(array)[:, None, None], (len(array), 1, 2)).copy()
    mass = expand(dp/base.G); pressure = expand(p); height = expand(z)
    g = coordinates.Geometry(mass, np.full((1, 2), BOTTOM), pressure, height, expand(edges), 'manufactured_integral_preserving')
    d = SimpleNamespace(land=np.ones((1, 2), bool), dx=1000., dy=1000.)
    t = expand(THETA*pi-273.15)
    q = np.full_like(mass, .0002 if vapor else 0.)
    if vapor:
        q[:layers//4, 0, 0] = .009
    state = base.State(mass*q, mass*(base.CP*(t+273.15)+base.G*height)+base.LV*mass*q, np.zeros((1, 2)))
    vertical = FLUX*np.sin(np.pi*(BOTTOM-edges)/(BOTTOM-TOP)); vertical[[0, -1]] = 0.
    x = np.zeros((layers, 1, 3)); x[:, 0, 1] = d.dx*(vertical[:-1]-vertical[1:])
    flow = base.balanced(x, np.zeros((layers, 2, 2)), d.dx, d.dy)
    np.testing.assert_allclose(flow.vertical[:, 0, 0], vertical[1:-1], atol=1e-15, rtol=0)
    np.testing.assert_allclose(flow.vertical[:, 0, 1], -vertical[1:-1], atol=1e-15, rtol=0)
    return d, g, state, flow


def advance(state, domain, geometry, flow, dt, mode, physics=True):
    if mode not in ('bulk', 'unmixed') or not np.isfinite(dt) or dt <= 0 or dt > base.stable_step(flow, geometry.mass, domain)*(1+1e-12):
        raise ValueError('Invalid column-lab mode or CFL step.')
    g = geometry
    if state.water.shape != g.mass.shape or state.energy.shape != g.mass.shape or not all(np.isfinite(a).all() for a in (state.water, state.energy)) or (state.water < 0).any():
        raise ValueError('Invalid manufactured column state.')
    before_t = base.temperature(state.energy, g.mass, state.water, g.height_m)
    water, energy, wd, ed, work, changes, theta_error = lab.frozen.core.thermal_transport(
        state, flow, dt, domain, g, before_t, np.zeros_like(g.mass))
    if water.min() < 0:
        raise FloatingPointError('Manufactured transport produced negative vapor.')
    parcel = np.zeros_like(water)
    rain = np.zeros_like(water)
    if physics:
        if mode == 'unmixed':
            q = state.water[:-1]/g.mass[:-1]
            dry = (before_t[:-1]+273.15)*(g.pressure[1:]/g.pressure[:-1])**lab.KAPPA-273.15
            e = base.CP*(dry+273.15)+base.G*g.height_m[1:]+base.LV*q
            _, condensate, _ = base.adjust(q, e, np.ones_like(q), g.height_m[1:], g.pressure[1:])
            parcel[1:] = np.maximum(flow.vertical, 0.)*dt*condensate
            if (water-parcel).min() < 0:
                raise FloatingPointError('Manufactured parcel rain exceeds transported vapor.')
            water -= parcel
        water, rain, after_t = base.adjust(water, energy, g.mass, g.height_m, g.pressure)
        rain += parcel
    else:
        after_t = base.temperature(energy, g.mass, water, g.height_m)
    thermal_error = float(abs(after_t-before_t-changes.sum(0)-base.LV*rain/(g.mass*base.CP)).max())
    next_state = base.State(water, energy, state.soil.copy())
    water_error = float((water-state.water).sum(0).mean()+rain.sum(0).mean())
    energy_error = float((energy-state.energy).sum(0).mean()-work.sum(0).mean())
    if abs(water_error)>1e-10 or abs(energy_error)>1e-5 or abs(theta_error)>1e-7 or thermal_error>1e-9:
        raise FloatingPointError('Manufactured column step accounting failed.')
    return next_state, rain, parcel, float(work.sum(0).mean()), thermal_error


def run(layers, mode, time_factor=1., vapor=True, physics=True):
    if time_factor not in (1., .5):
        raise ValueError('Use the declared full or half time step.')
    d, g, initial, flow = fixture(layers, vapor)
    state = initial; times = np.linspace(0., TURNOVER_S, 17)
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
        raise FloatingPointError('Manufactured column trajectory accounting failed.')
    return {'layers': layers, 'mode': mode, 'time_factor': time_factor, 'steps': steps,
        'duration_seconds': float(times[-1]), 'column_dry_mass_kg_m2': float(g.mass.sum(0).mean()),
        'initial_vapor_mm': float(initial.water.sum(0).mean()), 'initial_energy_j_m2': float(initial.energy.sum(0).mean()),
        'rain_mm': float(rain.sum(0).mean()), 'parcel_rain_mm': float(parcel.sum(0).mean()),
        'remaining_vapor_mm': float(state.water.sum(0).mean()), 'pressure_work_j_m2': work,
        'water_error_mm': water_error, 'energy_error_j_m2': energy_error, 'maximum_step_temperature_ledger_error_c': maximum_thermal,
        'times_seconds': times, 'rain_history_mm': np.array(total_rain), 'parcel_rain_history_mm': np.array(parcel_rain),
        'state': state, 'geometry': g, 'flow': flow}


def advect_contact(cells, courant):
    """Periodic, isobaric warm/cold contact; exact inviscid solution has no rain.

Each initial parcel is saturated. A constant velocity translates it through
one complete periodic circuit without ascent or physical diffusion. The
declared first-order upwind stencil mixes enthalpy and vapor numerically.
CFL=1 is an exact one-cell-shift control for this uniform toy only; it is not
a recommendation to raise the regional engine's CFL limit.
"""
    if isinstance(cells, bool) or not isinstance(cells, (int, np.integer)) or cells < 4 or cells > 4096 or cells % 2 or courant not in (.5, 1.):
        raise ValueError('Use an even 4–4096 cell contact and declared CFL .5 or 1.')
    p = 90000.
    t = np.where(np.arange(cells) < cells//2, 20., 0.)
    q = lab.base.saturation(t, np.full(cells, p))
    h = lab.enthalpy(t, q)
    initial_q = q.copy(); initial_h = h.copy(); total_rain = 0.
    steps = int(cells/courant)
    for _ in range(steps):
        q = (1-courant)*q+courant*np.roll(q, 1)
        h = (1-courant)*h+courant*np.roll(h, 1)
        q, condensed, t = base.adjust(q, h, np.ones(cells), np.zeros(cells), np.full(cells, p))
        total_rain += float(condensed.mean())
    water_error = float(q.mean()+total_rain-initial_q.mean())
    heat_error = float(h.mean()-initial_h.mean())
    if abs(water_error) > 1e-11 or abs(heat_error) > 1e-6 or (q < 0).any():
        raise FloatingPointError('Periodic contact conservation failed.')
    return {'cells': cells, 'courant': courant, 'steps': steps, 'circuits': 1,
        'rain_g_per_kg_initial_dry_air': total_rain*1000.,
        'exact_inviscid_rain_g_per_kg': 0.,
        'water_error_kg_per_kg': water_error, 'enthalpy_error_j_per_kg': heat_error,
        'initial_vapor_ratio': initial_q, 'final_vapor_ratio': q,
        'initial_enthalpy_j_per_kg': initial_h, 'final_enthalpy_j_per_kg': h,
        'final_temperature_c': t}
