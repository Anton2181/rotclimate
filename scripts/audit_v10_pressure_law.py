"""Independent manufactured/frozen-state pressure-law probes; no seasonal run."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_pressure_thermo as model
from scripts import review_v10_spatial_wind as review
from rotclimate_v10.core import Domain, divergence
from rotclimate_v10.earth import atomic_json


def manufactured_probe(mode):
    if mode not in ('flat', 'tilted_isobar', 'isentropic_hill', 'pressure_transfer'):
        raise ValueError('Unknown pressure-law probe.')
    shape = (4, 7);ny, nx = shape
    x = np.linspace(-1, 1, nx)[None, :]
    ps = np.full(shape, model.coordinates.P0)
    if mode in ('isentropic_hill', 'pressure_transfer'):
        ps *= 1-.18*np.exp(-5*x*x)
    mass, pressure, interfaces = model.coordinates.pressure_grid(ps, 'hybrid')
    pi = model.exner(pressure)
    z = model.base.CP*300*(1-pi)/model.base.G
    if mode == 'tilted_isobar':
        z = z+np.linspace(0., 1000., nx)[None, None, :]
    geometry = model.coordinates.Geometry(mass, ps, pressure, z, interfaces, 'hybrid')
    theta = np.full_like(mass, 300.)
    if mode == 'pressure_transfer':
        theta += np.linspace(0., 12., nx)[None, None, :]
    temperature = pi*theta-273.15
    air = np.broadcast_to(temperature, (12,)+mass.shape).copy()
    domain = Domain('california', np.ones(shape, bool), np.zeros(shape), np.full(shape, 37.),
        np.full((12,)+shape, 15.), 60000., 60000.)
    profile = model.base.Profile(np.zeros((12, 4)), np.zeros((12, 4)),
        np.full((12, 4), 8.), np.zeros((12, 4)), z[:, 0, 0])
    settings = model.base.Settings(storm_rate_month=0.)
    state = model.base.State(np.zeros_like(mass), mass*(model.base.CP*(temperature+273.15)+model.base.G*z), np.zeros(shape))
    fx = np.broadcast_to((mass[:, 0, 0]*8.)[:, None, None], (4, ny, nx+1)).copy()
    flow = model.base.balanced(fx, np.zeros((4, ny+1, nx)), domain.dx, domain.dy)
    dt = min(60., model.base.stable_step(flow, mass, domain))
    old = model.coordinates.advance(state, domain, profile, settings, flow, dt, 0., air, physics=False, geometry=geometry)
    new = model.advance(state, domain, profile, settings, flow, dt, 0., air, physics=False, geometry=geometry)
    fraction = dt*fx[:, :, 1:]/(mass*domain.dx)
    expected_theta = theta.copy()
    expected_theta[:, :, 1:] = (1-fraction[:, :, 1:])*theta[:, :, 1:]+fraction[:, :, 1:]*theta[:, :, :-1]
    expected_t = expected_theta*pi-273.15
    return {'mode': mode, 'dt_s': dt,
        'old_max_expected_temperature_error_c': float(abs(old[2]-expected_t).max()),
        'new_max_expected_temperature_error_c': float(abs(new[2]-expected_t).max()),
        'old_max_temperature_change_c': float(abs(old[2]-temperature).max()),
        'new_max_temperature_change_c': float(abs(new[2]-temperature).max()),
        'new_work_j_m2': new[4]['prescribed_flow_work_j_m2'],
        'theta_transport_error_kg_k_m2': new[4]['theta_transport_error_kg_k_m2'],
        'water_error_mm': new[4]['water_error_mm'], 'energy_error_j_m2': new[4]['energy_error_j_m2']}


def analyse(source):
    manifest, state, inputs, settings, _, records, _ = review.load_verified(source)
    probes = [manufactured_probe(mode) for mode in ('flat', 'tilted_isobar', 'isentropic_hill', 'pressure_transfer')]
    snapshots = []
    for key, record in records.items():
        region, name = key.split('_', 1);case, profile, g, air, wind = inputs[region]
        config = settings[name];st = record[0]
        storms = model.nested_events(case.domain, config, 41, profile.storm_domain_width_m)
        flow = model.flow_at(case.domain, profile, config, storms, 0., g, wind)
        dt = min(60., model.base.stable_step(flow, g.mass, case.domain))
        old = model.coordinates.advance(st, case.domain, profile, config, flow, dt, 0., air, physics=False, geometry=g)
        new = model.advance(st, case.domain, profile, config, flow, dt, 0., air, physics=False, geometry=g)
        np.testing.assert_allclose(old[0].water, new[0].water, atol=1e-12)
        dse = (st.energy-model.base.LV*st.water)/g.mass
        md = divergence(flow.x, flow.y, case.domain.dx, case.domain.dy)
        mv = model.coordinates.vertical_divergence(flow.vertical, g.mass.shape)
        corrected = old[6][:2].copy()
        corrected[0] += dt*dse*md/(g.mass*model.base.CP)
        corrected[1] += dt*dse*mv/(g.mass*model.base.CP)
        np.testing.assert_allclose(corrected.sum(0), old[6][:2].sum(0), atol=1e-10)
        snapshots.append({'case': key, 'time_s': 0., 'dt_s': dt,
            'temperature_difference_p95_c_by_layer': np.percentile(abs(new[2]-old[2])[:, case.score_mask], 95, axis=1).tolist(),
            'old_flux_split_mean_change_c_by_layer': old[6][:2, :, case.score_mask].mean(2).tolist(),
            'mass_anomaly_split_mean_change_c_by_layer': corrected[:, :, case.score_mask].mean(2).tolist(),
            'prescribed_flow_work_j_m2': new[4]['prescribed_flow_work_j_m2'],
            'theta_transport_error_kg_k_m2': new[4]['theta_transport_error_kg_k_m2'],
            'water_error_mm': new[4]['water_error_mm'], 'energy_error_j_m2': new[4]['energy_error_j_m2'],
            'temperature_ledger_error_c': new[-1]})
    digest = hashlib.sha256(review.run.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(review.__file__)):
        digest.update(path.read_bytes())
    return {'code_sha256': digest.hexdigest(), 'manufactured': probes, 'frozen_state_snapshots': snapshots,
        'note': 'Dry theta=T*(1000hPa/p)^(Rd/cp) conserved by prescribed adiabatic transport. Work is explicit exchange with the unsolved prescribed flow, not a new total-energy conservation claim. Large old horizontal/vertical terms contain cancelling mass-divergence parts.',
        'seasonal_runs_started': 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_spatial_wind')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_spatial_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    result = analyse(args.source)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'pressure_law_audit.json', result)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
