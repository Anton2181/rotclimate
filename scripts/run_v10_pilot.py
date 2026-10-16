#!/usr/bin/env python3
"""Opt-in fixed-physics Earth rainfall pilot. Default only describes the work."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np

from rotclimate_v10.core import Config,State,initial_state
from rotclimate_v10.earth import (REGIONS,SCHEMA,SOURCES,atomic_json,atomic_npz,fetch_raw,
                                load_case,prepare_region,save_case,sha256)
from rotclimate_v10.integrate import YearResult,integrate_year,rain_metrics,settling


def code_hash():
    h = hashlib.sha256()
    paths = sorted((ROOT/'rotclimate_v10').glob('*.py'))+[Path(__file__).resolve()]
    for path in paths:
        h.update(str(path.relative_to(ROOT)).encode());h.update(path.read_bytes())
    return h.hexdigest()


def prepare_inputs(cache,spacing,fetch):
    cache = Path(cache)
    if fetch:fetch_raw(cache)
    raw = cache/'raw'
    missing = [name for name in SOURCES if not (raw/name).is_file()]
    if missing:
        raise ValueError('Missing Earth inputs. Run the same command with --fetch --run (about 46 MB).')
    raw_hashes = {name:sha256(raw/name) for name in SOURCES}
    expected = {'schema':SCHEMA,'spacing_km':spacing,'raw_sha256':raw_hashes,'preparation_code_sha256':sha256(ROOT/'rotclimate_v10/earth.py')}
    manifest_path = cache/f'prepared_{spacing:g}km.json'
    paths = {name:cache/f'{name}_{spacing:g}km.npz' for name in REGIONS}
    if manifest_path.exists():
        saved = json.loads(manifest_path.read_text())
        if saved.get('inputs') == expected and all(p.exists() and sha256(p)==saved.get('prepared_sha256',{}).get(name) for name,p in paths.items()):
            return paths
    for name,path in paths.items():
        print(f'Preparing {name} at {spacing:g} km...',flush=True)
        save_case(path,prepare_region(name,raw,spacing))
    atomic_json(manifest_path,{'inputs':expected,'prepared_sha256':{name:sha256(p) for name,p in paths.items()}})
    return paths


def validate_result(result,shape):
    state,rain,budget = result.state,result.rain_mm,result.budget
    if any(x.shape != shape or not np.isfinite(x).all() or (x<0).any() for x in (state.lower,state.upper,state.soil)):
        raise ValueError('Invalid checkpoint stores.')
    if rain.shape != (12,)+shape or not np.isfinite(rain).all() or (rain<0).any():
        raise ValueError('Invalid checkpoint rainfall.')
    if (not np.isfinite(list(budget.values())).all() or abs(budget['annual_water_error_mm'])>1e-6
        or budget['max_step_water_error_mm']>1e-9 or budget['max_air_continuity_kg_m2_s']>1e-10 or budget['min_store_mm']<0):
        raise ValueError('Checkpoint has a failed physical budget.')


def write_year(folder,number,result,elapsed):
    validate_result(result,result.state.lower.shape)
    arrays = folder/f'year{number}.npz';record = folder/f'year{number}.json'
    atomic_npz(arrays,lower=result.state.lower,upper=result.state.upper,soil=result.state.soil,rain_mm=result.rain_mm)
    atomic_json(record,{'year':number,'array_sha256':sha256(arrays),'budget':result.budget,'elapsed_seconds':elapsed})


def read_year(folder,number,shape):
    arrays = folder/f'year{number}.npz';record = folder/f'year{number}.json'
    if not record.exists():return None  # uncommitted .npz is intentionally ignored
    info = json.loads(record.read_text())
    if not arrays.exists() or info.get('year') != number or sha256(arrays) != info.get('array_sha256'):
        raise ValueError(f'Invalid checkpoint: {folder}, year {number}. Use a fresh --out; keep the old evidence.')
    with np.load(arrays,allow_pickle=False) as a:
        state = State(*(a[k] for k in ('lower','upper','soil')))
        rain = a['rain_mm']
    budget = info['budget']
    result = YearResult(state,rain,budget)
    validate_result(result,shape)
    return result


def run_case(case,config,folder,storms,integrator=integrate_year):
    folder.mkdir(parents=True,exist_ok=True)
    state = initial_state(case.domain,config)
    years = []
    for year in range(1,4):
        cached = read_year(folder,year,case.domain.land.shape)
        if cached is not None:
            print(f'{folder.name}, year {year}/3: reusing verified checkpoint.',flush=True)
            result = cached
        else:
            start = time.monotonic()
            def progress(month,steps):
                elapsed = time.monotonic()-start
                remaining = elapsed*(12-month)/month
                atomic_json(folder/'progress.json',{'case':folder.name,'year':year,'month_completed':month,
                    'steps_this_year':steps,'elapsed_seconds_this_year':elapsed,
                    'estimated_seconds_left_this_year':remaining,'updated_utc':datetime.now(timezone.utc).isoformat()})
                print(f'{folder.name}, year {year}/3, month {month}/12: {steps} steps, '
                      f'{elapsed/60:.1f} min; this year about {remaining/60:.1f} min remaining.',flush=True)
            result = integrator(case.domain,config,state,storms=storms,progress=progress)
            validate_result(result,case.domain.land.shape)
            write_year(folder,year,result,time.monotonic()-start)
        years.append(result);state = result.state
    stability = settling(years[1],years[2],case.score_mask)
    summary = {'region':case.domain.name,'mode':'storms' if storms else 'mean_only',
               'settling':stability,'eligible_for_physics_comparison':stability['passed'],
               'rainfall':rain_metrics(case,years[2].rain_mm),'budgets':[r.budget for r in years],
               'note':'Rainfall benchmark only. Observed temperatures are forcing, never scored as a prediction.'}
    atomic_json(folder/'summary.json',summary)
    return summary,years[2].rain_mm


def plot_comparison(case,results,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes = plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    mask = case.score_mask
    obs = case.observed_rain_mm
    axes[0,0].plot(np.arange(1,13),obs[:,mask].mean(axis=1),'k-',label='Observed')
    for mode,(summary,rain) in results.items():
        label = mode.replace('_',' ')+(' (unsettled)' if not summary['settling']['passed'] else '')
        axes[0,0].plot(np.arange(1,13),rain[:,mask].mean(axis=1),label=label)
    axes[0,0].set(xlabel='Month',ylabel='Rain (mm/month)',title='Scored land mean');axes[0,0].legend()
    annual_obs = obs.sum(axis=0)
    vmax = max(1.,float(np.percentile(annual_obs[mask],98)))
    def panel(ax,data,title,cmap='Blues',limits=None):
        data = np.where(mask,data,np.nan)
        dlat = case.domain.dy/111195.
        dlon = case.domain.dx/(111195.*np.cos(np.deg2rad(case.domain.latitude.mean())))
        extent = [case.longitude.min()-.5*dlon,case.longitude.max()+.5*dlon,
                  case.domain.latitude.min()-.5*dlat,case.domain.latitude.max()+.5*dlat]
        im = ax.imshow(data,extent=extent,origin='upper',cmap=cmap,**(limits or {}))
        ax.set(title=title,xlabel='Longitude',ylabel='Latitude');fig.colorbar(im,ax=ax,label='mm/year')
    panel(axes[0,1],annual_obs,'Observed rain',limits={'vmin':0,'vmax':vmax})
    for ax,mode in zip(axes[1],('storms','mean_only')):
        summary,rain = results[mode]
        error = rain.sum(axis=0)-annual_obs
        v = max(1.,float(np.percentile(abs(error[mask]),98)))
        panel(ax,error,mode.replace('_',' ')+' rain error',cmap='RdBu',limits={'vmin':-v,'vmax':v})
    fig.suptitle(case.domain.name+' — prescribed temperature; pilot rainfall only')
    fig.savefig(out/f'{case.domain.name}_rainfall.png',dpi=140);plt.close(fig)


def summary_report(out,summaries,failures):
    lines = ['# V10 Earth rainfall pilot','',
        'Fixed physics, observed temperature/SST forcing; no calibration and no atlas publication.',
        'WorldClim 1970–2000 land normals; NOAA OISST 1971–2000 sea normals (one-year period difference).',
        'Sea data provided by [NOAA PSL, Boulder, Colorado, USA](https://psl.noaa.gov/). '
        'Land data: [WorldClim 2.1](https://www.worldclim.org/data/worldclim21.html).',
        'A three-year repeated forcing cycle is a settling check, not three independent climate samples.','',
        '| Region / mode | Settled | Annual bias (mm) | Annual RMSE (mm) | Monthly MAE (mm) | Winter fraction MAE |',
        '|---|---|---:|---:|---:|---:|']
    for s in summaries:
        m = s['rainfall'];fraction = m['winter_fraction_mae']
        seasonal = f'{fraction:.3f}' if fraction is not None else 'n/a'
        lines.append(f"| {s['region']} / {s['mode']} | {s['settling']['passed']} | {m['annual_bias_mm']:.1f} | "
                     f"{m['annual_rmse_mm']:.1f} | {m['monthly_mae_mm']:.1f} | {seasonal} |")
    lines += ['', 'Unsettled cases are diagnostic only. Small water-budget errors establish accounting, not rainfall skill.',
              'No target-zone labels or observed precipitation enter the transport, evaporation or weather forcing.']
    for region in REGIONS:
        by_mode = {s['mode']:s for s in summaries if s['region']==region}
        if len(by_mode)==2:
            a,b = by_mode['storms'],by_mode['mean_only']
            eligible = a['settling']['passed'] and b['settling']['passed']
            delta = a['rainfall']['monthly_mae_mm']-b['rainfall']['monthly_mae_mm']
            lines.append(f'\n{region}: storms minus mean-only monthly MAE = {delta:+.2f} mm '
                         f'(negative favours storms); eligible settled comparison: {eligible}.')
    if failures:
        lines += ['','## Failed cases']+[f"- {f['case']}: {f['error']}" for f in failures]
    (out/'summary.md').write_text('\n'.join(lines)+'\n')
    atomic_json(out/'summary.json',{'cases':summaries,'failures':failures,'atlas_updated':False})


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',action='store_true',help='Run four cases, three years each, sequentially.')
    p.add_argument('--fetch',action='store_true',help='Download/prepare official public inputs (requires --run).')
    p.add_argument('--out',type=Path,default=ROOT/'output/v10_earth_pilot')
    p.add_argument('--cache',type=Path,default=ROOT/'data/v10_earth')
    p.add_argument('--spacing-km',type=float,default=60.)
    args = p.parse_args(argv)
    if not 30<=args.spacing_km<=200:p.error('Spacing must be 30–200 km.')
    if args.fetch and not args.run:p.error('--fetch requires --run; default mode never writes or downloads.')
    print('V10 rainfall pilot: California and Iberia; storms vs mean flow, 3 repeated years each, sequentially.',flush=True)
    print(f'Grid: {args.spacing_km:g} km. Four cases / twelve simulated years. Fixed physics; no calibration or atlas update.',flush=True)
    print('Year 1 warms up; years 2 and 3 test settling. Observed temperature is forcing, not a prediction.',flush=True)
    if not args.run:
        print('Read-only plan. About 46 MB of public input downloads. To execute:\n'
              'caffeinate -i .venv/bin/python -u scripts/run_v10_pilot.py --fetch --run')
        return 0
    try:
        paths = prepare_inputs(args.cache,args.spacing_km,args.fetch)
        config = Config();config.validate()
        expected = {'schema':1,'code_sha256':code_hash(),'config':asdict(config),'spacing_km':args.spacing_km,
                    'prepared_sha256':{name:sha256(path) for name,path in paths.items()},'years':3,
                    'cases':[f'{name}_{mode}' for name in REGIONS for mode in ('storms','mean_only')]}
        manifest = args.out/'manifest.json'
        if manifest.exists():
            if json.loads(manifest.read_text()) != expected:
                raise ValueError('Output provenance differs from this code/config/input. Use a new --out directory.')
        elif args.out.exists() and any(args.out.iterdir()):
            raise ValueError('Nonempty output directory has no manifest. Use a new --out directory.')
        else:atomic_json(manifest,expected)
        summaries = [];failures = []
        for region,path in paths.items():
            case = load_case(path,region);results = {}
            print(f'{region}: {case.domain.land.shape}, {case.score_mask.sum()} scored land cells; '
                  f'{case.temperature_imputed.sum()} land temperature cells imputed/excluded.',flush=True)
            for mode in ('storms','mean_only'):
                label = f'{region}_{mode}'
                try:
                    result = run_case(case,config,args.out/label,storms=mode=='storms')
                    summaries.append(result[0]);results[mode] = result
                    print(f"{label}: settled={result[0]['settling']['passed']}, monthly rain MAE "
                          f"{result[0]['rainfall']['monthly_mae_mm']:.1f} mm",flush=True)
                except (ValueError,RuntimeError,FloatingPointError,OSError) as e:
                    failure = {'case':label,'error':str(e)};failures.append(failure)
                    atomic_json(args.out/label/'failure.json',failure)
                    print(f'{label}: FAILED: {e}',flush=True)
                summary_report(args.out,summaries,failures)
            if len(results)==2:plot_comparison(case,results,args.out)
        print(f'Pilot finished. Report: {args.out / "summary.md"}',flush=True)
        return 1 if failures else 0
    except (ValueError,OSError,KeyError,zipfile.BadZipFile) as e:
        print(f'Cannot run pilot: {e}',file=sys.stderr,flush=True)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
