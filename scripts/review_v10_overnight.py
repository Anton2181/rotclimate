"""Read completed overnight evidence. --write saves a separate review.

No downloads, atmospheric state integration, calibration or atlas publication.
The failure probe advances only a scalar clock under prescribed frozen flows.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_column as model, v10_forcing_audit as atmosphere
from experiments.v10_time import step_length
from rotclimate_v10.core import EDGES
from rotclimate_v10.earth import atomic_json, load_case, sha256
from scripts import overnight_v10 as night


def prepared_case(source, manifest, region, spacing):
    if spacing == 60:
        path = ROOT/'data/v10_earth'/f'{region}_60km.npz'
        expected = manifest['base_inputs_sha256'][region]
    else:
        path = source/'inputs'/f'{region}_{spacing}km.npz'
        expected = json.loads(path.with_suffix('.json').read_text())['sha256']
    if sha256(path) != expected:
        raise ValueError('Prepared reference input changed.')
    return load_case(path, region)


def profile_from_json(values):
    return model.Profile(**{k: v if k == 'storm_domain_width_m' else np.array(v)
                            for k, v in values.items()})


def pressure_reference(case, fields):
    """Sample actual local pressure levels, without surface-temperature imprint."""
    _, ps = model.masses(case.domain)
    temperature = []
    height = []
    for fraction in model.SIGMA:
        for variable, output in (('air', temperature), ('hgt', height)):
            value, iy, ix = atmosphere.at_pressure(fields[case.domain.name, variable],
                case.longitude, case.domain.latitude, fraction*ps/100.)
            field = fields[case.domain.name, variable]
            distance_lat = abs(field.latitude[iy]-case.domain.latitude)
            distance_lon = abs((field.longitude[ix]-case.longitude+180)%360-180)
            if (distance_lat > 1.250001).any() or (distance_lon > 1.250001).any():
                raise ValueError('Requested location outside cached native reference footprint.')
            output.append(value)
    temperature = np.stack(temperature, axis=1)
    height = np.stack(height, axis=1)
    if not np.isfinite(temperature).all() or not np.isfinite(height).all():
        raise ValueError('Missing local pressure-level reference; no silent filling.')
    return temperature, height


def error_statistics(actual, reference, mask):
    delta = (actual-reference)[:, :, mask]
    return {'layer_abs_p95_c': np.percentile(abs(delta), 95, axis=(0, 2)).tolist(),
            'layer_signed_median_c': np.median(delta, axis=(0, 2)).tolist(),
            'lower_upper_abs_p95_c': [float(np.percentile(abs(delta[:, :2]), 95)),
                                    float(np.percentile(abs(delta[:, 2:]), 95))]}


def clock_probe(case, profile, settings, seed):
    """Reproduce scheduling failures with NO water/energy/state integration."""
    d = case.domain
    mass, _ = model.masses(d)
    events = model.events(d, settings, seed, profile.storm_domain_width_m)
    first_rejected = None
    steps = 0
    short_fragments = 0
    integrated_seconds = 0.
    for month in range(12):
        t = float(EDGES[month])
        f = None
        next_forcing = t
        while t < EDGES[month+1]-1e-6:
            if f is None or t >= next_forcing-1e-6:
                tick = np.floor((t+1e-6)/10800.)*10800.
                next_forcing = tick+10800.
                f = model.flow_at(d, profile, settings, events, tick)
                limit = model.stable_step(f, mass, d)
            dt = step_length(t, limit, next_forcing, EDGES[month+1])
            if dt < .01:
                short_fragments += 1
                if first_rejected is None:
                    first_rejected = {'month': month+1, 'time_s': t, 'dt_s': dt,
                        'cfl_limit_s': limit, 'steps_before': steps,
                        'reason': 'Legal short remainder before a forcing boundary, not a tiny CFL limit.'}
            t += dt
            integrated_seconds += dt
            steps += 1
            if steps >= 500000:
                raise RuntimeError('Clock probe exceeded declared step bound.')
    return {'first_old_rejection': first_rejected, 'corrected_clock_steps': steps,
            'short_boundary_fragments': short_fragments,
            'corrected_clock_seconds': integrated_seconds,
            'climate_state_steps': 0}


def review(source):
    source = Path(source)
    manifest_path = source/'manifest.json'
    state_path = source/'state.json'
    manifest = json.loads(manifest_path.read_text())
    state = json.loads(state_path.read_text())
    if manifest['code_sha256'] != night.code_id():
        raise ValueError('Frozen source fingerprint does not match completed evidence.')
    if state['status'] != 'complete':
        raise ValueError('This review expects the completed batch.')
    audit_manifest = ROOT/'output/v10_forcing_audit/manifest.json'
    if sha256(audit_manifest) != manifest['audit_manifest_sha256']:
        raise ValueError('Atmospheric audit provenance changed.')
    texts, downloads = atmosphere.acquire(ROOT/'data/v10_atmosphere', False)
    if downloads != json.loads(audit_manifest.read_text())['reference_downloads']:
        raise ValueError('Reference download provenance changed.')
    fields = atmosphere.fields_from_cache(texts)
    cases = {}
    references = {}
    rows = {}
    errors = Counter()
    years_verified = 0
    for key, saved in state['cases'].items():
        candidate, region, grid, seed = key.split('_')
        index, spacing = int(candidate[1:]), int(grid[1:])
        group = region, spacing
        if group not in cases:
            case = prepared_case(source, manifest, *group)
            cases[group] = case
            references[group] = pressure_reference(case, fields)
        case = cases[group]
        folder = source/'cases'/key
        config = json.loads((folder/'config.json').read_text())
        if config['settings'] != manifest['settings'][index] or config['seed'] != int(seed[1:]) or config['region'] != region or config['spacing_m'] != case.domain.dx:
            raise ValueError('Case identity mismatch.')
        for name, digest in saved['evidence_sha256'].items():
            if Path(name).name != name or sha256(folder/name) != digest:
                raise ValueError('Completed evidence changed.')
        for year in range(1, saved['years']+1):
            record = night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed year.')
            years_verified += 1
        actual, height = references[group]
        zero_mae = float(case.observed_rain_mm[:, case.score_mask].mean())
        stats = error_statistics(record[2], actual, case.score_mask)
        bias = error_statistics(record[3], actual, case.score_mask)
        rows[key] = {'candidate': index, 'region': region, 'spacing_km': spacing,
            'seed': int(seed[1:]), 'years': saved['years'], 'eligible_original': saved['eligible'],
            'settled': saved['settling']['passed'], 'monthly_rain_mae_mm': saved['score'],
            'zero_rain_mae_mm': zero_mae, 'rain_skill_vs_zero': 1-saved['score']/zero_mae,
            'annual_rain_ratio': saved['annual_rain_ratio'],
            'wet_reference_coverage': saved['wet_reference_coverage'],
            'original_target_error_p95_c': saved['temperature_departure_p95_c'],
            'temperature_vs_local_pressure_reference': stats,
            'original_target_vs_local_pressure_reference': bias,
            'guards_original': saved['guards'], 'budget': saved['budget'],
            'reference_below_model_ground_fraction': [float((height[:, k, case.score_mask] < case.domain.elevation_m[case.score_mask]).mean()) for k in range(4)]}
        errors.update(k for k, passed in saved['guards'].items() if not passed)
    probes = {}
    for key, message in state['failures'].items():
        candidate, region, grid, seed = key.split('_')
        group = region, int(grid[1:])
        case = cases.get(group) or prepared_case(source, manifest, *group)
        p = profile_from_json(manifest['profiles'][region])
        probe = clock_probe(case, p, model.Settings(**manifest['settings'][int(candidate[1:])]), int(seed[1:]))
        probes[key] = {'reported_error': message, **probe}
    return {'source': str(source.resolve()), 'source_manifest_sha256': sha256(manifest_path),
        'source_state_sha256': sha256(state_path), 'frozen_sources_verified': True,
        'completed_cases': len(rows), 'completed_years_verified': years_verified,
        'numerical_failures': state['failures'], 'original_guard_failure_counts': dict(errors),
        'elapsed_seconds': sum(x['elapsed_seconds'] for x in state['invocations']),
        'selected': state['selected'], 'cases': rows, 'clock_probes': probes,
        'new_climate_integrations': 0, 'atlas_updated': False,
        'limitations': ['Local pressure-level reference is coarse 2.5-degree reanalysis, not independent station observations.',
            'Native terrain can differ; pressure-level products may contain below-ground extrapolation, especially for the lowest layer.',
            'Reference periods differ; temperature is observation-informed forcing, not an independent prediction.',
            'Local reference audit does not change historical eligibility, selection or acceptance rules.']}


def markdown(data):
    rows = data['cases']
    lines = ['# Completed V10 overnight review', '',
        f"Finished in {data['elapsed_seconds']/3600:.2f} hours: {len(rows)} completed cases, "
        f"{len(data['numerical_failures'])} failed cases, {data['completed_years_verified']} completed years verified.",
        'No original case qualifies. No 30/15 km refinement or atlas publication occurred.', '',
        '## Rainfall and the unchanged acceptance rules', '',
        '| Region, best-screen setting 120 at 60 km, seed 41 | Rain / reference | Rain MAE | Zero-rain MAE | Coverage |',
        '|---|---:|---:|---:|---:|']
    for region in ('california', 'iberia'):
        r = rows[f'c120_{region}_g60_s41']
        lines.append(f"| {region} | {r['annual_rain_ratio']:.2f} | {r['monthly_rain_mae_mm']:.2f} | {r['zero_rain_mae_mm']:.2f} | {r['wet_reference_coverage']:.1%} |")
    lines += ['', 'Zero rain is an information-free error baseline, not an acceptable climate model. '
        'The shortlisted 60 km cases all have worse monthly rain MAE than this baseline. '
        'Thus correcting the temperature comparison alone does not rescue rainfall.', '',
        '## The thermal screen also needs diagnosis', '',
        'Old targets add each local surface-temperature anomaly to an offshore profile in every layer. '
        'The following comparison samples cached NCEP air at each local layer pressure instead. '
        'The unchanged old guards remain recorded; this is a separate exploratory reference audit.', '',
        '| Reference-informed shallow control, 120 km | Old target error, lower / upper p95 °C | Local pressure-reference error, lower / upper p95 °C |',
        '|---|---:|---:|']
    for region in ('california', 'iberia'):
        r = rows[f'c007_{region}_g120_s41'];old = r['original_target_error_p95_c']
        new = r['temperature_vs_local_pressure_reference']['lower_upper_abs_p95_c']
        lines.append(f'| {region} | {old[0]:.2f} / {old[1]:.2f} | {new[0]:.2f} / {new[1]:.2f} |')
    lines += ['', 'Do not infer that all 215 runs have a 10–18°C free-air error from their departure '
        'from the imposed targets. The spatial target construction exaggerates upper departures; '
        'lower-layer/reference errors and rainfall failures still remain.', '', '## Three failures were clock remainders', '']
    for key, p in data['clock_probes'].items():
        f = p['first_old_rejection']
        if f:
            lines.append(f"- {key}: rejected a {f['dt_s']:.6f}-second boundary remainder despite a "
                f"{f['cfl_limit_s']:.2f}-second CFL allowance; scalar-only corrected clock completes "
                f"the year in {p['corrected_clock_steps']} steps.")
        else:lines.append(f'- {key}: scheduling rejection was not reproduced; further diagnosis required.')
    lines += ['', 'No atmospheric states were advanced in these probes. Failed physical cases remain failed '
        'in the original evidence. A new clock helper permits positive boundary fragments without '
        'discarding time; the old sources are unchanged.', '', '## Next controlled experiment', '',
        'Test replacing only the upper two temperature targets with spatial pressure-level reference '
        'temperatures. Keep setting 120, seed 41, 60 km inputs, geometry, winds, humidity and storms fixed; '
        'reuse the completed baseline in each region. Record signed horizontal/vertical thermal '
        'transport, relaxation, condensation heating and layer rain. Two new regional cases, no search '
        'or atlas publication. This tests the surface-temperature imprint and exposes the remaining '
        'rain mechanism without another broad sweep.', '', '## Limits', '']
    lines += ['- '+x for x in data['limitations']]
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_overnight_20261015')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_overnight_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    data = review(args.source)
    report = markdown(data)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'review.json', data)
        (args.out/'review.md').write_text(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
