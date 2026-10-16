"""User-run passive diagnostic replay of four saved final years; default is a plan."""
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
from experiments import v10_delivery_diagnostics as model
from scripts import review_v10_event_forcing as review
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256
run = review.run
SOURCE = ROOT/'output/v10_event_forcing'
PREFLIGHT = ROOT/'output/v10_delivery_preflight'
BUDGET_SECONDS = 45*60.


def source_id():
    digest = hashlib.sha256(run.source_id().encode())
    for path in (Path(__file__),Path(model.__file__),Path(review.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def prepare():
    parent,state,inputs,setting,finals,calendars,_,_,_ = review.load_verified(SOURCE)
    jobs = [];initials = {}
    for region in inputs:
        for name in ('lift1_steady','lift16_aligned'):
            key = region+'_'+name;row = state['cases'][key];year = row['years']
            folder = SOURCE/'cases'/key
            initial = run.parent.read_checkpoint(folder,year-1,inputs[region][0].domain.land.shape,completed=True)
            if initial is None:raise ValueError('Need the saved state preceding the final year.')
            initials[key] = initial[0]
            jobs.append({'key':key,'region':region,'amplitude':1. if name == 'lift1_steady' else 16.,
                'timing':'steady' if name == 'lift1_steady' else 'aligned','source_year':year,
                'source_start_npz_sha256':sha256(folder/f'year{year-1}.npz'),
                'source_final_npz_sha256':sha256(folder/f'year{year}.npz')})
    protocol = {'schema':1,'code_sha256':source_id(),'source_code_sha256':parent['code_sha256'],
        'source_manifest_sha256':sha256(SOURCE/'manifest.json'),'source_state_sha256':sha256(SOURCE/'state.json'),
        'forcing_array_sha256':parent['forcing_array_sha256'],'inputs':parent['inputs'],
        'jobs':jobs,'settings':asdict(setting),'seed':41,'budget_seconds':BUDGET_SECONDS,
        'policy':'One identical final-year replay per fixed case, initialized from its exact preceding-year state. No search or new warmup. All physical state/monthly fields, budgets and diagnostics must reproduce exactly; elapsed time excluded.',
        'diagnostics':'Time-weighted joint recipient humidity/upward exchange; layer rain; gross regional water budgets; signed thermal changes; independent instantaneous latent-condensation opportunities before/after prescribed thermal relaxation.',
        'opportunity_warning':'Stage opportunities follow the realized trajectory; they are not rainfall from a changed operator order or an alternative climate.',
        'regions':list(model.REGIONS),'stages':list(model.STAGES),
        'ascent_bin_edges_pa_s':[None if not np.isfinite(v) else float(v) for v in model.W_EDGES],
        'humidity_bin_edges':[None if not np.isfinite(v) else float(v) for v in model.RH_EDGES],
        'atlas_publication':False,'downloads':False}
    return protocol,inputs,setting,initials,finals,calendars


def verify_physical(actual,expected):
    for name in ('water','energy','soil'):
        a,b = getattr(actual[0],name),getattr(expected[0],name)
        if not np.array_equal(a,b):raise ValueError(f'Physical replay changed {name}; max difference {np.max(abs(a-b)):.3e}.')
    for name,a,b in zip(('rain','temperature','reference'),actual[1:4],expected[1:4]):
        if not np.array_equal(a,b):raise ValueError(f'Physical replay changed {name}; max difference {np.max(abs(a-b)):.3e}.')
    for key,value in expected[-1].items():
        if key != 'elapsed_seconds' and actual[-1].get(key) != value:
            raise ValueError('Physical replay changed annual ledger field '+key+'.')


def write_checkpoint(folder,record,collector,completed=False):
    run.parent.validate_record(record,collector.domain.land.shape,completed=completed)
    collector.validate_months(record[-1]['month'])
    stem = 'year1' if completed else 'year1_partial';meta = folder/(stem+'.json')
    previous = json.loads(meta.read_text()).get('arrays') if meta.exists() and not completed else None
    name = 'year1.npz' if completed else f'year1_m{record[-1]["month"]:02d}.npz'
    state,rain,temp,refs,info = record
    arrays = dict(water=state.water,energy=state.energy,soil=state.soil,rain=rain,temperature=temp,reference=refs)
    arrays.update({'trace_'+key:value for key,value in collector.arrays.items()})
    atomic_npz(folder/name,**arrays)
    atomic_json(meta,{'year':1,'arrays':name,'array_sha256':sha256(folder/name),'info':info})
    if previous and previous != name and Path(previous).name == previous:
        (folder/previous).unlink(missing_ok=True)


def read_checkpoint(folder,case,g,completed=False):
    record = run.parent.read_checkpoint(folder,1,case.domain.land.shape,completed=completed)
    if record is None:return None,None
    meta = json.loads((folder/('year1.json' if completed else 'year1_partial.json')).read_text())
    with np.load(folder/meta['arrays'],allow_pickle=False) as a:
        saved = {key[6:]:a[key] for key in a.files if key.startswith('trace_')}
    collector = model.Collector(case.domain,g,case.score_mask,case.coast_distance_km,saved=saved)
    collector.validate_months(record[-1]['month'])
    return record,collector


def preflight(out=PREFLIGHT):
    protocol,inputs,setting,initials,finals,calendars = prepare();checks = []
    for job in protocol['jobs']:
        key = job['key'];case,p,g,air,c = inputs[job['region']]
        driver = run.model.Driver(calendars[job['region']],case,p,setting,g,air,c,job['amplitude'],job['timing'])
        strongest = float(max(driver.events,key=lambda e:e.strength).day)
        for day in (0.,195.,strongest):
            t = float(np.floor(day*run.model.DAY/run.model.INTERVAL)*run.model.INTERVAL)
            f,bq,_ = driver.at(t);dt = min(60.,model.base.stable_step(f,g.mass,case.domain))
            state = initials[key];result = run.model.advance(state,case.domain,p,setting,f,dt,t,air,geometry=g,boundary=bq)
            before_arrays = [a.copy() for a in (result[0].water,result[0].energy,result[0].soil,*result[1:4],result[5],result[6])]
            collector = model.Collector(case.domain,g,case.score_mask,case.coast_distance_km)
            collector.add(state,result[0],result[5],result[6],f,bq,result[4],dt,t)
            for a,b in zip(before_arrays,(result[0].water,result[0].energy,result[0].soil,*result[1:4],result[5],result[6])):
                np.testing.assert_array_equal(a,b)
            checks.append({'case':key,'time_s':t,'dt_s':dt,'physical_arrays_unchanged':True,
                'maximum_reconstruction_errors':collector.arrays['maximum_reconstruction_errors'].tolist()})
    if source_id() != protocol['code_sha256']:raise ValueError('Sources changed during delivery preflight.')
    data = {'protocol':protocol,'checks':checks,'real_annual_replays_started':0,'atlas_updated':False,
        'note':'Twelve independent <=60-second probes; all physical arrays remain unchanged. Diagnostic states are not advanced into a real year.'}
    out.mkdir(parents=True,exist_ok=True);path = out/'manifest.json'
    if path.exists():
        if json.loads(path.read_text()) != data:raise ValueError('Preserve old delivery preflight; choose a new --preflight-out for changed sources.')
    else:atomic_json(path,data)
    print(data['note']);print('Source: '+protocol['code_sha256']);return data


def replay_case(folder,job,inputs,setting,initials,finals,calendars,stop,log,progress,code_id):
    key = job['key'];region = job['region'];case,p,g,air,c = inputs[region]
    folder.mkdir(parents=True,exist_ok=True)
    identity = {**job,'code_sha256':code_id}
    if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
        raise ValueError('Replay case identity changed.')
    if not (folder/'config.json').exists():atomic_json(folder/'config.json',identity)
    record,collector = read_checkpoint(folder,case,g,completed=True)
    if record is None:
        partial,collector = read_checkpoint(folder,case,g)
        if collector is None:collector = model.Collector(case.domain,g,case.score_mask,case.coast_distance_km)
        driver = run.model.Driver(calendars[region],case,p,setting,g,air,c,job['amplitude'],job['timing'])
        started = time.monotonic();before = partial[-1].get('elapsed_seconds',0.) if partial else 0.
        def save(*record):
            if source_id() != code_id:raise ValueError('Sources changed during the diagnostic replay.')
            info = dict(record[-1],elapsed_seconds=before+time.monotonic()-started)
            write_checkpoint(folder,(*record[:4],info),collector)
            progress(dict(case=key,month=info['month'],elapsed_case_seconds=info['elapsed_seconds']))
            log(f'{key}: {info["month"]}/12 months replayed; regional water/time weights checked')
        record = model.year(case.domain,p,setting,initials[key],air,case.score_mask,g,driver,
            checkpoint=partial,save_month=save,should_stop=stop,collector=collector)
        record[-1]['elapsed_seconds'] = before+time.monotonic()-started
        write_checkpoint(folder,record,collector,completed=True)
    verify_physical(record,finals[key]);summary = collector.summary()
    summary.update(physical_reproduction_exact=True,source_case=key,source_year=job['source_year'],
        elapsed_seconds=record[-1]['elapsed_seconds'],case_config_sha256=sha256(folder/'config.json'),
        evidence_sha256={name:sha256(folder/name) for name in ('year1.json','year1.npz')})
    atomic_json(folder/'summary.json',summary);return summary


def report(out,state):
    lines = ['# Passive delivery/process replay','',f"Status: {state['status']}; {len(state['cases'])}/4 cases. No atlas update.",'',
        '| Case | Physical year reproduced exactly | Coastal rain | Coastal RH after transport / relaxation | Coastal upward/moist fraction at 608 hPa |',
        '|---|---|---:|---:|---:|']
    for key,row in state['cases'].items():
        c = row['regions']['coast'];rh = np.array(c['mean_relative_humidity_by_stage_layer'])
        lines.append(f"| {key} | {row['physical_reproduction_exact']} | {sum(c['annual_layer_rain_mm']):.1f} mm/year | {rh[0,3]:.2f} / {rh[1,3]:.2f} | {c['recipient_moist_fraction_when_upward_exchange_ge_001_pa_s'][2]:.1%} |")
    lines += ['', 'The humidity column concerns the recipient 454 hPa layer at the fixed 607.95 hPa exchange. Moist means RH >=0.9 and upward exchange >=0.01 Pa/s; these are diagnostic thresholds, not observed event definitions. Stage condensation opportunities are not alternative-climate rainfall. Read regional water ledgers and full histograms together.']
    if state.get('error'):lines += ['', 'Stopped for diagnosis: '+state['error']]
    atomic_json(out/'state.json',state);(out/'summary.md').write_text('\n'.join(lines)+'\n')


def replay(out,preflight_out=PREFLIGHT,case_runner=replay_case,clock=time.monotonic):
    deadline = clock()+BUDGET_SECONDS
    protocol,inputs,setting,initials,finals,calendars = prepare()
    ready = json.loads((preflight_out/'manifest.json').read_text())
    if ready['protocol'] != protocol:raise ValueError('Delivery preflight is stale or incomplete.')
    for protected in (SOURCE,preflight_out,run.PREFLIGHT,ROOT/'output/v10_split_column'):
        a,b = out.resolve(),protected.resolve()
        if a == b or a in b.parents or b in a.parents:raise ValueError('Use a separate diagnostic replay folder.')
    out.mkdir(parents=True,exist_ok=True);manifest = out/'manifest.json'
    if manifest.exists() and json.loads(manifest.read_text()) != protocol:raise ValueError('Replay protocol changed; preserve output and use a new --out.')
    if not manifest.exists():atomic_json(manifest,protocol)
    state = json.loads((out/'state.json').read_text()) if (out/'state.json').exists() else {'cases':{}}
    if state.get('status') == 'needs_diagnosis':raise ValueError('Previous replay failure needs inspection.')
    state['status'] = 'running';interrupted = [False]
    handler = signal.signal(signal.SIGINT,lambda *_:interrupted.__setitem__(0,True))
    def stop():return interrupted[0] or clock() >= deadline
    def log(message):
        text = run.parent.night.utc()+' '+message;print(text,flush=True)
        with (out/'run.log').open('a') as f:f.write(text+'\n')
    def progress(info):
        atomic_json(out/'progress.json',dict(info,updated_utc=run.parent.night.utc(),completed_cases=len(state['cases']),planned_cases=4))
    try:
        report(out,state)
        for job in protocol['jobs']:
            if source_id() != protocol['code_sha256']:raise ValueError('Replay sources changed.')
            key = job['key'];folder = out/'cases'/key
            if key in state['cases']:
                row = state['cases'][key]
                if json.loads((folder/'summary.json').read_text()) != row or sha256(folder/'config.json') != row['case_config_sha256']:
                    raise ValueError('Completed replay identity/summary changed.')
                if any(Path(name).name != name or sha256(folder/name) != digest for name,digest in row['evidence_sha256'].items()):
                    raise ValueError('Completed replay evidence changed.')
                continue
            if stop():raise model.base.BudgetStop()
            log(f'Start {key}: replay source year {job["source_year"]}, without warmup.')
            row = case_runner(folder,job,inputs,setting,initials,finals,calendars,stop,log,progress,protocol['code_sha256'])
            if source_id() != protocol['code_sha256']:raise ValueError('Sources changed while completing a diagnostic replay.')
            state['cases'][key] = row;report(out,state)
        state['status'] = 'complete'
    except model.base.BudgetStop:state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except (ValueError,RuntimeError,FloatingPointError,OSError) as error:state['status'] = 'needs_diagnosis';state['error'] = str(error)
    finally:
        signal.signal(signal.SIGINT,handler);report(out,state);progress(dict(status=state['status']))
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true');parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--out',type=Path,default=ROOT/'output/v10_delivery_replay');parser.add_argument('--preflight-out',type=Path,default=PREFLIGHT)
    args = parser.parse_args(argv)
    if args.preflight:
        preflight(args.preflight_out);return 0
    print('Four single-year diagnostic replays from saved states. Estimated 5–15 minutes; 45-minute cap and monthly resume.',flush=True)
    print('Require exact original physical results; no search, download, warmup or atlas update.',flush=True)
    if not args.run:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/replay_v10_delivery.py --run');return 0
    state = replay(args.out,args.preflight_out);print('Status: '+state['status'],flush=True)
    return 0 if state['status'] in ('complete','interrupted','budget_reached') else 1


if __name__ == '__main__':raise SystemExit(main())
