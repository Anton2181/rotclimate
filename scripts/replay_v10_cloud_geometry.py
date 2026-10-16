"""User-run exact replays diagnosing moist ascent and cloud formation geometry."""
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

from experiments import v10_cloud_geometry as model
from scripts import check_v10_spatial_humidity as parent, review_v10_spatial_humidity as review
from scripts import check_v10_split_column as checkpoints, check_v10_event_forcing as event
from scripts import afternoon_v10_delivery as forcing, plot_v10_koppen as maps
from scripts.review_v10_storm_delivery import WINTER, SUMMER
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256

SOURCE = ROOT/'output/v10_spatial_humidity'
PREFLIGHT = ROOT/'output/v10_cloud_geometry_preflight'
BUDGET = 45*60.


def source_id():
    h = hashlib.sha256(parent.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(review.__file__)):
        h.update(path.read_bytes())
    return h.hexdigest()


def prepare():
    prepared = parent.prepare()
    old, inputs, setting, original_initials, original_finals, originals, profiles = prepared
    _, state, _, _, records, _, _, _, _ = review.load_verified(SOURCE, prepared)
    jobs = []; initials = {}; finals = {}
    for region, (case, p, g, air, circulation) in inputs.items():
        for variant in ('uniform', 'local_matched'):
            key = region+'_'+variant
            source_key = ('control_' if variant == 'uniform' else 'test_')+region+'_parcel_lower_'+variant
            n = state['cases'][source_key]['years']
            job = {'key': key, 'region': region, 'variant': variant, 'mode': 'parcel_lower', 'source_case': source_key, 'source_year': n}
            jobs.append(job); finals[key] = records[source_key]
            initials[key] = original_initials[region+'_parcel_lower'] if n == 1 else checkpoints.read_checkpoint(SOURCE/'cases'/source_key, n-1, case.domain.land.shape, completed=True)[0]
    tables = {region: forcing.read_calendar(parent.PREFLIGHT/'forcing'/region, parent.forcing_identity(old, region))[0] for region in inputs}
    protocol = {'schema': 1, 'code_sha256': source_id(), 'source_code_sha256': old['code_sha256'],
        'source_manifest_sha256': sha256(SOURCE/'manifest.json'), 'source_state_sha256': sha256(SOURCE/'state.json'),
        'jobs': jobs, 'settings': asdict(setting), 'metrics': list(model.METRICS), 'budget_seconds': BUDGET,
        'reproduction': 'Four exact final-year lower-interface cloud replays, each from its saved preceding-year state; no warm-up or new candidate climate.',
        'forcing': 'Same seed67 lift16 aligned dry flow and monthly-input-matched humidity as the completed parent. Uniform and local-matched remain paired.',
        'interpretation': 'Diagnose actual upward vapor, rain by interface, saturation onset relative to the true layer face, and pre-step environmental RH/T. Above-face onset is not a failure criterion or alternate climate. Gross upward vapor may recirculate.',
        'selection': 'Process diagnosis only. No new physics, fitted coefficient, best-seed selection or atlas promotion.',
        'downloads': False, 'atlas_publication': False}
    return protocol, inputs, setting, initials, finals, originals, tables


def write_checkpoint(folder, record, collector, completed=False):
    checkpoints.validate_record(record, collector.domain.land.shape, completed=completed)
    collector.validate_months(record[-1]['month'], record[0].water, record[1])
    meta = folder/('year1.json' if completed else 'year1_partial.json')
    previous = json.loads(meta.read_text()).get('arrays') if meta.exists() and not completed else None
    name = 'year1.npz' if completed else f'year1_m{record[-1]["month"]:02d}.npz'
    state, rain, temperature, reference, info = record
    arrays = dict(water=state.water, energy=state.energy, soil=state.soil, rain=rain, temperature=temperature, reference=reference)
    arrays.update({'geometry_'+key: value for key, value in collector.arrays.items()})
    atomic_npz(folder/name, **arrays)
    atomic_json(meta, {'year': 1, 'arrays': name, 'array_sha256': sha256(folder/name), 'info': info})
    if previous and previous != name and Path(previous).name == previous:
        (folder/previous).unlink(missing_ok=True)


def read_checkpoint(folder, case, g, setting, profile, air, completed=False):
    record = checkpoints.read_checkpoint(folder, 1, case.domain.land.shape, completed=completed)
    if record is None:
        return None, None
    meta = json.loads((folder/('year1.json' if completed else 'year1_partial.json')).read_text())
    with np.load(folder/meta['arrays'], allow_pickle=False) as a:
        saved = {key[9:]: a[key] for key in a.files if key.startswith('geometry_')}
    collector = model.Collector(case.domain, g, setting, profile, air, saved=saved)
    collector.validate_months(record[-1]['month'], record[0].water, record[1])
    return record, collector


