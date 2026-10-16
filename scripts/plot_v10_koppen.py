"""Köppen comparison of verified completed Earth pilots; no climate integration.

Main maps use common observed surface T to isolate simulated rain. A separately
labelled sensitivity view adds lowest-layer model-minus-target T anomalies.
The atmospheric layer temperature is never passed off as 2 m temperature.
"""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import review_v10_spatial_wind as spatial, review_v10_storm_delivery as storms
from scripts import review_v10_pressure_thermo as pressure
from rotclimate import koppen
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
SUMMER = np.array([False, False, False, True, True, True, True, True, True, False, False, False])
LABELS = {'target': 'Earth target', 'uniform': 'Model · uniform winds', 'spatial': 'Model · spatial winds'}
REGION_NAMES = {'california': 'California / western US', 'iberia': 'Iberia / western Mediterranean'}
LANDMARKS = {'california': [('San Francisco', -122.42, 37.77), ('Los Angeles', -118.24, 34.05)],
    'iberia': [('Lisbon', -9.14, 38.72), ('Madrid', -3.70, 40.42), ('Algiers', 3.06, 36.75)]}


def classify_months(temperature, rain, mask):
    if temperature.shape != (12,)+mask.shape or rain.shape != temperature.shape or not mask.any():
        raise ValueError('Need twelve ordered Gregorian monthly fields and a nonempty mask.')
    if not np.isfinite(temperature[:, mask]).all() or not np.isfinite(rain[:, mask]).all() or (rain[:, mask] < 0).any():
        raise ValueError('Invalid scored climate fields.')
    # classify directly: rain is already mm per real month, not mm/day. Do not
    # rebin it through the fantasy-calendar monthly_stats or default solstice.
    t = np.where(mask[None], temperature, 15.)
    p = np.where(mask[None], rain, 100.)
    result = koppen.classify(t, p, SUMMER, cd_threshold=0.)
    if (result[mask] < 0).any():
        raise ValueError('Unclassified scored climate.')
    return np.where(mask, result, -1)


def surface_proxy(observed, record):
    if record[2].shape != record[3].shape or record[2].shape != (12, 4)+observed.shape[1:]:
        raise ValueError('Invalid atmospheric temperature/target shapes.')
    return observed+record[2][:, 0]-record[3][:, 0]


def code_counts(classes, mask):
    return {code: int((classes[mask] == i).sum()) for i, code in enumerate(koppen.CODES) if (classes[mask] == i).any()}


def comparison(target, simulated, mask):
    names = np.array(koppen.CODES)
    a, b = names[target[mask]], names[simulated[mask]]
    med = np.isin(a, ['Csa', 'Csb', 'Csc'])
    confusion = {}
    for code in sorted(set(a)):
        confusion[str(code)] = dict(Counter(map(str, b[a == code])))
    return {'scored_cells': int(mask.sum()), 'exact_class_agreement': float((a == b).mean()),
        'main_group_agreement': float(np.mean([x[0] == y[0] for x, y in zip(a, b)])),
        'arid_share': float(np.mean([x.startswith('B') for x in b])),
        'desert_share': float(np.mean([x.startswith('BW') for x in b])),
        'target_mediterranean_cells': int(med.sum()),
        'target_mediterranean_to_arid': float(np.mean([x.startswith('B') for x in b[med]])) if med.any() else None,
        'target_mediterranean_retained': float(np.isin(b[med], ['Csa', 'Csb', 'Csc']).mean()) if med.any() else None,
        'class_counts': code_counts(simulated, mask), 'confusion_cells': confusion,
        'weighting': 'Equal scored 60 km model cells; not independent samples or an exact spherical land-area estimate.'}


