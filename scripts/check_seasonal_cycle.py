"""Frozen multi-year initialization pilot with exact historical controls."""
from dataclasses import asdict
from multiprocessing import Pool
from pathlib import Path
import importlib.metadata
import argparse
import json
import pickle
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from benchmark_local import DEV12_SPECS,temperature_metrics
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from rainfall_metrics import local_metrics
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.model import ClimateModel
from rotclimate.koppen import monthly_stats
from rotclimate.score import evaluate,objective


def run_one(job):
    name,years,params,kind,evidence,run,out,cell_km=job;out=Path(out);started=time.monotonic()
    folder=out/name;folder.mkdir(exist_ok=True)
    record=folder/f'years_{years}.json';cache=folder/f'years_{years}.pkl'
    if record.exists():
        row=json.loads(record.read_text())
        if row['identity']!=run or row['status']!='passed':raise ValueError('Changed inputs or preserved failed run: '+name)
        if kind=='earth':
            current_case=earth.region_case(name,float(cell_km))
            if row.get('case_identity')!=case_hash(current_case):
                raise ValueError('Saved derived Earth inputs differ: '+name)
        if file_hash(cache)!=row['checkpoint_sha256']:raise ValueError('Changed result checkpoint')
        return row
    p=Params(**params).replace(seasonal_spinup_years=years,seasonal_require_convergence=False)
    row=dict(name=name,extra_years=years,kind=kind,identity=run,params=asdict(p))
    try:
        if kind=='earth':
            case=earth.region_case(name,float(cell_km));row['case_identity']=case_hash(case)
            previous=json.loads((Path(evidence)/'cases'/f'{name}.json').read_text())
            if row['case_identity']!=previous['case_identity']:raise ValueError('Historical Earth inputs differ')
            cells_path=Path(evidence)/'cells'/f'{name}.npz'
            if file_hash(cells_path)!=previous['cells_sha256']:raise ValueError('Changed archived Earth cells')
            result=earth.run_case(p,case,steps=p.steps_per_year)
        else:
            case=None;result=ClimateModel(p).run()
        if not result.numerics.get('all_checks_passed'):raise ValueError('Per-step numerical checks failed')
        g=result.grid;st=monthly_stats(result.T,result.P,result.days,result.params.year_days,
            summer_solstice=result.params.winter_solstice_day+result.params.year_days/2)
        mask=g.inmap&g.land
        if case is not None:
            mask &= np.isfinite(case.obs_T).all(0)&np.isfinite(case.obs_P).all(0)
            if years==0:
                with np.load(cells_path) as old:
                    for key,value in [('Ts',st['Tm'][:,mask]),('Ps',np.maximum(st['Pm'][:,mask],0)),('To',case.obs_T[:,mask]),('Po',case.obs_P[:,mask])]:
                        if not np.array_equal(value.astype(np.float32),old[key]):raise ValueError('Legacy Earth control changed: '+key)
            row['temperature']=temperature_metrics(st['Tm'][:,mask],case.obs_T[:,mask])
            row['rain']=local_metrics(np.maximum(st['Pm'],0),np.nan_to_num(case.obs_P),mask)
        else:
            if years==0:
                with Path(evidence).open('rb') as stream:old=pickle.load(stream)['result']
                if asdict(old.params)!=asdict(p):raise ValueError('Cached world parameters differ')
                for key in ['T','Tsl','P','W','u','v','E']:
                    if not np.array_equal(getattr(result,key),getattr(old,key)):raise ValueError('Legacy world control changed: '+key)
            ev=evaluate(result);row['world']=dict(zonefit=objective(ev,'zonefit'),accuracy=ev['accuracy'],recall=ev['recall'])
        row['legacy_exact']=years==0
        if years:
            with (folder/'years_0.pkl').open('rb') as stream:baseline=pickle.load(stream)['result']
            previous=monthly_stats(baseline.T,baseline.P,baseline.days,baseline.params.year_days,
                summer_solstice=baseline.params.winter_solstice_day+baseline.params.year_days/2)
            changes={}
            for label,key in [('temperature_c','Tm'),('rain_mm_month','Pm')]:
                delta=st[key][:,mask]-previous[key][:,mask]
                changes[label]=dict(mean_absolute=float(np.abs(delta).mean()),maximum_absolute=float(np.abs(delta).max()),
                    mean_signed=float(delta.mean()),monthly_signed=delta.mean(1).tolist())
            row['change_from_default']=changes
        row.update(status='passed',numerics=result.numerics)
        with cache.with_suffix('.tmp').open('wb') as stream:pickle.dump(dict(identity=run,result=result),stream)
        cache.with_suffix('.tmp').replace(cache);row['checkpoint_sha256']=file_hash(cache)
    except Exception as error:row.update(status='failed',error=repr(error))
    row['seconds']=time.monotonic()-started;write_json(record,row)
    print(name+f' years={years}: '+row['status']+((' · cycle repeats='+str(row['numerics']['annual_cycle']['domain_repeats'])) if years and row['status']=='passed' else ''),flush=True)
    return row


