"""Independently review completed boundary-humidity cases; saved fields only."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np

from scripts import check_v10_spatial_humidity as run
from scripts import review_v10_cloud_mixing as cloud
from scripts import review_v10_split_column as balance
from scripts.review_v10_storm_delivery import WINTER, SUMMER, rain_vector
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def verify_fields(record, initial, case, geometry, mode):
    errors = balance.verify_annual(record, initial, case)
    changes = np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c']).sum(axis=(0, 1))
    temperature = run.physics.base.temperature
    difference = temperature(record[0].energy, geometry.mass, record[0].water, geometry.height_m) - temperature(initial.energy, geometry.mass, initial.water, geometry.height_m)
    residual = changes - difference[:, case.score_mask].mean(1)
    if not np.allclose(residual, 0., atol=1e-8, rtol=0):
        raise ValueError('Signed thermal ledger disagrees with physical states.')
    parcel = np.array(record[-1]['parcel_rain_scored_land_mm'])
    layer = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
    if parcel.shape != layer.shape or not np.isfinite(parcel).all() or (parcel < 0).any() or (parcel - layer > 1e-8).any():
        raise ValueError('Invalid parcel/total rainfall split.')
    if mode == 'bulk' and parcel.any():
        raise ValueError('Bulk control contains parcel rain.')
    if mode == 'parcel_lower' and parcel[:, -1].any():
        raise ValueError('Lower cloud rule contains highest-layer parcel rain.')
    return dict(errors, signed_temperature_c=float(abs(residual).max()))


def load_verified(source, prepared=None):
    protocol, inputs, setting, initials, finals, originals, profiles = run.prepare() if prepared is None else prepared
    state = json.loads((source / 'state.json').read_text())
    if json.loads((source / 'manifest.json').read_text()) != protocol or state['status'] != 'complete':
        raise ValueError('Need unchanged, completed boundary-humidity results.')
    if set(state['cases']) != {job['key'] for job in protocol['jobs']}:
        raise ValueError('Boundary-humidity case set differs from protocol.')
    ready = json.loads((run.PREFLIGHT / 'manifest.json').read_text())
    if ready['protocol'] != protocol:
        raise ValueError('Prepared boundary-humidity forcing is stale.')
    tables = {region: run.run.previous.read_calendar(run.PREFLIGHT / 'forcing' / region, run.forcing_identity(protocol, region))[0] for region in inputs}
    records = {}; errors = []; dose_errors = []; seconds = 0.; cycles = 0
    for job in protocol['jobs']:
        key = job['key']; folder = source / 'cases' / key; row = state['cases'][key]
        run.run.previous.verify_completed(folder, row)
        identity = {**job, 'code_sha256': protocol['code_sha256'], 'settings': asdict(setting)}
        if json.loads((folder / 'config.json').read_text()) != identity:
            raise ValueError('Boundary-humidity config changed.')
        n = row['years']
        evidence = {f'year{year}.{ext}' for year in range(1, n + 1) for ext in ('json', 'npz')}
        if set(row['evidence_sha256']) != evidence or (n != 1 if job['phase'] == 'control' else not 3 <= n <= 6):
            raise ValueError('Incomplete boundary-humidity annual evidence.')
        region = job['region']; case, p, g, air, circulation = inputs[region]
        anchor = finals[region + '_' + job['mode']]
        initial = initials[region + '_' + job['mode']] if job['phase'] == 'control' else anchor[0]
        target = tables[region]['target_' + job['variant']]
        last = None; check = {'passed': False}; elapsed = 0.
        for year in range(1, n + 1):
            record = run.run.run.parent.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing boundary-humidity saved year.')
            run.run.run.validate_control_record(record, target)
            errors.append(verify_fields(record, initial, case, g, job['mode']))
            if last is not None:
                check = run.run.run.parent.settling(last, record, case, g)
            if year < n and year >= 3 and check['passed']:
                raise ValueError('Case ran beyond its first eligible settling point.')
            initial = record[0]; last = record; elapsed += record[-1]['elapsed_seconds']; cycles += 1
            dose_errors.append(float(abs(np.array(record[-1]['diagnostics']['monthly_boundary_import_gross_mm']) - target).max()))
        if job['phase'] == 'control':
            run.run.previous.replay.verify_physical(record, anchor)
            check = {'passed': True}
        base = {'row': {'response': rain_vector(case, anchor[1])}}
        computed = run.run.summary(record, case, check, n, base)
        computed.update(
            note='Local boundary-humidity sensitivity; prescribed circulation and reference-informed temperature. Cloud mode is an unmixed liquid bound, not a validated scheme.',
            physical_control_exact=job['phase'] == 'control', monthly_import_target_mm=target.tolist(),
            boundary_import_change_fraction=float(target.sum() / originals[region]['monthly_import_target_mm'].sum() - 1),
            case_config_sha256=sha256(folder / 'config.json'), elapsed_seconds=elapsed,
            evidence_sha256={name: sha256(folder / name) for name in sorted(evidence)})
        if computed != row:
            raise ValueError('Boundary-humidity summary disagrees with reconstructed saved fields.')
        records[key] = record; seconds += elapsed
    if run.source_id() != protocol['code_sha256']:
        raise ValueError('Frozen sources changed during boundary-humidity review.')
    return protocol, state, inputs, finals, records, seconds, cycles, errors, dose_errors


def seasonal_errors(old, new, observed, groups):
    """Cell/month absolute errors, not error of a spatial or seasonal mean."""
    result = {}
    for name, selected in groups.items():
        if not selected.any():
            continue
        result[name] = {}
        for season, months in (('winter', WINTER), ('summer', SUMMER)):
            a = old[months][:, selected] - observed[months][:, selected]
            b = new[months][:, selected] - observed[months][:, selected]
            result[name][season] = {
                'old_monthly_mae_mm': float(abs(a).mean()), 'new_monthly_mae_mm': float(abs(b).mean()),
                'monthly_mae_change_mm': float((abs(b) - abs(a)).mean()),
                'old_positive_bias_mm': float(np.maximum(a, 0).mean()), 'new_positive_bias_mm': float(np.maximum(b, 0).mean()),
                'old_deficit_mm': float(np.maximum(-a, 0).mean()), 'new_deficit_mm': float(np.maximum(-b, 0).mean())}
    return result


def process_screen(variant, coast_gain, errors, settled, thermal):
    """Preserve the declared coast floor; extra winter rain is not penalized."""
    arid = errors.get('reference_arid', {}).get('summer')
    improvement = arid is not None and arid['monthly_mae_change_mm'] < 0.
    return {'primary_fixed_input_contrast': variant == 'local_matched',
            'reference_arid_summer_error_reduced': bool(improvement),
            'coastal_winter_loss_at_most_2mm': coast_gain >= -2.,
            'settled_and_temperature_guards_pass': bool(settled and thermal),
            'passes': bool(variant == 'local_matched' and improvement and coast_gain >= -2. and settled and thermal)}


def analyse(source):
    protocol, state, inputs, finals, records, seconds, cycles, errors, dose = load_verified(source)
    cases = {}; arrays = {}; fields = {}; maps = run.run.run.koppen_maps
    for region, (case, p, g, air, circulation) in inputs.items():
        target = maps.classify_months(case.domain.temperature_c, case.observed_rain_mm, case.score_mask)
        groups = cloud.groups_for(case, target); fields[region] = (case, target)
        arrays.update({region + '_target': target, region + '_reference_rain_mm': case.observed_rain_mm,
                       region + '_longitude': case.longitude, region + '_latitude': case.domain.latitude, region + '_mask': case.score_mask})
        for job in (j for j in protocol['jobs'] if j['region'] == region):
            key = job['key']; row = state['cases'][key]; record = records[key]
            old = finals[region + '_' + job['mode']][1]
            seasonal = seasonal_errors(old, record[1], case.observed_rain_mm, groups)
            thermal = row['guards']['lower_temperature'] and row['guards']['upper_temperature']
            cases[key] = {'region': region, 'mode': job['mode'], 'variant': job['variant'],
                'response': row['response'], 'baseline_response': row['baseline_response'],
                'coastal_winter_gain_mm': row['coastal_winter_gain_mm'], 'monthly_mae_change_mm': row['monthly_mae_change_mm'],
                'koppen': row['koppen_fixed_surface_temperature'], 'settled': row['settling']['passed'],
                'temperature_guards_pass': thermal, 'boundary_import_change_fraction': row['boundary_import_change_fraction'],
                'placement': cloud.placement(old, record[1], case.observed_rain_mm, case.score_mask, groups),
                'seasonal_errors': seasonal, 'process_screen': process_screen(job['variant'], row['coastal_winter_gain_mm'], seasonal, row['settling']['passed'], thermal)}
            # The three regime groups partition scored land; location groups overlap.
            contribution = sum(cases[key]['placement'][name]['overall_mae_gain_contribution_mm'] for name in ('reference_mediterranean', 'reference_arid', 'other_reference_land') if name in cases[key]['placement'])
            if not np.isclose(contribution, -row['monthly_mae_change_mm'], atol=1e-10, rtol=0):
                raise ValueError('Reference-regime error contributions do not close.')
            name = region + '_' + job['mode'] + '_' + job['variant']
            arrays[name + '_rain_mm'] = record[1]
            arrays[name + '_koppen'] = maps.classify_months(case.domain.temperature_c, record[1], case.score_mask)
    data = {'source_code_sha256': protocol['code_sha256'], 'source_manifest_sha256': sha256(source / 'manifest.json'),
            'source_state_sha256': sha256(source / 'state.json'), 'analysis_script_sha256': sha256(Path(__file__)),
            'sources_verified': True, 'completed_cases': len(cases), 'saved_years': cycles, 'integration_minutes': seconds / 60.,
            'all_settled': all(row['settled'] for row in cases.values()),
            'all_temperature_guards_pass': all(row['temperature_guards_pass'] for row in cases.values()),
            'exact_physical_controls': sum(job['phase'] == 'control' for job in protocol['jobs']),
            'maximum_recomputed_errors': {k: max(abs(e[k]) for e in errors) for k in errors[0]},
            'maximum_monthly_gross_import_error_mm': max(dose), 'cases': cases,
            'seasons': 'October–March winter; April–September summer, following the frozen response convention.',
            'limitations': 'One reused synthetic catalogue (67), 60km cells, prescribed flow and reference-informed atmospheric temperature. Coarse NCEP/NCAR 1981–2010 monthly humidity versus WorldClim 1970–2000 rain/T. Koppen uses the same observed surface temperature on both sides. Local-matched isolates redistribution at fixed actual monthly gross input, not unchanged observed humidity.',
            'geography': 'Iberia-domain interior includes North Africa. Coastal/interior masks overlap the three reference-climate groups; do not sum them together.',
            'new_climate_integrations': 0, 'new_downloads': 0, 'atlas_updated': False}
    return data, fields, arrays


def markdown(data):
    lines = ['# Completed boundary-humidity comparison', '',
        f"All {data['completed_cases']} cases and {data['saved_years']} saved years verified; {data['integration_minutes']:.1f} integration minutes. Four exact physical controls. Annual water/energy, signed thermal ledgers, monthly input, settling and reconstructed summaries pass.", '',
        '## Primary result: local humidity with the same monthly incoming water', '',
        '| Region / cloud rule | Coast winter: uniform → local matched / reference | Arid summer monthly MAE: uniform → matched | Med still arid | Declared process screen |',
        '|---|---:|---:|---:|---|']
    for region in ('california', 'iberia'):
        for mode in ('bulk', 'parcel_lower'):
            row = data['cases'][f'test_{region}_{mode}_local_matched']; coast = row['placement']['coast']
            arid = row['seasonal_errors']['reference_arid']['summer']
            base = data['cases'][f'control_{region}_{mode}_uniform']['koppen']['target_mediterranean_to_arid']
            lines.append(f"| {region} / {mode} | {coast['old_winter_mm']:.2f} → {coast['new_winter_mm']:.2f} / {coast['reference_winter_mm']:.1f} mm | {arid['old_monthly_mae_mm']:.3f} → {arid['new_monthly_mae_mm']:.3f} mm | {base:.1%} → {row['koppen']['target_mediterranean_to_arid']:.1%} | {'Pass' if row['process_screen']['passes'] else 'Fail'} |")
    lines += ['', 'The screen requires reduced cell/month absolute error in reference-arid summer land, no coastal winter loss greater than 2mm, settling and temperature guards. Passing this small mechanism screen is not sufficient for production selection. An improved spatial mean or overall MAE alone is not the criterion.', '',
        '## Separate redistribution from adding water', '',
        '| Region / lower-interface cloud rule | Gross incoming water change | Coast winter gain | Overall monthly MAE change | Arid summer monthly MAE change |',
        '|---|---:|---:|---:|---:|']
    for region in ('california', 'iberia'):
        for variant in ('local', 'local_matched'):
            row = data['cases'][f'test_{region}_parcel_lower_{variant}']
            delta = row['seasonal_errors']['reference_arid']['summer']['monthly_mae_change_mm']
            lines.append(f"| {region} / {variant} | {row['boundary_import_change_fraction']:+.1%} | {row['coastal_winter_gain_mm']:+.2f} mm | {row['monthly_mae_change_mm']:+.3f} mm | {delta:+.3f} mm |")
    lines += ['', 'Negative MAE change improves error. Unmatched local humidity changes amount and pattern together; it is retained as a sensitivity, not selected as the winner.', '',
        '![Seasonal rainfall](seasonal_rainfall.png)', '', '![Fixed-temperature Koppen](koppen_comparison.png)', '',
        'The same observed surface temperatures classify target and simulated rain. These are project classifications of WorldClim monthly data, not an external published Koppen raster. The Iberia domain includes North Africa. One reused synthetic catalogue does not give an observational uncertainty interval or independent validation. No atlas update, downloads or new climate integration during review.', '',
        'Reproduce saved-data review:', '', '```sh', '.venv/bin/python scripts/review_v10_spatial_humidity.py --write', '```']
    return '\n'.join(lines) + '\n'


def plot(data, fields, arrays, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    maps = run.run.run.koppen_maps
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8), constrained_layout=True)
    for i, (region, (case, target)) in enumerate(fields.items()):
        groups = cloud.groups_for(case, target)
        for j, (group, title) in enumerate((('coast', 'Coast <150km'), ('reference_arid', 'Reference-arid land'))):
            ax = axes[i, j]; selected = groups[group]; x = np.arange(1, 13)
            ax.plot(x, arrays[region + '_reference_rain_mm'][:, selected].mean(1), 'o-', color='#243e47', label='Earth target')
            for variant, label, color, style in (('uniform', 'Uniform humidity', '#828282', '--'), ('local', 'Local humidity · more input', '#c17b39', ':'), ('local_matched', 'Local · same monthly input', '#157c98', '-')):
                rain = arrays[region + '_parcel_lower_' + variant + '_rain_mm']
                ax.plot(x, rain[:, selected].mean(1), style, color=color, lw=2, label=label)
            ax.set(title=region.title() + ' · ' + title, ylabel='Rain (mm / month)', xticks=x, ylim=(0, None)); ax.grid(alpha=.2)
            ax.legend(frameon=False, fontsize=8)
    fig.suptitle('Changing boundary humidity has a small effect; winter drought remains', fontsize=14)
    for ext in ('png', 'svg'):
        fig.savefig(out / ('seasonal_rainfall.' + ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(15.4, 11.8))
    fig.subplots_adjust(left=.055, right=.99, top=.875, bottom=.22, wspace=.16, hspace=.28)
    fig.suptitle('Local boundary humidity does not restore Mediterranean climate', y=.975, fontsize=19, fontweight='bold')
    fig.text(.52, .94, 'Same monthly incoming water · lower-interface cloud bound · fixed seed67 · 60km cells', ha='center', fontsize=11)
    fig.text(.52, .917, 'Shared observed surface temperature; only the boundary humidity pattern changes', ha='center', fontsize=10)
    present = set()
    for i, (region, (case, target)) in enumerate(fields.items()):
        mask = case.score_mask; land = case.domain.land; lon = case.longitude[0]; lat = case.domain.latitude[:, 0]
        dx = float(np.diff(lon).mean()); dy = float(abs(np.diff(lat).mean()))
        extent = (lon[0]-dx/2, lon[-1]+dx/2, lat[-1]-dy/2, lat[0]+dy/2)
        for j, (variant, title) in enumerate((('target', 'Earth target'), ('uniform', 'Uniform boundary humidity'), ('local_matched', 'Local · same incoming water'))):
            classes = target if variant == 'target' else arrays[region + '_parcel_lower_' + variant + '_koppen']
            rgb = np.full(land.shape + (3,), np.array([226, 239, 243]) / 255.)
            rgb[land] = np.array([222, 226, 226]) / 255.
            rgb[mask] = np.array([maps.koppen.COLORS[maps.koppen.CODES[k]] for k in classes[mask]]) / 255.
            present.update(maps.koppen.CODES[k] for k in classes[mask])
            ax = axes[i, j]; ax.imshow(rgb, extent=extent, origin='upper', interpolation='nearest')
            ax.contour(case.longitude, case.domain.latitude, land.astype(float), levels=[.5], colors=['#52676d'], linewidths=.45)
            ax.set(title=title, xlim=(case.longitude[mask].min()-1.7*dx, case.longitude[mask].max()+1.7*dx), ylim=(case.domain.latitude[mask].min()-1.1*dy, case.domain.latitude[mask].max()+1.1*dy))
            ax.set_aspect(1 / np.cos(np.deg2rad(case.domain.latitude[mask].mean())))
            for city, x, y in maps.LANDMARKS[region]:
                ax.plot(x, y, 'o', ms=2.5, color='#14232a'); ax.annotate(city, (x, y), xytext=(4, 4), textcoords='offset points', fontsize=7, bbox=dict(facecolor='white', alpha=.75, edgecolor='none', pad=1))
            caption = 'Reference climate' if variant == 'target' else f"Med still arid: {data['cases'][('control_' if variant == 'uniform' else 'test_') + region + '_parcel_lower_' + variant]['koppen']['target_mediterranean_to_arid']:.1%}"
            ax.text(.5, -.13, caption, transform=ax.transAxes, ha='center', fontsize=10)
            if j == 0:
                ax.set_ylabel(region.title() + '\nLatitude')
    patches = [Patch(facecolor=np.array(maps.koppen.COLORS[code])/255., label=code + ' · ' + maps.koppen.DESCRIPTIONS[code]) for code in maps.koppen.CODES if code in present]
    fig.legend(handles=patches, loc='lower center', bbox_to_anchor=(.52, .045), ncol=3, frameon=False, fontsize=9)
    fig.text(.52, .022, 'WorldClim 1970–2000 · final settled synthetic year · grey: unscored land · atlas unchanged', ha='center', fontsize=9)
    for ext in ('png', 'svg'):
        fig.savefig(out / ('koppen_comparison.' + ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_spatial_humidity')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_spatial_humidity_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    if args.write:
        for protected in (args.source, run.PREFLIGHT, run.SOURCE, run.replay.PREFLIGHT, run.replay.SOURCE, run.run.SOURCE, run.run.PREFLIGHT):
            a, b = args.out.resolve(), protected.resolve()
            if a == b or a in b.parents or b in a.parents:
                raise ValueError('Preserve experiment evidence and prepared forcing.')
    data, fields, arrays = analyse(args.source)
    if args.write:
        atomic_json(args.out/'review.json', data); atomic_npz(args.out/'map_fields.npz', **arrays)
        (args.out/'review.md').write_text(markdown(data)); plot(data, fields, arrays, args.out)
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
