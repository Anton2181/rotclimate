"""Bounded user-run delivery diagnostics and paired weather robustness; no fitting."""
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
sys.path.insert(0,str(ROOT))
import numpy as np
from experiments import v10_weather_panel as weather
from scripts import replay_v10_delivery as replay
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256
run = replay.run
PREFLIGHT = ROOT/'output/v10_afternoon_preflight'
SEEDS = (67,103,149,211,307,401,503,607)
CONDITIONS = ((1.,'steady'),(16.,'steady'),(16.,'aligned'),(16.,'shifted'))


def source_id():
    h = hashlib.sha256(replay.source_id().encode())
    for path in (Path(__file__),Path(weather.__file__)):h.update(path.read_bytes())
    return h.hexdigest()


def prepare():
    original,inputs,setting,initials,finals,calendars = replay.prepare()
    jobs = [{'key':'reference_'+job['key'],'phase':'reference','reference_job':job} for job in original['jobs']]
    for seed in SEEDS:
        for region in inputs:
            for amplitude,timing in CONDITIONS:
                jobs.append({'key':f's{seed}_{region}_'+run.model.variant_key(amplitude,timing),'phase':'climate',
                    'seed':seed,'region':region,'amplitude':amplitude,'timing':timing})
            for amplitude,timing in ((1.,'steady'),(16.,'aligned')):
                case_key = f's{seed}_{region}_'+run.model.variant_key(amplitude,timing)
                jobs.append({'key':'diagnostic_'+case_key,'phase':'diagnostic','source_case':case_key,
                    'seed':seed,'region':region,'amplitude':amplitude,'timing':timing})
    protocol = {'schema':1,'code_sha256':source_id(),'reference_protocol':original,'jobs':jobs,
        'seeds':list(SEEDS),'conditions':[list(v) for v in CONDITIONS],'minimum_cycles':3,'maximum_cycles':6,
        'settings':asdict(setting),'forcing_control':'Within each seed/region, preserve monthly mean dry circulation and match monthly gross boundary vapor input across all conditions. Across catalogues, forcing means/doses may differ.',
        'selection':'Fixed paired catalogue sensitivity, no best-seed selection or parameter optimization. Retain all cases. Previously used catalogues are not untouched validation; none represents observational uncertainty.',
        'diagnostics':'Replay four completed reference years first; then final-year diagnostics of original/steady and lift16/aligned in each new seed/region. Require exact physical reproduction.',
        'atlas_publication':False,'downloads':False}
    return protocol,inputs,setting,initials,finals,calendars


def cache_identity(protocol,inputs,seed,region):
    return {'code_sha256':protocol['code_sha256'],'seed':seed,'region':region,
        'input_sha256':protocol['reference_protocol']['inputs'][region]}


def write_calendar(folder,identity,arrays,diagnostics):
    folder.parent.mkdir(parents=True,exist_ok=True)
    atomic_npz(folder.with_suffix('.npz'),**arrays)
    atomic_json(folder.with_suffix('.json'),{'identity':identity,'array_sha256':run.parent.geometry_rules.array_id(arrays),
        'file_sha256':sha256(folder.with_suffix('.npz')),'diagnostics':diagnostics})


def read_calendar(folder,identity):
    meta = json.loads(folder.with_suffix('.json').read_text())
    if meta['identity'] != identity or sha256(folder.with_suffix('.npz')) != meta['file_sha256']:
        raise ValueError('Weather forcing cache identity/integrity changed.')
    with np.load(folder.with_suffix('.npz'),allow_pickle=False) as a:arrays = {k:a[k] for k in a.files}
    if run.parent.geometry_rules.array_id(arrays) != meta['array_sha256']:
        raise ValueError('Weather forcing array identity changed.')
    return arrays,meta['diagnostics']


def get_calendar(out,protocol,inputs,setting,seed,region,log):
    identity = cache_identity(protocol,inputs,seed,region);stem = f's{seed}_{region}'
    path = out/'forcing'/stem
    if path.with_suffix('.json').exists():return read_calendar(path,identity)[0]
    prepared = PREFLIGHT/'forcing'/stem
    if prepared.with_suffix('.json').exists():
        arrays,diagnostics = read_calendar(prepared,identity)
    else:
        log(f'Preparing seed {seed}, {region} forcing; circulation/boundary queries only.')
        case,p,g,air,c = inputs[region]
        arrays,diagnostics = weather.prepare_calendar(case,p,setting,g,air,c,seed)
    if source_id() != protocol['code_sha256']:raise ValueError('Sources changed during weather-table preparation.')
    write_calendar(path,identity,arrays,diagnostics)
    return arrays