def main():
    folder=ROOT/'calibration/seasonal_cycle_20261026';path=folder/'plan.json';plan=json.loads(path.read_text())
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,default=ROOT/'output/seasonal_cycle_20261026_verified')
    args=ap.parse_args();out=args.out.resolve();out.mkdir(exist_ok=True)
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    base=load_params(ROOT/plan['earth_params']);evidence=ROOT/plan['earth_legacy_evidence']
    cases={name:(base,'earth',str(evidence)) for name in plan['earth_regions']}
    for name,spec in plan['world_cases'].items():
        cases[name]=(load_params(ROOT/spec['params']).replace(downsample=plan['world_downsample'],beyond_seed=plan['world_seed']),
                     'world',str(ROOT/spec['legacy_checkpoint']))
    sources=list((ROOT/'rotclimate').glob('*.py'))+[p for p in (ROOT/'data/source').iterdir() if p.is_file()]+[path,Path(__file__),DEV12_SPECS,ROOT/plan['earth_params'],
        ROOT/'scripts/benchmark_local.py',ROOT/'scripts/earth_benchmark.py',ROOT/'scripts/rainfall_metrics.py',ROOT/'scripts/local_benchmark_protocol.py']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{name}.zip' for name in ['tavg','prec','elev','vapr']]
    for name in plan['earth_regions']:sources += [evidence/'cases'/f'{name}.json',evidence/'cells'/f'{name}.npz']
    for spec in plan['world_cases'].values():sources += [ROOT/spec['params'],ROOT/spec['legacy_checkpoint']]
    run=freeze(out/'protocol.json',dict(plan=plan,params={name:asdict(p) for name,(p,_,_) in cases.items()},
        source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','numba']}))
    for function,args in [(earth.west_fetch,(1700.,)),(earth.west_fetch,(5100.,)),(earth.pole_fetch,()),
                          (earth.sea_reach,()),(earth.land_cloud,()),(earth.monsoon_descent,()),(earth.sea_depth,())]:function(*args)
    rows=[]
    with Pool(2) as pool:
        for years in plan['extra_spinup_years']:
            print('Extra complete spin-up years:',years,flush=True)
            jobs=[(name,years,asdict(p),kind,evidence,run,str(out),plan['earth_cell_km']) for name,(p,kind,evidence) in cases.items()]
            for row in pool.imap_unordered(run_one,jobs):
                rows.append(row);write_json(out/'progress.json',dict(complete=False,records=rows))
            if years==0 and any(row['status']!='passed' for row in rows):raise RuntimeError('Exact legacy control failed; do not run candidates')
    final=dict(complete=True,identity=run,records=rows,physics_or_atlas_adoption=False,
        all_per_step_checks_passed=all(row['status']=='passed' for row in rows),
        designated_three_year_case_repeats=all(row['status']=='passed' and row['numerics']['annual_cycle']['domain_repeats'] for row in rows if row['extra_years']==3),
        note='Initialization and numerical-repeatability pilot, not a physical parameter search. Defaults and published climates remain unchanged.')
    write_json(out/'review.json',final);write_json(out/'progress.json',final)
    print('Seasonal-cycle pilot complete',flush=True)


if __name__=='__main__':main()
