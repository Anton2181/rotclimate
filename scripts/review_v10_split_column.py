"""Verify completed split-column evidence and compare rain placement; no integration."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_split_column as run, plot_v10_koppen as maps
from rotclimate_v10.core import DAY
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def verify_annual(record, initial, case):
    """Rebuild annual balances and cross-check independently saved diagnostics."""
    state, rain, _, _, info = record
    b = info['budget'];d = info['diagnostics']
    start_water = float((initial.water.sum(0)+initial.soil).mean())
    start_energy = float(initial.energy.sum(0).mean())
    if abs(start_water-info['initial_water']) > 1e-8 or abs(start_energy-info['initial_energy']) > .01:
        raise ValueError('Annual start does not match the preceding physical state.')
    water_change = float((state.water.sum(0)+state.soil).mean())-start_water
    energy_change = float(state.energy.sum(0).mean())-start_energy
    water_error = water_change-(b['ocean_evaporation_mm']-b['ocean_rain_mm']-b['runoff_mm']
        -b['boundary_export_mm']+b['roundoff_correction_mm'])
    energy_error = energy_change-(b['surface_latent_input_j_m2']+b['temperature_relaxation_j_m2']
        -b['energy_boundary_export_j_m2']+b['roundoff_energy_j_m2']+b['prescribed_flow_work_j_m2'])
    gross_error = b['boundary_export_gross_mm']-b['boundary_import_gross_mm']-b['boundary_export_mm']
    atmospheric_change = float((state.water-initial.water).sum(0).mean())
    atmospheric_error = atmospheric_change-(b['boundary_import_gross_mm']-b['boundary_export_gross_mm']
        +b['ocean_evaporation_mm']+b['land_evaporation_mm']-b['rain_mm']+b['roundoff_correction_mm'])
    if abs(water_error) > 1e-6 or abs(energy_error) > 1 or abs(gross_error) > 1e-7 or abs(atmospheric_error) > 1e-6:
        raise ValueError('Recomputed annual water/energy/gross-flow balance failed.')
    if abs(water_error-b['annual_water_error_mm']) > 1e-8 or abs(energy_error-b['annual_energy_error_j_m2']) > .01:
        raise ValueError('Stored annual residual disagrees with the physical fields.')
    if any(info['totals'][key] != b[key] for key in info['totals']):
        raise ValueError('Annual totals and budget disagree.')
    if min(b['boundary_import_gross_mm'], b['boundary_export_gross_mm']) < 0:
        raise ValueError('Gross transport cannot be negative.')
    if abs(rain.sum(0).mean()-b['rain_mm']) > 1e-8 or abs(np.where(~case.domain.land, rain.sum(0), 0).mean()-b['ocean_rain_mm']) > 1e-8:
        raise ValueError('Saved rain does not match the physical ledger.')
    layer = np.array(d['layer_rain_scored_land_mm'])
    if (layer < 0).any() or not np.allclose(layer.sum(1), rain[:, case.score_mask].mean(1), atol=1e-8, rtol=0):
        raise ValueError('Layer rainfall disagrees with scored monthly rain.')
    return {'water_mm': water_error, 'energy_j_m2': energy_error,
        'gross_net_mm': gross_error, 'atmospheric_water_mm': atmospheric_error}


def load_verified(source):
    protocol, inputs, settings, baselines = run.prepare()
    state = json.loads((source/'state.json').read_text())
    if json.loads((source/'manifest.json').read_text()) != protocol or state['status'] != 'complete':
        raise ValueError('Need an unchanged completed split-column protocol.')
    if set(state['cases']) != {job['key'] for job in protocol['jobs']}:
        raise ValueError('Split-column case set differs from the declared plan.')
    for key, (case, profile, g, air, circulation) in inputs.items():
        expected = run.input_arrays(g, air, profile, circulation)
        with np.load(source/'inputs'/(key+'.npz'), allow_pickle=False) as saved:
            if set(saved.files) != set(expected) or run.geometry_rules.array_id({k:saved[k] for k in saved.files}) != protocol['inputs'][key]:
                raise ValueError('Split-column input arrays changed.')
    records = {};seconds = 0.;cycles = 0;errors = []
    for job in protocol['jobs']:
        variant = run.VARIANTS[job['variant']];input_key = job['region']+'_'+variant['lid']
        case, profile, g, air, circulation = inputs[input_key];setting = settings[job['wind']]
        folder = source/'cases'/job['key'];row = state['cases'][job['key']]
        identity = dict(job, variant=variant, settings=asdict(setting), input_array_sha256=protocol['inputs'][input_key])
        if json.loads((folder/'config.json').read_text()) != identity or json.loads((folder/'summary.json').read_text()) != row:
            raise ValueError('Split-column config or summary changed.')
        count = row['years'];evidence = {f'year{n}.{ext}' for n in range(1, count+1) for ext in ('json', 'npz')}
        if not 3 <= count <= 6 or set(row['evidence_sha256']) != evidence:
            raise ValueError('Incomplete split-column annual evidence declaration.')
        for name, digest in row['evidence_sha256'].items():
            if sha256(folder/name) != digest:
                raise ValueError('Split-column annual evidence changed.')
        initial = run.model.initial_state(case.domain, profile, setting, g, air, variant['boundary'], circulation)
        previous = None;check = {'passed': False}
        for year in range(1, count+1):
            record = run.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed split-column year.')
            errors.append(verify_annual(record, initial, case))
            thermal = np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c']).sum(axis=(0, 1))
            start_t = run.model.base.temperature(initial.energy, g.mass, initial.water, g.height_m)
            end_t = run.model.base.temperature(record[0].energy, g.mass, record[0].water, g.height_m)
            if not np.allclose(thermal, (end_t-start_t)[:, case.score_mask].mean(1), atol=1e-8, rtol=0):
                raise ValueError('Signed annual thermal changes disagree with the physical states.')
            if previous is not None:
                check = run.settling(previous, record, case, g)
            if year < count and year >= 3 and check['passed']:
                raise ValueError('Case continued beyond its declared first settling point.')
            initial = record[0];previous = record
            seconds += record[-1]['elapsed_seconds'];cycles += 1
        computed = run.night.summarize(record, case, check, count)
        computed['response'] = run.review.run.review.run.rain_vector(case, record[1])
        if any(computed[name] != row[name] for name in computed):
            raise ValueError('Split-column summaries disagree with the physical fields.')
        records[job['key']] = record
    if run.source_id() != protocol['code_sha256']:
        raise ValueError('Sources changed during the evidence review.')
    return protocol, state, inputs, settings, baselines, records, seconds, cycles, errors


def supply_balance(budget):
    supply = budget['boundary_import_gross_mm']+budget['ocean_evaporation_mm']+budget['land_evaporation_mm']
    if supply <= 0:
        raise ValueError('Need positive atmospheric vapor supply.')
    return {'gross_boundary_import_mm': budget['boundary_import_gross_mm'],
        'gross_boundary_export_mm': budget['boundary_export_gross_mm'],
        'total_atmospheric_supply_mm': supply,
        'rain_to_supply': budget['rain_mm']/supply,
        'export_to_supply': budget['boundary_export_gross_mm']/supply,
        'note': 'Whole-domain atmospheric input/removals, including ocean and unscored land. No source attribution or land precipitation efficiency.'}


def error_changes(old, new, observed, mask):
    gain = (abs(old-observed)-abs(new-observed)).mean(0)
    over = old.sum(0) > observed.sum(0)
    return {'total_mae_improvement_mm': float(gain[mask].mean()),
        'baseline_annual_overwet_cells_contribution_mm': float(np.where(over, gain, 0)[mask].mean()),
        'baseline_annual_underwet_cells_contribution_mm': float(np.where(~over, gain, 0)[mask].mean()),
        'fraction_cells_with_lower_monthly_error': float((gain[mask] > 0).mean()),
        'note': 'Additive MAE contributions grouped by baseline annual bias, not causal attribution or independent samples.'}


def analyse(source):
    protocol, state, inputs, settings, baselines, records, seconds, cycles, errors = load_verified(source)
    _, parent_state, _, parent_records, _, _ = run.review.load_verified(ROOT/'output/v10_water_sources')
    rows = {};map_fields = {};arrays = {};baseline_rows = {}
    for region in ('california', 'iberia'):
        case = inputs[region+'_rh300'][0];mask = case.score_mask
        target = maps.classify_months(case.domain.temperature_c, case.observed_rain_mm, mask)
        if not (case.domain.temperature_c[maps.SUMMER][:, mask].mean(0) > case.domain.temperature_c[~maps.SUMMER][:, mask].mean(0)).all():
            raise ValueError('Reference half-year convention changed.')
        map_fields[region] = (case, {'target': target})
        arrays[region+'_target'] = target;arrays[region+'_mask'] = mask
        arrays[region+'_longitude'] = case.longitude;arrays[region+'_latitude'] = case.domain.latitude
        for mode in settings:
            key = region+'_'+mode;old = baselines[key];record = parent_records[key+'_s41']
            classes = maps.classify_months(case.domain.temperature_c, record[1], mask)
            baseline_rows[key] = {'response': old['response'],
                'koppen': maps.comparison(target, classes, mask),
                'annual_layer_rain_mm': np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm']).sum(0).tolist(),
                'gross_boundary_import_mm': float(sum(old['sources']['atmospheric_budget_domain_mean']['totals']['import_mm']))}
    for job in protocol['jobs']:
        key = job['key'];region = job['region'];mode = job['wind']
        case = inputs[region+'_'+run.VARIANTS[job['variant']]['lid']][0]
        row = state['cases'][key];record = records[key];b = row['budget']
        baseline = baseline_rows[region+'_'+mode]
        layer = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm']).sum(0)
        classes = maps.classify_months(case.domain.temperature_c, record[1], case.score_mask)
        rows[key] = {'response': row['response'], 'baseline_key': region+'_'+mode,
            'annual_layer_rain_mm': layer.tolist(), 'highest_layer_rain_fraction': float(layer[-1]/layer.sum()),
            'actual_boundary_import_change_fraction': b['boundary_import_gross_mm']/baseline['gross_boundary_import_mm']-1,
            'supply': supply_balance(b), 'koppen': maps.comparison(map_fields[region][1]['target'], classes, case.score_mask),
            'error_change': error_changes(parent_records[region+'_'+mode+'_s41'][1], record[1], case.observed_rain_mm, case.score_mask),
            'settled': row['settling']['passed'], 'broad_screen_passed': row['eligible'],
            'temperature_departure_p95_c': row['temperature_departure_p95_c'],
            'mean_energy_flux_w_m2': {name: b[name]/(365*DAY) for name in
                ('surface_latent_input_j_m2', 'temperature_relaxation_j_m2', 'energy_boundary_export_j_m2', 'prescribed_flow_work_j_m2')}}
        arrays[key] = classes
        if job['variant'] == 'split_column_matched':
            map_fields[region][1][mode] = classes
    contrasts = {}
    for region in ('california', 'iberia'):
        for mode in settings:
            prefix = region+'_'+mode;a = rows[prefix+'_split_dry'];b = rows[prefix+'_split_rh300']
            change = b['response']['annual_rain_mm']-a['response']['annual_rain_mm']
            top = b['annual_layer_rain_mm'][-1]-a['annual_layer_rain_mm'][-1]
            contrasts[prefix] = {'annual_rain_change_mm': change, 'highest_layer_rain_change_mm': top,
                'fraction_rain_change_in_highest_layer': top/change if abs(change) > 1e-10 else None,
                'coastal_winter_change_mm': b['response']['coast_winter_mm']-a['response']['coast_winter_mm']}
    data = {'source_manifest_sha256': sha256(source/'manifest.json'), 'source_state_sha256': sha256(source/'state.json'),
        'source_code_sha256': protocol['code_sha256'], 'parent_manifest_sha256': protocol['parent_manifest_sha256'],
        'parent_state_sha256': protocol['parent_state_sha256'], 'analysis_script_sha256': sha256(Path(__file__)),
        'classifier_sha256': sha256(Path(maps.koppen.__file__)), 'map_helper_sha256': sha256(Path(maps.__file__)),
        'sources_verified': True, 'completed_cases': len(rows), 'cycles': cycles, 'integration_minutes': seconds/60,
        'all_settled': all(row['settled'] for row in rows.values()),
        'maximum_absolute_recomputed_errors': {name: max(abs(e[name]) for e in errors) for name in errors[0]},
        'baselines': baseline_rows, 'cases': rows, 'upper_humidity_contrasts': contrasts,
        'map_policy': 'Matched-column cases selected by fixed control identity, not best score. Common observed WorldClim surface T; Gregorian rain totals; project classifier, shared scored masks. Last settled synthetic year, not independent predicted surface climate or multi-decadal validation.',
        'new_climate_integrations': 0, 'atlas_updated': False}
    return data, map_fields, arrays


def markdown(data):
    ca = data['cases']['california_uniform_split_column_matched'];gain = ca['error_change']
    lines = ['# Completed five-layer structural review', '',
        f"{data['completed_cases']}/12 cases verified, {data['cycles']} cycles, {data['integration_minutes']:.2f} saved integration minutes. All settle; reconstructed annual water/energy and gross-flow budgets close.", '',
        '| Region / winds / upper control | Rain MAE | Annual rain / observed | Coastal winter / observed | Import change | Highest-layer rain |',
        '|---|---:|---:|---:|---:|---:|']
    for key, row in data['cases'].items():
        r = row['response']
        lines.append(f"| {key} | {r['monthly_mae_mm']:.2f} | {r['annual_rain_mm']:.1f} / {r['annual_reference_mm']:.1f} mm | {r['coast_winter_mm']:.1f} / {r['coast_winter_reference_mm']:.1f} mm | {row['actual_boundary_import_change_fraction']:+.1%} | {row['highest_layer_rain_fraction']:.1%} |")
    lines += ['', 'Import change compares actual gross vapor influx with the paired four-layer control. '
        'Matching incoming column concentration did not match wind-weighted water supply.', '',
        '## What the lower error means', '',
        'California uniform-wind monthly MAE improves 40.07 → 27.37 mm in the matched-column '
        'control, but annual rain falls 473.3 → 218.6 mm against 401.8 observed. Coastal '
        'winter rain falls 335.0 → 250.5 mm against 534.8 observed. This is useful error '
        'reduction without the desired coastal wetting. Iberia uniform MAE barely changes; '
        'the spatial-wind controls remain severely dry. No broad regional success.', '',
        f"The California uniform MAE gain of {gain['total_mae_improvement_mm']:.2f} mm decomposes into "
        f"{gain['baseline_annual_overwet_cells_contribution_mm']:+.2f} mm from cells that were annually too wet "
        f"and {gain['baseline_annual_underwet_cells_contribution_mm']:+.2f} mm from those already too dry. "
        f"Only {gain['fraction_cells_with_lower_monthly_error']:.1%} of scored cells improve their monthly error. "
        'This is an additive error decomposition, not a causal experiment.', '',
        '| Dry upper boundary → retained RH300 | Extra annual rain | Extra rain in highest layer | Fraction of increase there |',
        '|---|---:|---:|---:|']
    for key, row in data['upper_humidity_contrasts'].items():
        lines.append(f"| {key} | {row['annual_rain_change_mm']:.2f} mm | {row['highest_layer_rain_change_mm']:.2f} mm | {row['fraction_rain_change_in_highest_layer']:.1%} |")
    lines += ['', 'The upper incoming humidity is an assumption, not observed. These are changes '
        'in condensation/rainfall by formation layer, not tagged molecular origins. '
        'The new highest layer is represented at 150 hPa; liquid saturation adjustment '
        'and immediate surface rainout remain unchanged. These results do not validate '
        'high-cloud/ice processes or demonstrate that previously missing middle-level '
        'humidity becomes useful coastal rain.', '',
        '## Mediterranean climate response', '',
        '| Fixed column-matched control | Old → new exact class match | Old → new reference Mediterranean becoming arid |',
        '|---|---:|---:|']
    for region in ('california', 'iberia'):
        for mode in ('uniform', 'spatial'):
            key = region+'_'+mode;old = data['baselines'][key]['koppen'];new = data['cases'][key+'_split_column_matched']['koppen']
            lines.append(f"| {key} | {old['exact_class_agreement']:.1%} → {new['exact_class_agreement']:.1%} | {old['target_mediterranean_to_arid']:.1%} → {new['target_mediterranean_to_arid']:.1%} |")
    lines += ['', '![Fixed-temperature Köppen comparison](koppen_comparison.png)', '',
        'Both sides hold the same observed surface temperature; only monthly rain '
        'changes. Reference is the same-grid WorldClim classification, not an external '
        'published Köppen raster. The 60 km evaluation domains include neighboring '
        'western US / Mediterranean / North African land. Statistics count shared '
        'scored cells, not country-only areas or independent weather samples. No '
        'fantasy-calendar rebinning or conversion from monthly totals is applied.', '',
        '![Monthly coastal and interior rain](rainfall_comparison.png)', '',
        '## Decision', '',
        'Retain this as structural evidence, without selecting a fantasy climate or '
        'publishing an atlas. Do not start another parameter or storm-seed search. '
        'Next distinguish missing transient ascent/fronts and event-linked moisture '
        'from immediate rainout and vertical transport artifacts. Audit forcing '
        'and manufactured limits first; the paused six-hourly NOAA audit remains '
        'necessary for observational covariance, but cached monthly means cannot '
        'supply that information. A synthetic timing experiment would establish '
        'mechanism sensitivity only, not measured real-weather forcing.', '',
        'Reproduce this saved-only review:', '', '```sh',
        '.venv/bin/python scripts/review_v10_split_column.py --write', '```', '',
        'No seasonal simulation, optimization, download or atlas update was run.']
    return '\n'.join(lines)+'\n'


def draw(data, fields, records, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter
    fig, axes = plt.subplots(2, 3, figsize=(15.4, 11.8))
    fig.subplots_adjust(left=.055, right=.99, top=.875, bottom=.22, wspace=.16, hspace=.28)
    fig.suptitle('Five-layer test: Mediterranean rain is still missing', y=.975, fontsize=20, fontweight='bold')
    fig.text(.52, .94, 'Same observed surface temperature · reference rain versus simulated rain · 60 km cells', ha='center', fontsize=11)
    fig.text(.52, .917, 'Fixed column-matched controls · humidity above 300 hPa is assumed · weather seed 41', ha='center', fontsize=10)
    present = set()
    for row, (region, (case, classes)) in enumerate(fields.items()):
        mask = case.score_mask;land = case.domain.land;lon = case.longitude[0];lat = case.domain.latitude[:, 0]
        dx = float(np.diff(lon).mean());dy = float(abs(np.diff(lat).mean()))
        extent = (lon[0]-dx/2, lon[-1]+dx/2, lat[-1]-dy/2, lat[0]+dy/2)
        xlim = (case.longitude[mask].min()-1.7*dx, case.longitude[mask].max()+1.7*dx)
        ylim = (case.domain.latitude[mask].min()-1.1*dy, case.domain.latitude[mask].max()+1.1*dy)
        for column, mode in enumerate(('target', 'uniform', 'spatial')):
            ax = axes[row, column];image = np.empty(land.shape+(3,), float)
            image[:] = np.array([226, 239, 243])/255;image[land] = np.array([222, 226, 226])/255
            image[mask] = np.array([maps.koppen.COLORS[maps.koppen.CODES[i]] for i in classes[mode][mask]])/255
            present.update(maps.koppen.CODES[i] for i in classes[mode][mask])
            ax.imshow(image, extent=extent, origin='upper', interpolation='nearest')
            ax.contour(case.longitude, case.domain.latitude, land.astype(float), levels=[.5], colors=['#52676d'], linewidths=.45)
            ax.set(xlim=xlim, ylim=ylim, title=maps.LABELS[mode]);ax.set_aspect(1/np.cos(np.deg2rad(case.domain.latitude[mask].mean())))
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{abs(x):g}°'+('W' if x < 0 else 'E')))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f'{y:g}°N'));ax.tick_params(labelsize=8)
            for name, x, y in maps.LANDMARKS[region]:
                if xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]:
                    ax.plot(x, y, 'o', ms=2.5, color='#14232a');ax.annotate(name, (x, y), xytext=(4, 4), textcoords='offset points', fontsize=7, bbox=dict(facecolor='white', alpha=.75, edgecolor='none', pad=1))
            if mode == 'target':
                caption = f"{case.observed_rain_mm.sum(0)[mask].mean():.0f} mm/year · observed rain"
            else:
                entry = data['cases'][region+'_'+mode+'_split_column_matched'];k = entry['koppen']
                caption = f"{entry['response']['annual_rain_mm']:.0f} mm/year · {k['exact_class_agreement']:.0%} match · {k['target_mediterranean_to_arid']:.0%} Cs → arid"
            ax.set_xlabel(caption, fontsize=9, labelpad=8)
        axes[row, 0].set_ylabel(maps.REGION_NAMES[region], fontsize=11, fontweight='semibold', labelpad=14)
    handles = [Patch(facecolor=np.array(maps.koppen.COLORS[c])/255, label=c+' · '+maps.koppen.DESCRIPTIONS[c]) for c in maps.koppen.CODES if c in present]
    handles.append(Patch(facecolor='#dee2e2', label='Gray · outside shared evaluation mask'))
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.52, .047), ncol=4, frameon=False, fontsize=8.3)
    fig.text(.52, .022, 'WorldClim 1970–2000 target; fixed-temperature rainfall diagnostic. Last settled synthetic year; no atlas update.', ha='center', fontsize=9)
    for ext in ('png', 'svg'):
        fig.savefig(out/('koppen_comparison.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8), constrained_layout=True)
    colors = {'uniform': '#277d9a', 'spatial': '#b5652b'}
    for row, (region, (case, _)) in enumerate(fields.items()):
        for col, (name, mask) in enumerate((('Coast <150 km', case.score_mask & (case.coast_distance_km < 150)), ('Interior >300 km', case.score_mask & (case.coast_distance_km > 300)))):
            ax = axes[row, col];x = np.arange(1, 13)
            ax.plot(x, case.observed_rain_mm[:, mask].mean(1), 'o-', color='#26383e', label='Observed', lw=2)
            for mode in ('uniform', 'spatial'):
                for stage, style in (('old', '--'), ('matched', '-')):
                    rain = records[region+'_'+mode+'_'+stage]
                    ax.plot(x, rain[:, mask].mean(1), style, color=colors[mode], label=mode.title()+' · '+stage, lw=1.7)
            ax.set(title=region.title()+' · '+name, xticks=x, ylabel='Rainfall (mm / month)', ylim=(0, None))
            ax.grid(alpha=.2);ax.legend(frameon=False, fontsize=8)
    fig.suptitle('Vertical splitting reduces some error, without restoring coastal winter rain', fontsize=14)
    for ext in ('png', 'svg'):
        fig.savefig(out/('rainfall_comparison.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_split_column')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_split_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv);data, fields, arrays = analyse(args.source)
    if args.write:
        if args.out.resolve() == args.source.resolve() or args.source.resolve() in args.out.resolve().parents:
            raise ValueError('Choose a separate review folder to preserve experiment evidence.')
        args.out.mkdir(parents=True, exist_ok=True);atomic_json(args.out/'review.json', data)
        atomic_npz(args.out/'koppen_fields.npz', **arrays)
        (args.out/'review.md').write_text(markdown(data))
        rain_records = {}
        for region in fields:
            for mode in ('uniform', 'spatial'):
                key = region+'_'+mode
                for stage, folder in (('old', ROOT/'output/v10_water_sources/cases'/(key+'_s41')),
                                      ('matched', args.source/'cases'/(key+'_split_column_matched'))):
                    row = json.loads((folder/'summary.json').read_text())
                    with np.load(folder/f'year{row["years"]}.npz', allow_pickle=False) as a:
                        rain_records[key+'_'+stage] = a['rain']
        draw(data, fields, rain_records, args.out)
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
