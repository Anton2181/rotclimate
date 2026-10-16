"""Verify completed upper-air cases and audit terrain coupling without simulation."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_column as base, v10_coordinates as coordinates
from rotclimate_v10.earth import atomic_json, sha256
from scripts import check_v10_upper_air as run, overnight_v10 as night


def load_verified(source):
    source = Path(source)
    manifest = json.loads((source/'manifest.json').read_text())
    state = json.loads((source/'state.json').read_text())
    if manifest['code_sha256'] != run.source_id() or state['status'] != 'complete' or set(state['cases']) != {'california', 'iberia'}:
        raise ValueError('Need unchanged completed upper-air cases.')
    protocol, cases, profiles, references, baselines = run.prepare(ROOT/'output/v10_overnight_20261015')
    if manifest != protocol:
        raise ValueError('Upper-air input/baseline provenance changed.')
    records = {}
    elapsed = 0.
    for region, row in state['cases'].items():
        folder = source/'cases'/f'upper_air_{region}_g60_s41'
        config = json.loads((folder/'config.json').read_text())
        if config['settings'] != protocol['settings'] or config['seed'] != 41 or config['region'] != region or config['spacing_m'] != cases[region].domain.dx:
            raise ValueError('Upper-air case identity mismatch.')
        for name, digest in row['evidence_sha256'].items():
            if Path(name).name != name or sha256(folder/name) != digest:
                raise ValueError('Upper-air evidence changed.')
        for year in range(1, row['years']+1):
            record = night.read_checkpoint(folder, year, cases[region].domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed upper-air year.')
            elapsed += record[-1]['elapsed_seconds']
        records[region] = record
    return manifest, state, cases, profiles, references, baselines, records, elapsed


def ridge_probe(mode, hill=True):
    """One dry tracer transport step, no evaporation/relaxation/rain/weather."""
    ny, nx = 3, 81
    dx = 10000.
    x = (np.arange(nx)-nx//2)*dx
    h = np.broadcast_to(2000*np.exp(-.5*(x/100000)**2) if hill else np.zeros(nx), (ny, nx)).copy()
    ps = coordinates.P0*np.exp(-h/8400)
    mass, pressure, interfaces = coordinates.pressure_grid(ps, mode)
    z = -8400*np.log(pressure/coordinates.P0)
    f = base.balanced(np.broadcast_to((base.FRACTIONS*coordinates.P0/base.G*10)[:, None, None], (4, ny, nx+1)).copy(),
        np.zeros((4, ny+1, nx)), dx, dx)
    from rotclimate_v10.core import Domain
    domain = Domain('california', np.ones((ny, nx), bool), h, np.full((ny, nx), 37.),
        np.full((12, ny, nx), 15.), dx, dx)
    energy = mass*(base.CP*(15+273.15)+base.G*z)
    dt = min(60., base.stable_step(f, mass, domain))
    moved, exported = base.transport(energy, mass, f, energy/mass, dt, domain)
    delta = base.temperature(moved, mass, np.zeros_like(mass), z)-15
    interior = delta[:, 1, 2:-2]
    return {'mode': mode, 'hill': hill, 'dt_s': dt,
        'layer_cooling_max_c': np.maximum(-interior.min(1), 0).tolist(),
        'layer_absolute_change_max_c': abs(interior).max(1).tolist(),
        'upper_interface_vertical_flux_max': float(abs(f.vertical[-1]).max()),
        'energy_budget_error_j_m2': float((moved-energy).sum(0).mean()+exported),
        'warning': 'Different kinematic path assumptions, not equivalent coordinate representations. A one-step dry test, not a sustained cooling rate or rainfall prediction.'}


def analyse(source):
    manifest, state, cases, profiles, references, baselines, records, elapsed = load_verified(source)
    rows = {}
    for region, row in state['cases'].items():
        record = records[region]
        diag = record[-1]['diagnostics']
        rain = np.array(diag['layer_rain_scored_land_mm'])
        thermal = np.array(diag['temperature_changes_scored_land_c'])
        annual = record[1].sum(0)
        mask = cases[region].score_mask
        if rain.shape != (12, 4) or thermal.shape != (12, 5, 4) or not np.isfinite(rain).all() or not np.isfinite(thermal).all():
            raise ValueError('Invalid saved process diagnostics.')
        if not np.isclose(rain.sum(), annual[mask].mean(), atol=1e-8):
            raise ValueError('Layer rain does not sum to scored rainfall.')
        top5 = mask & (annual >= np.percentile(annual[mask], 95))
        rows[region] = {'baseline_mae_mm': baselines[region]['score'], 'new_mae_mm': row['score'],
            'annual_rain_mm': row['rainfall']['predicted_mean_annual_mm'],
            'observed_annual_rain_mm': row['rainfall']['observed_mean_annual_mm'],
            'annual_rain_by_layer_mm': rain.sum(0).tolist(),
            'rain_fraction_by_layer': (rain.sum(0)/rain.sum()).tolist(),
            'thermal_processes': diag['processes'],
            'signed_temperature_changes_k_day': (thermal.sum(0)/365).tolist(),
            'top5_land_rain_fraction': float(annual[top5].sum()/annual[mask].sum()),
            'median_annual_rain_mm': float(np.median(annual[mask])),
            'coverage': row['wet_reference_coverage'], 'years': row['years'],
            'settled': row['settling']['passed'], 'guards': row['guards'],
            'max_temperature_ledger_error_c': diag['max_step_temperature_ledger_error_c'],
            'budget': record[-1]['budget']}
    return {'source_manifest_sha256': sha256(Path(source)/'manifest.json'),
        'source_state_sha256': sha256(Path(source)/'state.json'),
        'sources_verified': True, 'saved_integration_seconds': elapsed, 'regions': rows,
        'manufactured_ridge': [ridge_probe(mode, hill) for mode in ('sigma', 'hybrid') for hill in (False, True)],
        'new_seasonal_integrations': 0, 'atlas_updated': False}


def markdown(data):
    lines = ['# Completed upper-air target diagnosis', '',
        f"Eight saved cycles took {data['saved_integration_seconds']/60:.2f} minutes. Both cases settle; neither qualifies. No new seasonal integration.", '',
        '| Region | Rain MAE before → after | Highest-layer rain share | Rain falling on wettest 5% of scored land |',
        '|---|---:|---:|---:|']
    for region, row in data['regions'].items():
        lines.append(f"| {region} | {row['baseline_mae_mm']:.2f} → {row['new_mae_mm']:.2f} | {row['rain_fraction_by_layer'][-1]:.1%} | {row['top5_land_rain_fraction']:.1%} |")
    lines += ['', 'Upper-air target correction did not repair rain placement. In the highest layer, '
        'scored-land mean horizontal transport cools while mean vertical exchange warms. '
        'These signed averages do not exclude strong local vertical cooling or prove a single cause.', '',
        'All current sigma surfaces rise with ground elevation. Constant layer face flux with little '
        'coordinate-vertical exchange therefore carries high air along those slopes. A dry one-step '
        'ridge test below isolates that prescribed path, with all condensation and thermal forcing absent.', '',
        '| Dry ridge path hypothesis | Highest-layer cooling in one 60-second step |',
        '|---|---:|']
    for probe in data['manufactured_ridge']:
        if probe['hill']:
            lines.append(f"| {probe['mode']} | {probe['layer_cooling_max_c'][-1]:.6f}°C |")
    lines += ['', 'Terrain-following coordinates themselves are not invalid. This prototype prescribes '
        'the flow on them; it does not solve or transform a complete physical vertical velocity. '
        'The hybrid test keeps the upper pressure surface level, changing the implied path. '
        'It is not a coordinate-invariance demonstration or a predicted regional rain improvement.', '',
        'Next: paired reference-aligned sigma and hybrid pressure-geometry hypotheses in both regions. '
        'Both use all-layer pressure-level temperature and pressure-consistent mean heights. '
        'The hybrid top interface is fixed at 607.95 hPa; lower layers follow terrain. '
        'Identical prescribed face fluxes and storms imply different local physical velocities, '
        'which must be reported. No cloud/fallout tuning or atlas promotion.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=ROOT/'output/v10_upper_air_check')
    p.add_argument('--out', type=Path, default=ROOT/'output/v10_upper_air_diagnosis')
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
