"""Verify completed dry-theta controls and diagnose saved fields; no integration."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_pressure_thermo as run
from rotclimate_v10.earth import atomic_json, sha256
from rotclimate_v10.core import DAY


def load_verified(source):
    manifest = json.loads((source/'manifest.json').read_text())
    state = json.loads((source/'state.json').read_text())
    expected, inputs, settings, baselines = run.prepare(ROOT/'output/v10_spatial_wind')
    if manifest != expected or state['status'] != 'complete' or set(state['cases']) != set(baselines):
        raise ValueError('Need unchanged completed four-case pressure-thermodynamic evidence.')
    for region, (_, _, g, air, wind) in inputs.items():
        arrays = run.input_arrays(g, air, wind)
        with np.load(source/'inputs'/(region+'.npz'), allow_pickle=False) as saved:
            if set(saved.files) != set(arrays) or run.geometry_rules.array_id({k: saved[k] for k in saved.files}) != expected['inputs'][region]:
                raise ValueError('Saved pressure-thermodynamic inputs changed.')
    records = {};seconds = 0.
    for key, row in state['cases'].items():
        region, mode = key.split('_', 1);case, profile, g, air, wind = inputs[region]
        folder = source/'cases'/key
        config = {'region': case.domain.name, 'settings': asdict(settings[mode]), 'seed': 41,
            'input_array_sha256': expected['inputs'][region], 'wind': mode, 'thermal_transport': 'dry_theta'}
        evidence = {f'year{year}.{ext}' for year in range(1, row['years']+1) for ext in ('json', 'npz')}
        if json.loads((folder/'config.json').read_text()) != config or not 3 <= row['years'] <= 6 or set(row['evidence_sha256']) != evidence:
            raise ValueError('Pressure-thermodynamic case identity/evidence mismatch.')
        for filename, digest in row['evidence_sha256'].items():
            if sha256(folder/filename) != digest:
                raise ValueError('Pressure-thermodynamic evidence changed.')
        previous = None
        for year in range(1, row['years']+1):
            record = run.night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed pressure-thermodynamic year.')
            seconds += record[-1]['elapsed_seconds']
            if previous is not None:
                check = run.geometry_rules.settling(previous, record, case, g)
            previous = record
        computed = run.night.summarize(record, case, check, row['years'])
        computed['response'] = run.rain_vector(case, record[1])
        if any(computed[k] != row[k] for k in computed):
            raise ValueError('Pressure-thermodynamic summary disagrees with fields.')
        if record[-1]['diagnostics']['processes'] != list(run.model.PROCESSES):
            raise ValueError('Incorrect thermodynamic process ledger.')
        records[key] = record
    return manifest, state, inputs, settings, baselines, records, seconds


def analyse(source):
    manifest, state, inputs, settings, baselines, records, seconds = load_verified(source)
    rows = {}
    for key, record in records.items():
        row = state['cases'][key];baseline = baselines[key]
        layer = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
        thermal = np.array(record[-1]['diagnostics']['temperature_changes_scored_land_c'])
        if not np.isclose(layer.sum(), row['response']['annual_rain_mm'], atol=1e-8):
            raise ValueError('Rain-by-layer mismatch.')
        b = row['budget']
        rows[key] = {'response': row['response'], 'baseline_response': baseline['rainfall'],
            'score_delta': row['score']-baseline['score'],
            'rain_ratio': row['annual_rain_ratio'], 'coverage': row['wet_reference_coverage'],
            'eligible': row['eligible'], 'annual_layer_rain_mm': layer.sum(0).tolist(),
            'signed_temperature_changes_k_day': (thermal.sum(0)/365).tolist(),
            'budget': b, 'mean_energy_flux_w_m2': {name: b[name]/(365*DAY) for name in
                ('surface_latent_input_j_m2', 'temperature_relaxation_j_m2',
                 'energy_boundary_export_j_m2', 'prescribed_flow_work_j_m2')}}
    return {'source_manifest_sha256': sha256(source/'manifest.json'),
        'source_state_sha256': sha256(source/'state.json'), 'sources_verified': True,
        'saved_integration_minutes': seconds/60, 'cycles': sum(r['years'] for r in state['cases'].values()),
        'cases': rows, 'new_seasonal_runs': 0, 'atlas_updated': False}


def markdown(data):
    lines = ['# Completed pressure-based heat-transport comparison', '',
        f"Four cases / {data['cycles']} cycles; {data['saved_integration_minutes']:.2f} saved minutes. All settle.", '',
        '| Case | Rain MAE | MAE change | Rain / reference | Minimum coverage | Prescribed work, W/m² | Broad screen |',
        '|---|---:|---:|---:|---:|---:|---|']
    for key, row in data['cases'].items():
        r = row['response']
        lines.append(f"| {key} | {r['monthly_mae_mm']:.2f} | {row['score_delta']:+.2f} | {row['rain_ratio']:.2f} | {row['coverage']:.1%} | {row['mean_energy_flux_w_m2']['prescribed_flow_work_j_m2']:.2f} | {row['eligible']} |")
    lines += ['', 'The dry-law correction passes its manufactured limits but does not resolve '
        'regional rain placement or the spatial-wind drought. California uniform-flow '
        'MAE improves modestly but remains worse than zero rain; other cases worsen. '
        'Diagnosed work is exchange with an unsolved prescribed circulation, not an '
        'independently verified total-energy budget. No atlas promotion.', '',
        'Next priority: measure missing transient moisture/thermal forcing rather than '
        'launch another frequency sweep. Boundary imports, cloud/transport physics and '
        'vertical quadrature remain unresolved. No further seasonal run started here.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_pressure_thermo')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_pressure_review')
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
