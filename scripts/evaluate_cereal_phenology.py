"""Declared training and separately committed evaluation of a daily cereal clock."""
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.phenology import CerealParameters,cereal_development
from local_benchmark_protocol import file_hash,write_json
from check_observed_crop_durations import number,score_records

PLAN=ROOT/'calibration/cereal_phenology_20261103/plan.json'
OUT=ROOT/'output/cereal_phenology_20261103'
MONTH_DAYS=np.array([31,28,31,30,31,30,31,31,30,31,30,31])


def evaluation_country(country):
    return int(hashlib.sha256(('cereal-phenology-v1:'+str(country)).encode()).hexdigest(),16)%5==0


def daily_temperature(monthly):
    monthly=np.asarray(monthly,float)
    if monthly.ndim!=2 or monthly.shape[0]!=12 or not np.isfinite(monthly).all():
        raise ValueError('Finite twelve-month temperature fields required')
    mid=np.cumsum(MONTH_DAYS)-MONTH_DAYS/2
    return np.stack([np.interp(np.arange(365)+.5,np.r_[mid[-1]-365,mid,mid[0]+365],
                    np.r_[monthly[-1,j],monthly[:,j],monthly[0,j]]) for j in range(monthly.shape[1])],axis=1)


def daylight_hours(latitude):
    phi=np.radians(np.asarray(latitude,float))[None,:]
    declination=-np.radians(23.44)*np.cos(2*np.pi*((np.arange(365)+.5)[:,None]-354.5)/365)
    return 24/np.pi*np.arccos(np.clip(-np.tan(phi)*np.tan(declination),-1,1))


def prepare():
    plan=json.loads(PLAN.read_text());OUT.mkdir(exist_ok=True)
    raw=ROOT/plan['raw_calendar'];forcing=ROOT/'data/cache/worldclim/wc2.1_5m_tavg.zip'
    if file_hash(raw)!=plan['raw_sha256'] or file_hash(forcing)!=plan['forcing_sha256']:
        raise ValueError('Declared calendar/forcing source changed')
    source_plan=json.loads((ROOT/'calibration/crop_calendar_observations_20261103/plan.json').read_text())
    rows=list(csv.DictReader(raw.read_text(encoding='utf-8-sig').splitlines()))
    parsed,discarded=score_records(rows,source_plan);original={r['Data.ID']:r for r in rows}
    records=[];excluded=[r for r in discarded if r['crop'] in ('Wheat','Barley')]
    for row in parsed:
        if row['crop'] not in ('wheat','barley'):continue
        why=None;source=original[row['id']]
        if row['source_flagged_exclude']:why='source_exclude_qualifier'
        lat=number(source['lat.avg']);lon=number(source['lon.avg']);country=source['Nation.code']
        if why is None and (lat is None or lon is None or not -90<=lat<=90 or not -180<=lon<=180 or country in ('','NA')):
            why='missing_centroid_or_country'
        if why:
            excluded.append(dict(id=row['id'],crop=row['crop'],reason=why));continue
        records.append({**row,'lat':lat,'lon':lon,'country':country,'evaluation':evaluation_country(country),
                        'winter':'winter' in row['qualifier'].lower()})
    lat=np.array([r['lat'] for r in records]);lon=np.array([r['lon'] for r in records])
    monthly=[]
    with zipfile.ZipFile(forcing) as z:
        for m in range(1,13):
            with Image.open(io.BytesIO(z.read(f'wc2.1_5m_tavg_{m:02d}.tif'))) as im:
                a=np.asarray(im,dtype=float)
            if a.shape!=(2160,4320):raise ValueError('Unexpected WorldClim grid')
            yy=(90-lat)*12-.5;xx=(lon+180)*12-.5
            y0=np.floor(yy).astype(int);x0=np.floor(xx).astype(int);fy=yy-y0;fx=xx-x0
            corners=np.stack([a[np.clip(y0+dy,0,2159),(x0+dx)%4320] for dy,dx in [(0,0),(0,1),(1,0),(1,1)]])
            good=np.all(np.isfinite(corners)&(corners>-1e20),axis=0)
            value=np.sum(corners*np.stack([(1-fy)*(1-fx),(1-fy)*fx,fy*(1-fx),fy*fx]),axis=0)
            monthly.append(np.where(good,value,np.nan))
    monthly=np.stack(monthly);valid=np.isfinite(monthly).all(0)
    for r,ok in zip(records,valid):
        if not ok:excluded.append(dict(id=r['id'],crop=r['crop'],reason='invalid_worldclim_corners'))
    records=[r for r,ok in zip(records,valid) if ok];monthly=monthly[:,valid]
    if not records or not any(r['evaluation'] for r in records) or all(r['evaluation'] for r in records):
        raise ValueError('Both declared country pools must contain records')
    # A prescribed sowing midpoint, rounded at most half a day, conditions
    # this duration test. Calendar year wrap never resets crop development.
    sow=np.array([int(np.floor(r['planting_median']-.5))%365 for r in records])
    daily=daily_temperature(monthly);light=daylight_hours([r['lat'] for r in records])
    index=(np.arange(365)[:,None]+sow[None,:])%365;columns=np.arange(len(records))[None,:]
    arrays=dict(temperature=daily[index,columns],daylight=light[index,columns],annual_temperature=daily.mean(0))
    write_json(OUT/'inputs.json',dict(records=records,excluded=excluded,plan_sha256=file_hash(PLAN),
        raw_sha256=file_hash(raw),forcing_sha256=file_hash(forcing),
        selection_scope='No evaluation-country maturity scores are computed during preparation or selection.'))
    return plan,records,arrays