def collect(include_pressure=False):
    sm, ss, inputs, _, _, spatial_records, _ = spatial.load_verified(ROOT/'output/v10_spatial_wind')
    om, os, _, _, _, uniform_records, _ = storms.load_verified(ROOT/'output/v10_storm_delivery')
    pm = ps = None
    if include_pressure:
        pm, ps, _, _, _, records, _ = pressure.load_verified(ROOT/'output/v10_pressure_thermo')
        uniform_records = {r+'_rare_storms': records[r+'_uniform'] for r in inputs}
        spatial_records = {r+'_humidity_10': records[r+'_spatial'] for r in inputs}
    arrays = {};metrics = {};fields = {}
    for region, (case, profile, g, air, wind) in inputs.items():
        mask = case.score_mask
        observed_t = case.domain.temperature_c
        target = classify_months(observed_t, case.observed_rain_mm, mask)
        # The season convention is checked against the actual reference, rather
        # than assuming it from the calendar used by the fantasy planet.
        if not (observed_t[SUMMER][:, mask].mean(0) > observed_t[~SUMMER][:, mask].mean(0)).all():
            raise ValueError('April–September is not the warmer half-year at every scored cell.')
        maps = {'target': target};proxies = {'target': target};rows = {}
        for mode, record in (('uniform', uniform_records[region+'_rare_storms']),
                             ('spatial', spatial_records[region+'_humidity_10'])):
            maps[mode] = classify_months(observed_t, record[1], mask)
            proxies[mode] = classify_months(surface_proxy(observed_t, record), record[1], mask)
            rows[mode] = {'common_surface_temperature': comparison(target, maps[mode], mask),
                'surface_anomaly_proxy': comparison(target, proxies[mode], mask),
                'proxy_changes_class_fraction': float((maps[mode][mask] != proxies[mode][mask]).mean()),
                'mean_annual_rain_mm': float(record[1].sum(0)[mask].mean())}
        metrics[region] = {'reference': comparison(target, target, mask), 'models': rows,
            'mean_reference_annual_rain_mm': float(case.observed_rain_mm.sum(0)[mask].mean())}
        fields[region] = (case, maps, proxies)
        arrays[region+'_mask'] = mask
        arrays[region+'_longitude'] = case.longitude
        arrays[region+'_latitude'] = case.domain.latitude
        for mode in maps:
            arrays[region+'_'+mode] = maps[mode]
            arrays[region+'_'+mode+'_temperature_proxy'] = proxies[mode]
    source = {'spatial_source_sha256': sm['code_sha256'], 'storm_source_sha256': om['code_sha256'],
        'spatial_manifest_sha256': sha256(ROOT/'output/v10_spatial_wind/manifest.json'),
        'spatial_state_sha256': sha256(ROOT/'output/v10_spatial_wind/state.json'),
        'storm_manifest_sha256': sha256(ROOT/'output/v10_storm_delivery/manifest.json'),
        'storm_state_sha256': sha256(ROOT/'output/v10_storm_delivery/state.json'),
        'spatial_final_evidence': {r: (ps['cases'][r+'_spatial'] if include_pressure else ss['cases'][r+'_humidity_10'])['evidence_sha256'] for r in inputs},
        'uniform_final_evidence': {r: (ps['cases'][r+'_uniform'] if include_pressure else os['cases'][r+'_rare_storms'])['evidence_sha256'] for r in inputs},
        'classifier_sha256': sha256(Path(koppen.__file__)), 'plotter_sha256': sha256(Path(__file__)),
        'reference': 'WorldClim 2.1 1970–2000 monthly surface temperature/rain, sampled at the exact model grid; not a separately published Köppen raster.',
        'main_temperature_policy': 'Observed surface temperature held identical for reference and model rain classifications; rainfall-only diagnostic.',
        'proxy_temperature_policy': 'Observed surface T + model lowest-layer T minus its prescribed local target. Sensitivity proxy only; no predicted 2 m T exists.',
        'rules': 'Unmodified project classifier; C/D coldest-month boundary 0°C; April–September summer; direct monthly mm totals; shared scored mask excluding rim and imputed T.',
        'model_selection': 'Both completed humidity-1.0, rate-one, seed-41 controls; not selected as calibrated winners.',
        'model_weather_period': 'Final settled year of a repeated synthetic weather catalogue; not a multi-decadal weather ensemble. Spin-up years are not independent climate samples.',
        'pressure_law_experiment_included': include_pressure, 'new_climate_integrations': 0, 'atlas_updated': False}
    if include_pressure:
        source.update(pressure_source_sha256=pm['code_sha256'],
            pressure_manifest_sha256=sha256(ROOT/'output/v10_pressure_thermo/manifest.json'),
            pressure_state_sha256=sha256(ROOT/'output/v10_pressure_thermo/state.json'))
    return {'sources': source, 'regions': metrics}, fields, arrays


