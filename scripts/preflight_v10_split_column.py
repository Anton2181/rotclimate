"""Short independent input/operator checks only; never a seasonal integration."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_split_column as run
from rotclimate_v10.core import DAY
from rotclimate_v10.earth import atomic_json, sha256


def check():
    protocol, inputs, settings, baselines = run.prepare()
    checks = []
    for job in protocol['jobs']:
        variant = run.VARIANTS[job['variant']]
        case, profile, g, air, circulation = inputs[job['region']+'_'+variant['lid']]
        config = settings[job['wind']]
        storms = run.model.nested_events(case.domain, config, 41, profile.storm_domain_width_m)
        event = max(storms, key=lambda a:a.strength)
        for day in (0., 195., float(event.day)):
            t = day*DAY
            target, _ = run.model.coordinates.targets(case.domain, profile, config, t, air)
            r = run.model.boundary_ratio(case.domain, profile, config, g, air, t, variant['boundary'], circulation)
            water = g.mass*np.minimum(r, .6*run.model.base.saturation(target, g.pressure))
            state = run.model.base.State(water,
                g.mass*(run.model.base.CP*(target+273.15)+run.model.base.G*g.height_m)+run.model.base.LV*water,
                np.where(case.domain.land, 75., 0.))
            coarse = run.model.core.flow_at(case.domain, circulation[1], config, storms, t,
                circulation[0], circulation[3], wind_mode=job['wind'])
            flow = run.model.flow_at(case.domain, profile, config, storms, t, g, circulation[3],
                wind_mode=job['wind'], circulation=circulation)
            np.testing.assert_array_equal(flow.x[:3], coarse.x[:3])
            np.testing.assert_array_equal(flow.y[:3], coarse.y[:3])
            np.testing.assert_allclose(flow.x[3:].sum(0), coarse.x[3], atol=1e-9)
            np.testing.assert_allclose(flow.y[3:].sum(0), coarse.y[3], atol=1e-9)
            dt = min(60., run.model.base.stable_step(flow, g.mass, case.domain))
            record = run.model.advance(state, case.domain, profile, config, flow, dt, t, air,
                geometry=g, boundary_mode=variant['boundary'], circulation=circulation)
            b = record[4]
            checks.append({'case': job['key'], 'day': day, 'dt_s': dt,
                'water_error_mm': b['water_error_mm'], 'energy_error_j_m2': b['energy_error_j_m2'],
                'theta_error_kg_k_m2': b['theta_transport_error_kg_k_m2'],
                'temperature_ledger_error_c': record[-1], 'continuity': flow.continuity,
                'gross_vs_net_boundary_error_mm': b['boundary_export_gross_mm']-b['boundary_import_gross_mm']-b['boundary_export_mm']})
    matched = {};legacy = []
    for region in ('california', 'iberia'):
        case, profile, g, air, c = inputs[region+'_rh300'];config = settings['spatial']
        errors = [];factors = []
        for day in range(365):
            t = day*DAY
            old = run.model.boundary_ratio(case.domain, c[1], config, c[0], c[2], t)
            raw = run.model.boundary_ratio(case.domain, profile, config, g, air, t)
            new = run.model.boundary_ratio(case.domain, profile, config, g, air, t, 'column_matched', c)
            requested = (c[0].mass*old).sum(0)
            errors.append(float(abs((g.mass*new).sum(0)-requested).max()))
            factors.append(requested/(g.mass*raw).sum(0))
        matched[region] = {'independent_boundary_queries': 365, 'max_column_match_error_mm': max(errors),
            'scale_min': float(np.min(factors)), 'scale_max': float(np.max(factors))}
        old_g, old_p, old_air, old_wind = c
        for mode, config in settings.items():
            key = region+'_'+mode+'_s41'
            folder = ROOT/'output/v10_water_sources/cases'/key
            record = run.review.run.read_checkpoint(folder, baselines[region+'_'+mode]['years'], case.domain.land.shape, completed=True)
            state = record[0]
            storms = run.model.nested_events(case.domain, config, 41, old_p.storm_domain_width_m)
            for day in (0., 195., float(max(storms, key=lambda a:a.strength).day)):
                t = day*DAY
                flow = run.model.core.flow_at(case.domain, old_p, config, storms, t, old_g, old_wind, wind_mode=mode)
                dt = min(60., run.model.base.stable_step(flow, old_g.mass, case.domain))
                old = run.model.core.advance(state, case.domain, old_p, config, flow, dt, t, old_air, geometry=old_g)
                new = run.model.advance(state, case.domain, old_p, config, flow, dt, t, old_air, geometry=old_g)
                for name in ('water', 'energy', 'soil'):
                    np.testing.assert_array_equal(getattr(old[0], name), getattr(new[0], name))
                for a,b in zip(old[1:4], new[1:4]):
                    np.testing.assert_array_equal(a,b)
                if old[4] != new[4]:
                    raise ValueError('Four-layer physical budget regression failed.')
                legacy.append({'region': region, 'wind': mode, 'day': day, 'dt_s': dt,
                    'physical_arrays_and_budget_identical': True})
    if run.source_id() != protocol['code_sha256']:
        raise ValueError('Sources changed during preflight.')
    return {'protocol': protocol, 'operator_checks': checks, 'column_matched_boundary_checks': matched,
        'legacy_four_layer_operator_regression': legacy, 'preflight_script_sha256': sha256(Path(__file__)),
        'checks': '48 independent <=60-second probes (36 new five-layer + 12 four-layer actual-state regression); 730 independent boundary-only queries. No seasonal integration.',
        'climate_integrations_started': 0, 'no_downloads': True, 'atlas_updated': False,
        'frozen_parent_source_evidence_verified': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_water_sources_review/split_column_preflight.json')
    args = parser.parse_args(argv);data = check()
    if args.write:
        atomic_json(args.out, data)
    print(data['checks'])
    print('Frozen experiment source: '+data['protocol']['code_sha256'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
