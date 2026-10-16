"""User-run twelve-case five-layer vertical-structure experiment.

Default is read-only. Cached inputs, four saved controls, no search or atlas
export. Explicit dry/RH300 upper lids and an old-column-water matched control.
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
from experiments import v10_split_column as model, v10_forcing_audit as atmosphere
from scripts import review_v10_water_sources as review, audit_v10_source_forcing as audit
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256
night = review.run.night
geometry_rules = review.run.review.run.geometry_rules
VARIANTS = {'split_dry': {'lid': 'dry', 'boundary': 'reference'},
    'split_rh300': {'lid': 'rh300', 'boundary': 'reference'},
    'split_column_matched': {'lid': 'rh300', 'boundary': 'column_matched'}}


def source_id():
    digest = hashlib.sha256(review.run.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(review.__file__), Path(audit.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def input_arrays(g, air, profile, circulation):
    old_g, old_p, old_air, old_wind = circulation
    arrays = geometry_rules.geometry_arrays(g, air)
    arrays.update(profile_mixing_ratio=profile.mixing_ratio, profile_offsets=profile.offsets,
        profile_eastward=profile.eastward, profile_northward=profile.northward, profile_height=profile.height_m)
    arrays.update({'original_'+k:v for k,v in review.run.review.run.input_arrays(old_g, old_air, old_wind).items()})
    arrays['original_profile_mixing_ratio'] = old_p.mixing_ratio
    return arrays


def prepare():
    parent, state, original, _, _, _ = review.load_verified(ROOT/'output/v10_water_sources')
    _, _, settings, _, _ = review.run.prepare()
    texts, downloads = atmosphere.acquire(ROOT/'data/v10_atmosphere', fetch=False)
    fields = atmosphere.fields_from_cache(texts)
    inputs = {};baselines = {}
    for region, (case, profile, g, air, wind) in original.items():
        new_g, new_air = model.prepare_geometry(case, g, air, fields)
        circulation = (g, profile, air, wind)
        for lid in ('dry', 'rh300'):
            p = model.prepare_profile(case, profile, new_g, new_air, fields, lid)
            inputs[region+'_'+lid] = (case, p, new_g, new_air, circulation)
        for mode in settings:
            baselines[region+'_'+mode] = state['cases'][region+'_'+mode+'_s41']
    jobs = [{'key': f'{region}_{mode}_{variant}', 'region': region, 'wind': mode, 'variant': variant, 'seed': 41}
        for variant in VARIANTS for region in ('california', 'iberia') for mode in ('uniform', 'spatial')]
    protocol = {'schema': 1, 'code_sha256': source_id(),
        'parent_manifest_sha256': sha256(ROOT/'output/v10_water_sources/manifest.json'),
        'parent_state_sha256': sha256(ROOT/'output/v10_water_sources/state.json'),
        'baseline_evidence': {k:v['evidence_sha256'] for k,v in baselines.items()},
        'inputs': {key: geometry_rules.array_id(input_arrays(g, air, p, c)) for key, (_, p, g, air, c) in inputs.items()},
        'reference_downloads': downloads, 'settings': {k:asdict(v) for k,v in settings.items()},
        'variants': VARIANTS, 'jobs': jobs, 'seed': 41, 'split_pressure_pa': model.SPLIT_PA,
        'new_layer_pressures_pa': [45397.5, 15000.], 'spacing_km': 60,
        'minimum_cycles': 3, 'maximum_cycles': 6, 'budget_hours': 1.5,
        'circulation': 'Partition old upper horizontal flux by the two new dry masses, preserve lower fluxes/aggregate upper flux, derive interface exchange from continuity. Original four-layer projection retained; not new reference winds at 454/150 hPa.',
        'thermal': 'New upper temperature and annual mean height targets at the new pressures. Dry-theta transport, fixed pressure and explicit diagnosed flow work; unchanged microphysics and timescale groups (lowest two lower, all remaining upper).',
        'humidity': 'First three profile entries retained. 454 hPa offshore r from cached data. Above 300 hPa no humidity observations available: zero or offshore monthly RH300 retained at 150 hPa T/p. Sensitivity assumptions, not measured upper humidity.',
        'matched_control': 'After local saturation caps, scale all five boundary r values down to the original four-layer mass-weighted column vapor at the same cell/time. Never scale up. Matches column concentration, not wind-weighted boundary import. Initialization still uses the common 60%-saturation ceiling.',
        'diagnostics': 'Physical/rain/thermal/work/layer budgets, coastal/interior seasonal responses. Source tags not generalized in this first structural batch.',
        'downloads': False, 'atlas_publication': False}
    return protocol, inputs, settings, baselines


def validate_record(record, shape, count=5, completed=False):
    state, rain, temp, refs, info = record
    if state.water.shape != (count,)+shape or state.energy.shape != state.water.shape or state.soil.shape != shape:
        raise ValueError('Wrong split-column state shape.')
    if rain.shape != (12,)+shape or temp.shape != (12, count)+shape or refs.shape != temp.shape:
        raise ValueError('Wrong split-column monthly shape.')
    if not all(np.isfinite(a).all() for a in (state.water, state.energy, state.soil, rain, temp, refs)) or min(state.water.min(), state.soil.min(), rain.min()) < 0:
        raise ValueError('Invalid split-column fields.')
    if not isinstance(info['month'], int) or not 0 <= info['month'] <= 12:
        raise ValueError('Invalid split-column checkpoint month.')
    bounds = np.array([info[k] for k in ('maxw', 'maxe', 'continuity')])
    if not np.isfinite(bounds).all() or (bounds < 0).any() or (bounds > np.array([1e-9, 1e-5, 1e-10])).any() or not np.isfinite(list(info['totals'].values())).all() or not np.isfinite([info[k] for k in ('initial_water', 'initial_energy', 'steps')]).all():
        raise ValueError('Split-column physical checks failed.')
    diag = info['diagnostics']
    if diag['processes'] != list(model.PROCESSES) or np.shape(diag['layer_rain_scored_land_mm']) != (12, count) or np.shape(diag['temperature_changes_scored_land_c']) != (12, len(model.PROCESSES), count):
        raise ValueError('Split-column process shapes/identity changed.')
    if not np.isfinite(diag['layer_rain_scored_land_mm']).all() or not np.isfinite(diag['temperature_changes_scored_land_c']).all() or not np.isfinite(diag['max_step_temperature_ledger_error_c']) or diag['max_step_temperature_ledger_error_c'] > 1e-9:
        raise ValueError('Invalid split-column process ledger.')
    if completed:
        b = info['budget']
        if info['month'] != 12 or not np.isfinite(list(b.values())).all() or abs(b['annual_water_error_mm']) > 1e-6 or abs(b['annual_energy_error_j_m2']) > 1:
            raise ValueError('Split-column annual ledger failed.')


def write_checkpoint(folder, year, record, completed=False):
    validate_record(record, record[0].soil.shape, len(record[0].water), completed)
    state, rain, temp, refs, info = record
    stem = f'year{year}' if completed else f'year{year}_partial'
    meta = folder/(stem+'.json');previous = None
    if not completed and meta.exists():
        previous = json.loads(meta.read_text()).get('arrays')
    path = folder/(f'year{year}.npz' if completed else f'year{year}_m{info["month"]:02d}.npz')
    atomic_npz(path, water=state.water, energy=state.energy, soil=state.soil, rain=rain, temperature=temp, reference=refs)
    atomic_json(meta, {'year': year, 'arrays': path.name, 'array_sha256': sha256(path), 'info': info})
    if previous and previous != path.name and Path(previous).name == previous:
        (folder/previous).unlink(missing_ok=True)


def read_checkpoint(folder, year, shape, count=5, completed=False):
    stem = f'year{year}' if completed else f'year{year}_partial'
    meta = folder/(stem+'.json')
    if not meta.exists():
        return None
    row = json.loads(meta.read_text());name = row.get('arrays', '')
    if not name or Path(name).name != name or row.get('year') != year or sha256(folder/name) != row.get('array_sha256'):
        raise ValueError('Split-column checkpoint integrity mismatch.')
    with np.load(folder/name, allow_pickle=False) as a:
        record = (model.base.State(a['water'], a['energy'], a['soil']), a['rain'], a['temperature'], a['reference'], row['info'])
    validate_record(record, shape, count, completed)
    return record


def settling(previous, current, case, geometry):
    old, op, ot, _, _ = previous;new, p, t, _, _ = current;mask = case.score_mask
    values = {'monthly_rain_p95_mm': float(np.percentile(abs(p-op)[:, mask], 95)),
        'annual_rain_p95_mm': float(np.percentile(abs((p-op).sum(0))[mask], 95)),
        'water_store_p95_mm': max(float(np.percentile(abs(new.water[k]-old.water[k]), 95)) for k in range(len(geometry.mass))),
        'soil_p95_mm': float(np.percentile(abs(new.soil-old.soil), 95)),
        'monthly_temperature_p95_c': float(np.percentile(abs(t-ot)[:, :, mask], 95)),
        'end_temperature_p95_c': float(np.percentile(abs(model.base.temperature(new.energy, geometry.mass, new.water, geometry.height_m)-model.base.temperature(old.energy, geometry.mass, old.water, geometry.height_m)), 95))}
    limits = dict(zip(values, (1., 5., 1., 1., .05, .05)))
    return {'passed': all(v <= limits[k] for k,v in values.items()), 'changes': values, 'limits': limits}


def run_case(folder, job, inputs, settings, stop, log, progress):
    variant = VARIANTS[job['variant']];key = job['region']+'_'+variant['lid']
    case, profile, g, air, circulation = inputs[key];s = settings[job['wind']]
    folder.mkdir(parents=True, exist_ok=True)
    identity = dict(job, variant=variant, settings=asdict(s), input_array_sha256=geometry_rules.array_id(input_arrays(g, air, profile, circulation)))
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Split-column case changed.')
    if not (folder/'config.json').exists():
        atomic_json(folder/'config.json', identity)
    state = model.initial_state(case.domain, profile, s, g, air, variant['boundary'], circulation)
    previous = None;check = {'passed': False}
    for year in range(1, 7):
        record = read_checkpoint(folder, year, case.domain.land.shape, completed=True)
        if record is None:
            partial = read_checkpoint(folder, year, case.domain.land.shape)
            started = time.monotonic();before = partial[-1].get('elapsed_seconds', 0.) if partial else 0.
            def save(*record):
                info = dict(record[-1], elapsed_seconds=before+time.monotonic()-started)
                write_checkpoint(folder, year, (*record[:4], info))
                progress(dict(case=job['key'], year=year, month=info['month'], elapsed_year_seconds=info['elapsed_seconds']))
                log(f'{job["key"]}: cycle {year}/6, month {info["month"]}/12')
            record = model.year(case.domain, profile, s, 41, state, air, case.score_mask, g, circulation[3],
                checkpoint=partial, save_month=save, should_stop=stop, wind_mode=job['wind'],
                boundary_mode=variant['boundary'], circulation=circulation)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            write_checkpoint(folder, year, record, completed=True)
        if previous is not None:
            check = settling(previous, record, case, g)
        state = record[0]
        if year >= 3 and check['passed']:
            break
        previous = record
    row = night.summarize(record, case, check, year)
    row.update(response=review.run.review.run.rain_vector(case, record[1]),
        evidence_sha256={f'year{n}.{ext}': sha256(folder/f'year{n}.{ext}') for n in range(1, year+1) for ext in ('json', 'npz')})
    atomic_json(folder/'summary.json', row)
    return row


def report(out, state, protocol, baselines):
    lines = ['# Controlled five-layer upper-column split', '',
        f"Status: {state['status']}; {len(state['cases'])}/{len(protocol['jobs'])} new cases complete. Atlas unchanged.", '',
        '| Case | Old → new rain MAE | Old → new rain/reference | Coastal winter rain | Settled | Broad screen |',
        '|---|---:|---:|---:|---|---|']
    for key, row in state['cases'].items():
        region, mode, _ = key.split('_', 2);old = baselines[region+'_'+mode]
        lines.append(f"| {key} | {old['score']:.2f} → {row['score']:.2f} | {old['annual_rain_ratio']:.2f} → {row['annual_rain_ratio']:.2f} | {row['response']['coast_winter_mm']:.1f} mm | {row['settling']['passed']} | {row['eligible']} |")
    lines += ['', 'Three fixed hypotheses: dry above 300 hPa; offshore RH300 retained at '
        '150 hPa; the latter with boundary column vapor concentration matched to the '
        'old four-layer value after saturation caps. Upper humidity assumptions are '
        'not observations. Matched column concentration does not guarantee identical '
        'wind-weighted inflow. Lower/aggregate upper horizontal circulation is retained; '
        'the new internal interface and thermal/moisture structure are resolved.', '',
        'Temperature remains reference-informed, momentum is prescribed and flow work '
        'is diagnosed. Existing broad screens are development evidence, not climate '
        'validation. Read source input/protocol, thermal/layer/work budgets and '
        'coastal/interior seasonal responses together. No automatic selection or '
        'atlas publication; original source-tag evidence is preserved.']
    if state.get('error'):
        lines += ['', 'Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json', state)
    (out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out, case_runner=run_case, clock=time.monotonic):
    deadline = clock()+1.5*3600
    protocol, inputs, settings, baselines = prepare()
    parent = ROOT/'output/v10_water_sources'
    if out.resolve() == parent.resolve() or parent.resolve() in out.resolve().parents:
        raise ValueError('Choose separate output to preserve source-water evidence.')
    out.mkdir(parents=True, exist_ok=True);manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:
        raise ValueError('Split-column protocol changed; preserve output and use a new --out.')
    if not manifest.exists():
        atomic_json(manifest, protocol)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous split-column failure needs inspection.')
    state['status'] = 'running';interrupted = [False]
    handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
    def stop():
        return interrupted[0] or clock() >= deadline
    def log(message):
        text = night.utc()+' '+message;print(text, flush=True)
        with (out/'run.log').open('a') as file:
            file.write(text+'\n')
    def progress(info):
        atomic_json(out/'progress.json', dict(info, updated_utc=night.utc(), completed_cases=len(state['cases']), planned_cases=len(protocol['jobs'])))
    try:
        report(out, state, protocol, baselines)
        for job in protocol['jobs']:
            if source_id() != protocol['code_sha256']:
                raise ValueError('Sources changed during the split-column experiment.')
            key = job['key'];folder = out/'cases'/key
            if key in state['cases']:
                row = state['cases'][key]
                if json.loads((folder/'summary.json').read_text()) != row:
                    raise ValueError('Completed split-column summary changed.')
                for name, digest in row['evidence_sha256'].items():
                    if Path(name).name != name or sha256(folder/name) != digest:
                        raise ValueError('Completed split-column evidence changed.')
                continue
            if stop():
                raise model.base.BudgetStop()
            input_key = job['region']+'_'+VARIANTS[job['variant']]['lid']
            _, p, g, air, c = inputs[input_key];arrays = input_arrays(g, air, p, c)
            input_path = out/'inputs'/(input_key+'.npz')
            if input_path.exists():
                with np.load(input_path, allow_pickle=False) as a:
                    if set(a.files) != set(arrays) or geometry_rules.array_id({k:a[k] for k in a.files}) != protocol['inputs'][input_key]:
                        raise ValueError('Saved split-column inputs changed.')
            else:
                atomic_npz(input_path, **arrays)
            log(f'Start {key}; {(deadline-clock())/3600:.2f} hours left in this invocation.')
            row = case_runner(folder, job, inputs, settings, stop, log, progress)
            if source_id() != protocol['code_sha256']:
                raise ValueError('Sources changed while computing a split-column case.')
            state['cases'][key] = row;report(out, state, protocol, baselines)
        state['status'] = 'complete'
    except model.base.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError, RuntimeError, FloatingPointError, OSError) as error:
        state['status'] = 'needs_diagnosis';state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT, handler);report(out, state, protocol, baselines)
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_split_column')
    args = parser.parse_args(argv)
    print('12 new five-layer cases; dry/RH300 upper lids and a column-water matched control; four saved four-layer controls reused.', flush=True)
    print('Estimated 45–75 minutes; 90-minute invocation budget, monthly checkpoints and same-command resume.', flush=True)
    print('Cached inputs only; no NOAA access, parameter optimization or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_split_column.py --run')
        return 0
    state = run(args.out);print('Status: '+state['status'], flush=True)
    return 0 if state['status'] in ('complete', 'interrupted', 'budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
