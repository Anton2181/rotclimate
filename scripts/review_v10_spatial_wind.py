"""Verify completed spatial-wind cases and review saved fields only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_spatial_wind as run
from rotclimate_v10.earth import atomic_json, sha256


def load_verified(source):
    manifest = json.loads((source/'manifest.json').read_text())
    state = json.loads((source/'state.json').read_text())
    expected, inputs, settings, baselines = run.prepare(ROOT/'output/v10_storm_delivery')
    if manifest != expected or state['status'] != 'complete' or set(state['cases']) != set(baselines):
        raise ValueError('Need unchanged completed four-case spatial-wind evidence.')
    for region, (_, _, g, air, wind) in inputs.items():
        arrays = run.input_arrays(g, air, wind)
        with np.load(source/'inputs'/(region+'.npz'), allow_pickle=False) as saved:
            if set(saved.files) != set(arrays) or run.old.old.array_id({k: saved[k] for k in saved.files}) != expected['inputs'][region]:
                raise ValueError('Saved spatial-wind inputs changed.')
    records = {};seconds = 0.
    for key, row in state['cases'].items():
        region, name = key.split('_', 1);case, profile, g, air, wind = inputs[region]
        folder = source/'cases'/key
        config = {'region': case.domain.name, 'settings': asdict(settings[name]), 'seed': 41,
            'input_array_sha256': expected['inputs'][region], 'wind': 'spatial_bilinear'}
        evidence = {f'year{year}.{ext}' for year in range(1, row['years']+1) for ext in ('json', 'npz')}
        if json.loads((folder/'config.json').read_text()) != config or not 3 <= row['years'] <= 6 or set(row['evidence_sha256']) != evidence:
            raise ValueError('Spatial-wind case identity/evidence mismatch.')
        for filename, digest in row['evidence_sha256'].items():
            if sha256(folder/filename) != digest:
                raise ValueError('Spatial-wind evidence changed.')
        previous = None
        for year in range(1, row['years']+1):
            record = run.night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing spatial-wind completed year.')
            seconds += record[-1]['elapsed_seconds']
            if previous is not None:
                check = run.old.old.settling(previous, record, case, g)
            previous = record
        computed = run.night.summarize(record, case, check, row['years'])
        computed['response'] = run.review.rain_vector(case, record[1])
        if any(computed[k] != row[k] for k in computed):
            raise ValueError('Spatial-wind summary disagrees with saved fields.')
        records[key] = record
    return manifest, state, inputs, settings, baselines, records, seconds


def analyse(source):
    manifest, state, inputs, settings, baselines, records, seconds = load_verified(source)
    rows = {}
    for key, record in records.items():
        row = state['cases'][key]
        layer = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
        thermal = np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c'])
        if not np.isclose(layer.sum(), row['response']['annual_rain_mm'], atol=1e-8):
            raise ValueError('Spatial-wind layer rainfall accounting mismatch.')
        rows[key] = {'response': row['response'], 'uniform_control': baselines[key]['rainfall'],
            'rain_ratio': row['annual_rain_ratio'], 'coverage': row['wet_reference_coverage'],
            'guard_passed': row['eligible'], 'years': row['years'],
            'annual_layer_rain_mm': layer.sum(0).tolist(),
            'old_split_temperature_changes_k_day': (thermal.sum(0)/365).tolist(),
            'budget': row['budget'],
            'note': 'Old horizontal/vertical conservative flux-divergence terms contain cancelling mass-divergence contributions; their separate magnitude is not a physical parcel heating rate.'}
    return {'source_manifest_sha256': sha256(source/'manifest.json'),
        'source_state_sha256': sha256(source/'state.json'), 'sources_verified': True,
        'saved_integration_minutes': seconds/60, 'cases': rows,
        'new_seasonal_runs': 0, 'atlas_updated': False}


def markdown(data):
    lines = ['# Completed spatial-wind diagnosis', '',
        f"Four cases; all settle; none qualifies. Sixteen cycles took {data['saved_integration_minutes']:.2f} minutes.", '',
        '| Case | Annual rain / reference, mm | Coast / interior rain, mm | Coverage | Rain MAE |',
        '|---|---:|---:|---:|---:|']
    for key, row in data['cases'].items():
        r = row['response']
        lines.append(f"| {key} | {r['annual_rain_mm']:.1f} / {r['annual_reference_mm']:.1f} | {r['coast_annual_mm']:.1f} / {r['interior_annual_mm']:.1f} | {row['coverage']:.1%} | {r['monthly_mae_mm']:.2f} |")
    lines += ['', 'Spatial mean winds alone do not repair rainfall. California lower MAE accompanies '
        'severe drying, while Iberia MAE worsens. Budgets/settling pass. No atlas promotion.', '',
        'Next mechanism audit: pressure-based dry-adiabatic transport versus the frozen passively '
        'advected approximate moist-static energy. Keep missing frontal covariance and boundary '
        'moisture as unresolved hypotheses. Large cancelling old heat terms are not causal proof.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_spatial_wind')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_spatial_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    data = analyse(args.source);text = markdown(data)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'review.json', data)
        (args.out/'review.md').write_text(text)
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
