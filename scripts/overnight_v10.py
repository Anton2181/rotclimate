"""Nine-hour, resumable four-layer Earth research batch. Default is read-only.

Matched mechanism controls -> California parameter coverage -> two-region
weather checks -> finer grids. Independent rainfall references are scoring only.
No downloads, background scheduling, production-model edits or atlas publication.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
import itertools
import json
from pathlib import Path
import shutil
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from experiments import v10_column as model
from experiments import v10_forcing_audit as atmosphere
from scripts import audit_v10_forcing as audit
from scripts import check_v10_thermodynamics as heat
from rotclimate_v10.core import CENTERS,DAY,Domain,interpolate_months
from rotclimate_v10.earth import (atomic_json,atomic_npz,load_case,prepare_region,save_case,sha256)
from rotclimate_v10.earth import REGIONS,EarthCase,read_wc,read_sst,nearest_fill
from rotclimate_v10.earth import SOURCES
from scipy.ndimage import distance_transform_edt
from rotclimate_v10.integrate import rain_metrics

SCREEN = 120


def utc():return datetime.now(timezone.utc).isoformat()


def code_id():
    digest = hashlib.sha256(heat.source_hash().encode())
    for path in (Path(__file__).resolve(),Path(model.__file__),Path(atmosphere.__file__),Path(audit.__file__)):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def design():
    """Declared factorial controls, then reproducible balanced parameter coverage."""
    settings = []
    for wind,temp,humidity in itertools.product((False,True),repeat=3):
        settings.append(model.Settings(observed_wind=wind,observed_temperature=temp,observed_humidity=humidity))
    for terrain,rate in itertools.product(('shallow','deep','none'),(0.,4.)):
        s = model.Settings(terrain=terrain,storm_rate_month=rate)
        if s not in settings:settings.append(s)
    anchors = len(settings)
    choices = {'terrain':('shallow','shallow','shallow','deep','none'),
        'humidity_scale':(.8,1.,1.2),'relaxation_lower_days':(.5,2.,5.),'relaxation_upper_days':(5.,10.,20.),
        'storm_rate_month':(1.,2.,4.,6.),'storm_convergence_ms':(0.,.25,.5,1.),
        'storm_rotation_ms':(6.,12.,18.),'storm_radius_km':(250.,350.,500.),'terrain_drag_height_m':(1200.,1800.,3000.)}
    rng = np.random.default_rng(15102026)
    # Each dimension has approximately equal category coverage; this is not an optimizer.
    n = 144
    columns = {key:rng.permutation(np.resize(np.array(values,dtype=object),n)) for key,values in choices.items()}
    for i in range(n):
        s = model.Settings(**{key:values[i].item() if hasattr(values[i],'item') else values[i] for key,values in columns.items()})
        if s not in settings:settings.append(s)
    for s in settings:s.validate()
    return settings,anchors


def candidate_indices(settings):
    # Legacy-forcing factorials diagnose mechanisms; they cannot win by
    # compensating a rain error with winds/humidity known to miss the reference.
    return [i for i,s in enumerate(settings) if s.observed_wind and s.observed_temperature and s.observed_humidity]


def prepare_profiles(cases,texts):
    fields = atmosphere.fields_from_cache(texts);profiles = {}
    for region,case in cases.items():
        mask = atmosphere.offshore_mask(case);d = case.domain
        sea = np.stack([interpolate_months(d.temperature_c,t) for t in CENTERS])[:,mask].mean(1)
        columns = {key:[] for key in ('air','shum','uwnd','vwnd','hgt')}
        for sigma in model.SIGMA:
            for variable in columns:
                values,_,_ = atmosphere.at_pressure(fields[region,variable],case.longitude,d.latitude,1013.25*sigma)
                if not np.isfinite(values[:,mask]).all():raise ValueError('Missing offshore atmospheric reference.')
                columns[variable].append(values[:,mask].mean(1))
        values = {key:np.stack(arrays,axis=1) for key,arrays in columns.items()}
        west,east,south,north = REGIONS[region]
        width = (east-west)*111195*np.cos(np.deg2rad(.5*(south+north)))
        profile = model.Profile(values['air']-sea[:,None],values['shum'],values['uwnd'],values['vwnd'],values['hgt'].mean(0),float(width))
        profile.validate();profiles[region] = profile
    return profiles


def profiles_json(profiles):
    return {name:{key:array.tolist() if isinstance(array,np.ndarray) else array for key,array in vars(p).items()} for name,p in profiles.items()}


def prepare_grid(region,spacing,raw):
    """Same raw reference, 120 km scoring inset at every resolution."""
    if spacing>=30:
        case = prepare_region(region,raw,spacing)
    elif spacing==15:
        west,east,south,north = REGIONS[region];step = spacing*1000.
        dlat = step/111195;dlon = step/(111195*np.cos(np.deg2rad(.5*(south+north))))
        lon,lat = np.meshgrid(np.arange(west+.5*dlon,east,dlon),np.arange(north-.5*dlat,south,-dlat))
        elev = read_wc(raw,'elev',lon,lat);land = np.isfinite(elev)
        air = read_wc(raw,'tavg',lon,lat);rain = read_wc(raw,'prec',lon,lat)
        sea = read_sst(raw/'sst.ltm.1971-2000.nc',lon,lat)
        imputed = land&~np.isfinite(air).all(0)
        temp = np.stack([np.where(land,nearest_fill(t),s) for t,s in zip(air,sea)])
        mask = land&~imputed&np.isfinite(rain).all(0)&(rain>=0).all(0)
        d = Domain(region,land,np.where(land,elev,0.),lat,temp,step,step);d.validate()
        case = EarthCase(d,lon,rain,mask,distance_transform_edt(land,sampling=(step,step))/1000,imputed)
    else:raise ValueError('Unsupported overnight grid spacing.')
    n = int(np.ceil(120/spacing))
    case.score_mask = case.domain.land&~case.temperature_imputed&np.isfinite(case.observed_rain_mm).all(0)&(case.observed_rain_mm>=0).all(0)
    mask = case.score_mask
    mask[:n] = False;mask[-n:] = False;mask[:,:n] = False;mask[:,-n:] = False
    if not mask.any():raise ValueError('No scored fine-grid land.')
    return case


def validate_fields(state,rain,temp,refs,info,shape,completed=False):
    if state.water.shape!=(4,)+shape or state.energy.shape!=(4,)+shape or state.soil.shape!=shape:
        raise ValueError('Wrong column checkpoint shapes.')
    if not all(np.isfinite(a).all() for a in (state.water,state.energy,state.soil,rain,temp,refs)) or state.water.min()<0 or state.soil.min()<0:
        raise ValueError('Invalid column checkpoint fields.')
    if rain.shape!=(12,)+shape or rain.min()<0 or temp.shape!=(12,4)+shape or refs.shape!=temp.shape:
        raise ValueError('Invalid monthly checkpoint fields.')
    if not isinstance(info['month'],int) or not 0<=info['month']<=12:raise ValueError('Invalid checkpoint month.')
    if (not np.isfinite(list(info['totals'].values())).all() or not np.isfinite([info[k] for k in ('maxw','maxe','continuity','initial_water','initial_energy','steps')]).all()
        or info['maxw']>1e-9 or info['maxe']>1e-5 or info['continuity']>1e-10):
        raise ValueError('Failed partial checkpoint physical checks.')
    if completed:
        b = info['budget']
        if info['month']!=12 or not np.isfinite(list(b.values())).all() or abs(b['annual_water_error_mm'])>1e-6 or abs(b['annual_energy_error_j_m2'])>1:
            raise ValueError('Failed annual checkpoint budget.')
        if b['max_step_water_error_mm']>1e-9 or b['max_step_energy_error_j_m2']>1e-5 or b['max_air_continuity_kg_m2_s']>1e-10:
            raise ValueError('Failed checkpoint physical checks.')


def write_checkpoint(folder,year,record,completed=False):
    state,rain,temp,refs,info = record
    validate_fields(state,rain,temp,refs,info,state.soil.shape,completed)
    stem = f'year{year}' if completed else f'year{year}_partial'
    meta = folder/(stem+'.json');previous_array = None
    if not completed and meta.exists():previous_array = json.loads(meta.read_text()).get('arrays')
    # Commit a pointer to a new immutable array: interruption between the two
    # writes leaves the previous committed month readable.
    path = folder/(f'year{year}.npz' if completed else f'year{year}_m{info["month"]:02d}.npz')
    atomic_npz(path,water=state.water,energy=state.energy,soil=state.soil,rain=rain,temperature=temp,reference=refs)
    atomic_json(meta,{'year':year,'arrays':path.name,'array_sha256':sha256(path),'info':info})
    if previous_array and previous_array!=path.name and Path(previous_array).name==previous_array:
        (folder/previous_array).unlink(missing_ok=True)


def read_checkpoint(folder,year,shape,completed=False):
    stem = f'year{year}' if completed else f'year{year}_partial'
    meta = folder/(stem+'.json')
    if not meta.exists():return None
    row = json.loads(meta.read_text())
    name = row.get('arrays','')
    if not name or Path(name).name!=name:raise ValueError('Invalid checkpoint array path.')
    path = folder/name
    if row.get('year')!=year or not path.is_file() or row.get('array_sha256')!=sha256(path):
        raise ValueError('Checkpoint integrity mismatch. Preserve output and choose a fresh --out.')
    with np.load(path,allow_pickle=False) as a:
        record = (model.State(a['water'],a['energy'],a['soil']),a['rain'],a['temperature'],a['reference'],row['info'])
    validate_fields(*record,shape,completed)
    return record


def settling(previous,current,case,profile):
    old,op,ot,_,_ = previous;new,p,t,_,_ = current;mask = case.score_mask
    mass,_ = model.masses(case.domain);z = model.geometry(case.domain,profile)
    values = {'monthly_rain_p95_mm':float(np.percentile(abs(p-op)[:,mask],95)),
        'annual_rain_p95_mm':float(np.percentile(abs((p-op).sum(0))[mask],95)),
        'water_store_p95_mm':max(float(np.percentile(abs(new.water[k]-old.water[k]),95)) for k in range(4)),
        'soil_p95_mm':float(np.percentile(abs(new.soil-old.soil),95)),
        'monthly_temperature_p95_c':float(np.percentile(abs(t-ot)[:,:,mask],95)),
        'end_temperature_p95_c':float(np.percentile(abs(model.temperature(new.energy,mass,new.water,z)-model.temperature(old.energy,mass,old.water,z)),95))}
    limits = dict(zip(values,(1.,5.,1.,1.,.05,.05)))
    return {'passed':all(v<=limits[k] for k,v in values.items()),'changes':values,'limits':limits}


def summarize(record,case,check,years):
    _,rain,temp,refs,info = record;mask = case.score_mask
    m = rain_metrics(case,rain);delta = abs(temp-refs)[:,:,mask]
    low = float(np.percentile(delta[:,:2],95));high = float(np.percentile(delta[:,2:],95))
    obs = case.observed_rain_mm.sum(0);annual = rain.sum(0);wet_reference = mask&(obs>=50.)
    wet_coverage = float((annual[wet_reference]>=1.).mean()) if wet_reference.any() else 0.
    ratio = m['predicted_mean_annual_mm']/max(m['observed_mean_annual_mm'],1e-9)
    tail_ratio = float(np.percentile(annual[mask],99)/max(np.percentile(obs[mask],99),1.))
    guards = {'lower_temperature':low<=5.,'upper_temperature':high<=10.,'rain_amount':.5<=ratio<=1.75,
              'wet_reference_coverage':wet_coverage>=.8,'rain_tail':tail_ratio<=4.}
    return {'rainfall':m,'settling':check,'years':years,'temperature_departure_p95_c':[low,high],
        'annual_rain_ratio':ratio,'annual_rain_p99_ratio':tail_ratio,'wet_reference_coverage':wet_coverage,
        'guards':guards,'eligible':bool(check['passed'] and all(guards.values())),
        'budget':info['budget'],'score':m['monthly_mae_mm'],
        'note':'Temperature remains observation-informed relaxation forcing. Provisional guards, not independent climate validation.'}


def job_id(index,region,spacing,seed):return f'c{index:03d}_{region}_g{spacing}_s{seed}'


def run_case(job,case,profile,settings,out,should_stop,log,integrator=model.year,max_years=6):
    folder = out/'cases'/job;folder.mkdir(parents=True,exist_ok=True)
    config = {'settings':asdict(settings),'region':case.domain.name,'spacing_m':case.domain.dx,'seed':int(job.rsplit('s',1)[1]),'max_years':max_years}
    manifest = folder/'config.json'
    if manifest.exists() and json.loads(manifest.read_text())!=config:raise ValueError('Changed case configuration.')
    if not manifest.exists():atomic_json(manifest,config)
    state = model.initial_state(case.domain,profile,settings);previous = None;check = {'passed':False}
    for year in range(1,max_years+1):
        record = read_checkpoint(folder,year,case.domain.land.shape,completed=True)
        if record is None:
            partial = read_checkpoint(folder,year,case.domain.land.shape)
            start = time.monotonic();elapsed_before = partial[-1].get('elapsed_seconds',0.) if partial else 0.
            def save_month(state,rain,temp,refs,info):
                saved_info = dict(info,elapsed_seconds=elapsed_before+time.monotonic()-start)
                write_checkpoint(folder,year,(state,rain,temp,refs,saved_info))
                atomic_json(out/'progress.json',{'case':job,'year':year,'month':info['month'],'updated_utc':utc(),
                    'elapsed_year_seconds':saved_info['elapsed_seconds']})
                log(f'{job}: year {year}/{max_years}, month {info["month"]}/12; {saved_info["elapsed_seconds"]/60:.1f} min this year')
            record = integrator(case.domain,profile,settings,config['seed'],state,checkpoint=partial,save_month=save_month,should_stop=should_stop)
            record[-1]['elapsed_seconds'] = elapsed_before+time.monotonic()-start
            write_checkpoint(folder,year,record,completed=True)
        if previous is not None:check = settling(previous,record,case,profile)
        state = record[0]
        if year>=3 and check['passed']:break
        previous = record
    summary = summarize(record,case,check,year)
    forcing_complete = settings.observed_wind and settings.observed_temperature and settings.observed_humidity
    summary['guards']['reference_forcing'] = bool(forcing_complete)
    summary['eligible'] = bool(summary['eligible'] and forcing_complete)
    summary['evidence_sha256'] = {path.name:sha256(path) for path in sorted(folder.glob('year[0-9].*')) if path.suffix in ('.npz','.json')}
    atomic_json(folder/'summary.json',summary)
    return summary


def ranked(rows,indices,region='california',spacing=SCREEN,seed=41):
    entries = [(i,rows[job_id(i,region,spacing,seed)]) for i in indices if job_id(i,region,spacing,seed) in rows]
    # Failed eligibility remains diagnostic, never silently promoted to a validated winner.
    return [i for i,r in sorted(entries,key=lambda item:(not item[1]['eligible'],not item[1]['settling']['passed'],item[1]['score']))]


def report(out,state,settings):
    rows = state['cases'];order = ranked(rows,range(len(settings)))
    lines = ['# Overnight four-layer Earth research','',f"Status: {state['status']}. Stage: {state['stage']}.",
        f"Completed cases: {len(rows)}. Numerical failures: {len(state['failures'])}. Atlas updated: no.",'',
        'Regional reanalysis wind, humidity and thermal profiles; shallow terrain return tested separately from deep storm ascent.',
        'Observed temperatures remain forcing; Earth results cannot publish a fantasy atlas. Selection on California monthly rain MAE; other-region/weather/grid checks reported separately.','',
        '| Candidate | California 120 km MAE (mm/month) | Eligible | Years | Return | Humidity scale |',
        '|---|---:|---|---:|---|---:|']
    for i in order[:16]:
        r = rows[job_id(i,'california',SCREEN,41)]
        lines.append(f"| {i} | {r['score']:.2f} | {r['eligible']} | {r['years']} | {settings[i].terrain} | {settings[i].humidity_scale:g} |")
    lines += ['', 'Eligibility requires settling, budget closure, temperature departures <=5/10°C (lower/upper), '
        'annual rain ratio 0.5–1.75, >=80% coverage of observed non-arid land, and p99 rain <=4× observed. '
        'These are declared development screens, not independent uncertainty estimates. Diagnostic cases are labelled in the data.','',
        '## Transfer, weather and finer-grid checks','',
        '| Case | MAE (mm/month) | Eligible | Settled |','|---|---:|---|---|']
    for name,r in rows.items():
        if '_iberia_' in name or '_g60_' in name or '_g30_' in name or '_g15_' in name or not name.endswith('_s41'):
            lines.append(f"| {name} | {r['score']:.2f} | {r['eligible']} | {r['settling']['passed']} |")
    if state['failures']:lines += ['','## Numerical failures']+[f'- {key}: {error}' for key,error in state['failures'].items()]
    lines += ['', 'Full settings, frozen input/code hashes, monthly resume points and case budgets are retained beside this report. '
        'A budget stop is a resumable partial experiment, not completion of every planned check.']
    (out/'summary.md').write_text('\n'.join(lines)+'\n');atomic_json(out/'state.json',state)


def execute(out,settings,anchors,cases,profiles,budget_hours=9.,clock=time.monotonic,case_runner=run_case):
    path = out/'state.json'
    state = json.loads(path.read_text()) if path.exists() else {'status':'running','stage':'controls','cases':{},'failures':{},'selected':{},'invocations':[]}
    if state['status'] in ('complete','needs_diagnosis'):return state
    start = clock();deadline = start+budget_hours*3600;interrupted = [False]
    def request_stop(*_):interrupted[0] = True
    old_handler = signal.signal(signal.SIGINT,request_stop)
    invocation = {'started_utc':utc(),'budget_hours':budget_hours};state['invocations'].append(invocation)
    state['status'] = 'running'
    def stop():return interrupted[0] or clock()>=deadline
    def log(message):
        line = utc()+' '+message;print(line,flush=True)
        with (out/'run.log').open('a') as f:f.write(line+'\n')
    consecutive = 0
    def case(index,region,spacing=SCREEN,seed=41):
        nonlocal consecutive
        key = job_id(index,region,spacing,seed)
        manifest_path = out/'manifest.json'
        if manifest_path.exists():
            provenance = json.loads(manifest_path.read_text())
            if provenance['code_sha256']!=code_id():raise ValueError('Code changed during the overnight run; refusing mixed sources.')
        if key in state['cases']:
            if manifest_path.exists():
                evidence = state['cases'][key].get('evidence_sha256')
                if not evidence:raise ValueError('Completed case lacks evidence provenance.')
                for name,digest in evidence.items():
                    if sha256(out/'cases'/key/name)!=digest:raise ValueError('Completed case evidence changed.')
            return
        if key in state['failures']:return
        if stop():raise model.BudgetStop()
        if shutil.disk_usage(out).free<500*1024*1024:raise RuntimeError('Less than 500 MB disk space remains; checkpoint preserved.')
        if (region,spacing) not in cases:
            p = out/'inputs'/f'{region}_{spacing}km.npz'
            record = p.with_suffix('.json')
            if not p.exists():
                if manifest_path.exists():
                    for name,digest in provenance['raw_sha256'].items():
                        if sha256(ROOT/'data/v10_earth/raw'/name)!=digest:raise ValueError('Raw reference changed during run.')
                save_case(p,prepare_grid(region,spacing,ROOT/'data/v10_earth/raw'))
                atomic_json(record,{'sha256':sha256(p),'spacing_km':spacing,'inset_km':120})
            elif not record.is_file() or json.loads(record.read_text())['sha256']!=sha256(p):
                raise ValueError('Fine-grid prepared input integrity mismatch.')
            cases[region,spacing] = load_case(p,region)
        log(f'Start {key}; {(deadline-clock())/3600:.2f} hours left in this invocation.')
        try:
            row = case_runner(key,cases[region,spacing],profiles[region],settings[index],out,stop,log)
            state['cases'][key] = row;consecutive = 0
            log(f'{key}: MAE {row["score"]:.2f} mm/month; eligible={row["eligible"]}; {row["years"]} years.')
        except (FloatingPointError,RuntimeError) as e:
            state['failures'][key] = str(e);consecutive += 1;log(f'{key}: numerical failure: {e}')
            if consecutive>=5:raise RuntimeError('Five consecutive numerical failures; stopping for diagnosis.')
        report(out,state,settings)
    try:
        state['stage'] = 'controls';report(out,state,settings)
        for i in range(anchors):
            for region in ('california','iberia'):case(i,region)
        state['stage'] = 'parameter_coverage';report(out,state,settings)
        for i in range(anchors,len(settings)):case(i,'california')
        if 'weather' not in state['selected']:
            state['selected']['weather'] = ranked(state['cases'],candidate_indices(settings))[:8]
        state['stage'] = 'weather_and_transfer';report(out,state,settings)
        for i in state['selected']['weather']:
            for region in ('california','iberia'):
                for seed in (41,73,109):case(i,region,60,seed)
        if 'fine' not in state['selected']:
            # Refinement uses only configurations that qualify on both regions and all three checked weather seeds.
            state['selected']['fine'] = [i for i in state['selected']['weather'] if all(
                state['cases'].get(job_id(i,r,60,s),{}).get('eligible',False) for r in ('california','iberia') for s in (41,73,109))][:6]
        state['stage'] = 'grid30_weather_ensemble';report(out,state,settings)
        for i in state['selected']['fine']:
            for seed in (41,73,109,149,197,251,307,401):
                for region in ('california','iberia'):case(i,region,30,seed)
        state['stage'] = 'grid15_resolution';report(out,state,settings)
        for i in state['selected']['fine'][:2]:
            for region in ('california','iberia'):
                for seed in (41,73):case(i,region,15,seed)
        state['status'] = 'complete';state['stage'] = 'complete'
    except model.BudgetStop:
        state['status'] = 'interrupted' if interrupted[0] else 'budget_reached'
    except RuntimeError as e:
        state['status'] = 'needs_diagnosis';state['stop_reason'] = str(e)
    except (ValueError,OSError) as e:
        state['status'] = 'needs_diagnosis';state['stop_reason'] = 'Input/checkpoint error: '+str(e)
    finally:
        signal.signal(signal.SIGINT,old_handler)
        invocation.update(ended_utc=utc(),elapsed_seconds=clock()-start,status=state['status'])
        report(out,state,settings)
    return state


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true');p.add_argument('--hours',type=float,default=9.)
    p.add_argument('--prepare-only',action='store_true',help='Validate inputs and freeze the manifest without simulations.')
    p.add_argument('--out',type=Path,default=ROOT/'output/v10_overnight_20261015')
    args = p.parse_args(argv)
    if not 1<=args.hours<=10:p.error('--hours must be between 1 and 10.')
    settings,anchors = design()
    print(f'Overnight: {anchors} matched controls + {len(settings)-anchors} parameter settings at 120 km; then 60 km weather/transfer and 30/15 km refinement.',flush=True)
    print(f'{args.hours:g}-hour execution limit; monthly checkpoints; sequential simulations; no downloads or atlas publication.',flush=True)
    if args.run and args.prepare_only:p.error('Choose --run or --prepare-only.')
    if not args.run and not args.prepare_only:
        print('Read-only plan. Launch: caffeinate -i .venv/bin/python -u scripts/overnight_v10.py --run --hours 9');return 0
    try:
        _,base_cases,config = audit.saved_analysis(ROOT/'output/v10_earth_pilot',ROOT/'output/v10_heat_check',ROOT/'data/v10_earth')
        audit_record = json.loads((ROOT/'output/v10_forcing_audit/manifest.json').read_text())
        audit_code = hashlib.sha256(Path(audit.__file__).read_bytes()+Path(atmosphere.__file__).read_bytes()+heat.source_hash().encode()).hexdigest()
        texts,downloads = atmosphere.acquire(ROOT/'data/v10_atmosphere',False)
        if audit_record['code_sha256']!=audit_code or audit_record['reference_downloads']!=downloads:
            raise ValueError('Completed atmospheric audit does not match current sources/reference inputs.')
        profiles = prepare_profiles(base_cases,texts)
        raw = ROOT/'data/v10_earth/raw'
        expected = {'schema':1,'code_sha256':code_id(),'audit_manifest_sha256':sha256(ROOT/'output/v10_forcing_audit/manifest.json'),
            'raw_sha256':{name:sha256(raw/name) for name in SOURCES},
            'base_inputs_sha256':{r:sha256(ROOT/f'data/v10_earth/{r}_60km.npz') for r in base_cases},
            'profiles':profiles_json(profiles),'settings':[asdict(s) for s in settings],'anchors':anchors,
            'screen_spacing_km':SCREEN,'scoring_inset_km':120,
            'max_years':6,'minimum_years':3,'screen_seed':41,'runtime':{'python':sys.version.split()[0],'numpy':np.__version__}}
        out = args.out.resolve()
        if out==ROOT or any(parent in out.parents for parent in (ROOT/'data',ROOT/'atlas',ROOT/'rotclimate',ROOT/'rotclimate_v10',ROOT/'output/v10_earth_pilot',ROOT/'output/v10_heat_check',ROOT/'output/v10_forcing_audit')):
            raise ValueError('Use a separate output directory, preserving the frozen inputs/model/results.')
        manifest = out/'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text())!=expected:raise ValueError('Overnight provenance changed; use a new --out.')
        elif out.exists() and any(out.iterdir()):raise ValueError('Nonempty output lacks overnight provenance; use a new --out.')
        else:atomic_json(manifest,expected)
        if args.prepare_only:
            print(f'Prepared and verified: {manifest}. No simulations started.',flush=True);return 0
        cases = {(r,60):c for r,c in base_cases.items()}
        result = execute(out,settings,anchors,cases,profiles,args.hours)
        print(f'Finished invocation: {result["status"]}. Report: {out/"summary.md"}',flush=True)
        return 1 if result['status']=='needs_diagnosis' else 0
    except (ValueError,OSError,KeyError) as e:
        print(f'Cannot start overnight batch: {e}',file=sys.stderr);return 2


if __name__=='__main__':raise SystemExit(main())