def climate_case(folder,job,case_input,setting,calendar,stop,log,progress,code_id):
    case,p,g,air,c = case_input;folder.mkdir(parents=True,exist_ok=True)
    identity = {**job,'settings':asdict(setting),'forcing_array_sha256':run.parent.geometry_rules.array_id(calendar)}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Weather climate case identity changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    driver = weather.Driver(calendar,case,p,setting,g,air,c,job['amplitude'],job['timing'],job['seed'])
    state = run.model.core.initial_state(case.domain,p,setting,g,air);previous = None;check = {'passed':False}
    for year in range(1,7):
        if source_id() != code_id:raise ValueError('Weather experiment sources changed.')
        record = run.parent.read_checkpoint(folder,year,case.domain.land.shape,completed=True)
        if record is None:
            partial = run.parent.read_checkpoint(folder,year,case.domain.land.shape)
            if partial is not None:run.validate_control_record(partial,driver.monthly_targets)
            started = time.monotonic();before = partial[-1].get('elapsed_seconds',0.) if partial else 0.
            def save(*record):
                if source_id() != code_id:raise ValueError('Sources changed during weather integration.')
                info = dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
                run.parent.write_checkpoint(folder,year,(*record[:4],info))
                progress(dict(year=year,month=info['month'],elapsed_year_seconds=info['elapsed_seconds']))
                log(f'{job["key"]}: cycle {year}/6, month {info["month"]}/12; incoming water checked')
            record = run.model.year(case.domain,p,setting,state,air,case.score_mask,g,driver,
                checkpoint=partial,save_month=save,should_stop=stop)
            record[-1]['elapsed_seconds'] = before+time.monotonic()-started
            run.parent.write_checkpoint(folder,year,record,completed=True)
        run.validate_control_record(record,driver.monthly_targets)
        if previous is not None:check = run.parent.settling(previous,record,case,g)
        state = record[0]
        if year >= 3 and check['passed']:break
        previous = record
    row = run.parent.night.summarize(record,case,check,year)
    target = run.koppen_maps.classify_months(case.domain.temperature_c,case.observed_rain_mm,case.score_mask)
    classes = run.koppen_maps.classify_months(case.domain.temperature_c,record[1],case.score_mask)
    row.update(response=run.parent.review.run.review.run.rain_vector(case,record[1]),
        koppen_fixed_surface_temperature=run.koppen_maps.comparison(target,classes,case.score_mask),
        maximum_monthly_import_error_mm=float(abs(np.array(record[-1]['diagnostics']['monthly_boundary_import_gross_mm'])-driver.monthly_targets).max()),
        case_config_sha256=sha256(folder/'config.json'),
        evidence_sha256={f'year{n}.{ext}':sha256(folder/f'year{n}.{ext}') for n in range(1,year+1) for ext in ('json','npz')})
    atomic_json(folder/'summary.json',row);return row


def diagnostic_case(folder,job,source_folder,source_row,case_input,setting,calendar,stop,log,progress,code_id):
    case,p,g,air,c = case_input;n = source_row['years'];folder.mkdir(parents=True,exist_ok=True)
    identity = {**job,'source_year':n,'source_start_sha256':sha256(source_folder/f'year{n-1}.npz'),
        'source_final_sha256':sha256(source_folder/f'year{n}.npz'),'code_sha256':code_id}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Weather diagnostic source identity changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    expected = run.parent.read_checkpoint(source_folder,n,case.domain.land.shape,completed=True)
    initial = run.parent.read_checkpoint(source_folder,n-1,case.domain.land.shape,completed=True)[0]
    record,collector = replay.read_checkpoint(folder,case,g,completed=True)
    if record is None:
        partial,collector = replay.read_checkpoint(folder,case,g)
        if collector is None:collector = replay.model.Collector(case.domain,g,case.score_mask,case.coast_distance_km)
        driver = weather.Driver(calendar,case,p,setting,g,air,c,job['amplitude'],job['timing'],job['seed'])
        started = time.monotonic();before = partial[-1].get('elapsed_seconds',0.) if partial else 0.
        def save(*record):
            if source_id() != code_id:raise ValueError('Sources changed during weather diagnostic replay.')
            info = dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
            replay.write_checkpoint(folder,(*record[:4],info),collector)
            progress(dict(month=info['month'],elapsed_case_seconds=info['elapsed_seconds']))
            log(f'{job["key"]}: {info["month"]}/12 months diagnosed; regional water budgets checked')
        record = replay.model.year(case.domain,p,setting,initial,air,case.score_mask,g,driver,
            checkpoint=partial,save_month=save,should_stop=stop,collector=collector)
        record[-1]['elapsed_seconds'] = before+time.monotonic()-started
        replay.write_checkpoint(folder,record,collector,completed=True)
    replay.verify_physical(record,expected);row = collector.summary()
    row.update(physical_reproduction_exact=True,source_case=job['source_case'],source_year=n,
        source_settled=source_row['settling']['passed'],elapsed_seconds=record[-1]['elapsed_seconds'],
        case_config_sha256=sha256(folder/'config.json'),evidence_sha256={name:sha256(folder/name) for name in ('year1.json','year1.npz')})
    atomic_json(folder/'summary.json',row);return row


