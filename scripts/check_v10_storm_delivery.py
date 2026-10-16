"""Ten bounded mass-consistent circulation/storm controls. Default is read-only.

Two projected-flow anchors compare with completed hybrid baselines. Four fixed humidity/
storm controls per region use nested weather. No optimizer, downloads or atlas.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, replace
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
from experiments import v10_mass_projection as model, v10_forcing_audit as atmosphere
from scripts import check_v10_coordinates as old, diagnose_v10_coordinates as diagnosis
from scripts import overnight_v10 as night
from rotclimate_v10.core import CENTERS
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def source_id():
    h = hashlib.sha256(old.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(diagnosis.__file__)):
        h.update(path.read_bytes())
    return h.hexdigest()


def design(anchor):
    return {'anchor': anchor,
        'mean_only': replace(anchor, humidity_scale=1., storm_rate_month=0.),
        'rare_storms': replace(anchor, humidity_scale=1., storm_rate_month=1.),
        'winter_storms': replace(anchor, humidity_scale=1., storm_rate_month=4.),
        'frequent_storms': replace(anchor, humidity_scale=1., storm_rate_month=8.)}


def wind_audit(case, profile, g, settings, fields):
    projector = model.ColumnProjection(case.domain, g)
    speed = [];proxy_speed = [];old_speed = [];reference_error = [];adjustments = []
    local_u = [];local_v = []
    for layer in range(4):
        u, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'uwnd'], case.longitude, case.domain.latitude, g.pressure[layer]/100)
        v, _, _ = atmosphere.at_pressure(fields[case.domain.name, 'vwnd'], case.longitude, case.domain.latitude, g.pressure[layer]/100)
        local_u.append(u);local_v.append(v)
    local_u, local_v = np.stack(local_u, axis=1), np.stack(local_v, axis=1)
    if not np.isfinite(local_u).all() or not np.isfinite(local_v).all():
        raise ValueError('Missing pressure-level wind reference.')
    for month, t in enumerate(CENTERS):
        previous = model.base.flow_at(case.domain, profile, settings, [], float(t))
        projected = model.flow_at(case.domain, profile, settings, [], float(t), g, projector)
        u, v = model.cell_velocity(projected, projector)
        ou, ov = model.cell_velocity(previous, projector)
        speed.append(np.hypot(u, v));old_speed.append(np.hypot(ou, ov))
        pu = .5*(projected.x[:, :, 1:]+projected.x[:, :, :-1])/g.mass
        pv = -.5*(projected.y[:, 1:]+projected.y[:, :-1])/g.mass
        proxy_speed.append(np.hypot(pu, pv))
        reference_error.append(np.hypot(u-local_u[month], v-local_v[month]))
        adjustments.append(projector.last_info.copy())
    def maximum(values):
        return np.stack(values)[:, :, case.score_mask].max(axis=(0, 2)).tolist()
    return {'new_face_velocity_max_m_s_by_layer': maximum(speed),
        'old_face_velocity_max_m_s_by_layer': maximum(old_speed),
        'new_legacy_flux_store_proxy_max_m_s_by_layer': maximum(proxy_speed),
        'local_reference_vector_error_p95_m_s_by_layer': np.percentile(np.stack(reference_error)[:, :, case.score_mask], 95, axis=(0, 2)).tolist(),
        'background_adjustment_max_m_s': max(x['barotropic_velocity_adjustment_max_m_s'] for x in adjustments),
        'continuity_residual_max_kg_m2_s': max(x['projected_column_divergence_max_kg_m2_s'] for x in adjustments),
        'note': 'Face-interpolated velocities and the older flux/cell-mass proxy are different diagnostics. Coarse reference winds and stationary mass projection are not a solved momentum model.'}


def prepare(source):
    manifest, state, all_inputs, anchor, records, _ = diagnosis.load_verified(source)
    texts, _ = atmosphere.acquire(ROOT/'data/v10_atmosphere', False)
    fields = atmosphere.fields_from_cache(texts)
    inputs = {region: all_inputs[region+'_hybrid'] for region in ('california', 'iberia')}
    settings = design(anchor)
    winds = {region: wind_audit(*values[:3], anchor, fields) for region, values in inputs.items()}
    # values order is case, profile, geometry, thermal reference.
    event_records = {}
    for region, (case, profile, g, air) in inputs.items():
        for name, config in settings.items():
            events = [asdict(event) for event in model.nested_events(case.domain, config, 41, profile.storm_domain_width_m)]
            event_records[region+'_'+name] = {'count': len(events),
                'sha256': hashlib.sha256(json.dumps(events, sort_keys=True).encode()).hexdigest()}
    expected = {'schema': 1, 'code_sha256': source_id(),
        'source_manifest_sha256': sha256(source/'manifest.json'), 'source_state_sha256': sha256(source/'state.json'),
        'source_hybrid_evidence': {r: state['cases'][r+'_hybrid']['evidence_sha256'] for r in inputs},
        'settings': {k: asdict(v) for k, v in settings.items()},
        'inputs': {r: old.array_id(old.geometry_arrays(g, air)) for r, (_, _, g, air) in inputs.items()},
        'winds': winds, 'weather_catalogues': event_records,
        'projection': 'Mass-weighted nominal face velocities; minimum-change barotropic potential; zero exterior potential on open boundaries; diagnosed vertical exchange balances each layer.',
        'weather': 'Old rate-one catalogue retained exactly. Independent rate-seven master events thinned to extend rates four/eight; zero/one/four/eight catalogues are nested.',
        'spacing_km': 60, 'seed': 41, 'minimum_cycles': 3, 'maximum_cycles': 6,
        'hour_cap_per_invocation': 1.5, 'atlas_publication': False,
        'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': scipy.__version__}}
    baselines = {region: state['cases'][region+'_hybrid'] for region in inputs}
    return expected, inputs, settings, baselines


def run_case(folder, case, profile, g, air, config, stop, log):
    folder.mkdir(parents=True, exist_ok=True)
    declaration = {'region': case.domain.name, 'settings': asdict(config), 'seed': 41,
        'input_array_sha256': old.array_id(old.geometry_arrays(g, air)),
        'projection': 'mass_weighted', 'nested_weather': True}
    path = folder/'config.json'
    if path.exists() and json.loads(path.read_text()) != declaration:
        raise ValueError('Storm-delivery case configuration changed.')
    if not path.exists():
        atomic_json(path, declaration)
    state = model.initial_state(case.domain, profile, config, g, air)
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
            record = model.year(case.domain, profile, config, 41, state, air,
                case.score_mask, g, checkpoint=partial, save_month=save, should_stop=stop)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            night.write_checkpoint(folder, year, record, completed=True)
        if previous is not None:
            check = old.settling(previous, record, case, g)
        state = record[0]
        if year >= 3 and check['passed']:
            break
        previous = record
    row = night.summarize(record, case, check, year)
    row['evidence_sha256'] = {p.name: sha256(p) for p in sorted(folder.glob('year[0-9].*')) if p.suffix in ('.json', '.npz')}
    atomic_json(folder/'summary.json', row)
    return row


def report(out, state, expected, baselines):
    lines = ['# Mass-consistent wind and storm-delivery check', '',
        f"Status: {state['status']}. Ten fixed cases; no optimizer or atlas export.", '',
        '| Case | Rain MAE | Rain / reference | Wet-reference coverage | Settled | Provisional rain/thermal screen |',
        '|---|---:|---:|---:|---|---|']
    for key, row in state['cases'].items():
        lines.append(f"| {key} | {row['score']:.2f} | {row['annual_rain_ratio']:.2f} | {row['wet_reference_coverage']:.1%} | {row['settling']['passed']} | {row['eligible']} |")
    lines += ['', 'The anchor differs from each completed hybrid baseline only in velocity-to-mass-flux '
        'construction and its column projection; its old rate-one weather catalogue is retained. '
        'Other controls restore the reference humidity multiplier and vary nested storm count.', '',
        '| Completed hybrid baseline | Rain MAE, mm/month | Rain / reference | Wet-reference coverage |',
        '|---|---:|---:|---:|']
    for region, row in baselines.items():
        lines.append(f"| {region} | {row['score']:.2f} | {row['annual_rain_ratio']:.2f} | {row['wet_reference_coverage']:.1%} |")
    lines += ['',
        '| Region | Old / new maximum middle-layer face speed, m/s |', '|---|---:|']
    for region, row in expected['winds'].items():
        previous = max(row['old_face_velocity_max_m_s_by_layer'][1:3]);new = max(row['new_face_velocity_max_m_s_by_layer'][1:3])
        lines.append(f'| {region} | {previous:.1f} / {new:.1f} |')
    lines += ['', 'Face velocities use face dry mass consistently. The earlier cell-flux/store proxy '
        'can differ on steep mass gradients; both conventions are retained in the manifest. '
        'Projection enforces stationary column mass with explicit open-boundary adjustments, '
        'not a prognostic momentum/radiation system. Temperature remains observation-informed.', '',
        'The provisional screen requires settling, closed budgets, temperature departures '
        '<=5/10°C (lower/upper), annual rain ratio 0.5–1.75, at least 80% of reference '
        'non-arid land receiving >=1 mm/year, and rain p99 <=4 times reference. This '
        'coverage threshold is a minimal dry-gap check, not evidence of a realistic rainfall map.', '',
        'A provisional rain/thermal pass is diagnostic evidence, not independent validation. '
        'Geometry, rain-out closure and old acceptance evidence remain unchanged.']
    if state.get('error'):
        lines += ['', 'Stopped: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, source, hours=1.5, case_runner=run_case):
    expected, inputs, settings, baselines = prepare(source)
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != expected:
        raise ValueError('Storm experiment changed; preserve output and use a new --out.')
    if not manifest.exists():
        atomic_json(manifest, expected)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous failure needs inspection before another run.')
    state['status'] = 'running'
    interrupted = [False]
    previous_handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
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
            for region, (case, profile, g, air) in inputs.items():
                if source_id() != expected['code_sha256']:
                    raise ValueError('Sources changed during storm-delivery check.')
                key = region+'_'+name;folder = out/'cases'/key
                if key in state['cases']:
                    for filename, digest in state['cases'][key]['evidence_sha256'].items():
                        if Path(filename).name != filename or sha256(folder/filename) != digest:
                            raise ValueError('Completed storm evidence changed.')
                    continue
                if stop():
                    raise model.base.BudgetStop()
                input_path = out/'inputs'/(region+'.npz')
                arrays = old.geometry_arrays(g, air)
                if input_path.exists():
                    with np.load(input_path, allow_pickle=False) as saved:
                        if set(saved.files) != set(arrays) or old.array_id({k: saved[k] for k in saved.files}) != expected['inputs'][region]:
                            raise ValueError('Saved storm input changed.')
                else:
                    input_path.parent.mkdir(exist_ok=True)
                    atomic_npz(input_path, **arrays)
                row = case_runner(folder, case, profile, g, air, config, stop, log)
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
        signal.signal(signal.SIGINT, previous_handler)
        report(out, state, expected, baselines)
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', action='store_true')
    p.add_argument('--source', type=Path, default=ROOT/'output/v10_coordinate_check')
    p.add_argument('--out', type=Path, default=ROOT/'output/v10_storm_delivery')
    args = p.parse_args(argv)
    print('Ten fixed cases: projected anchor plus reference-humidity zero/one/four/eight storms in each region.', flush=True)
    print('Roughly 20–45 minutes from prior timings; 90-minute cap, monthly checkpoints and same-command resume.', flush=True)
    print('No optimizer, downloads or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_storm_delivery.py --run')
        return 0
    result = run(args.out, args.source)
    print('Status: '+result['status'], flush=True)
    return 0 if result['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
