"""Fixed Earth mechanism check: energy feedback, then terrain-drag ablation.

Default prints a read-only plan. --run reuses the four verified original pilot
cases, runs eight coupled cases, and extends only the unsettled original
Iberia mean-flow control by at most two years. Never updates the atlas.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np

from scripts.diagnose_v10_pilot import load_verified
from scripts import run_v10_pilot as pilot
from experiments import v10_thermodynamics as thermal
from rotclimate_v10.core import State
from rotclimate_v10.earth import atomic_json,atomic_npz,sha256
from rotclimate_v10.integrate import YearResult,rain_metrics,settling

PROPOSALS = {'heat':thermal.Closure(), 'heat_no_drag':thermal.Closure(terrain_drag=False)}


def source_hash():
    h = hashlib.sha256(pilot.code_hash().encode())
    for path in (ROOT/'experiments/v10_thermodynamics.py',ROOT/'scripts/diagnose_v10_pilot.py',Path(__file__).resolve()):
        h.update(str(path.relative_to(ROOT)).encode());h.update(path.read_bytes())
    return h.hexdigest()


def validate(result,shape):
    r = result;w = r.state.water;b = r.budget
    if any(a.shape!=shape or not np.isfinite(a).all() or (a<0).any() for a in (w.lower,w.upper,w.soil)):
        raise ValueError('Invalid coupled water stores.')
    if any(a.shape!=shape or not np.isfinite(a).all() for a in (r.state.lower_energy,r.state.upper_energy)):
        raise ValueError('Invalid coupled energy stores.')
    if r.rain_mm.shape!=(12,)+shape or not np.isfinite(r.rain_mm).all() or (r.rain_mm<0).any():
        raise ValueError('Invalid coupled rainfall.')
    for a in (r.lower_temperature_c,r.upper_temperature_c,r.reference_temperature_c):
        if a.shape!=(12,)+shape or not np.isfinite(a).all() or a.min()<-123.15 or a.max()>96.85:
            raise ValueError('Invalid coupled monthly temperatures.')
    if (not np.isfinite(list(b.values())).all() or abs(b['annual_water_error_mm'])>1e-6
        or b['max_step_water_error_mm']>1e-9 or abs(b['annual_energy_error_j_m2'])>1.
        or b['max_step_energy_error_j_m2']>1e-5 or b['max_air_continuity_kg_m2_s']>1e-10 or b['min_store_mm']<0):
        raise ValueError('Failed coupled water/static-energy budget.')


def save_year(folder,y,r,elapsed):
    validate(r,r.state.water.lower.shape)
    path = folder/f'year{y}.npz'
    atomic_npz(path,lower=r.state.water.lower,upper=r.state.water.upper,soil=r.state.water.soil,
        lower_energy=r.state.lower_energy,upper_energy=r.state.upper_energy,rain_mm=r.rain_mm,
        lower_temperature_c=r.lower_temperature_c,upper_temperature_c=r.upper_temperature_c,
        reference_temperature_c=r.reference_temperature_c)
    atomic_json(folder/f'year{y}.json',{'year':y,'array_sha256':sha256(path),'budget':r.budget,'elapsed_seconds':elapsed})


def read_year(folder,y,shape):
    record = folder/f'year{y}.json';path = folder/f'year{y}.npz'
    if not record.exists():return None
    info = json.loads(record.read_text())
    if not path.is_file() or info.get('year')!=y or info.get('array_sha256')!=sha256(path):
        raise ValueError('Invalid coupled checkpoint; use a fresh --out directory.')
    with np.load(path,allow_pickle=False) as a:
        w = State(*(a[k] for k in ('lower','upper','soil')))
        s = thermal.ThermalState(w,a['lower_energy'],a['upper_energy'])
        r = thermal.ThermalYear(s,a['rain_mm'],a['lower_temperature_c'],a['upper_temperature_c'],a['reference_temperature_c'],info['budget'])
    validate(r,shape);return r


def stability(a,b,case,config):
    old = YearResult(a.state.water,a.rain_mm,{})
    new = YearResult(b.state.water,b.rain_mm,{})
    check = settling(old,new,case.score_mask)
    monthly = max(float(np.percentile(abs(x-y)[:,case.score_mask],95)) for x,y in zip(
        (a.lower_temperature_c,a.upper_temperature_c),(b.lower_temperature_c,b.upper_temperature_c)))
    ml,mu,_ = thermal.air_masses(case.domain,config);zl,zu = thermal.levels(case.domain,config)
    end = max(float(np.percentile(abs(thermal.temperature(e2,m,w2,z)-thermal.temperature(e1,m,w1,z)),95))
        for e1,e2,m,w1,w2,z in ((a.state.lower_energy,b.state.lower_energy,ml,a.state.water.lower,b.state.water.lower,zl),
                              (a.state.upper_energy,b.state.upper_energy,mu,a.state.water.upper,b.state.water.upper,zu)))
    check.update(monthly_temperature_p95_change_c=monthly,end_temperature_p95_change_c=end,
                 temperature_change_limit_c=.05)
    check['passed'] = bool(check['passed'] and monthly<=.05 and end<=.05)
    return check


def temperature_diagnostics(result,case,config):
    diffs = [result.lower_temperature_c-result.reference_temperature_c-config.lower_temperature_offset_c,
             result.upper_temperature_c-result.reference_temperature_c-config.upper_temperature_offset_c]
    out = {}
    for name,delta in zip(('lower','upper'),diffs):
        values = delta[:,case.score_mask]
        out[name] = {'monthly_abs_departure_p95_c':float(np.percentile(abs(values),95)),
                     'monthly_mean_departure_c':float(values.mean()),'monthly_max_abs_departure_c':float(abs(values).max())}
    out['provisional_guard'] = {'lower_p95_limit_c':5.,'upper_p95_limit_c':10.}
    out['provisional_guard_passed'] = bool(out['lower']['monthly_abs_departure_p95_c']<=5 and out['upper']['monthly_abs_departure_p95_c']<=10)
    return out


def run_case(case,config,closure,folder,storms,integrator=thermal.integrate_year):
    folder.mkdir(parents=True,exist_ok=True);state = thermal.initial_state(case.domain,config);years = []
    for y in (1,2,3):
        result = read_year(folder,y,case.domain.land.shape)
        if result is None:
            start = time.monotonic()
            def progress(month,steps):
                elapsed = time.monotonic()-start
                atomic_json(folder/'progress.json',{'case':folder.name,'year':y,'month_completed':month,
                    'steps':steps,'elapsed_seconds_this_year':elapsed,'updated_utc':datetime.now(timezone.utc).isoformat()})
                print(f'{folder.name}, year {y}/3, month {month}/12: {elapsed/60:.2f} min; '
                      f'this year about {elapsed*(12-month)/month/60:.2f} min remaining.',flush=True)
            result = integrator(case.domain,config,closure,state,storms=storms,progress=progress)
            validate(result,case.domain.land.shape);save_year(folder,y,result,time.monotonic()-start)
        else:print(f'{folder.name}: reusing verified year {y}.',flush=True)
        years.append(result);state = result.state
    check = stability(years[1],years[2],case,config);temp = temperature_diagnostics(result,case,config)
    annual = result.rain_mm.sum(0)
    summary = {'region':case.domain.name,'mode':'storms' if storms else 'mean_only','closure':asdict(closure),
        'settling':check,'temperature_departure':temp,'rainfall':rain_metrics(case,result.rain_mm),
        'annual_rain_p99_mm':float(np.percentile(annual[case.score_mask],99)),
        'annual_rain_max_mm':float(annual[case.score_mask].max()),'budgets':[r.budget for r in years],
        'eligible_for_mechanism_comparison':bool(check['passed'] and temp['provisional_guard_passed']),
        'atlas_updated':False}
    atomic_json(folder/'summary.json',summary)
    return summary,result


def extend_baseline(region,mode,case,years,config,folder,integrator=pilot.integrate_year):
    """At most two extra unchanged years; save outside original pilot directory."""
    folder.mkdir(parents=True,exist_ok=True);previous = years[-1]
    for y in (4,5):
        r = pilot.read_year(folder,y,case.domain.land.shape)
        if r is None:
            start = time.monotonic()
            def progress(month,steps):
                print(f'{region}_{mode} unchanged extension, year {y}/5, month {month}/12: '
                      f'{(time.monotonic()-start)/60:.2f} min',flush=True)
            r = integrator(case.domain,config,previous.state,storms=mode=='storms',progress=progress)
            pilot.validate_result(r,case.domain.land.shape);pilot.write_year(folder,y,r,time.monotonic()-start)
        check = settling(previous,r,case.score_mask)
        if check['passed']:return r,check,y
        previous = r
    return r,check,5


def write_summary(out,rows,baselines,failures):
    lines = ['# V10 heat and terrain mechanism test','',
        'Fixed circulation and observed temperature relaxation targets; no calibration or atlas update.',
        'Eight coupled cases with five-day temperature relaxation, plus at most two unchanged baseline settling years.','',
        '| Region / case | Monthly rain MAE (mm) | Rain p99 (mm/year) | Settled | Lower / upper T departure p95 (°C) |',
        '|---|---:|---:|---|---:|']
    for name,s in baselines.items():
        lines.append(f"| {name} original (year {s['year']}) | {s['rainfall']['monthly_mae_mm']:.2f} | {s['annual_rain_p99_mm']:.0f} | {s['settling']['passed']} | prescribed |")
    for name,s in rows.items():
        t = s['temperature_departure']
        lines.append(f"| {name} | {s['rainfall']['monthly_mae_mm']:.2f} | {s['annual_rain_p99_mm']:.0f} | "
                     f"{s['settling']['passed']} | {t['lower']['monthly_abs_departure_p95_c']:.2f} / {t['upper']['monthly_abs_departure_p95_c']:.2f} |")
    lines += ['', 'Lower rainfall error is not sufficient: inspect water/static-energy budgets, settling, and temperature departures.',
        'Provisional departure guards: monthly p95 <=5°C lower / <=10°C upper. These are declared screening choices, not an independently validated energy closure.',
        'The heat case changes thermal transport, latent feedback, and finite relaxation together; it does not isolate each one separately. '
        'The no-drag case additionally removes only the terrain term from the prescribed circulation; real terrain, air masses, temperatures and reference rain are retained.',
        'Observed temperatures remain relaxation targets and boundary forcing. Do not claim independent temperature prediction. '
        'Surface evaporation latent enthalpy and the relaxation reservoir are explicit external energy inputs; this is not a closed Earth energy budget.']
    if failures:lines += ['','## Failed cases']+[f"- {name}: {error}" for name,error in failures.items()]
    (out/'summary.md').write_text('\n'.join(lines)+'\n')
    atomic_json(out/'summary.json',{'cases':rows,'baselines':baselines,'failures':failures,'atlas_updated':False})


def plot_region(case,results,baselines,out,config):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    mask = case.score_mask;x = np.arange(1,13);region = case.domain.name
    for col,mode in enumerate(('storms','mean_only')):
        axes[0,col].plot(x,case.observed_rain_mm[:,mask].mean(1),'k-',label='Observed')
        axes[0,col].plot(x,baselines[region,mode].rain_mm[:,mask].mean(1),':',label='Original')
        for proposal in PROPOSALS:
            name = f'{region}_{mode}_{proposal}'
            if name not in results:continue
            s,r = results[name]
            label = proposal+(' (unsettled)' if not s['settling']['passed'] else '')
            axes[0,col].plot(x,r.rain_mm[:,mask].mean(1),label=label)
            delta = r.lower_temperature_c-r.reference_temperature_c
            axes[1,col].plot(x,(delta[:,mask]-config.lower_temperature_offset_c).mean(1),label=label)
        axes[0,col].set(title=mode.replace('_',' '),xlabel='Month',ylabel='Rain (mm/month)');axes[0,col].legend()
        axes[1,col].axhline(0,color='k',linewidth=.7);axes[1,col].set(xlabel='Month',ylabel='Lower air minus reference (°C)');axes[1,col].legend()
    fig.suptitle(f'{region}: heat feedback and terrain ablation; observed T remains forcing')
    fig.savefig(out/f'{region}_heat_check.png',dpi=140);plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true')
    p.add_argument('--source',type=Path,default=ROOT/'output/v10_earth_pilot')
    p.add_argument('--cache',type=Path,default=ROOT/'data/v10_earth')
    p.add_argument('--out',type=Path,default=ROOT/'output/v10_heat_check')
    args = p.parse_args(argv)
    print('Heat + terrain check: reuse original data/results; eight fixed coupled cases, three years each.',flush=True)
    print('Extend unsettled original control by at most two years. No search, download or atlas publication.',flush=True)
    if not args.run:
        print('Read-only plan. To execute: caffeinate -i .venv/bin/python -u scripts/check_v10_thermodynamics.py --run')
        return 0
    try:
        source = args.source.resolve();out = args.out.resolve()
        if source==out or source in out.parents:raise ValueError('Use a separate --out directory; preserve the original pilot.')
        manifest,config,cases,saved = load_verified(args.source,args.cache)
        expected = {'schema':1,'code_sha256':source_hash(),'baseline_manifest_sha256':sha256(source/'manifest.json'),
            'original_code_sha256':manifest['code_sha256'],'config':asdict(config),
            'closures':{name:asdict(c) for name,c in PROPOSALS.items()},'years':3,
            'runtime':{'python':sys.version.split()[0],'numpy':np.__version__},
            'temperature_departure_p95_guards_c':{'lower':5.,'upper':10.},
            'original_checkpoints':{str(path.relative_to(source)):sha256(path) for path in sorted(source.glob('*/year*.json'))}}
        path = out/'manifest.json'
        if path.exists():
            if json.loads(path.read_text())!=expected:raise ValueError('Changed experiment provenance: use a fresh --out directory.')
        elif out.exists() and any(out.iterdir()):raise ValueError('Nonempty output lacks provenance: use a fresh --out directory.')
        else:atomic_json(path,expected)
        rows = {};base = {};base_results = {};results = {};failures = {}
        for (region,mode),years in saved.items():
            case = cases[region];r = years[-1];check = settling(years[1],r,case.score_mask);year = 3
            if not check['passed']:
                try:r,check,year = extend_baseline(region,mode,case,years,config,out/f'{region}_{mode}_unchanged_extension')
                except (ValueError,RuntimeError,FloatingPointError,OSError) as e:failures[f'{region}_{mode}_extension'] = str(e)
            name = f'{region}_{mode}';base_results[region,mode] = r
            base[name] = {'region':region,'mode':mode,'year':year,'settling':check,'rainfall':rain_metrics(case,r.rain_mm),
                         'annual_rain_p99_mm':float(np.percentile(r.rain_mm.sum(0)[case.score_mask],99))}
        write_summary(out,rows,base,failures)
        for region,case in cases.items():
            for proposal,closure in PROPOSALS.items():
                for mode in ('storms','mean_only'):
                    name = f'{region}_{mode}_{proposal}'
                    try:
                        result = run_case(case,config,closure,out/name,mode=='storms')
                        rows[name] = result[0];results[name] = result
                        print(f"{name}: monthly rain MAE {result[0]['rainfall']['monthly_mae_mm']:.2f} mm; "
                              f"settled={result[0]['settling']['passed']}; T guard={result[0]['temperature_departure']['provisional_guard_passed']}",flush=True)
                    except (ValueError,RuntimeError,FloatingPointError,OSError) as e:
                        failures[name] = str(e);atomic_json(out/name/'failure.json',{'case':name,'error':str(e)})
                        print(f'{name}: FAILED: {e}',flush=True)
                    write_summary(out,rows,base,failures)
            if any(name.startswith(region+'_') for name in results):plot_region(case,results,base_results,out,config)
        print(f'Finished: {out/"summary.md"}',flush=True)
        return 1 if failures else 0
    except (ValueError,OSError,KeyError) as e:
        print(f'Cannot run mechanism check: {e}',file=sys.stderr,flush=True);return 2


if __name__=='__main__':raise SystemExit(main())
