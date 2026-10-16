"""Saved-coordinate result review. No seasonal simulation or calibration."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rotclimate_v10.earth import atomic_json, sha256
from scripts import check_v10_coordinates as run, overnight_v10 as night


def load_verified(source):
    manifest = json.loads((source/'manifest.json').read_text())
    state = json.loads((source/'state.json').read_text())
    if state['status'] != 'complete' or manifest['code_sha256'] != run.source_id():
        raise ValueError('Need unchanged completed coordinate experiment.')
    expected, inputs, settings = run.prepare(ROOT/'output/v10_upper_air_check')
    if expected != manifest or set(state['cases']) != set(inputs):
        raise ValueError('Coordinate experiment inputs/configuration changed.')
    records = {}
    seconds = 0.
    for key, row in state['cases'].items():
        case, profile, g, air = inputs[key]
        folder = source/'cases'/key
        config = json.loads((folder/'config.json').read_text())
        if config['region'] != case.domain.name or config['mode'] != g.mode or config['settings'] != manifest['settings'] or config['seed'] != 41 or config['input_array_sha256'] != expected['cases'][key]['array_sha256']:
            raise ValueError('Coordinate case identity mismatch.')
        with np.load(source/'inputs'/(key+'.npz'), allow_pickle=False) as saved:
            if run.array_id({k: saved[k] for k in saved.files}) != expected['cases'][key]['array_sha256']:
                raise ValueError('Saved coordinate input changed.')
        for name, digest in row['evidence_sha256'].items():
            if Path(name).name != name or sha256(folder/name) != digest:
                raise ValueError('Coordinate evidence changed.')
        for year in range(1, row['years']+1):
            record = night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed coordinate year.')
            seconds += record[-1]['elapsed_seconds']
        records[key] = record
    return manifest, state, inputs, settings, records, seconds


def analyse(source):
    manifest, state, inputs, settings, records, seconds = load_verified(source)
    rows = {}
    for key, row in state['cases'].items():
        case, profile, g, air = inputs[key]
        record = records[key]
        rain = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
        thermal = np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c'])
        annual = record[1].sum(0)
        if not np.isclose(rain.sum(), annual[case.score_mask].mean(), atol=1e-8):
            raise ValueError('Layer rain ledger disagrees with saved fields.')
        rows[key] = {'monthly_mae_mm': row['score'], 'annual_rain_ratio': row['annual_rain_ratio'],
            'annual_rain_by_layer_mm': rain.sum(0).tolist(),
            'signed_temperature_changes_k_day': (thermal.sum(0)/365).tolist(),
            'coverage': row['wet_reference_coverage'], 'guards': row['guards'],
            'settled': row['settling']['passed'], 'years': row['years'],
            'median_annual_rain_mm': float(np.median(annual[case.score_mask])),
            'coast_interior': row['rainfall']['coast_interior'],
            'budget': record[-1]['budget']}
    return {'source_manifest_sha256': sha256(source/'manifest.json'),
        'source_state_sha256': sha256(source/'state.json'), 'sources_verified': True,
        'saved_integration_seconds': seconds, 'cases': rows,
        'new_seasonal_integrations': 0, 'atlas_updated': False}


def markdown(data):
    lines = ['# Completed coordinate-path diagnosis', '',
        f"Four cases / {sum(row['years'] for row in data['cases'].values())} cycles completed in {data['saved_integration_seconds']/60:.2f} minutes. All settle; none qualifies.", '',
        '| Region / path | Rain MAE | Annual rain / reference | Wet-reference coverage | Highest-layer rain, mm/year |',
        '|---|---:|---:|---:|---:|']
    for key, row in data['cases'].items():
        lines.append(f"| {key} | {row['monthly_mae_mm']:.2f} | {row['annual_rain_ratio']:.2f} | {row['coverage']:.1%} | {row['annual_rain_by_layer_mm'][-1]:.2f} |")
    lines += ['', 'The hybrid path removes high-level mountain rain but leaves most land too dry. '
        'Its lower MAE partly reflects suppression of excessive rain, not adequate wetting. '
        'Its unchanged face fluxes also imply excessive speeds in thin layers.', '',
        'Next: convert prescribed velocities to flux using actual face mass, then apply a '
        'weighted column-continuity projection. Compare the unchanged rare-storm/humidity anchor '
        'first; separately test reference humidity and nested zero/one/four/eight-storm forcing. '
        'Keep geometry and thermodynamic closure fixed. No unconstrained search or atlas update.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'output/v10_coordinate_check')
    p.add_argument('--out', type=Path, default=ROOT/'output/v10_coordinate_diagnosis')
    p.add_argument('--write', action='store_true')
    args = p.parse_args(argv)
    result = analyse(args.source)
    report = markdown(result)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'diagnosis.json', result)
        (args.out/'diagnosis.md').write_text(report)
    print(report)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