def draw(data, fields, out, proxy=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    import matplotlib.patheffects as effects
    from matplotlib.ticker import FuncFormatter
    fig, axes = plt.subplots(2, 3, figsize=(15.4, 11.8))
    fig.subplots_adjust(left=.055, right=.99, top=.875, bottom=.22, wspace=.16, hspace=.28)
    fig.suptitle('Earth pilots vs target · Köppen climate zones', x=.52, y=.975, fontsize=21, fontweight='bold', color='#203037')
    subtitle = ('Temperature sensitivity: observed surface T plus lowest-layer model anomaly; proxy, not predicted 2 m T.' if proxy else
        'Observed surface temperature held fixed · differences show simulated rainfall · 60 km cells')
    fig.text(.52, .94, subtitle, ha='center', fontsize=11, color='#40565f')
    stage = ('Completed pressure-based heat transport · humidity 1.0 · same weather seed 41' if
        data['sources'].get('pressure_law_experiment_included') else
        'Completed controls at humidity 1.0 · pressure-law experiment not included in this comparison')
    fig.text(.52, .917, stage, ha='center', fontsize=10, color='#586a70')
    present = set()
    for row, (region, (case, maps, proxies)) in enumerate(fields.items()):
        shown = proxies if proxy else maps
        mask = case.score_mask;land = case.domain.land
        lon = case.longitude[0];lat = case.domain.latitude[:, 0]
        dx = float(np.diff(lon).mean());dy = float(abs(np.diff(lat).mean()))
        extent = (lon[0]-dx/2, lon[-1]+dx/2, lat[-1]-dy/2, lat[0]+dy/2)
        scored_lon, scored_lat = case.longitude[mask], case.domain.latitude[mask]
        xlim = (scored_lon.min()-1.7*dx, scored_lon.max()+1.7*dx)
        ylim = (scored_lat.min()-1.1*dy, scored_lat.max()+1.1*dy)
        for column, mode in enumerate(('target', 'uniform', 'spatial')):
            ax = axes[row, column];classes = shown[mode]
            image = np.empty(land.shape+(3,), float);image[:] = np.array([226, 239, 243])/255
            image[land] = np.array([222, 226, 226])/255
            image[mask] = np.array([koppen.COLORS[koppen.CODES[i]] for i in classes[mask]])/255
            present.update(koppen.CODES[i] for i in classes[mask])
            ax.imshow(image, extent=extent, origin='upper', interpolation='nearest')
            ax.contour(case.longitude, case.domain.latitude, land.astype(float), levels=[.5], colors=['#52676d'], linewidths=.45)
            ax.set(xlim=xlim, ylim=ylim)
            ax.set_aspect(1/np.cos(np.deg2rad(scored_lat.mean())))
            ax.set_title(LABELS[mode], fontsize=12, pad=9, fontweight='semibold')
            ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f'{abs(x):g}°'+('W' if x < 0 else 'E')))
            ax.yaxis.set_major_formatter(FuncFormatter(lambda y, pos: f'{y:g}°N'))
            ax.tick_params(labelsize=8, color='#8a999d')
            ax.grid(alpha=.13, color='#304950', lw=.5)
            for name, x, y in LANDMARKS[region]:
                if xlim[0] < x < xlim[1] and ylim[0] < y < ylim[1]:
                    ax.plot(x, y, 'o', ms=2.7, mec='white', mew=.6, color='#14232a', zorder=4)
                    label = ax.annotate(name, (x, y), xytext=(4, 4), textcoords='offset points', fontsize=7.3, color='#14232a')
                    label.set_path_effects([effects.withStroke(linewidth=2.3, foreground='white')])
            if mode == 'target':
                r = data['regions'][region]['reference'];rain = data['regions'][region]['mean_reference_annual_rain_mm']
                caption = f"{rain:.0f} mm/year · {r['desert_share']:.0%} desert"
            else:
                key = 'surface_anomaly_proxy' if proxy else 'common_surface_temperature'
                model_row = data['regions'][region]['models'][mode];r = model_row[key]
                caption = f"{model_row['mean_annual_rain_mm']:.0f} mm/year · {r['desert_share']:.0%} desert · {r['exact_class_agreement']:.0%} match"
            ax.set_xlabel(caption, fontsize=9.2, labelpad=8, color='#304950')
        axes[row, 0].set_ylabel(REGION_NAMES[region], fontsize=11, fontweight='semibold', labelpad=14)
    handles = [Patch(facecolor=np.array(koppen.COLORS[c])/255, edgecolor='#666', linewidth=.4,
        label=c+' · '+koppen.DESCRIPTIONS[c]) for c in koppen.CODES if c in present]
    handles.append(Patch(facecolor=np.array([222, 226, 226])/255, label='Gray · outside shared evaluation mask'))
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.52, .047), ncol=4, frameon=False, fontsize=8.4,
        handlelength=1.5, columnspacing=1.5)
    fig.text(.52, .022, 'Target: WorldClim 1970–2000 classified on the same grid. Neighboring US / Mediterranean / North African land is included.',
        ha='center', fontsize=9, color='#586a70')
    stem = 'koppen_temperature_sensitivity' if proxy else 'koppen_comparison'
    fig.savefig(out/(stem+'.png'), dpi=185, facecolor='#fbfcfc')
    fig.savefig(out/(stem+'.svg'), facecolor='#fbfcfc')
    plt.close(fig)