def heat_requirements(records,annual_temperature,scale=1.):
    winter=np.array([r['winter'] for r in records]);sow=np.array([int(np.floor(r['planting_median']+.5)) for r in records])
    key=np.array([365 if r['lat']>=0 else 181 for r in records]);delta=sow-key
    winter_base=np.clip(-.1081*delta**2+3.1633*delta+2876.9,1700,2876.9)
    spring_base=np.clip(np.maximum(annual_temperature,0)*200,1000,2648.4)
    return np.where(winter,np.clip(winter_base*scale,1700,2876.9),np.clip(spring_base*scale,1000,2648.4))


def predict(records,arrays,*,scale=1.,chilling=45.,kind='adapted'):
    if kind=='legacy':heat=np.array([1500 if r['crop']=='wheat' else 1200 for r in records],float)
    else:heat=heat_requirements(records,arrays['annual_temperature'],scale)
    cold=np.array([chilling if r['winter'] and kind!='legacy' else 0 for r in records])
    return cereal_development(arrays['temperature'],arrays['daylight'],CerealParameters(1700),
                              heat_units=heat,vernalization_days=cold).maturity_days


def metrics(records,predicted):
    if not records or len(records)!=len(predicted):raise ValueError('A complete declared case pool is required')
    target=np.array([r['growing_days'] for r in records]);mature=np.asarray(predicted)>0
    error=np.where(mature,np.abs(predicted-target),365.)
    countries=sorted({r['country'] for r in records})
    country={c:float(np.mean(error[[r['country']==c for r in records]])) for c in countries}
    return dict(records=len(records),countries=len(countries),country_mean_penalized_error_days=float(np.mean(list(country.values()))),
        record_mean_penalized_error_days=float(error.mean()),mature_records=int(mature.sum()),
        nonmature_records=int((~mature).sum()),mature_only_mae_days=None if not mature.any() else float(error[mature].mean()),country_errors=country)


def source_hashes():
    return {name:file_hash(ROOT/name) for name in ['harvest/phenology.py','scripts/evaluate_cereal_phenology.py',
        'scripts/check_observed_crop_durations.py','scripts/land_people.py']}


def select(plan,records,arrays):
    idx=np.array([not r['evaluation'] for r in records]);train=[r for r in records if not r['evaluation']]
    forcing={k:v[:,idx] if v.ndim==2 else v[idx] for k,v in arrays.items()}
    trials=[]
    for scale in plan['tuning']['heat_scales']:
        for cold in plan['tuning']['winter_chilling_days']:
            score=metrics(train,predict(train,forcing,scale=scale,chilling=cold))
            trials.append(dict(scale=scale,chilling=cold,training=score))
    winner=min(trials,key=lambda t:(t['training']['country_mean_penalized_error_days'],abs(t['scale']-1),abs(t['chilling']-45),t['scale'],t['chilling']))
    result=dict(status='selected_training_only',selected=winner,trials=trials,plan_sha256=file_hash(PLAN),
        sources_sha256=source_hashes(),inputs_sha256=file_hash(OUT/'inputs.json'),evaluation_scored=False,
        training_ids=[r['id'] for r in train],evaluation_ids=[r['id'] for r in records if r['evaluation']],
        training_countries=sorted({r['country'] for r in train}),evaluation_countries=sorted({r['country'] for r in records if r['evaluation']}))
    assert not set(result['training_countries'])&set(result['evaluation_countries'])
    write_json(OUT/'selection.json',result)
    print(json.dumps(dict(status=result['status'],selected=winner,training_records=len(train),evaluation_records=len(records)-len(train)),indent=2))


def evaluate(plan,records,arrays):
    path=OUT/'selection.json';selection=json.loads(path.read_text())
    relative=str(path.relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)!=path.read_bytes():
        raise ValueError('Commit the exact selection before scoring evaluation countries')
    if selection['sources_sha256']!=source_hashes() or selection['inputs_sha256']!=file_hash(OUT/'inputs.json') or selection['plan_sha256']!=file_hash(PLAN):
        raise ValueError('Frozen source, inputs or declaration changed')
    profiles={'legacy_heat_only':dict(kind='legacy',chilling=0),
              'published_heat_only':dict(chilling=0),'reference_chilling':dict(chilling=45),
              'selected_global':{k:selection['selected'][k] for k in ['scale','chilling']}}
    summaries={};predictions={}
    for name,params in profiles.items():
        predictions[name]=predict(records,arrays,**params);summaries[name]={}
        for evaluation,label in [(False,'training'),(True,'evaluation')]:
            idx=np.array([r['evaluation']==evaluation for r in records])
            summaries[name][label]=metrics([r for r in records if r['evaluation']==evaluation],predictions[name][idx])
    write_json(OUT/'result.json',dict(status='country_separated_evaluation',adoption=False,earth_climate_holdout_used=False,
        parameters=profiles,scores=summaries,records=records,predictions={k:v.tolist() for k,v in predictions.items()},
        selection_sha256=file_hash(path),plan_sha256=file_hash(PLAN),sources_sha256=source_hashes(),
        selection_commit=subprocess.check_output(['git','log','-1','--format=%H','--',relative],cwd=ROOT,text=True).strip(),
        scope='Conditional maturity duration at approximate regional centroids under interpolated modern climatology. Country split fixed before fitting; dataset already inspected diagnostically, not untouched. No sowing prediction, biomass/yield, winter survival, drought or ancient population validation. All nonmature cases cost365days.'))
    print(json.dumps(summaries,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',choices=['select','evaluate'],required=True)
    args=parser.parse_args();plan,records,arrays=prepare()
    (select if args.stage=='select' else evaluate)(plan,records,arrays)


if __name__=='__main__':main()
