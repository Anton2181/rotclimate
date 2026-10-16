"""Four bounded coordinate-path cases. User launches with --run.

No parameter search, data download or atlas export. Both controls use aligned
pressure/height/temperature references; they differ in the vertical pressure
grid and physical paths implied by identical kinematic face fluxes.
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
from experiments import v10_coordinates as model, v10_forcing_audit as atmosphere
from scripts import check_v10_upper_air as upper, diagnose_v10_upper_air as diagnosis
from scripts import overnight_v10 as night
from rotclimate_v10.core import CENTERS
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def source_id():
    h = hashlib.sha256(upper.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(diagnosis.__file__)):
        h.update(path.read_bytes())
    return h.hexdigest()


def array_id(arrays):
    h = hashlib.sha256()
    for name, array in sorted(arrays.items()):
        h.update(name.encode())
        h.update(str(array.shape).encode())
        h.update(np.asarray(array, dtype='<f8').tobytes())
    return h.hexdigest()


def geometry_arrays(g, local_air):
    return {'mass': g.mass, 'surface_pressure': g.surface_pressure, 'pressure': g.pressure,
        'height_m': g.height_m, 'interfaces_pa': g.interfaces_pa, 'local_air': local_air}


def implied_wind(case, g, profile, settings):
    speeds = []
    errors = []
    for t in CENTERS:
        flow = model.base.flow_at(case.domain, profile, settings, [], float(t))
        u = .5*(flow.x[:, :, 1:]+flow.x[:, :, :-1])/g.mass
        v = -.5*(flow.y[:, 1:]+flow.y[:, :-1])/g.mass
        ru = model.interpolate_months(profile.eastward, float(t))[:, None, None]
        rv = model.interpolate_months(profile.northward, float(t))[:, None, None]
        speeds.append(np.hypot(u, v))
        errors.append(np.hypot(u-ru, v-rv))
    speed = np.stack(speeds)[:, :, case.score_mask]
    error = np.stack(errors)[:, :, case.score_mask]
    return {'no_storm_speed_max_m_s_by_layer': speed.max(axis=(0, 2)).tolist(),
        'no_storm_speed_p95_m_s_by_layer': np.percentile(speed, 95, axis=(0, 2)).tolist(),
        'difference_from_offshore_vector_p95_m_s_by_layer': np.percentile(error, 95, axis=(0, 2)).tolist(),
        'warning': 'Offshore vectors are not local wind observations. Fixed face fluxes imply different velocities when masses change; this is a path hypothesis test, not pure coordinate invariance.'}


def prepare(source):
    manifest, state, cases, profiles, _, _, _, _ = diagnosis.load_verified(source)
    texts, _ = atmosphere.acquire(ROOT/'data/v10_atmosphere', False)
    fields = atmosphere.fields_from_cache(texts)
    settings = model.base.Settings(**manifest['settings'])
    inputs = {}
    records = {}
    for region, case in cases.items():
        for mode in ('sigma', 'hybrid'):
            g, air = model.prepare_geometry(case, fields, mode)
            key = region+'_'+mode
            inputs[key] = (case, profiles[region], g, air)
            records[key] = {'array_sha256': array_id(geometry_arrays(g, air)),
                'wind': implied_wind(case, g, profiles[region], settings)}
    expected = {'schema': 1, 'code_sha256': source_id(),
        'source_manifest_sha256': sha256(source/'manifest.json'),
        'source_state_sha256': sha256(source/'state.json'), 'settings': asdict(settings),
        'cases': records, 'spacing_km': 60, 'seed': 41, 'minimum_cycles': 3, 'maximum_cycles': 6,
        'upper_transition_pa': model.TRANSITION_PA,
        'common_change': 'All-layer local pressure temperature; annual reference geopotential heights; surface pressure inferred from those heights at model terrain. Below-1000-hPa surface inference extrapolates only the lowest reference interval.',
        'comparison': 'Sigma versus hybrid pressure geometry and its implied kinematic circulation. Same prescribed face fluxes/storms; physical velocities differ. Not coordinate invariance.',
        'atlas_publication': False, 'hour_cap_per_invocation': 1.}
    return expected, inputs, settings


def settling(previous, current, case, g):
    old, op, ot, _, _ = previous
    new, p, t, _, _ = current
    mask = case.score_mask
    changes = {'monthly_rain_p95_mm': float(np.percentile(abs(p-op)[:, mask], 95)),
        'annual_rain_p95_mm': float(np.percentile(abs((p-op).sum(0))[mask], 95)),
        'water_store_p95_mm': max(float(np.percentile(abs(new.water[k]-old.water[k]), 95)) for k in range(4)),
        'soil_p95_mm': float(np.percentile(abs(new.soil-old.soil), 95)),
        'monthly_temperature_p95_c': float(np.percentile(abs(t-ot)[:, :, mask], 95)),
        'end_temperature_p95_c': float(np.percentile(abs(model.base.temperature(new.energy, g.mass, new.water, g.height_m)-model.base.temperature(old.energy, g.mass, old.water, g.height_m)), 95))}
    limits = dict(zip(changes, (1., 5., 1., 1., .05, .05)))
    return {'passed': all(v <= limits[k] for k, v in changes.items()), 'changes': changes, 'limits': limits}


def run_case(folder, case, profile, geometry, air, settings, stop, log):
    folder.mkdir(parents=True, exist_ok=True)
    config = {'region': case.domain.name, 'mode': geometry.mode,
        'settings': asdict(settings), 'seed': 41, 'input_array_sha256': array_id(geometry_arrays(geometry, air))}
    path = folder/'config.json'
    if path.exists() and json.loads(path.read_text()) != config:
        raise ValueError('Coordinate case configuration changed.')
    if not path.exists():
        atomic_json(path, config)
    state = model.initial_state(case.domain, profile, settings, geometry, air)
    previous = None
    check = {'passed': False}
    for year in range(1, 7):
        record = night.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
        if record is None:
            partial = night.read_checkpoint(folder, year, case.domain.land.shape)
            started = time.monotonic()
            before = partial[-1].get('elapsed_seconds', 0.) if partial else 0.
            def save(*record):
                info = dict(record[-1], elapsed_seconds=before+time.monotonic()-started)
                night.write_checkpoint(folder, year, (*record[:4], info))
                log(f'{case.domain.name}/{geometry.mode}: year {year}/6, month {info["month"]}/12')
            record = model.year(case.domain, profile, settings, 41, state, air,
                case.score_mask, geometry, checkpoint=partial, save_month=save, should_stop=stop)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            night.write_checkpoint(folder, year, record, completed=True)
        if previous is not None:
            check = settling(previous, record, case, geometry)
        state = record[0]
        if year >= 3 and check['passed']:
            break
        previous = record
    result = night.summarize(record, case, check, year)
    result['mode'] = geometry.mode
    result['reference_forcing'] = True
    result['evidence_sha256'] = {p.name: sha256(p) for p in sorted(folder.glob('year[0-9].*')) if p.suffix in ('.json', '.npz')}
    atomic_json(folder/'summary.json', result)
    return result


def report(out, state, expected):
    lines = ['# Pressure-geometry path check', '', f"Status: {state['status']}. No parameter search or atlas update.", '',
        '| Region / mode | Rain MAE | Rain / reference | Coverage | Settled | Provisional rain/thermal screen |',
        '|---|---:|---:|---:|---|---|']
    for key, row in state['cases'].items():
        lines.append(f"| {key} | {row['score']:.2f} | {row['annual_rain_ratio']:.2f} | {row['wet_reference_coverage']:.1%} | {row['settling']['passed']} | {row['eligible']} |")
    lines += ['', 'Both modes align pressure, mean geopotential and all-layer thermal targets. '
        'The hybrid upper interface is fixed at 607.95 hPa; lower layers follow terrain. '
        'Identical prescribed face fluxes imply different physical velocities. '
        'This is a controlled circulation-path hypothesis, not a coordinate-invariance test.', '',
        '| Region / mode | Maximum no-storm speed by layer, m/s |', '|---|---|']
    for key, row in expected['cases'].items():
        lines.append('| '+key+' | '+', '.join(f'{v:.1f}' for v in row['wind']['no_storm_speed_max_m_s_by_layer'])+' |')
    lines += ['', 'A rain/thermal screen pass alone cannot validate winds, momentum, vertical quadrature '
        'or independent temperature prediction. Layer rain and signed thermal ledgers are in final-year metadata. '
        'No map export or automatic promotion occurs.']
    if state.get('error'):
        lines += ['', 'Stopped: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, source, hours=1., case_runner=run_case):
    expected, inputs, settings = prepare(source)
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != expected:
        raise ValueError('Coordinate experiment changed; preserve evidence and choose a new --out.')
    if not manifest.exists():
        atomic_json(manifest, expected)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous coordinate failure needs inspection before another run.')
    state['status'] = 'running'
    deadline = time.monotonic()+hours*3600
    interrupted = [False]
    old_handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
    def stop():
        return interrupted[0] or time.monotonic() >= deadline
    def log(message):
        print(message, flush=True)
        with (out/'run.log').open('a') as f:
            f.write(night.utc()+' '+message+'\n')
    try:
        report(out, state, expected)
        for key, (case, profile, g, air) in inputs.items():
            if source_id() != expected['code_sha256']:
                raise ValueError('Source changed during coordinate test.')
            folder = out/'cases'/key
            if key in state['cases']:
                for name, digest in state['cases'][key]['evidence_sha256'].items():
                    if Path(name).name != name or sha256(folder/name) != digest:
                        raise ValueError('Completed coordinate evidence changed.')
                continue
            if stop():
                raise model.base.BudgetStop()
            arrays = geometry_arrays(g, air)
            input_path = out/'inputs'/(key+'.npz')
            if input_path.exists():
                with np.load(input_path, allow_pickle=False) as saved:
                    if set(saved.files) != set(arrays) or array_id({k: saved[k] for k in saved.files}) != expected['cases'][key]['array_sha256']:
                        raise ValueError('Saved geometry inputs changed.')
            else:
                input_path.parent.mkdir(exist_ok=True)
                atomic_npz(input_path, **arrays)
            row = case_runner(folder, case, profile, g, air, settings, stop, log)
            state['cases'][key] = row
            report(out, state, expected)
            if not row['settling']['passed']:
                raise RuntimeError('Six cycles did not settle; inspect before continuing.')
        state['status'] = 'complete'
    except model.base.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError, RuntimeError, FloatingPointError, OSError) as error:
        state['status'] = 'needs_diagnosis'
        state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT, old_handler)
        report(out, state, expected)
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', action='store_true')
    p.add_argument('--source', type=Path, default=ROOT/'output/v10_upper_air_check')
    p.add_argument('--out', type=Path, default=ROOT/'output/v10_coordinate_check')
    args = p.parse_args(argv)
    print('Four cases: sigma/hybrid paths in California/Iberia; setting 120, seed 41, 60 km.', flush=True)
    print('Three to six cycles each. Approximately 20–40 minutes from comparable timings; one-hour cap and monthly resume.', flush=True)
    print('No search, downloads or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_coordinates.py --run')
        return 0
    result = run(args.out, args.source)
    print('Status: '+result['status'], flush=True)
    return 0 if result['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