def verify_completed(folder,row):
    if json.loads((folder/'summary.json').read_text()) != row or sha256(folder/'config.json') != row['case_config_sha256']:
        raise ValueError('Completed afternoon case identity/summary changed.')
    if any(Path(name).name != name or sha256(folder/name) != digest for name,digest in row['evidence_sha256'].items()):
        raise ValueError('Completed afternoon case evidence changed.')


def paired_results(state):
    groups = {}
    for seed in SEEDS:
        for region in ('california','iberia'):
            keys = [f's{seed}_{region}_'+run.model.variant_key(a,t) for a,t in CONDITIONS]
            if not all(key in state['cases'] for key in keys):continue
            rows = [state['cases'][key] for key in keys];base,steady,aligned,shifted = [row['response'] for row in rows]
            groups[f's{seed}_{region}'] = {'seed':seed,'region':region,'all_settled':all(row['settling']['passed'] for row in rows),
                'lifting_coastal_winter_gain_mm':steady['coast_winter_mm']-base['coast_winter_mm'],
                'combined_coastal_winter_gain_mm':aligned['coast_winter_mm']-base['coast_winter_mm'],
                'timing_coastal_winter_gain_mm':aligned['coast_winter_mm']-shifted['coast_winter_mm'],
                'combined_monthly_mae_change_mm':aligned['monthly_mae_mm']-base['monthly_mae_mm'],
                'reference_coastal_winter_mm':base['coast_winter_reference_mm'],'combined_coastal_winter_mm':aligned['coast_winter_mm']}
    return groups


