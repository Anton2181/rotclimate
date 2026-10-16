"""Verify and measure completed storm controls without climate integration."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_storm_delivery as run
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
WINTER = np.array([0, 1, 2, 9, 10, 11])  # October through March, same convention as rain_metrics.
SUMMER = np.array([3, 4, 5, 6, 7, 8])


def load_verified(source):
    manifest = json.loads((source/'manifest.json').read_text())
    state = json.loads((source/'state.json').read_text())
    expected, inputs, settings, baselines = run.prepare(ROOT/'output/v10_coordinate_check')
    keys = {region+'_'+name for region in inputs for name in settings}
    if state['status'] != 'complete' or manifest != expected or set(state['cases']) != keys:
        raise ValueError('Need unchanged completed ten-case storm experiment.')
    for region, (_, _, g, air) in inputs.items():
        arrays = run.old.geometry_arrays(g, air)
        with np.load(source/'inputs'/(region+'.npz'), allow_pickle=False) as saved:
            if set(saved.files) != set(arrays) or run.old.array_id({k: saved[k] for k in saved.files}) != expected['inputs'][region]:
                raise ValueError('Saved storm input changed.')
    records = {};seconds = 0.
    for key, row in state['cases'].items():
        region, name = key.split('_', 1)
        case, profile, g, air = inputs[region]
        folder = source/'cases'/key
        config = {'region': case.domain.name, 'settings': asdict(settings[name]), 'seed': 41,
            'input_array_sha256': expected['inputs'][region], 'projection': 'mass_weighted', 'nested_weather': True}
        if json.loads((folder/'config.json').read_text()) != config or not 3 <= row['years'] <= 6:
            raise ValueError('Storm case identity mismatch.')
        evidence = {f'year{year}.{ext}' for year in range(1, row['years']+1) for ext in ('json', 'npz')}
        if set(row['evidence_sha256']) != evidence:
            raise ValueError('Incomplete storm evidence declaration.')
        for filename, digest in row['evidence_sha256'].items():
            if sha256(folder/filename) != digest:
                raise ValueError('Completed storm evidence changed.')
        previous = None
        for year in range(1, row['years']+1):
            record = run.night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing storm checkpoint.')
            seconds += record[-1]['elapsed_seconds']
            if previous is not None:
                check = run.old.settling(previous, record, case, g)
            previous = record
        recomputed = run.night.summarize(record, case, check, row['years'])
        if any(recomputed[k] != row[k] for k in recomputed):
            raise ValueError('Storm summary disagrees with completed fields.')
        records[key] = record
    return manifest, state, inputs, settings, baselines, records, seconds


def rain_vector(case, rain):
    """Continuous paired responses; no treating cells/settling years as replicates."""
    observed = case.observed_rain_mm
    mask = case.score_mask
    if rain.shape != observed.shape or not np.isfinite(rain).all() or (rain < 0).any():
        raise ValueError('Invalid rainfall response fields.')
    annual = rain.sum(0);ref = observed.sum(0)
    zero_mae = float(observed[:, mask].mean())
    if zero_mae <= 0:
        raise ValueError('Need positive reference rain to measure skill.')
    mae = float(abs(rain-observed)[:, mask].mean())
    out = {'monthly_mae_mm': mae, 'zero_rain_mae_mm': zero_mae,
        'skill_vs_zero_rain': 1-mae/zero_mae,
        'annual_rain_mm': float(annual[mask].mean()),
        'annual_reference_mm': float(ref[mask].mean()),
        'median_annual_rain_mm': float(np.median(annual[mask])),
        'winter_rain_mm': float(rain[WINTER][:, mask].sum(0).mean()),
        'summer_rain_mm': float(rain[SUMMER][:, mask].sum(0).mean()),
        'winter_reference_mm': float(observed[WINTER][:, mask].sum(0).mean()),
        'summer_reference_mm': float(observed[SUMMER][:, mask].sum(0).mean()),
        'cells_below_tenth_reference_fraction': float((annual[mask] < .1*ref[mask]).mean())}
    count = max(1, int(np.ceil(mask.sum()*.05)))
    out['wettest_five_percent_rain_share'] = float(np.sort(annual[mask])[-count:].sum()/max(annual[mask].sum(), 1e-12))
    out['reference_wettest_five_percent_rain_share'] = float(np.sort(ref[mask])[-count:].sum()/ref[mask].sum())
    for name, selected in (('coast', mask & (case.coast_distance_km < 150)),
                           ('interior', mask & (case.coast_distance_km > 300))):
        if not selected.any():
            raise ValueError('Need both coast and interior for response diagnosis.')
        for season, months in (('annual', np.arange(12)), ('winter', WINTER), ('summer', SUMMER)):
            out[name+'_'+season+'_mm'] = float(rain[months][:, selected].sum(0).mean())
            out[name+'_'+season+'_reference_mm'] = float(observed[months][:, selected].sum(0).mean())
    return out


RESPONSE_KEYS = ('coast_winter_mm', 'interior_winter_mm', 'coast_summer_mm',
    'interior_summer_mm', 'annual_rain_mm', 'monthly_mae_mm')
CONTRASTS = (('humidity_0.8_to_1', 'anchor', 'rare_storms', .2),
    ('storms_0_to_1', 'mean_only', 'rare_storms', 1.),
    ('storms_1_to_4', 'rare_storms', 'winter_storms', 3.),
    ('storms_4_to_8', 'winter_storms', 'frequent_storms', 4.))


def analyse(source):
    manifest, state, inputs, settings, baselines, records, seconds = load_verified(source)
    rows = {};contrasts = {};maps = {}
    for key, record in records.items():
        region = key.split('_', 1)[0];case = inputs[region][0]
        row = rain_vector(case, record[1])
        layer = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
        if not np.isclose(layer.sum(), row['annual_rain_mm'], atol=1e-8):
            raise ValueError('Layer rainfall ledger disagrees with scored fields.')
        row.update(eligible=state['cases'][key]['eligible'],
            coverage=state['cases'][key]['wet_reference_coverage'],
            annual_rain_by_layer_mm=layer.sum(0).tolist(),
            projection_adjustment_max_m_s=record[-1]['diagnostics']['max_projection_adjustment_m_s'])
        rows[key] = row
    for region in inputs:
        contrasts[region] = {}
        for label, a, b, size in CONTRASTS:
            start, end = region+'_'+a, region+'_'+b
            delta = {k: rows[end][k]-rows[start][k] for k in RESPONSE_KEYS}
            contrasts[region][label] = {'start': start, 'end': end, 'parameter_step': size,
                'delta': delta, 'per_unit_secant': {k: v/size for k, v in delta.items()}}
            maps[region+'_'+label+'_annual_delta_mm'] = (records[end][1]-records[start][1]).sum(0)
    return {'source_manifest_sha256': sha256(source/'manifest.json'),
        'source_state_sha256': sha256(source/'state.json'), 'sources_verified': True,
        'saved_integration_seconds': seconds, 'cycles': sum(r['years'] for r in state['cases'].values()),
        'cases': rows, 'paired_responses': contrasts, 'response_outputs': list(RESPONSE_KEYS),
        'note': 'Finite matched secants at one weather seed. No inferred global feasibility, independence of pixels/settling years, emulator or history matching. Fantasy protected-zone constraints are not Earth metrics.',
        'new_seasonal_integrations': 0, 'atlas_updated': False}, maps


def markdown(data):
    lines = ['# Storm delivery: measured responses', '',
        f"Ten cases / {data['cycles']} cycles; {data['saved_integration_seconds']/60:.2f} saved integration minutes. All settle.", '',
        '| Case | Monthly MAE | Skill against zero rain | Annual rain | Coast / interior annual rain | Minimum coverage | Broad screen |',
        '|---|---:|---:|---:|---:|---:|---|']
    for key, row in data['cases'].items():
        lines.append(f"| {key} | {row['monthly_mae_mm']:.2f} | {row['skill_vs_zero_rain']:.1%} | {row['annual_rain_mm']:.1f} | {row['coast_annual_mm']:.1f} / {row['interior_annual_mm']:.1f} | {row['coverage']:.1%} | {row['eligible']} |")
    lines += ['', 'Skill = 1 - monthly cellwise MAE / zero-rain MAE. Positive is better than zero rain. '
        'The broad screen did not require this skill and is preserved unchanged.', '',
        '| Region / paired change | Coastal winter delta | Interior winter delta | Coastal summer delta | Interior summer delta | MAE delta |',
        '|---|---:|---:|---:|---:|---:|']
    for region, entries in data['paired_responses'].items():
        for name, entry in entries.items():
            d = entry['delta']
            lines.append(f"| {region} / {name} | {d['coast_winter_mm']:+.2f} | {d['interior_winter_mm']:+.2f} | {d['coast_summer_mm']:+.2f} | {d['interior_summer_mm']:+.2f} | {d['monthly_mae_mm']:+.2f} |")
    lines += ['', data['note'], '', 'No new seasonal integration, calibration or atlas publication.']
    return '\n'.join(lines)+'\n'


def plot_responses(data, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), constrained_layout=True)
    for region, ax in zip(('california', 'iberia'), axes):
        def point(name):
            row = data['cases'][region+'_'+name]
            return (row['interior_annual_mm']/row['interior_annual_reference_mm'],
                row['coast_annual_mm']/row['coast_annual_reference_mm'])
        storm_names = ('mean_only', 'rare_storms', 'winter_storms', 'frequent_storms')
        xy = np.array([point(name) for name in storm_names])
        ax.plot(xy[:, 0], xy[:, 1], 'o-', color='#267ba2', label='Humidity 1.0; storms 0, 1, 4, 8')
        for name, rate in zip(storm_names, (0, 1, 4, 8)):
            offset = (-9, -18) if rate == 0 else (8, 1)
            ax.annotate(str(rate), point(name), xytext=offset, textcoords='offset points', fontsize=9)
        start, end = point('anchor'), point('rare_storms')
        ax.scatter(*start, color='#a94f43', marker='s', label='Humidity 0.8; one storm')
        ax.annotate('', xy=end, xytext=start, arrowprops={'arrowstyle': '->', 'color': '#a94f43', 'lw': 1.5})
        ax.scatter([1], [1], marker='*', s=180, color='#1d292e', label='Reference')
        ax.axhline(1, color='#777', lw=.7, ls='--');ax.axvline(1, color='#777', lw=.7, ls='--')
        ax.set(title=region.title(), xlabel='Interior annual rain / reference', ylabel='Coastal annual rain / reference', xlim=(0, 1.8), ylim=(0, 1.15))
        ax.grid(alpha=.2)
    axes[0].legend(loc='lower right', fontsize=8)
    fig.suptitle('Measured rain responses: a wetter region can still have the wrong distribution', fontsize=12)
    fig.savefig(out/'response_plane.png', dpi=170)
    plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'output/v10_storm_delivery')
    p.add_argument('--out', type=Path, default=ROOT/'output/v10_storm_review')
    p.add_argument('--write', action='store_true')
    args = p.parse_args(argv)
    data, maps = analyse(args.source)
    text = markdown(data)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'review.json', data)
        atomic_npz(args.out/'response_maps.npz', **maps)
        (args.out/'review.md').write_text(text)
        plot_responses(data, args.out)
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
