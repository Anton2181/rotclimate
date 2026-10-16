"""User-run, cached-input 2.5-hour source/paired-weather diagnosis.

Twenty fixed cases; no search, downloads, changed climate physics or atlas export.
Default only prints a plan. --run executes with monthly checkpoints and resume.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import signal
import sys
import time
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from experiments import v10_water_sources as model
from scripts import review_v10_pressure_thermo as review
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
night = review.run.night
SEEDS = (41, 67, 103, 149, 211)


def source_id():
    digest = hashlib.sha256(review.run.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(review.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare():
    manifest, state, inputs, settings, _, records, seconds = review.load_verified(ROOT/'output/v10_pressure_thermo')
    jobs = [{'key': f'{region}_{mode}_s{seed}', 'region': region, 'wind': mode, 'seed': seed}
        for seed in SEEDS for region in ('california', 'iberia') for mode in ('uniform', 'spatial')]
    protocol = {'schema': 1, 'code_sha256': source_id(),
        'source_manifest_sha256': sha256(ROOT/'output/v10_pressure_thermo/manifest.json'),
        'source_state_sha256': sha256(ROOT/'output/v10_pressure_thermo/state.json'),
        'inputs': manifest['inputs'], 'settings': {k: asdict(v) for k,v in settings.items()},
        'jobs': jobs, 'sources': list(model.SOURCES), 'minimum_cycles': 3, 'maximum_cycles': 6,
        'spacing_km': 60, 'budget_hours': 2.5, 'downloads': False, 'atlas_publication': False,
        'intervention': 'Passive last-vapor-source diagnostics only. Frozen dry-theta water/energy/rain/soil/flow untouched. Five fixed storm seeds, paired within region across uniform/spatial background winds; no best-seed selection.',
        'source_policy': 'Incoming atmospheric boundary water, local ocean evaporation, latest land evaporation, initial vapor. Rain tags proportional to vapor at each layer/cell. Soil ancestry is deliberately reset on land evaporation. Explicit bounded numerical reconciliation.',
        'checks': 'Per-step/per-cycle source budgets, sums to unchanged water/rain, physical and source settling. At the original completed year seed-41 climate arrays must reproduce the saved pressure controls.',
        'reference_saved_minutes_four_cases': seconds/60,
        'limitations': 'Synthetic seed spread, not observed weather uncertainty or independent years. Source fractions alone do not establish a causal fix or import-to-land precipitation efficiency. No real weather covariance measurement.'}
    return protocol, inputs, settings, state['cases'], records


def validate_record(record, shape, completed=False):
    state, rain, temp, refs, tagged_rain, info = record
    night.validate_fields(state, rain, temp, refs, info, shape, completed)
    model.validate_tags(state)
    if tagged_rain.shape != (12, len(model.SOURCES))+shape or not np.isfinite(tagged_rain).all() or tagged_rain.min() < 0:
        raise ValueError('Invalid rain-source checkpoint.')
    if abs(tagged_rain.sum(1)-rain).max() > 1e-8:
        raise ValueError('Rain sources do not reproduce total rain.')
    sources = info['sources']
    if sources['names'] != list(model.SOURCES):
        raise ValueError('Source identity changed.')
    for key in model.TAG_KEYS:
        value = np.array(sources['totals'][key])
        if value.shape != (len(model.SOURCES),) or not np.isfinite(value).all():
            raise ValueError('Invalid source ledger.')
        if key != 'numerical_adjustment_mm' and value.min() < 0:
            raise ValueError('Negative gross source transfer.')
    initial = np.array(sources['initial_store_mm'])
    bounds = np.array([sources['max_step_error_mm'], sources['max_step_reconciliation_mm']])
    if initial.shape != (len(model.SOURCES),) or not np.isfinite(initial).all() or initial.min() < 0 or not np.isfinite(bounds).all() or (bounds < 0).any():
        raise ValueError('Invalid source checkpoint initial stores/tolerances.')
    if (bounds > 1e-9).any():
        raise ValueError('Source checkpoint exceeds step tolerances.')
    if completed:
        error = np.array(sources['annual_error_mm']);end = np.array(sources['end_store_mm'])
        measured_end = state.tags.sum(axis=(1, 2, 3))/state.soil.size
        ledger = sources['totals']
        recomputed = measured_end-initial-(np.array(ledger['import_mm'])-np.array(ledger['export_mm'])+
            np.array(ledger['evaporation_mm'])-np.array(ledger['rain_mm'])+np.array(ledger['numerical_adjustment_mm']))
        if error.shape != (len(model.SOURCES),) or end.shape != error.shape or not np.isfinite(error).all() or not np.isfinite(end).all() or (end < 0).any():
            raise ValueError('Invalid annual source budget.')
        if abs(error).max() > 1e-6 or not np.allclose(error, recomputed, atol=1e-10, rtol=0) or not np.allclose(end, measured_end, atol=1e-10, rtol=0):
            raise ValueError('Source checkpoint exceeds annual tolerance or disagrees with stores.')


def write_checkpoint(folder, year, record, completed=False):
    validate_record(record, record[0].soil.shape, completed)
    state, rain, temp, refs, tagged_rain, info = record
    stem = f'year{year}' if completed else f'year{year}_partial'
    meta = folder/(stem+'.json');previous = None
    if not completed and meta.exists():
        previous = json.loads(meta.read_text()).get('arrays')
    path = folder/(f'year{year}.npz' if completed else f'year{year}_m{info["month"]:02d}.npz')
    atomic_npz(path, water=state.water, energy=state.energy, soil=state.soil, tags=state.tags,
        rain=rain, temperature=temp, reference=refs, rain_by_source=tagged_rain)
    atomic_json(meta, {'year': year, 'arrays': path.name, 'array_sha256': sha256(path), 'info': info})
    if previous and previous != path.name and Path(previous).name == previous:
        (folder/previous).unlink(missing_ok=True)


def read_checkpoint(folder, year, shape, completed=False):
    stem = f'year{year}' if completed else f'year{year}_partial'
    meta = folder/(stem+'.json')
    if not meta.exists():
        return None
    row = json.loads(meta.read_text());name = row.get('arrays', '')
    if not name or Path(name).name != name or row.get('year') != year or sha256(folder/name) != row.get('array_sha256'):
        raise ValueError('Source checkpoint integrity mismatch.')
    with np.load(folder/name, allow_pickle=False) as arrays:
        record = (model.State(arrays['water'], arrays['energy'], arrays['soil'], arrays['tags']),
            arrays['rain'], arrays['temperature'], arrays['reference'], arrays['rain_by_source'], row['info'])
    validate_record(record, shape, completed)
    return record


def settling(previous, current, case, geometry):
    check = review.run.geometry_rules.settling(model.physical_record(previous), model.physical_record(current), case, geometry)
    tag_changes = {'source_store_p95_mm': float(np.percentile(abs(current[0].tags-previous[0].tags), 95)),
        'source_monthly_rain_p95_mm': float(np.percentile(abs(current[4]-previous[4])[:, :, case.score_mask], 95))}
    check['source_changes'] = tag_changes;check['source_limits'] = dict.fromkeys(tag_changes, 1.)
    check['physical_passed'] = check['passed']
    check['passed'] = check['passed'] and all(value <= 1. for value in tag_changes.values())
    return check


def verify_anchor(record, baseline):
    for a,b in zip(record[:4], baseline[:4]):
        if hasattr(a, 'water'):
            for field in ('water', 'energy', 'soil'):
                if not np.array_equal(getattr(a, field), getattr(b, field)):
                    raise ValueError('Passive tags changed a seed-41 physical state.')
        elif not np.array_equal(a, b):
            raise ValueError('Passive tags changed a seed-41 climate array.')


def source_summary(record, case):
    tagged_rain = record[4];all_rain = record[1]
    rows = {}
    for name, mask in (('scored_land', case.score_mask),
        ('coast', case.score_mask & (case.coast_distance_km < 150)),
        ('interior', case.score_mask & (case.coast_distance_km > 300))):
        if not mask.any():
            raise ValueError('Source analysis needs coast and interior masks.')
        annual = tagged_rain[:, :, mask].sum(0).mean(1)
        winter = tagged_rain[[0, 1, 2, 9, 10, 11]][:, :, mask].sum(0).mean(1)
        total = float(all_rain[:, mask].sum(0).mean())
        if abs(annual.sum()-total) > 1e-8:
            raise ValueError('Scored rain-source sum mismatch.')
        rows[name] = {'annual_rain_mm_by_source': dict(zip(model.SOURCES, annual.tolist())),
            'winter_rain_mm_by_source': dict(zip(model.SOURCES, winter.tolist())),
            'annual_rain_fraction_by_source': dict(zip(model.SOURCES, (annual/total).tolist())) if total > 0 else None}
    return {'rain': rows, 'atmospheric_budget_domain_mean': record[-1]['sources'],
        'note': 'Last vapor source. Land recycling resets soil ancestry. Source fractions and gross inflow are not a land precipitation efficiency or a causal attribution of model errors.'}


def run_case(folder, job, inputs, settings, baseline_rows, baseline_records, stop, log, progress):
    region, mode, seed = job['region'], job['wind'], job['seed']
    case, profile, g, air, wind = inputs[region];config = settings[mode]
    folder.mkdir(parents=True, exist_ok=True)
    identity = dict(job, settings=asdict(config), input_array_sha256=review.run.geometry_rules.array_id(review.run.input_arrays(g, air, wind)))
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Source experiment case changed.')
    if not (folder/'config.json').exists():
        atomic_json(folder/'config.json', identity)
    state = model.initial_state(case.domain, profile, config, g, air)
    previous = None;check = {'passed': False};anchor_checked = False
    old = region+'_'+mode
    for year in range(1, 7):
        record = read_checkpoint(folder, year, case.domain.land.shape, completed=True)
        if record is None:
            partial = read_checkpoint(folder, year, case.domain.land.shape)
            started = time.monotonic();before = partial[-1].get('elapsed_seconds', 0.) if partial else 0.
            def save(*record):
                info = dict(record[-1], elapsed_seconds=before+time.monotonic()-started)
                write_checkpoint(folder, year, (*record[:-1], info))
                progress(dict(case=job['key'], year=year, month=info['month'], elapsed_year_seconds=info['elapsed_seconds']))
                log(f'{job["key"]}: cycle {year}/6, month {info["month"]}/12')
            record = model.year(case.domain, profile, config, seed, state, air, case.score_mask,
                g, wind, checkpoint=partial, save_month=save, should_stop=stop, wind_mode=mode)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            write_checkpoint(folder, year, record, completed=True)
        if seed == 41 and year == baseline_rows[old]['years']:
            verify_anchor(record, baseline_records[old]);anchor_checked = True
        if previous is not None:
            check = settling(previous, record, case, g)
        state = record[0]
        minimum = max(3, baseline_rows[old]['years']) if seed == 41 else 3
        if year >= minimum and check['passed']:
            break
        previous = record
    summary = night.summarize(model.physical_record(record), case, check, year)
    summary.update(response=review.run.rain_vector(case, record[1]), sources=source_summary(record, case),
        seed=seed, wind=mode, anchor_reproduced=anchor_checked if seed == 41 else None,
        evidence_sha256={f'year{n}.{ext}': sha256(folder/f'year{n}.{ext}') for n in range(1, year+1) for ext in ('json', 'npz')})
    atomic_json(folder/'summary.json', summary)
    return summary


def report(out, state, protocol):
    lines = ['# Water sources and paired synthetic weather', '',
        f"Status: {state['status']}; {len(state['cases'])}/{len(protocol['jobs'])} cases complete.", '',
        'Fixed physics and parameters. Last-vapor-source tracers do not feed back into climate. '
        'No download, optimization, best-seed selection or atlas update.', '',
        '| Case | Rain / reference | Monthly MAE | Boundary / ocean / land share of land rain | Settled |',
        '|---|---:|---:|---|---|']
    for key, row in state['cases'].items():
        fractions = row['sources']['rain']['scored_land']['annual_rain_fraction_by_source']
        text = 'no rain' if fractions is None else ' / '.join(f'{fractions[k]:.0%}' for k in model.SOURCES[1:])
        lines.append(f"| {key} | {row['annual_rain_ratio']:.2f} | {row['score']:.2f} | {text} | {row['settling']['passed']} |")
    lines += ['', '## Completed matched wind contrasts', '',
        '| Region / storm seed | Spatial − uniform annual rain | Spatial − uniform coastal winter rain |',
        '|---|---:|---:|']
    for seed in SEEDS:
        for region in ('california', 'iberia'):
            keys = [f'{region}_{mode}_s{seed}' for mode in ('uniform', 'spatial')]
            if all(key in state['cases'] for key in keys):
                a,b = [state['cases'][key]['response'] for key in keys]
                lines.append(f"| {region} / {seed} | {b['annual_rain_mm']-a['annual_rain_mm']:+.1f} mm | {b['coast_winter_mm']-a['coast_winter_mm']:+.1f} mm |")
    lines += ['', 'Initial-vapor shares, coast/interior and winter source amounts, per-source '
        'gross import/export and physical budgets are in state.json and annual checkpoints. '
        'Land evaporation resets the source tag; this is not original molecular ancestry. '
        'Domain gross transport is not a regional precipitation efficiency. Five synthetic '
        'catalogues measure sensitivity to this generator, not actual weather uncertainty. '
        'Warm-up cycles and cells are not independent climate replicates. A partial batch '
        'is not the verdict from all five paired catalogues. Existing broad screens are '
        'reported, not used to pick a winner. No atlas promotion.']
    if state.get('error'):
        lines += ['', 'Stopped: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, case_runner=run_case, clock=time.monotonic):
    started = clock();deadline = started+2.5*3600
    protocol, inputs, settings, baseline_rows, baseline_records = prepare()
    if out.resolve() == (ROOT/'output/v10_pressure_thermo').resolve() or (ROOT/'output/v10_pressure_thermo').resolve() in out.resolve().parents:
        raise ValueError('Use a separate output directory to preserve pressure controls.')
    out.mkdir(parents=True, exist_ok=True)
    manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:
        raise ValueError('Water-source protocol changed; preserve results and use a new --out.')
    if not manifest.exists():
        atomic_json(manifest, protocol)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}, 'invocations': []}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous failure needs inspection before resuming.')
    state['status'] = 'running';interrupted = [False]
    handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
    invocation = {'started_utc': night.utc(), 'budget_hours': 2.5};state['invocations'].append(invocation)
    def stop():
        return interrupted[0] or clock() >= deadline
    def log(message):
        text = night.utc()+' '+message;print(text, flush=True)
        with (out/'run.log').open('a') as file:
            file.write(text+'\n')
    def progress(info):
        atomic_json(out/'progress.json', dict(info, updated_utc=night.utc(), completed_cases=len(state['cases']), planned_cases=len(protocol['jobs'])))
    try:
        report(out, state, protocol)
        for job in protocol['jobs']:
            if source_id() != protocol['code_sha256']:
                raise ValueError('Sources changed during water-source diagnosis.')
            key = job['key'];folder = out/'cases'/key
            if key in state['cases']:
                row = state['cases'][key]
                if json.loads((folder/'summary.json').read_text()) != row:
                    raise ValueError('Completed source summary changed.')
                for filename, digest in row['evidence_sha256'].items():
                    if Path(filename).name != filename or sha256(folder/filename) != digest:
                        raise ValueError('Completed source evidence changed.')
                continue
            if stop():
                raise model.base.BudgetStop()
            if shutil.disk_usage(out).free < 500*1024*1024:
                raise RuntimeError('Less than 500 MB free space; checkpoint preserved.')
            log(f'Start {key}; {(deadline-clock())/3600:.2f} hours left; {len(state["cases"])}/20 complete.')
            state['cases'][key] = case_runner(folder, job, inputs, settings, baseline_rows, baseline_records, stop, log, progress)
            report(out, state, protocol)
        state['status'] = 'complete'
    except model.base.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError, RuntimeError, FloatingPointError, OSError) as error:
        state['status'] = 'needs_diagnosis';state['error'] = str(error)
    finally:
        invocation.update(ended_utc=night.utc(), elapsed_seconds=clock()-started, status=state['status'])
        signal.signal(signal.SIGINT, handler);report(out, state, protocol)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_water_sources')
    args = parser.parse_args(argv)
    print('20 fixed cases: two regions × two wind backgrounds × five paired storm seeds; passive water-source tracers.', flush=True)
    print('Plan for 2–3 hours; stops at a 2.5-hour budget, with monthly checkpoints and same-command resume. May finish sooner.', flush=True)
    print('Cached inputs only. No NOAA requests, parameter search, changed climate physics or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_water_sources.py --run')
        return 0
    state = run(args.out)
    print('Status: '+state['status'], flush=True)
    return 0 if state['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