def markdown(data):
    included = data['sources'].get('pressure_law_experiment_included', False)
    stage = ('The completed pressure-law experiment is included.' if included else
        'The newer pressure-law experiment is not included.')
    lines = ['# Earth Köppen comparison from completed regional pilots', '',
        '![Earth Köppen maps](koppen_comparison.png)', '',
        'Main maps hold WorldClim surface temperature identical on both sides and classify '
        'observed versus simulated monthly rain. They isolate rainfall errors; the Earth '
        'pilots do not predict independent near-surface temperature. Uniform and spatial '
        'controls both use humidity 1.0, rate-one storms and seed 41. '+stage+' Each model map classifies the final '
        'settled year of one repeated synthetic weather catalogue, not a multi-decadal '
        'weather ensemble; warm-up cycles are not independent climate samples.', '',
        '| Region / completed model | Same Köppen code | Desert land | Reference Mediterranean becoming arid |',
        '|---|---:|---:|---:|']
    for region, entry in data['regions'].items():
        for mode, row in entry['models'].items():
            r = row['common_surface_temperature']
            lines.append(f"| {REGION_NAMES[region]} / {mode} | {r['exact_class_agreement']:.1%} | {r['desert_share']:.1%} | {r['target_mediterranean_to_arid']:.1%} |")
    lines += ['', 'Arid includes desert and steppe (B climates); desert is BW only. Mediterranean '
        'means Csa/Csb/Csc. Statistics count the shared scored 60 km cells, including '
        'neighboring land within each regional test domain; they are not country-only '
        'area statistics or independent observation replicates.', '',
        'The target is derived from the exact observed monthly fields used in these '
        'tests, not copied from a different published Köppen atlas. Both sides use the '
        'unmodified project classifier, 0°C C/D boundary, April–September summer and '
        'Gregorian monthly rainfall totals directly. No fantasy-calendar rebinning, '
        'solstice or mm/day conversion is applied. Reference temperatures confirm that '
        'April–September is the warmer half-year at every evaluated cell. Rim and '
        'imputed-temperature cells are excluded and shown gray; coastlines reflect '
        'the coarse model grid. Minor threshold conventions belong to the existing '
        'classifier and are not adjusted for this comparison.', '',
        'The classification follows the project’s Peel-style rules; the C/D boundary '
        'and seasonal criteria are described in '
        '[Peel et al. (2007), Table 1](https://hess.copernicus.org/articles/11/1633/2007/hess-11-1633-2007.pdf). '
        'The same data/grid/classifier comparison avoids confounding a model error '
        'with a different reference-map period, resolution or classification convention.', '',
        '## Temperature sensitivity, explicitly a proxy', '',
        '![Lowest-layer temperature-anomaly sensitivity](koppen_temperature_sensitivity.png)', '',
        'This companion adds the simulated lowest atmospheric layer’s monthly departure '
        'from its prescribed target to observed surface temperature. It is an inferred '
        'surface-anomaly sensitivity, not a simulated 2 m temperature or an independent '
        'temperature validation. Directly classifying lowest-layer temperature would '
        'confuse free-air altitude with surface climate.', '',
        '| Region / model | Class match using proxy | Fraction changed from fixed-temperature map |',
        '|---|---:|---:|']
    for region, entry in data['regions'].items():
        for mode, row in entry['models'].items():
            lines.append(f"| {REGION_NAMES[region]} / {mode} | {row['surface_anomaly_proxy']['exact_class_agreement']:.1%} | {row['proxy_changes_class_fraction']:.1%} |")
    lines += ['', 'Both views expose serious errors, especially replacement of Mediterranean '
        'and steppe climates by desert. They are development diagnostics and do not '
        'support an atlas update. Monthly rain and continuous aridity margins remain '
        'necessary alongside these threshold-based labels.', '',
        '## Reproduce', '', '```sh', '.venv/bin/python scripts/plot_v10_koppen.py --write'+(' --include-pressure' if included else ''), '```', '',
        'Saved-field analysis only. No climate integration, calibration, input download '
        'or atlas mutation. `comparison.json` includes full class counts/confusion tables '
        'and source/evidence identities; `classes.npz` stores exact masks, grids and '
        'class arrays; `class_counts.csv` and vector SVG versions are also included. '
        'Sources of the ongoing experiment remain unchanged.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--include-pressure', action='store_true', help='Require and include all four completed pressure-law cases.')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    if args.out is None:
        args.out = ROOT/'output'/('v10_koppen_pressure' if args.include_pressure else 'v10_koppen_comparison')
    data, fields, arrays = collect(args.include_pressure)
    text = markdown(data)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'comparison.json', data)
        atomic_npz(args.out/'classes.npz', **arrays)
        with (args.out/'class_counts.csv').open('w') as file:
            writer = csv.writer(file);writer.writerow(['region', 'view', 'model', 'code', 'cells'])
            for region, (_, maps, proxies) in fields.items():
                mask = fields[region][0].score_mask
                for view, shown in (('common_surface_temperature', maps), ('surface_anomaly_proxy', proxies)):
                    for mode, classes in shown.items():
                        for code, count in code_counts(classes, mask).items():
                            writer.writerow([region, view, mode, code, count])
        draw(data, fields, args.out)
        draw(data, fields, args.out, proxy=True)
        (args.out/'comparison.md').write_text(text)
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
