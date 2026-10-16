"""Tiny manufactured moist-front/ascent checks; no regional integration."""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_event_forcing as model
from rotclimate_v10.core import Domain


def manufactured_inputs():
    shape = (3, 8);land = np.ones(shape, bool)
    domain = Domain('manufactured', land, np.zeros(shape), np.full(shape, 37.), np.full((12,)+shape, 15.), 60000., 60000.)
    edges = np.broadcast_to(np.array([101325., 91192.5, 75993.75, 60795., 30000., 0.])[:, None, None], (6,)+shape).copy()
    mass = -np.diff(edges, axis=0)/model.base.G;pressure = .5*(edges[:-1]+edges[1:]);height = -8400*np.log(pressure/101325.)
    g = model.core.coordinates.Geometry(mass, edges[0], pressure, height, edges, 'hybrid_split300')
    profile = model.core.Profile(np.zeros((12, 5)), np.zeros((12, 5)), np.zeros((12, 5)), np.zeros((12, 5)), height.mean((1, 2)))
    setting = model.base.Settings(terrain='none', storm_rate_month=0.)
    return domain,profile,setting,g


def probes():
    domain,profile,setting,g = manufactured_inputs();m = model.base
    t = np.broadcast_to(np.array([15., 8., -3., -25., -55.])[:, None, None], g.mass.shape)
    air = np.broadcast_to(t, (12,)+t.shape).copy();sat = m.saturation(t, g.pressure)
    rh = np.array([.2, .2, .2, .9, .9, .9, .2, .2])[None, None, :]
    water = g.mass*sat*rh
    state = m.State(water, g.mass*(m.CP*(t+273.15)+m.G*g.height_m)+m.LV*water, np.zeros(domain.land.shape))
    u = 5.;dt = 60.;x = np.broadcast_to(g.mass[..., :1]*u, (5, 3, 9)).copy();y = np.zeros((5, 4, 8))
    flow = m.balanced(x, y, domain.dx, domain.dy);boundary = .2*sat
    out = model.advance(state, domain, profile, setting, flow, dt, 0., air, geometry=g, boundary=boundary)
    donor = np.concatenate([boundary[..., :1]*g.mass[..., :1], water[..., :-1]], axis=-1)
    expected = water+(u*dt/domain.dx)*(donor-water)
    front = {'dt_s': dt, 'maximum_water_translation_error_mm': float(abs(out[0].water-expected).max()),
        'maximum_temperature_change_c': float(abs(out[2]-t).max()), 'total_rain_mm': float(out[1].sum()),
        'water_error_mm': out[4]['water_error_mm'], 'energy_error_j_m2': out[4]['energy_error_j_m2']}
    # A closed two-layer exchange: constant theta, saturation at each pressure.
    # Upward dry transfer makes the recipient supersaturated before latent warming.
    t = 300.*model.core.core.exner(g.pressure)-273.15
    air = np.broadcast_to(t, (12,)+t.shape).copy();sat = m.saturation(t, g.pressure)
    water = g.mass*sat;energy = g.mass*(m.CP*(t+273.15)+m.G*g.height_m)+m.LV*water
    state = m.State(water, energy, np.zeros(domain.land.shape));x = np.zeros((5, 3, 9));y = np.zeros((5, 4, 8))
    x[0, :, 2] = 500.;x[1, :, 2] = -500.
    flow = m.balanced(x, y, domain.dx, domain.dy);dt = min(60., m.stable_step(flow, g.mass, domain))
    out = model.advance(state, domain, profile, setting, flow, dt, 0., air, geometry=g, boundary=np.zeros_like(g.mass))
    recipient = (1, 0, 2);nu = dt*flow.vertical[0, 0, 2]/g.mass[recipient]
    q = sat[recipient]+nu*(sat[0, 0, 2]-sat[recipient]);lo,hi = 0.,q
    for _ in range(90):
        c = .5*(lo+hi);residual = c+m.saturation(np.array(t[recipient]+m.LV/m.CP*c), np.array(g.pressure[recipient]))-q
        if residual > 0:
            hi = c
        else:
            lo = c
    expected_rain = .5*(lo+hi)*g.mass[recipient]
    ascent = {'dt_s': dt, 'recipient_condensation_mm': float(out[5][recipient]),
        'independent_latent_saturation_solution_mm': float(expected_rain),
        'condensation_error_mm': float(abs(out[5][recipient]-expected_rain)),
        'water_error_mm': out[4]['water_error_mm'], 'energy_error_j_m2': out[4]['energy_error_j_m2'],
        'thermal_ledger_error_c': out[-1]}
    if front['maximum_water_translation_error_mm'] > 1e-10 or front['maximum_temperature_change_c'] > 1e-10 or front['total_rain_mm'] > 1e-10:
        raise ValueError('Manufactured unsaturated translating front failed.')
    if expected_rain <= 0 or ascent['condensation_error_mm'] > 1e-8:
        raise ValueError('Manufactured saturated pressure-transfer check failed.')
    return {'unsaturated_front': front, 'saturated_pressure_transfer': ascent,
        'checks': 'Two independent <=60-second manufactured steps. Constant-temperature moisture front and latent-coupled saturated ascent; not a resolved thermal front or cloud-fallout validation.', 'regional_climate_integrations': 0}


if __name__ == '__main__':
    import json
    print(json.dumps(probes(), indent=2))
