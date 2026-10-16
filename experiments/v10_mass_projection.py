"""Mass-weighted prescribed velocities with a minimum-change column projection.

Dry masses remain fixed. A weighted pressure potential removes column dry-mass
divergence, adjusting every layer by the same face velocity. Open boundaries
use zero exterior potential; all water/energy boundary fluxes remain explicit.
No momentum equation is solved. Thermodynamic closure is imported unchanged.
"""
from dataclasses import replace
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import splu
from experiments import v10_coordinates as coordinates
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, interpolate_months, divergence
base = coordinates.base
advance = coordinates.advance
initial_state = coordinates.initial_state
PROCESSES = coordinates.PROCESSES


def face_masses(mass):
    ny, nx = mass.shape[-2:]
    x = np.empty(mass.shape[:-1]+(nx+1,))
    y = np.empty(mass.shape[:-2]+(ny+1, nx))
    x[..., 1:-1] = .5*(mass[..., :-1]+mass[..., 1:])
    x[..., 0] = mass[..., 0]
    x[..., -1] = mass[..., -1]
    y[..., 1:-1, :] = .5*(mass[..., :-1, :]+mass[..., 1:, :])
    y[..., 0, :] = mass[..., 0, :]
    y[..., -1, :] = mass[..., -1, :]
    return x, y


class ColumnProjection:
    def __init__(self, domain, geometry):
        if geometry.mass.shape != (4,)+domain.land.shape or not np.isfinite(geometry.mass).all() or (geometry.mass <= 0).any():
            raise ValueError('Positive four-layer masses required for projection.')
        self.dx, self.dy = domain.dx, domain.dy
        self.mx, self.my = face_masses(geometry.mass)
        self.column_x, self.column_y = self.mx.sum(0), self.my.sum(0)
        self.shape = domain.land.shape
        ny, nx = self.shape
        rows, cols, values = [], [], []
        for y in range(ny):
            for x in range(nx):
                i = y*nx+x
                diagonal = 0.
                for sy, sx, weight in (
                    (y, x-1, self.column_x[y, x]/self.dx**2),
                    (y, x+1, self.column_x[y, x+1]/self.dx**2),
                    (y-1, x, self.column_y[y, x]/self.dy**2),
                    (y+1, x, self.column_y[y+1, x]/self.dy**2)):
                    if 0 <= sy < ny and 0 <= sx < nx:
                        rows.append(i);cols.append(sy*nx+sx);values.append(-weight)
                        diagonal += weight
                    else:
                        # Zero potential at the boundary face, half a cell away.
                        diagonal += 2*weight
                rows.append(i);cols.append(i);values.append(diagonal)
        matrix = coo_matrix((values, (rows, cols)), shape=(ny*nx, ny*nx)).tocsc()
        self.factor = splu(matrix)
        self.last_info = {}

    def gradient(self, potential):
        ny, nx = self.shape
        x = np.empty((ny, nx+1))
        y = np.empty((ny+1, nx))
        x[:, 1:-1] = np.diff(potential, axis=1)/self.dx
        x[:, 0] = 2*potential[:, 0]/self.dx
        x[:, -1] = -2*potential[:, -1]/self.dx
        y[1:-1] = np.diff(potential, axis=0)/self.dy
        y[0] = 2*potential[0]/self.dy
        y[-1] = -2*potential[-1]/self.dy
        return x, y

    def project(self, raw_x, raw_y):
        if raw_x.shape != self.mx.shape or raw_y.shape != self.my.shape or not np.isfinite(raw_x).all() or not np.isfinite(raw_y).all():
            raise ValueError('Invalid raw dry-mass flux.')
        residual = divergence(raw_x.sum(0), raw_y.sum(0), self.dx, self.dy)
        potential = self.factor.solve(-residual.ravel()).reshape(self.shape)
        gx, gy = self.gradient(potential)
        x = raw_x-self.mx*gx
        y = raw_y-self.my*gy
        flow = base.balanced(x, y, self.dx, self.dy)
        adjustment = np.hypot(.5*(gx[:, 1:]+gx[:, :-1]), .5*(gy[1:]+gy[:-1]))
        self.last_info = {'raw_column_divergence_max_kg_m2_s': float(abs(residual).max()),
            'projected_column_divergence_max_kg_m2_s': flow.continuity,
            'barotropic_velocity_adjustment_max_m_s': float(adjustment.max())}
        return flow


def flow_at(domain, profile, settings, storms, time_s, geometry, projector=None):
    if projector is None:
        projector = ColumnProjection(domain, geometry)
    prescribed = base.flow_at(domain, profile, settings, storms, time_s)
    reference_mass = (base.FRACTIONS*coordinates.P0/base.G)[:, None, None]
    # Interpret the old face forcing as nominal velocities, then use actual mass.
    raw_x = prescribed.x/reference_mass*projector.mx
    raw_y = prescribed.y/reference_mass*projector.my
    return projector.project(raw_x, raw_y)


def nested_events(domain, settings, seed, width_m):
    rate = settings.storm_rate_month
    if not 0 <= rate <= 8:
        raise ValueError('Nested storm design requires rate between zero and eight.')
    if rate == 0:
        return []
    anchor = base.events(domain, replace(settings, storm_rate_month=1.), seed, width_m)
    if rate <= 1:
        # The declared experiment uses exactly zero or one here.
        if rate != 1:
            raise ValueError('Use zero or at least one storm per month in this design.')
        return anchor
    extra_seed = int(np.random.SeedSequence([seed, 84117]).generate_state(1)[0])
    extra = base.events(domain, replace(settings, storm_rate_month=7.), extra_seed, width_m)
    marks = np.random.default_rng(np.random.SeedSequence([seed, 84118])).uniform(size=len(extra))
    return sorted(anchor+[event for event, mark in zip(extra, marks) if mark < (rate-1)/7],
        key=lambda event: (event.day, event.x, event.latitude, event.strength))


def cell_velocity(flow, projector):
    """Interpolate face velocities, rather than dividing flux by a cell store."""
    uf = flow.x/projector.mx
    vf = -flow.y/projector.my
    return .5*(uf[:, :, 1:]+uf[:, :, :-1]), .5*(vf[:, 1:]+vf[:, :-1])


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
                flow = flow_at(domain, profile, settings, storms, tick, geometry, projector)
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