def summarize(folder, job, case, record, collector):
    target = maps.classify_months(case.domain.temperature_c, case.observed_rain_mm, case.score_mask)
    masks = {'domain': np.ones(case.domain.land.shape, bool), 'scored_land': case.score_mask, **review.cloud.groups_for(case, target)}
    row = collector.summary(masks, WINTER, SUMMER)
    scored = np.array(row['regions']['scored_land']['monthly_by_interface']['parcel_rain_mm'])
    if not np.allclose(scored, np.array(record[-1]['parcel_rain_scored_land_mm'])[:, 1:4], atol=1e-9, rtol=0):
        raise ValueError('Passive interface rain disagrees with the original physical ledger.')
    row.update(physical_reproduction_exact=True, source_case=job['source_case'], source_year=job['source_year'],
        elapsed_seconds=record[-1]['elapsed_seconds'], case_config_sha256=sha256(folder/'config.json'),
        evidence_sha256={name: sha256(folder/name) for name in ('year1.json', 'year1.npz')})
    return row


def replay_case(folder, job, inputs, setting, initials, finals, originals, tables, stop, log, progress, code_id):
    key = job['key']; region = job['region']; case, p, g, air, circulation = inputs[region]
    folder.mkdir(parents=True, exist_ok=True)
    identity = {**job, 'code_sha256': code_id}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Cloud geometry replay changed.')
    if not (folder/'config.json').exists():
        atomic_json(folder/'config.json', identity)
    record, collector = read_checkpoint(folder, case, g, setting, p, air, completed=True)
    driver = parent.boundary.Driver(originals[region], tables[region], job['variant'], case, p, setting, g, air, circulation)
    if record is None:
        partial, collector = read_checkpoint(folder, case, g, setting, p, air)
        if collector is None:
            collector = model.Collector(case.domain, g, setting, p, air)
        if partial is not None:
            event.validate_control_record(partial, driver.monthly_targets)
        started = time.monotonic(); prior = partial[-1].get('elapsed_seconds', 0.) if partial else 0.
        def save(*record):
            if source_id() != code_id:
                raise ValueError('Cloud geometry sources changed during replay.')
            info = dict(record[-1], elapsed_seconds=prior+time.monotonic()-started)
            write_checkpoint(folder, (*record[:4], info), collector)
            progress({'case': key, 'month': info['month'], 'elapsed_case_seconds': info['elapsed_seconds']})
            log(f'{key}: month {info["month"]}/12; passive cloud-path measurements saved')
        record = model.physical.year(case.domain, p, setting, initials[key], air, case.score_mask, g, driver,
            checkpoint=partial, save_month=save, should_stop=stop, condensation_mode='parcel_lower', collector=collector)
        record[-1]['elapsed_seconds'] = prior+time.monotonic()-started
        write_checkpoint(folder, record, collector, completed=True)
    event.validate_control_record(record, driver.monthly_targets)
    forcing.replay.verify_physical(record, finals[key])
    review.verify_fields(record, initials[key], case, g, 'parcel_lower')
    row = summarize(folder, job, case, record, collector)
    atomic_json(folder/'summary.json', row)
    return row


def report(out, state):
    lines = ['# Passive cloud-geometry replays', '', f"Status: {state['status']}; {len(state['cases'])}/4 exact final-year replays. Atlas unchanged.", '',
        '| Case | Coastal winter rain | Arid summer parcel rain | Of that rain: saturation first above layer face | Into pre-step RH <70% air |',
        '|---|---:|---:|---:|---:|']
    for key, row in state['cases'].items():
        coast = row['regions']['coast']['winter']; arid = row['regions']['reference_arid']['summer']
        percent = lambda value: f'{value:.1%}' if value is not None else 'no parcel rain'
        lines.append(f"| {key} | {coast['total_rain_mm']:.2f} mm | {arid['parcel_rain_mm']:.2f} mm | {percent(arid['parcel_rain_first_saturation_above_face_fraction'])} | {percent(arid['parcel_rain_dry_pre_step_recipient_fraction'])} |")
    lines += ['', 'These are passive subsets of actual condensate, not changed climates. Above-face onset diagnoses dependence on the finite layer path; it is not proof of incorrect transport. Upward-vapor sums may recount water, and pre-step receiver RH is not in-cloud RH. Check seasonal/interface details before choosing a physical change.']
    if state.get('error'):
        lines += ['', 'Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json', state); (out/'summary.md').write_text('\n'.join(lines)+'\n')


def protected_paths():
    return (SOURCE, PREFLIGHT, parent.PREFLIGHT, parent.SOURCE, parent.replay.PREFLIGHT, parent.replay.SOURCE, parent.run.SOURCE, parent.run.PREFLIGHT)