def report(out,state,protocol):
    phases = {job['key']:job['phase'] for job in protocol['jobs']}
    counts = {phase:sum(phases[key] == phase for key in state['cases']) for phase in ('reference','climate','diagnostic')}
    groups = paired_results(state)
    lines = ['# Delivery diagnostics and fixed weather robustness','',
        f"Status: {state['status']}; {len(state['cases'])}/{len(protocol['jobs'])} jobs. Reference replays {counts['reference']}/4; climates {counts['climate']}/64; new-weather diagnostic replays {counts['diagnostic']}/32. Atlas unchanged.", '',
        '| Catalogue / region | Stronger lift: coastal winter gain | Lift + linked moisture gain | Linked minus shifted | MAE change | All settle |',
        '|---|---:|---:|---:|---:|---|']
    for key,row in groups.items():
        lines.append(f"| {key} | {row['lifting_coastal_winter_gain_mm']:+.2f} mm | {row['combined_coastal_winter_gain_mm']:+.2f} mm | {row['timing_coastal_winter_gain_mm']:+.2f} mm | {row['combined_monthly_mae_change_mm']:+.3f} mm | {row['all_settled']} |")
    lines += ['', 'Fixed paired synthetic-catalogue sensitivity; no best-seed selection or observational climate confidence interval. Input is matched across conditions within each catalogue/region, not across different catalogues. Unsettled cases remain labelled. Diagnostics require exact physical replay; stage condensation opportunities are not alternative-climate rainfall.']
    if state.get('error'):lines += ['', 'Stopped for diagnosis: '+state['error']]
    state['paired_results'] = groups
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def batch(out,hours=3.75,case_runner=None,clock=time.monotonic):
    if not np.isfinite(hours) or not 0 < hours <= 4:raise ValueError('Use a positive invocation budget up to four hours.')
    started = clock();deadline = started+hours*3600
    protocol,inputs,setting,initials,finals,reference_calendars = prepare()
    ready = json.loads((PREFLIGHT/'manifest.json').read_text())
    if ready['protocol'] != protocol:raise ValueError('Afternoon preflight is stale or incomplete.')
    for protected in (replay.SOURCE,replay.PREFLIGHT,run.PREFLIGHT,PREFLIGHT,ROOT/'output/v10_split_column'):
        a,b = out.resolve(),protected.resolve()
        if a == b or a in b.parents or b in a.parents:raise ValueError('Use a separate afternoon output folder.')
    out.mkdir(parents=True,exist_ok=True);manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:raise ValueError('Afternoon protocol changed; preserve output and use a new --out.')
    if not manifest.exists():atomic_json(manifest,protocol)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases':{},'invocations':[]}
    if state.get('status') == 'needs_diagnosis':raise ValueError('Previous afternoon failure needs inspection.')
    invocation = {'started_utc':run.parent.night.utc(),'budget_hours':hours};state['invocations'].append(invocation)
    state['status'] = 'running';interrupted = [False];current_job = {};cached_key = None;calendar = None
    handler = signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    def stop():return interrupted[0] or clock() >= deadline
    def log(message):
        text = run.parent.night.utc()+' '+message;print(text,flush=True)
        with (out/'run.log').open('a') as f:f.write(text+'\n')
    def progress(info):
        if source_id() != protocol['code_sha256']:raise ValueError('Afternoon sources changed.')
        atomic_json(out/'progress.json',dict(info,case=current_job.get('key'),phase=current_job.get('phase'),updated_utc=run.parent.night.utc(),
            completed_jobs=len(state['cases']),planned_jobs=len(protocol['jobs']),elapsed_invocation_seconds=clock()-started,budget_hours=hours))
    try:
        report(out,state,protocol)
        for job in protocol['jobs']:
            current_job = job
            if source_id() != protocol['code_sha256']:raise ValueError('Afternoon sources changed.')
            folder = out/'cases'/job['key']
            if job['key'] in state['cases']:
                verify_completed(folder,state['cases'][job['key']]);continue
            if stop():raise run.model.base.BudgetStop()
            log(f'[{len(state["cases"])+1}/{len(protocol["jobs"])}] {job["phase"]}: {job["key"]}; {(deadline-clock())/3600:.2f} hours left.')
            if case_runner is not None:
                row = case_runner(folder,job)
            elif job['phase'] == 'reference':
                row = replay.replay_case(folder,job['reference_job'],inputs,setting,initials,finals,reference_calendars,
                    stop,log,progress,protocol['reference_protocol']['code_sha256'])
            else:
                key = (job['seed'],job['region'])
                if key != cached_key:
                    calendar = get_calendar(out,protocol,inputs,setting,*key,log);cached_key = key
                if stop():raise run.model.base.BudgetStop()
                if job['phase'] == 'climate':
                    row = climate_case(folder,job,inputs[job['region']],setting,calendar,stop,log,progress,protocol['code_sha256'])
                else:
                    source_folder = out/'cases'/job['source_case'];source_row = state['cases'][job['source_case']]
                    verify_completed(source_folder,source_row)
                    row = diagnostic_case(folder,job,source_folder,source_row,inputs[job['region']],setting,calendar,stop,log,progress,protocol['code_sha256'])
            if source_id() != protocol['code_sha256']:raise ValueError('Sources changed while completing an afternoon job.')
            state['cases'][job['key']] = row;report(out,state,protocol);progress(dict(status='running'))
        state['status'] = 'complete'
    except run.model.base.BudgetStop:state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:state['status'] = 'needs_diagnosis';state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT,handler)
        invocation.update(finished_utc=run.parent.night.utc(),elapsed_seconds=clock()-started,status=state['status'])
        report(out,state,protocol)
        atomic_json(out/'progress.json',{'status':state['status'],'completed_jobs':len(state['cases']),'planned_jobs':len(protocol['jobs']),
            'updated_utc':run.parent.night.utc(),'elapsed_invocation_seconds':invocation['elapsed_seconds']})
    return state


