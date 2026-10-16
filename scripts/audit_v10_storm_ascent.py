"""Sample cached prescribed circulation, not a climate integration or real weather."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_split_column as run
from rotclimate_v10.core import DAY, EDGES
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def ascent_statistics(background, actual):
    """Equal time/cell means. Positive-only mean is not the signed mean."""
    if background.shape != actual.shape or background.size == 0 or not np.isfinite(background).all() or not np.isfinite(actual).all():
        raise ValueError('Need paired finite circulation samples.')
    transient = actual-background
    return {'background_signed_pa_s': float(background.mean()),
        'actual_signed_pa_s': float(actual.mean()),
        'storm_signed_pa_s': float(transient.mean()),
        'background_positive_only_pa_s': float(np.maximum(background, 0).mean()),
        'actual_positive_only_pa_s': float(np.maximum(actual, 0).mean()),
        'storm_positive_component_pa_s': float(np.maximum(transient, 0).mean()),
        'actual_positive_fraction': float((actual > 1e-10).mean()),
        'background_positive_fraction': float((background > 1e-10).mean()),
        'storm_reverses_descent_fraction': float(((background < -1e-10) & (actual > 1e-10)).mean()),
        'change_in_positive_only_pa_s': float((np.maximum(actual, 0)-np.maximum(background, 0)).mean())}


def check(interval_hours=3):
    if interval_hours not in (3, 24):
        raise ValueError('Use the actual three-hour forcing clock or a daily sampling check.')
    protocol, inputs, settings, _ = run.prepare()
    if json.loads((ROOT/'output/v10_split_column/manifest.json').read_text()) != protocol:
        raise ValueError('Split-column source/input protocol changed.')
    times = np.arange(0, 365*DAY, interval_hours*3600., dtype=float)
    months = np.searchsorted(EDGES[1:], times, side='right')
    # Match the saved rain-vector convention: November–April (not DJF).
    winter = np.isin(months, [0, 1, 2, 3, 10, 11])
    rows = {};arrays = {};deltas = {};max_continuity = 0.
    for region in ('california', 'iberia'):
        case, profile, geometry, air, circulation = inputs[region+'_rh300']
        if not np.allclose(geometry.interfaces_pa[3], 60795.) or not np.allclose(geometry.interfaces_pa[4], 30000.):
            raise ValueError('Need the fixed-pressure interface for the ascent diagnostic.')
        for mode, setting in settings.items():
            projector = run.model.ColumnProjection(case.domain, circulation[0])
            events = run.model.nested_events(case.domain, setting, 41, profile.storm_domain_width_m)
            background = [];actual = []
            for time_s in times:
                quiet = run.model.flow_at(case.domain, profile, setting, [], time_s, geometry, circulation[3], projector, wind_mode=mode, circulation=circulation)
                full = run.model.flow_at(case.domain, profile, setting, events, time_s, geometry, circulation[3], projector, wind_mode=mode, circulation=circulation)
                # Vertical index 2 crosses the fixed 607.95 hPa interface.
                # Upward-positive g*mass_flux = -omega for this stationary p surface.
                background.append(quiet.vertical[2]*run.model.base.G)
                actual.append(full.vertical[2]*run.model.base.G)
                max_continuity = max(max_continuity, quiet.continuity, full.continuity)
            background = np.stack(background);actual = np.stack(actual);key = region+'_'+mode
            deltas[key] = actual-background
            masks = {'coastal': case.score_mask & (case.coast_distance_km < 150),
                'interior': case.score_mask & (case.coast_distance_km > 300), 'scored_land': case.score_mask}
            groups = {}
            for name, mask in masks.items():
                groups[name] = {'annual': ascent_statistics(background[:, mask], actual[:, mask]),
                    'winter_nov_apr': ascent_statistics(background[winter][:, mask], actual[winter][:, mask]),
                    'monthly': [ascent_statistics(background[months == month][:, mask], actual[months == month][:, mask]) for month in range(12)]}
            rows[key] = {'groups': groups, 'events': len(events), 'samples': len(times),
                'storm_settings': {'convergence_m_s': setting.storm_convergence_ms, 'rotation_m_s': setting.storm_rotation_ms,
                    'radius_km': setting.storm_radius_km, 'rate_per_month': setting.storm_rate_month}}
            arrays[key+'_background_monthly_pa_s'] = np.stack([background[months == month].mean(0) for month in range(12)])
            arrays[key+'_actual_monthly_pa_s'] = np.stack([actual[months == month].mean(0) for month in range(12)])
        difference = float(abs(deltas[region+'_uniform']-deltas[region+'_spatial']).max())
        if difference > 1e-10:
            raise ValueError('Paired storm circulation differs between background controls.')
        rows[region+'_storm_increment_identity_max_pa_s'] = difference
        arrays[region+'_coastal_mask'] = masks['coastal']
    if run.source_id() != protocol['code_sha256']:
        raise ValueError('Sources changed during the forcing audit.')
    data = {'source_code_sha256': protocol['code_sha256'],
        'source_manifest_sha256': sha256(ROOT/'output/v10_split_column/manifest.json'),
        'audit_script_sha256': sha256(Path(__file__)), 'forcing_interval_hours': interval_hours,
        'interface_pressure_pa': 60795., 'upward_positive': True, 'winter': 'November–April, matched to saved rainfall responses',
        'weighting': 'Equal model cells and equally spaced forcing ticks; no statistical independence or real-weather claim.',
        'maximum_air_continuity_kg_m2_s': max_continuity, 'cases': rows,
        'circulation_constructions': len(times)*8, 'state_advances': 0, 'downloads': 0, 'atlas_updated': False,
        'interpretation': 'Prescribed engine ascent, not observed omega. Linear storm increments can be identical while nonlinear positive ascent differs because background descent masks them. No humidity/temperature anomalies are explicitly coupled to the synthetic events; transported model humidity can still develop covariance.'}
    return data, arrays


def markdown(data):
    lines = ['# Cached storm-ascent audit', '',
        f"{data['circulation_constructions']} independent circulation constructions on the {data['forcing_interval_hours']}-hour clock. No climate states advanced. Cached inputs; no downloads.", '',
        'At the fixed 607.95 hPa interface, upward-positive g × vertical dry-air mass '
        'flux is reported in Pa/s (the opposite sign to omega). November–April '
        'matches the rainfall review. These are engine-implied motions, not observed '
        'vertical velocities or country-only area statistics.', '',
        '| Region / background | Coastal winter signed background | Signed storm increment | Positive-only background | Positive-only with storms | Storms reverse descent |',
        '|---|---:|---:|---:|---:|---:|']
    for key, row in data['cases'].items():
        if not isinstance(row, dict) or 'groups' not in row:
            continue
        r = row['groups']['coastal']['winter_nov_apr']
        lines.append(f"| {key} | {r['background_signed_pa_s']:+.5f} | {r['storm_signed_pa_s']:+.5f} | {r['background_positive_only_pa_s']:.5f} | {r['actual_positive_only_pa_s']:.5f} | {r['storm_reverses_descent_fraction']:.2%} |")
    lines += ['', 'Positive-only means average max(ascent, 0), including zeros in descending '
        'cells/times; they are not the mean conditioned on ascent. Signed storm '
        'contributions cannot be inferred by subtracting positive-only means.', '',
        '## Implication and limits', '',
        'The prescribed spatial monthly background has net coastal winter descent '
        'in both regions. The same synthetic storm perturbations that act on the '
        'uniform background mostly fail to overcome that descent. This identifies '
        'a forcing mechanism consistent with the dry spatial-wind runs; it does '
        'not prove that the monthly background should be reversed or increased. '
        'Terrain, projection and coarse pressure interpolation remain part of '
        'this imposed engine circulation.', '',
        'The events explicitly perturb wind/convergence but do not carry a '
        'moist warm sector or frontal temperature anomalies. Internally transported '
        'humidity can still correlate with winds; this audit does not measure '
        'that covariance or infer a real storm amplitude.', '',
        'An independent [ERA5 Mediterranean moisture-budget study](https://wcd.copernicus.org/articles/6/245/2025/) '
        'finds that submonthly eddies sustain winter net precipitation over land '
        'while the mean circulation partly opposes it. That supports testing '
        'event-linked forcing rather than making the monthly mean artificially '
        'wet. The study concerns the Mediterranean, not validation of this '
        'California experiment or a measured parameter choice.', '',
        'Next development: a bounded, conservative event/front mechanism test '
        'with an identical monthly mean supply and paired timing control. '
        'Separate imposed lifting from moisture timing; record actual import '
        'and coastal/interior rain. Obtain accessible high-frequency reference '
        'data before claiming realistic event statistics. No further parameter '
        'or storm-seed sweep is justified by this audit.', '',
        'Reproduce this forcing-only audit:', '', '```sh',
        '.venv/bin/python scripts/audit_v10_storm_ascent.py --write', '```']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--interval-hours', type=int, choices=(3, 24), default=3)
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_split_review/storm_ascent')
    args = parser.parse_args(argv);data, arrays = check(args.interval_hours)
    if args.write:
        atomic_json(args.out.with_suffix('.json'), data)
        atomic_npz(args.out.with_suffix('.npz'), **arrays)
        args.out.with_suffix('.md').write_text(markdown(data))
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