def batch(out, case_runner=replay_case, clock=time.monotonic):
    started = clock(); deadline = started+BUDGET
    protocol, inputs, setting, initials, finals, originals, tables = prepare()
    if json.loads((PREFLIGHT/'manifest.json').read_text())['protocol'] != protocol:
        raise ValueError('Cloud geometry preflight is stale.')
    for protected in protected_paths():
        a, b = out.resolve(), protected.resolve()
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('Preserve parent evidence and prepared forcing.')
    out.mkdir(parents=True, exist_ok=True); manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:
        raise ValueError('Cloud geometry protocol changed; preserve output and use a separate --out.')
    if not manifest.exists():
        atomic_json(manifest, protocol)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous cloud geometry failure needs inspection.')
    state['status'] = 'running'; interrupted = [False]
    handler = signal.signal(signal.SIGINT, lambda *_: interrupted.__setitem__(0, True))
    stop = lambda: interrupted[0] or clock() >= deadline
    def log(message):
        message = checkpoints.night.utc()+' '+message; print(message, flush=True)
        with (out/'run.log').open('a') as f:
            f.write(message+'\n')
    def progress(info):
        atomic_json(out/'progress.json', dict(info, updated_utc=checkpoints.night.utc(), completed_jobs=len(state['cases']), planned_jobs=4, elapsed_invocation_seconds=clock()-started))
    try:
        report(out, state)
        for job in protocol['jobs']:
            if source_id() != protocol['code_sha256']:
                raise ValueError('Cloud geometry sources changed.')
            folder = out/'cases'/job['key']
            if job['key'] in state['cases']:
                forcing.verify_completed(folder, state['cases'][job['key']]); continue
            if stop():
                raise model.base.BudgetStop()
            log('Start '+job['key'])
            row = case_runner(folder, job, inputs, setting, initials, finals, originals, tables, stop, log, progress, protocol['code_sha256'])
            if source_id() != protocol['code_sha256']:
                raise ValueError('Sources changed while completing cloud geometry replay.')
            state['cases'][job['key']] = row; report(out, state)
        state['status'] = 'complete'
    except model.base.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError, RuntimeError, FloatingPointError, OSError) as error:
        state['status'] = 'needs_diagnosis'; state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT, handler); report(out, state); progress({'status': state['status']})
    return state


def preflight():
    protocol, inputs, setting, initials, finals, originals, tables = prepare(); checks = []
    for job in protocol['jobs']:
        region = job['region']; case, p, g, air, circulation = inputs[region]; before = initials[job['key']]
        driver = parent.boundary.Driver(originals[region], tables[region], job['variant'], case, p, setting, g, air, circulation)
        flow, humidity, _ = driver.at(0.); dt = min(60., model.base.stable_step(flow, g.mass, case.domain))
        result = model.physics.advance(before, case.domain, p, setting, flow, dt, 0., air, geometry=g, boundary=humidity, condensation_mode='parcel_lower')
        collector = model.Collector(case.domain, g, setting, p, air)
        physical_before = [array.copy() for array in (before.water, before.energy, before.soil, result[0].water, result[0].energy, result[0].soil, result[5], result[8])]
        collector.add(before, result[0], result[5], result[8], flow, humidity, result[4], dt, 0.)
        for old, actual in zip(physical_before, (before.water, before.energy, before.soil, result[0].water, result[0].energy, result[0].soil, result[5], result[8])):
            np.testing.assert_array_equal(old, actual)
        np.testing.assert_array_equal(collector.arrays['layer_rain'][0], result[5])
        np.testing.assert_array_equal(collector.arrays['metrics'][0, 2], result[8][1:4])
        checks.append({'key': job['key'], 'dt_s': dt, 'physical_arrays_unchanged': True, 'parcel_rain_reconstructed_exactly': True,
            'water_error_mm': result[4]['water_error_mm'], 'energy_error_j_m2': result[4]['energy_error_j_m2'], 'temperature_ledger_error_c': result[7]})
    if source_id() != protocol['code_sha256']:
        raise ValueError('Cloud geometry sources changed during preflight.')
    data = {'protocol': protocol, 'checks': checks, 'new_real_annual_integrations_started': 0, 'new_downloads': 0, 'atlas_updated': False}
    path = PREFLIGHT/'manifest.json'
    if path.exists() and json.loads(path.read_text()) != data:
        raise ValueError('Preserve existing cloud geometry preflight.')
    if not path.exists():
        atomic_json(path, data)
    print('Cloud geometry ready: four independent <=60-second probes, no annual integration.')
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true'); parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_cloud_geometry')
    args = parser.parse_args(argv)
    if args.preflight:
        preflight(); return 0
    print('Four exact final-year diagnostic replays. Estimated 10–25 minutes; 45-minute invocation cap, monthly resume. No search, downloads or atlas update.', flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/replay_v10_cloud_geometry.py --run'); return 0
    state = batch(args.out); print('Status: '+state['status'])
    return 1 if state['status'] == 'needs_diagnosis' else 0


if __name__ == '__main__':
    raise SystemExit(main())