def preflight():
    protocol,inputs,setting,initials,finals,reference_calendars = prepare();checks = [];calendars = {}
    for region,(case,p,g,air,c) in inputs.items():
        print(region+': checking seed adapters and preparing seed 67 forcing; no annual integration.',flush=True)
        if region == 'california':
            same,_ = weather.prepare_calendar(case,p,setting,g,air,c,41)
            if run.parent.geometry_rules.array_id(same) != run.parent.geometry_rules.array_id(reference_calendars[region]):
                raise ValueError('Seed-41 adapter changed the original forcing calendar.')
        arrays,diag = weather.prepare_calendar(case,p,setting,g,air,c,67)
        calendars[region] = (arrays,diag)
        for amplitude,timing in CONDITIONS:
            original = run.model.Driver(reference_calendars[region],case,p,setting,g,air,c,amplitude,timing)
            identical = weather.Driver(reference_calendars[region],case,p,setting,g,air,c,amplitude,timing,41)
            fresh = weather.Driver(arrays,case,p,setting,g,air,c,amplitude,timing,67)
            strongest = float(max(fresh.events,key=lambda e:e.strength).day)
            for day in (0.,195.,strongest):
                t = float(np.floor(day*run.model.DAY/run.model.INTERVAL)*run.model.INTERVAL)
                old,old_q,_ = original.at(t);same,same_q,_ = identical.at(t)
                for a,b in ((old.x,same.x),(old.y,same.y),(old.vertical,same.vertical),(old_q,same_q)):np.testing.assert_array_equal(a,b)
                f,q,_ = fresh.at(t);dt = min(60.,run.model.base.stable_step(f,g.mass,case.domain))
                initial = run.model.core.initial_state(case.domain,p,setting,g,air)
                result = run.model.advance(initial,case.domain,p,setting,f,dt,t,air,geometry=g,boundary=q)
                saved = [a.copy() for a in (result[0].water,result[0].energy,result[0].soil,*result[1:4],result[5],result[6])]
                collector = replay.model.Collector(case.domain,g,case.score_mask,case.coast_distance_km)
                collector.add(initial,result[0],result[5],result[6],f,q,result[4],dt,t)
                for a,b in zip(saved,(result[0].water,result[0].energy,result[0].soil,*result[1:4],result[5],result[6])):np.testing.assert_array_equal(a,b)
                checks.append({'region':region,'amplitude':amplitude,'timing':timing,'time_s':t,'dt_s':dt,
                    'seed41_flow_boundary_identical':True,'seed67_physical_diagnostics_unchanged':True,
                    'reconstruction_errors':collector.arrays['maximum_reconstruction_errors'].tolist()})
    if source_id() != protocol['code_sha256']:raise ValueError('Sources changed during afternoon preflight.')
    data = {'protocol':protocol,'checks':checks,'seed41_california_calendar_identical':True,
        'new_annual_integrations_started':0,'new_seed67_calendars_verified':True,'atlas_updated':False}
    path = PREFLIGHT/'manifest.json'
    if path.exists():
        if json.loads(path.read_text()) != data:raise ValueError('Preserve existing afternoon preflight for changed sources.')
        for region,(arrays,_) in calendars.items():
            saved,_ = read_calendar(PREFLIGHT/'forcing'/f's67_{region}',cache_identity(protocol,inputs,67,region))
            if run.parent.geometry_rules.array_id(saved) != run.parent.geometry_rules.array_id(arrays):
                raise ValueError('Prepared seed67 weather calendar changed.')
    else:
        for region,(arrays,diag) in calendars.items():write_calendar(PREFLIGHT/'forcing'/f's67_{region}',cache_identity(protocol,inputs,67,region),arrays,diag)
        atomic_json(path,data)
    print('Afternoon preflight passed: exact seed41 adapter, two seed67 calendars and 24 independent <=60-second diagnostic probes.')
    return data


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__);p.add_argument('--run',action='store_true');p.add_argument('--preflight',action='store_true')
    p.add_argument('--hours',type=float,default=3.75);p.add_argument('--out',type=Path,default=ROOT/'output/v10_afternoon_delivery')
    a = p.parse_args(argv)
    if a.preflight:preflight();return 0
    print('First four exact diagnostic replays; then eight fixed weather catalogues × two regions × four conditions, with 32 final-year diagnostic replays.',flush=True)
    print(f'Approximately 3–4 hours of work; this invocation stops after {a.hours:g} hours with monthly resume. No fitting, best-seed selection, download or atlas update.',flush=True)
    if not a.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/afternoon_v10_delivery.py --run --hours 3.75');return 0
    state = batch(a.out,a.hours);print('Status: '+state['status'],flush=True)
    return 0 if state['status'] in ('complete','budget_reached','interrupted') else 1


if __name__ == '__main__':raise SystemExit(main())
