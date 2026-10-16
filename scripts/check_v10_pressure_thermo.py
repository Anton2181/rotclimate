"""Four pressure-thermodynamic cases; default is read-only.

Compare dry-theta transport with saved approximate-MSE controls at humidity 1.0,
uniform/spatial winds in both regions. Explicit prescribed-flow work; no atlas.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import signal
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import scipy
from experiments import v10_pressure_thermo as model
from scripts import review_v10_spatial_wind as review
from scripts import check_v10_coordinates as geometry_rules, audit_v10_pressure_law as pressure_audit
from scripts.review_v10_storm_delivery import rain_vector
from scripts import overnight_v10 as night
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
old = review.run


def source_id():
    digest = hashlib.sha256(old.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(review.__file__), Path(pressure_audit.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def input_arrays(g, air, wind):
    return dict(geometry_rules.geometry_arrays(g, air), local_wind=wind)


def prepare(source):
    manifest, state, inputs, settings, uniform_controls, _, _ = review.load_verified(source)
    config = settings['humidity_10']
    controls = {'uniform': config, 'spatial': config}
    baselines = {}
    for region in inputs:
        baselines[region+'_uniform'] = uniform_controls[region+'_humidity_10']
        baselines[region+'_spatial'] = state['cases'][region+'_humidity_10']
    expected = {'schema': 1, 'code_sha256': source_id(),
        'source_manifest_sha256': sha256(source/'manifest.json'), 'source_state_sha256': sha256(source/'state.json'),
        'baseline_evidence': {key: row['evidence_sha256'] for key, row in baselines.items()},
        'settings': {key: asdict(value) for key, value in controls.items()},
        'inputs': {r: geometry_rules.array_id(input_arrays(g, air, wind)) for r, (_, _, g, air, wind) in inputs.items()},
        'change': 'Dry theta transported with existing dry-air fluxes, then local pressure conversion; constant dry Rd/cp; explicit diagnosed prescribed-flow work in the old MSE representation. Existing microphysics and water transport unchanged.',
        'energy_policy': 'Stored m(cp*T+gz)+Lv*water includes explicit diagnosed prescribed_flow_work_j_m2. Momentum/kinetic energy remain unsolved; no new total-energy conservation claim.',
        'processes': list(model.PROCESSES), 'rd_j_kg_k': model.RD, 'reference_pressure_pa': model.P_REF,
        'weather': 'Unchanged rate-one storms, seed 41. Same monthly winds, terrain, boundary moisture, relaxation and geometry as each saved control.',
        'spacing_km': 60, 'seed': 41, 'minimum_cycles': 3, 'maximum_cycles': 6,
        'hour_cap_per_invocation': 1., 'atlas_publication': False,
        'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': scipy.__version__}}
    return expected, inputs, controls, baselines


def run_case(folder, case, profile, g, air, wind, settings, wind_mode, stop, log):
    folder.mkdir(parents=True, exist_ok=True)
    config = {'region': case.domain.name, 'settings': asdict(settings), 'seed': 41,
        'input_array_sha256': geometry_rules.array_id(input_arrays(g, air, wind)), 'wind': wind_mode, 'thermal_transport': 'dry_theta'}
    path = folder/'config.json'
    if path.exists() and json.loads(path.read_text()) != config:
        raise ValueError('Pressure-thermodynamic case configuration changed.')
    if not path.exists():
        atomic_json(path, config)
    state = model.initial_state(case.domain, profile, settings, g, air)
    previous = None;check = {'passed': False}
    for year in range(1, 7):
        record = night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
        if record is None:
            partial = night.read_checkpoint(folder, year, case.domain.land.shape)
            started = time.monotonic()
            before = partial[-1].get('elapsed_seconds', 0.) if partial else 0.
            def save(*record):
                info = dict(record[-1], elapsed_seconds=before+time.monotonic()-started)
                night.write_checkpoint(folder, year, (*record[:4], info))
                log(f'{folder.name}: year {year}/6, month {info["month"]}/12')
            record = model.year(case.domain, profile, settings, 41, state, air, case.score_mask,
                g, wind, checkpoint=partial, save_month=save, should_stop=stop, wind_mode=wind_mode)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            night.write_checkpoint(folder, year, record, completed=True)
        if previous is not None:
            check = geometry_rules.settling(previous, record, case, g)
        state = record[0]
        if year >= 3 and check['passed']:
            break
        previous = record
    row = night.summarize(record, case, check, year)
    row['response'] = rain_vector(case, record[1])
    row['evidence_sha256'] = {p.name: sha256(p) for p in sorted(folder.glob('year[0-9].*')) if p.suffix in ('.json', '.npz')}
    atomic_json(folder/'summary.json', row)
    return row


def report(out, state, expected, baselines):
    lines = ['# Pressure-based thermodynamic transport check', '',
        f"Status: {state['status']}. Four fixed cases; no search or atlas export.", '',
        '| Case | Old → theta rain MAE | Old → theta rain/reference | Old → theta coverage | Settled | Broad screen |',
        '|---|---:|---:|---:|---|---|']
    for key, row in state['cases'].items():
        baseline = baselines[key]
        lines.append(f"| {key} | {baseline['score']:.2f} → {row['score']:.2f} | {baseline['annual_rain_ratio']:.2f} → {row['annual_rain_ratio']:.2f} | {baseline['wet_reference_coverage']:.1%} → {row['wet_reference_coverage']:.1%} | {row['settling']['passed']} | {row['eligible']} |")
    lines += ['', 'Dry potential temperature is advected with the same dry-air fluxes as water. '
        'Pressure conversion replaces passive approximate-MSE transport. Diagnosed '
        'prescribed-flow work is an explicit energy exchange; the kinetic/momentum system '
        'is unsolved, so this is not a claim of complete total-energy conservation.', '',
        'Water transport, microphysics, geometry, boundaries, winds and weather remain paired. '
        'All old broad screens are retained in separately fingerprinted evidence. '
        'Review physical rainfall, target departure and work magnitude together; '
        'temperature is observation-informed. No automatic atlas promotion.']
    if state.get('error'):
        lines += ['', 'Stopped: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, source, hours=1., case_runner=run_case):
    expected, inputs, settings, baselines = prepare(source)
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != expected:
        raise ValueError('Pressure-thermodynamic experiment changed; preserve output and use a new --out.')
    if not manifest.exists():
        atomic_json(manifest, expected)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous failure needs inspection before resuming.')
    state['status'] = 'running'
    interrupted = [False]
    handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
    deadline = time.monotonic()+hours*3600
    def stop():
        return interrupted[0] or time.monotonic() >= deadline
    def log(message):
        print(message, flush=True)
        with (out/'run.log').open('a') as file:
            file.write(night.utc()+' '+message+'\n')
    try:
        report(out, state, expected, baselines)
        for name, config in settings.items():
            for region, (case, profile, g, air, wind) in inputs.items():
                if source_id() != expected['code_sha256']:
                    raise ValueError('Sources changed during pressure-thermodynamic check.')
                key = region+'_'+name;folder = out/'cases'/key
                if key in state['cases']:
                    for filename, digest in state['cases'][key]['evidence_sha256'].items():
                        if Path(filename).name != filename or sha256(folder/filename) != digest:
                            raise ValueError('Completed pressure-thermodynamic evidence changed.')
                    continue
                if stop():
                    raise model.base.BudgetStop()
                input_path = out/'inputs'/(region+'.npz')
                arrays = input_arrays(g, air, wind)
                if input_path.exists():
                    with np.load(input_path, allow_pickle=False) as saved:
                        if set(saved.files) != set(arrays) or geometry_rules.array_id({k: saved[k] for k in saved.files}) != expected['inputs'][region]:
                            raise ValueError('Saved pressure-thermodynamic inputs changed.')
                else:
                    input_path.parent.mkdir(exist_ok=True)
                    atomic_npz(input_path, **arrays)
                row = case_runner(folder, case, profile, g, air, wind, config, name, stop, log)
                state['cases'][key] = row
                report(out, state, expected, baselines)
                if not row['settling']['passed']:
                    raise RuntimeError('Six cycles did not settle; inspect before continuing.')
        state['status'] = 'complete'
    except model.base.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError, RuntimeError, FloatingPointError, OSError) as error:
        state['status'] = 'needs_diagnosis';state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT, handler)
        report(out, state, expected, baselines)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_spatial_wind')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_pressure_thermo')
    args = parser.parse_args(argv)
    print('Four dry-theta cases: uniform/spatial winds in California and Iberia, humidity 1.0; four completed MSE controls reused.', flush=True)
    print('Estimated 15–30 minutes, one-hour cap, monthly checkpoints and same-command resume. No search, download or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_pressure_thermo.py --run')
        return 0
    state = run(args.out, args.source)
    print('Status: '+state['status'], flush=True)
    return 0 if state['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
