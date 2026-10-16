"""Four fixed spatial-mean-wind cases; default is read-only.

Reuse four completed uniform-wind baselines at humidity 0.8/1.0 in both regions.
Only mean wind varies spatially. No search, download or atlas publication.
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
from experiments import v10_spatial_wind as model, v10_forcing_audit as atmosphere
from scripts import review_v10_storm_delivery as review
from scripts import overnight_v10 as night
from rotclimate_v10.core import CENTERS
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
old = review.run


def source_id():
    digest = hashlib.sha256(old.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(review.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def input_arrays(g, air, wind):
    return dict(old.old.geometry_arrays(g, air), local_wind=wind)


def wind_audit(case, profile, g, settings, wind):
    errors = [];previous = [];adjustments = [];residuals = [];speeds = []
    projector = model.ColumnProjection(case.domain, g)
    for t in CENTERS:
        flow = model.flow_at(case.domain, profile, settings, [], float(t), g, wind, projector)
        adjustments.append(projector.last_info['barotropic_velocity_adjustment_max_m_s'])
        residuals.append(flow.continuity)
        old_flow = model.mass_model.flow_at(case.domain, profile, settings, [], float(t), g)
        u, v = model.mass_model.cell_velocity(flow, projector)
        ou, ov = model.mass_model.cell_velocity(old_flow, projector)
        ru, rv = model.interpolate_months(wind, float(t))
        errors.append(np.hypot(u-ru, v-rv));previous.append(np.hypot(ou-ru, ov-rv))
        speeds.append(np.hypot(u, v))
    def p95(a):
        return np.percentile(np.stack(a)[:, :, case.score_mask], 95, axis=(0, 2)).tolist()
    return {'uniform_target_departure_p95_m_s_by_layer': p95(previous),
        'spatial_target_departure_p95_m_s_by_layer': p95(errors),
        'spatial_speed_max_m_s_by_layer': np.stack(speeds)[:, :, case.score_mask].max(axis=(0, 2)).tolist(),
        'background_projection_adjustment_max_m_s': max(adjustments),
        'continuity_residual_max_kg_m2_s': max(residuals),
        'note': 'Consistency against the imposed bilinear monthly wind target, not independent wind validation. Terrain drag, face interpolation and projection change that target.'}


def prepare(source):
    manifest, state, inputs, settings, _, _, _ = review.load_verified(source)
    texts, downloads = atmosphere.acquire(ROOT/'data/v10_atmosphere', False)
    fields = atmosphere.fields_from_cache(texts)
    inputs = {r: (*values, model.prepare_wind(values[0], values[2], fields)) for r, values in inputs.items()}
    controls = {'humidity_08': settings['anchor'], 'humidity_10': settings['rare_storms']}
    baseline_names = {'humidity_08': 'anchor', 'humidity_10': 'rare_storms'}
    baselines = {r+'_'+name: state['cases'][r+'_'+baseline_names[name]] for r in inputs for name in controls}
    winds = {r: wind_audit(case, profile, g, controls['humidity_08'], wind)
        for r, (case, profile, g, air, wind) in inputs.items()}
    expected = {'schema': 1, 'code_sha256': source_id(),
        'source_manifest_sha256': sha256(source/'manifest.json'), 'source_state_sha256': sha256(source/'state.json'),
        'baseline_case_names': baseline_names,
        'baseline_evidence': {key: row['evidence_sha256'] for key, row in baselines.items()},
        'settings': {k: asdict(v) for k, v in controls.items()},
        'inputs': {r: old.old.array_id(input_arrays(g, air, wind)) for r, (_, _, g, air, wind) in inputs.items()},
        'winds': winds, 'reference_downloads': downloads,
        'change': 'Only background winds: bilinear horizontal and log-pressure interpolation of cached local monthly NCEP wind at each representative layer pressure; same terrain drag, mass projection, thermodynamics and offshore boundary humidity.',
        'weather': 'Unchanged old rate-one catalogue, seed 41, same spatial domain and storm strength/radius. No observed storm heat/moisture covariance.',
        'spacing_km': 60, 'seed': 41, 'minimum_cycles': 3, 'maximum_cycles': 6,
        'hour_cap_per_invocation': 1., 'atlas_publication': False,
        'runtime': {'python': sys.version.split()[0], 'numpy': np.__version__, 'scipy': scipy.__version__}}
    return expected, inputs, controls, baselines


def run_case(folder, case, profile, g, air, wind, settings, stop, log):
    folder.mkdir(parents=True, exist_ok=True)
    config = {'region': case.domain.name, 'settings': asdict(settings), 'seed': 41,
        'input_array_sha256': old.old.array_id(input_arrays(g, air, wind)), 'wind': 'spatial_bilinear'}
    path = folder/'config.json'
    if path.exists() and json.loads(path.read_text()) != config:
        raise ValueError('Spatial-wind case configuration changed.')
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
                g, wind, checkpoint=partial, save_month=save, should_stop=stop)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            night.write_checkpoint(folder, year, record, completed=True)
        if previous is not None:
            check = old.old.settling(previous, record, case, g)
        state = record[0]
        if year >= 3 and check['passed']:
            break
        previous = record
    row = night.summarize(record, case, check, year)
    row['response'] = review.rain_vector(case, record[1])
    row['evidence_sha256'] = {p.name: sha256(p) for p in sorted(folder.glob('year[0-9].*')) if p.suffix in ('.json', '.npz')}
    atomic_json(folder/'summary.json', row)
    return row


def report(out, state, expected, baselines):
    lines = ['# Spatial background wind check', '', f"Status: {state['status']}. Four fixed cases; no search or atlas export.", '',
        '| Case | Uniform → spatial MAE | Uniform → spatial rain/reference | Uniform → spatial coverage | Settled | Provisional screen |',
        '|---|---:|---:|---:|---|---|']
    for key, row in state['cases'].items():
        base = baselines[key]
        lines.append(f"| {key} | {base['score']:.2f} → {row['score']:.2f} | {base['annual_rain_ratio']:.2f} → {row['annual_rain_ratio']:.2f} | {base['wet_reference_coverage']:.1%} → {row['wet_reference_coverage']:.1%} | {row['settling']['passed']} | {row['eligible']} |")
    lines += ['', 'The broad screen is retained unchanged. Positive skill against zero rain, coastal/interior '
        'winter/summer responses and rain concentration must accompany an apparent improvement; '
        'neither development region is independent validation. The seasonal driver records signed '
        'thermal terms, layer rainfall, maximum projection adjustment and full water/energy budgets.', '',
        'Monthly spatial winds remain imposed forcing. Offshore boundary humidity and synthetic '
        'storm heat/moisture covariance remain limitations. Bilinear interpolation smooths native '
        'grid steps but adds no information beyond the coarse reference. Existing terrain drag '
        'may overlap resolved terrain effects; this matched experiment keeps it fixed.', '',
        'Temperature remains observation-informed. No automatic promotion or fantasy atlas update.']
    if state.get('error'):
        lines += ['', 'Stopped: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, source, hours=1., case_runner=run_case):
    expected, inputs, settings, baselines = prepare(source)
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != expected:
        raise ValueError('Spatial-wind experiment changed; preserve output and use a new --out.')
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
                    raise ValueError('Sources changed during spatial-wind check.')
                key = region+'_'+name;folder = out/'cases'/key
                if key in state['cases']:
                    for filename, digest in state['cases'][key]['evidence_sha256'].items():
                        if Path(filename).name != filename or sha256(folder/filename) != digest:
                            raise ValueError('Completed spatial-wind evidence changed.')
                    continue
                if stop():
                    raise model.base.BudgetStop()
                input_path = out/'inputs'/(region+'.npz')
                arrays = input_arrays(g, air, wind)
                if input_path.exists():
                    with np.load(input_path, allow_pickle=False) as saved:
                        if set(saved.files) != set(arrays) or old.old.array_id({k: saved[k] for k in saved.files}) != expected['inputs'][region]:
                            raise ValueError('Saved spatial-wind inputs changed.')
                else:
                    input_path.parent.mkdir(exist_ok=True)
                    atomic_npz(input_path, **arrays)
                row = case_runner(folder, case, profile, g, air, wind, config, stop, log)
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
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_storm_delivery')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_spatial_wind')
    args = parser.parse_args(argv)
    print('Four spatial-wind cases at humidity 0.8/1.0 in California and Iberia; completed uniform-wind controls reused.', flush=True)
    print('Estimated 15–30 minutes, one-hour cap, monthly checkpoints and same-command resume. No search, download or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_spatial_wind.py --run')
        return 0
    state = run(args.out, args.source)
    print('Status: '+state['status'], flush=True)
    return 0 if state['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
