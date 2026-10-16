"""User-run matched-import event experiment. Default is a read-only plan."""
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
from experiments import v10_event_forcing as model
from scripts import check_v10_split_column as parent, review_v10_split_column as review
from scripts import audit_v10_event_fronts as fronts, plot_v10_koppen as koppen_maps
from rotclimate_v10.earth import atomic_json, sha256
PREFLIGHT = ROOT/'output/v10_event_preflight_lift16'
POWER_AUDIT = ROOT/'output/v10_event_preflight/lifting_power_audit.json'
BUDGET_HOURS = 2.


def source_id():
    digest = hashlib.sha256(parent.source_id().encode())
    for path in (Path(__file__), Path(model.__file__), Path(fronts.__file__), Path(review.__file__),
                 ROOT/'scripts/preflight_v10_event_forcing.py', Path(koppen_maps.__file__), Path(koppen_maps.koppen.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def load_inputs():
    audit = json.loads(POWER_AUDIT.read_text())
    if audit.get('selected_dose') != model.AMPLITUDES[1] or audit.get('state_advances') != 0:
        raise ValueError('The chosen lifting contrast does not match its forcing-only design audit.')
    protocol,state,original,settings,_,records,_,_,_ = review.load_verified(ROOT/'output/v10_split_column')
    inputs = {region: original[region+'_dry'] for region in ('california', 'iberia')}
    baselines = {region: state['cases'][region+'_spatial_split_dry'] for region in inputs}
    anchors = {region: records[region+'_spatial_split_dry'] for region in inputs}
    identity = {'code_sha256': source_id(),
        'lifting_contrast_audit_sha256': sha256(POWER_AUDIT),
        'parent_manifest_sha256': sha256(ROOT/'output/v10_split_column/manifest.json'),
        'parent_state_sha256': sha256(ROOT/'output/v10_split_column/state.json'),
        'inputs': {region: parent.geometry_rules.array_id(parent.input_arrays(g, air, p, c)) for region,(_,p,g,air,c) in inputs.items()},
        'settings': asdict(settings['spatial']), 'seed': 41}
    return identity,inputs,settings['spatial'],baselines,anchors


def prepare(preflight=PREFLIGHT):
    identity,inputs,setting,baselines,anchors = load_inputs()
    ready = json.loads((preflight/'manifest.json').read_text())
    if ready.get('identity') != identity or not ready.get('verified'):
        raise ValueError('Event preflight is stale or incomplete; preserve evidence and rerun the short preflight.')
    calendars = {}
    for region,(_,p,g,air,c) in inputs.items():
        path = preflight/(region+'.npz')
        if sha256(path) != ready['forcing_file_sha256'][region]:
            raise ValueError('Prepared event calendar hash changed.')
        with np.load(path, allow_pickle=False) as a:
            values = {k:a[k] for k in a.files}
        if parent.geometry_rules.array_id(values) != ready['forcing_array_sha256'][region]:
            raise ValueError('Prepared forcing array identity changed.')
        if not np.array_equal(values['times'], np.arange(0., model.EDGES[-1], model.INTERVAL)) or not np.array_equal(values['edges'], model.EDGES):
            raise ValueError('Prepared forcing clock changed.')
        mask = model.boundary_mask(g.mass.shape[1:])
        if not np.array_equal(values['boundary_mask'], mask):
            raise ValueError('Prepared boundary mask changed.')
        for amp in model.AMPLITUDES:
            for timing in model.TIMINGS:
                q = values['boundary_'+model.variant_key(amp,timing)]
                if q.shape != (len(values['times']), 5, mask.sum()) or not np.isfinite(q).all() or (q < 0).any() or q[:, 4].any():
                    raise ValueError('Invalid prepared dry-upper boundary water.')
        calendars[region] = values
    jobs = [{'key': region+'_lift1_steady', 'region': region, 'amplitude': 1., 'timing': 'steady', 'anchor': True} for region in inputs]
    jobs += [{'key': region+'_'+model.variant_key(amp,timing), 'region': region, 'amplitude': amp, 'timing': timing, 'anchor': False}
        for amp in model.AMPLITUDES for timing in model.TIMINGS for region in inputs if (amp,timing) != (1.,'steady')]
    protocol = {'schema': 1, **identity, 'preflight_manifest_sha256': sha256(preflight/'manifest.json'),
        'forcing_array_sha256': ready['forcing_array_sha256'], 'forcing_file_sha256': ready['forcing_file_sha256'],
        'jobs': jobs, 'minimum_cycles': 3, 'maximum_cycles': 6, 'budget_hours': BUDGET_HOURS,
        'forcing_interval_seconds': model.INTERVAL, 'lifting_fluctuation_amplitudes': list(model.AMPLITUDES),
        'nominal_moisture_pulse_amplitude': model.PULSE_AMPLITUDE, 'upper_humidity': 'Zero prescribed incoming water above 300 hPa; an explicit assumption, not observed.',
        'circulation_control': 'Original full circulation plus (amplitude-1) times convergence-only anomaly about its exact monthly face mean. Original rotation, catalogue and mean circulation retained.',
        'moisture_control': 'Same monthly gross incoming vapor in every case, verified after saturation caps and again in each integrated month. Boundary r held at each 3-hour tick. Concentration means and variance are diagnosed, not matched.',
        'timing_control': 'At each boundary cell, moisture follows positive convergence-only storm ascent there. A within-month half-window shift preserves identical nominal pulse values per cell. Caps and gross-dose normalization alter actual humidity distributions; a timing sensitivity, not a pure covariance isolation or observed front.',
        'anchor_guard': {'monthly_rain_p95_mm': 1., 'annual_rain_p95_mm': 5., 'monthly_mae_change_mm': .1,
            'annual_mean_change_limit': 'max(1 mm, 2% of frozen control annual mean)', 'coastal_winter_change_limit': 'max(1 mm, 2% of frozen control coastal winter)'},
        'selection': 'No automatic climate selection. Coastal/interior seasonal response, fixed-T Koppen, gross input/export and physical/thermal/work budgets; average error alone is insufficient.',
        'downloads': False, 'atlas_publication': False}
    return protocol,inputs,setting,baselines,anchors,calendars


def validate_control_record(record, monthly_targets):
    info = record[-1];d = info['diagnostics'];month = info['month']
    actual = np.array(d['monthly_boundary_import_gross_mm']);expected = np.array(d['monthly_boundary_import_target_mm'])
    if actual.shape != (12,) or not np.isfinite(actual).all() or (actual < 0).any() or not np.array_equal(expected, monthly_targets):
        raise ValueError('Saved event dose-control identity changed.')
    if not np.allclose(actual[:month], expected[:month], atol=1e-7, rtol=0) or np.any(actual[month:]):
        raise ValueError('Saved integrated monthly import control failed.')
    if abs(actual.sum()-info['totals']['boundary_import_gross_mm']) > 1e-7:
        raise ValueError('Saved monthly and accumulated gross import disagree.')


def compare_anchor(record, baseline_record, baseline, case):
    p,old = record[1],baseline_record[1];mask = case.score_mask
    r = parent.review.run.review.run.rain_vector(case,p)
    changes = {'monthly_rain_p95_mm': float(np.percentile(abs(p-old)[:,mask],95)),
        'annual_rain_p95_mm': float(np.percentile(abs((p-old).sum(0))[mask],95)),
        'monthly_mae_change_mm': abs(r['monthly_mae_mm']-baseline['score']),
        'annual_mean_change_mm': abs(r['annual_rain_mm']-baseline['response']['annual_rain_mm']),
        'coastal_winter_change_mm': abs(r['coast_winter_mm']-baseline['response']['coast_winter_mm'])}
    limits = {'monthly_rain_p95_mm': 1., 'annual_rain_p95_mm': 5., 'monthly_mae_change_mm': .1,
        'annual_mean_change_mm': max(1., .02*baseline['response']['annual_rain_mm']),
        'coastal_winter_change_mm': max(1., .02*baseline['response']['coast_winter_mm'])}
    return {'passed': all(changes[k] <= limits[k] for k in changes), 'changes': changes, 'limits': limits,
        'note': 'Checks the new held-boundary-water discretization against the frozen continuously interpolated boundary. Not an exact annual reproduction or climate-validation claim.'}


def run_case(folder, job, inputs, setting, baseline, anchor, calendar, stop, log, progress, code_id):
    case,profile,g,air,circulation = inputs[job['region']]
    folder.mkdir(parents=True,exist_ok=True)
    identity = {**job, 'settings': asdict(setting), 'seed': 41,
        'input_sha256': parent.geometry_rules.array_id(parent.input_arrays(g,air,profile,circulation)),
        'forcing_array_sha256': parent.geometry_rules.array_id(calendar)}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Event-forcing case identity changed.')
    if not (folder/'config.json').exists():
        atomic_json(folder/'config.json',identity)
    driver = model.Driver(calendar,case,profile,setting,g,air,circulation,job['amplitude'],job['timing'])
    state = model.core.initial_state(case.domain,profile,setting,g,air)
    previous = None;check = {'passed': False}
    for year in range(1,7):
        if source_id() != code_id:
            raise ValueError('Sources changed during the event-forcing case.')
        record = parent.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
        if record is None:
            partial = parent.read_checkpoint(folder,year,case.domain.land.shape)
            if partial is not None:
                validate_control_record(partial,driver.monthly_targets)
            started = time.monotonic();before = partial[-1].get('elapsed_seconds',0.) if partial else 0.
            def save(*record):
                if source_id() != code_id:
                    raise ValueError('Sources changed during the event-forcing month.')
                info = dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
                parent.write_checkpoint(folder,year,(*record[:4],info))
                progress(dict(case=job['key'],year=year,month=info['month'],elapsed_year_seconds=info['elapsed_seconds']))
                log(f'{job["key"]}: cycle {year}/6, month {info["month"]}/12; incoming water checked')
            record = model.year(case.domain,profile,setting,state,air,case.score_mask,g,driver,
                checkpoint=partial,save_month=save,should_stop=stop)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            parent.write_checkpoint(folder,year,record,completed=True)
        validate_control_record(record,driver.monthly_targets)
        if previous is not None:
            check = parent.settling(previous,record,case,g)
        state = record[0]
        if year >= 3 and check['passed']:
            break
        previous = record
    row = parent.night.summarize(record,case,check,year)
    target = koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
    simulated = koppen_maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)
    row.update(response=parent.review.run.review.run.rain_vector(case,record[1]),
        case_config_sha256=sha256(folder/'config.json'),
        koppen_fixed_surface_temperature=koppen_maps.comparison(target,simulated,case.score_mask),
        maximum_monthly_import_error_mm=float(abs(np.array(record[-1]['diagnostics']['monthly_boundary_import_gross_mm'])-driver.monthly_targets).max()),
        evidence_sha256={f'year{n}.{ext}': sha256(folder/f'year{n}.{ext}') for n in range(1,year+1) for ext in ('json','npz')})
    if job['anchor']:
        row['anchor_check'] = compare_anchor(record,anchor,baseline,case)
        row['anchor_check']['passed'] &= check['passed']
    atomic_json(folder/'summary.json',row)
    return row


def report(out,state,protocol):
    lines = ['# Matched-import event forcing', '', f"Status: {state['status']}; {len(state['cases'])}/{len(protocol['jobs'])} cases. Atlas unchanged.", '',
        '| Case | Rain MAE | Coastal winter / reference | Interior winter | Cs → arid | Settled | Dose error |',
        '|---|---:|---:|---:|---:|---|---:|']
    for key,row in state['cases'].items():
        r = row['response'];k = row['koppen_fixed_surface_temperature']
        lines.append(f"| {key} | {row['score']:.2f} | {r['coast_winter_mm']:.1f} / {r['coast_winter_reference_mm']:.1f} mm | {r['interior_winter_mm']:.1f} mm | {k['target_mediterranean_to_arid']:.1%} | {row['settling']['passed']} | {row['maximum_monthly_import_error_mm']:.1e} mm |")
    lines += ['', 'Monthly mean dry circulation and gross incoming vapor are controlled. Ocean evaporation, recycling, humidity concentration statistics, export and diagnosed flow work can change. These synthetic cases test mechanism sensitivity, not measured storm statistics or a complete thermal front. Fixed-surface-temperature Köppen labels isolate rainfall errors. No automatic selection or atlas publication.']
    if state.get('error'):
        lines += ['', 'Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def run(out,preflight=PREFLIGHT,case_runner=run_case,clock=time.monotonic):
    deadline = clock()+BUDGET_HOURS*3600
    protocol,inputs,setting,baselines,anchors,calendars = prepare(preflight)
    for protected in (ROOT/'output/v10_split_column', ROOT/'output/v10_water_sources', ROOT/'output/v10_event_preflight', preflight):
        a,b = out.resolve(),protected.resolve()
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('Use a separate event-forcing output folder.')
    out.mkdir(parents=True,exist_ok=True);manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:
        raise ValueError('Event-forcing protocol changed; preserve output and use a new --out.')
    if not manifest.exists():
        atomic_json(manifest,protocol)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases': {}}
    if state.get('status') == 'needs_diagnosis':
        raise ValueError('Previous event-forcing failure needs inspection.')
    state['status'] = 'running';interrupted = [False]
    handler = signal.signal(signal.SIGINT,lambda *_: interrupted.__setitem__(0,True))
    def stop():
        return interrupted[0] or clock() >= deadline
    def log(message):
        text = parent.night.utc()+' '+message;print(text,flush=True)
        with (out/'run.log').open('a') as file:
            file.write(text+'\n')
    def progress(info):
        atomic_json(out/'progress.json',dict(info,updated_utc=parent.night.utc(),completed_cases=len(state['cases']),planned_cases=len(protocol['jobs'])))
    try:
        report(out,state,protocol)
        for job in protocol['jobs']:
            if source_id() != protocol['code_sha256']:
                raise ValueError('Sources changed during event-forcing experiment.')
            key = job['key'];folder = out/'cases'/key
            if key in state['cases']:
                row = state['cases'][key]
                if json.loads((folder/'summary.json').read_text()) != row:
                    raise ValueError('Completed event summary changed.')
                if sha256(folder/'config.json') != row['case_config_sha256']:
                    raise ValueError('Completed event case config changed.')
                for name,digest in row['evidence_sha256'].items():
                    if Path(name).name != name or sha256(folder/name) != digest:
                        raise ValueError('Completed event evidence changed.')
                if job['anchor'] and not row['anchor_check']['passed']:
                    raise ValueError('Held-boundary anchor differs materially from its frozen control.')
                continue
            if stop():
                raise model.base.BudgetStop()
            log(f'Start {key}; {(deadline-clock())/3600:.2f} hours left in invocation.')
            region = job['region']
            row = case_runner(folder,job,inputs,setting,baselines[region],anchors[region],calendars[region],stop,log,progress,protocol['code_sha256'])
            if source_id() != protocol['code_sha256']:
                raise ValueError('Sources changed while computing an event-forcing case.')
            state['cases'][key] = row;report(out,state,protocol)
            if job['anchor'] and not row['anchor_check']['passed']:
                raise ValueError('Held-boundary anchor differs materially from its frozen control; stop before mechanism cases.')
        state['status'] = 'complete'
    except model.base.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:
        state['status'] = 'needs_diagnosis';state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT,handler);report(out,state,protocol)
        progress(dict(status=state['status']))
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--out',type=Path,default=ROOT/'output/v10_event_forcing')
    parser.add_argument('--preflight',type=Path,default=PREFLIGHT)
    args = parser.parse_args(argv)
    print('12 fixed cases: two held-boundary controls first; then paired lifting/moisture-timing cases in California and Iberia.',flush=True)
    print('Estimated 45–75 minutes; two-hour invocation cap, monthly checkpoints and same-command resume.',flush=True)
    print('Cached inputs only; actual monthly incoming water checked. No downloads, calibration or atlas update.',flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/check_v10_event_forcing.py --run')
        return 0
    state = run(args.out,args.preflight);print('Status: '+state['status'],flush=True)
    return 0 if state['status'] in ('complete','interrupted','budget_reached') else 1


if __name__ == '__main__':
    raise SystemExit(main())
