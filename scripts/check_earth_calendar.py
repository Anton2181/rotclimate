"""Paired observation-calendar audit with exact old-score controls."""
from pathlib import Path
from dataclasses import asdict
from multiprocessing import Pool
import importlib.metadata
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from benchmark_local import DEV12_SPECS,temperature_metrics
from earth_benchmark import load_params
from earth_calendar import monthly_stats as gregorian_stats
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from rainfall_metrics import local_metrics
from rotclimate import earth,joint
from rotclimate.koppen import monthly_stats as equal_stats
from rotclimate.model import ClimateModel


def one(job):
    name,plan,identity,out=job
    out=Path(out);path=out/f'{name}.json';arrays=out/f'{name}.npz'
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case=earth.region_case(name,float(plan['cell_km']));derived=case_hash(case)
    if path.exists():
        row=json.loads(path.read_text())
        if (row['identity']!=identity or row['case_identity']!=derived or row['status']!='passed'
                or not row['numerics']['all_checks_passed'] or file_hash(arrays)!=row['arrays_sha256']):
            raise ValueError('Changed calendar audit inputs or preserved failed run')
        return row
    row=dict(region=name,identity=identity,case_identity=derived);started=time.monotonic()
    try:
        p=earth.earth_params(joint.earth_profile(load_params(ROOT/plan['physics'])),case)
        model=ClimateModel(p,grid=case.grid);result=model.run();row['numerics']=result.numerics
        if not result.numerics['all_checks_passed']:raise ValueError('Numerical control failed')
        old=equal_stats(result.T,result.P,result.days,p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
        g=case.grid;mask=g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        archive=ROOT/plan['archive'];previous=json.loads((archive/'cases'/f'{name}.json').read_text())
        old_cells=archive/'cells'/f'{name}.npz'
        if derived!=previous['case_identity'] or file_hash(old_cells)!=previous['cells_sha256']:
            raise ValueError('Archived geography or cell inputs changed')
        with np.load(old_cells) as z:
            for key,value in [('Ts',old['Tm'][:,mask]),('Ps',old['Pm'][:,mask]),
                              ('To',case.obs_T[:,mask]),('Po',case.obs_P[:,mask])]:
                if not np.array_equal(value.astype(np.float32),z[key]):raise ValueError('Legacy control changed: '+key)
        mirrored=earth.REGIONS[name]['lat0']<0
        new=gregorian_stats(result.T,result.P,result.days,mirrored=mirrored)
        annual_delta=float(np.max(np.abs((new['Pm'].sum(0)-old['Pm'].sum(0))[mask])))
        if annual_delta>1e-8:raise ValueError('Calendar aggregation lost annual precipitation')
        scores={}
        for label,values in [('equal',old),('gregorian',new)]:
            scores[label]=dict(temperature=temperature_metrics(values['Tm'][:,mask],case.obs_T[:,mask]),
                rain=local_metrics(values['Pm'],np.nan_to_num(case.obs_P),mask),
                monthly_temperature=values['Tm'][:,mask].mean(1).tolist(),
                monthly_rain=values['Pm'][:,mask].mean(1).tolist())
        with arrays.with_suffix('.tmp').open('wb') as stream:
            np.savez_compressed(stream,days=result.days,T=result.T[:,mask],P=result.P[:,mask],
                observed_T=case.obs_T[:,mask],observed_P=case.obs_P[:,mask],
                equal_T=old['Tm'][:,mask],equal_P=old['Pm'][:,mask],
                gregorian_T=new['Tm'][:,mask],gregorian_P=new['Pm'][:,mask],
                original_month=new['original_month'],month_days=new['month_days'])
        arrays.with_suffix('.tmp').replace(arrays)
        row.update(status='passed',legacy_exact=True,params=asdict(p),mirrored=mirrored,scores=scores,
            observed_month_order=new['original_month'].tolist(),month_days=new['month_days'].tolist(),
            observed_mean_rain=case.obs_P[:,mask].mean(1).tolist(),
            annual_rain_integral_max_difference_mm=annual_delta,arrays_sha256=file_hash(arrays))
    except Exception as error:row.update(status='failed',error=repr(error))
    row['seconds']=time.monotonic()-started;write_json(path,row)
    print(name+': '+row['status'],flush=True)
    return row


def main():
    path=ROOT/'calibration/earth_calendar_20261026/plan.json';plan=json.loads(path.read_text())
    out=ROOT/'output/earth_calendar_20261026';out.mkdir(exist_ok=True)
    sources=list((ROOT/'rotclimate').glob('*.py'))+[path,Path(__file__),ROOT/'scripts/earth_calendar.py',
        ROOT/plan['physics'],DEV12_SPECS,ROOT/'scripts/benchmark_local.py',ROOT/'scripts/earth_benchmark.py',
        ROOT/'scripts/rainfall_metrics.py',ROOT/'scripts/local_benchmark_protocol.py']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{key}.zip' for key in ['tavg','prec','elev','vapr']]
    for name in plan['regions']:sources += [ROOT/plan['archive']/'cases'/f'{name}.json',ROOT/plan['archive']/'cells'/f'{name}.npz']
    identity=freeze(out/'protocol.json',dict(plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','numba']}))
    with Pool(2) as pool:rows=pool.map(one,[(name,plan,identity,str(out)) for name in plan['regions']])
    complete=all(r['status']=='passed' for r in rows)
    write_json(out/'review.json',dict(complete=complete,identity=identity,records=rows,
        physics_or_atlas_adoption=False,benchmark_default_change=False,scope=plan['decision']))
    if not complete:raise SystemExit('Failed calendar controls retained; do not interpret new scores')


if __name__=='__main__':main()
