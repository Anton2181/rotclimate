"""Common-period meteorological inputs, before any new regional field scores."""
import argparse
import calendar
import csv
import datetime as dt
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write

CAL=ROOT/'calibration/matched_regional_weather_20261114'
SOURCE=ROOT/'data/source/matched_regional_weather_20261114'
OLD=ROOT/'output/regional_reference_forcing_20261114'
OUT=ROOT/'output/matched_regional_weather_20261114'
PARAMETERS=['T2M','T2M_MAX','T2M_MIN','T2MDEW','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS']


def main(out):
    plan=CAL/'plan.json';assert subprocess.check_output(['git','show','HEAD:'+str(plan.relative_to(ROOT))],cwd=ROOT)==plan.read_bytes()
    p=json.loads(plan.read_text());receipt=json.loads((SOURCE/'sources.json').read_text())
    assert receipt['plan_sha256']==sha(plan)
    assert receipt['capturer_sha256']==sha(ROOT/'scripts/capture_matched_regional_weather.py')
    assert receipt['parent_capturer_sha256']==sha(ROOT/'scripts/capture_regional_reference_weather.py')
    before=json.loads((ROOT/'data/source/regional_reference_forcing_20261114/sources.json').read_text());lookup={r['cell']['id']:r for r in before['sources']}
    dates=[dt.date(2020,1,1)+dt.timedelta(days=i) for i in range(1827)];keys=[day.strftime('%Y%m%d') for day in dates]
    assert dates[-1]==dt.date(2024,12,31)
    oldreview=json.loads((OLD/'weather_review.json').read_text());assert oldreview['weather_sha256']==sha(OLD/'weather.json')
    assert oldreview['reviewer_sha256']==sha(ROOT/'scripts/review_regional_reference_weather.py')
    for name,digest in oldreview['fresh_byte_exact'].items():assert sha(OLD/name)==digest,name
    with np.load(OLD/'forcing.npz') as z:old={name:z[name] for name in z.files}
    cells=[];temperatures=[];rain=[];rows=[];daily=[];summaries=[];pins={}
    for record in receipt['sources']:
        cell=record['cell']['id'];cells.append(cell);path=ROOT/record['file'];assert sha(path)==record['sha256'];pins[record['file']]=record['sha256']
        prior=lookup[cell];assert sha(ROOT/prior['file'])==prior['sha256'];raw=json.loads(path.read_bytes());previous=json.loads((ROOT/prior['file']).read_bytes())
        data=raw['properties']['parameter'];olddata=previous['properties']['parameter'];fill=raw['header']['fill_value']
        overlap=raw['geometry']==previous['geometry'] and raw['header']['time_standard']==previous['header']['time_standard']=='LST'
        for parameter in PARAMETERS:overlap=overlap and data[parameter]==olddata[parameter] and raw['parameters'][parameter]['units']==previous['parameters'][parameter]['units']
        assert raw['parameters']['PRECTOTCORR']['units']=='mm/day'
        t=np.array([data['T2M'].get(k,np.nan) for k in keys]);r=np.array([data['PRECTOTCORR'].get(k,np.nan) for k in keys])
        assert set(data['T2M'])==set(keys)==set(data['PRECTOTCORR'])
        valid=np.isfinite(t)&np.isfinite(r)&(t!=fill)&(r!=fill)&(r>=0)&(t>=-100)&(t<=70)
        complete=bool(valid.all() and overlap)
        # Do not drop or substitute changed/incomplete samples. Entire inputs remain unqualified.
        tm=[];pm=[]
        for month in range(1,13):
            ty=[];py=[]
            for year in range(2020,2025):
                select=np.array([d.year==year and d.month==month for d in dates]);assert select.sum()==calendar.monthrange(year,month)[1]
                ty.append(float(t[select].mean()));py.append(float(r[select].sum()))
            tm.append(float(np.mean(ty)) if complete else np.nan);pm.append(float(np.mean(py)) if complete else np.nan)
            index=list(old['cell_ids']).index(cell)
            rows.append(dict(cell=cell,month=month,temperature_c=tm[-1],rain_mm=pm[-1],hargreaves_mm=float(old['cell_hargreaves_mm'][index,month-1]) if complete else '',penman_monteith_mm=float(old['cell_penman_monteith_mm'][index,month-1]) if complete else '',qualified=int(complete)))
        temperatures.append(tm);rain.append(pm)
        for i,date in enumerate(dates):daily.append(dict(cell=cell,date=date.isoformat(),temperature_c=float(t[i]),rain_mm=float(r[i]),valid=int(valid[i])))
        summaries.append(dict(cell=cell,complete=complete,weather_overlap_exact=bool(overlap),valid_days=int(valid.sum()),mean_annual_rain_mm=float(np.sum(pm)) if complete else None))
    assert list(old['cell_ids'])==cells
    arrays=dict(cell_ids=np.array(cells),cell_temperature_c=np.array(temperatures),cell_rain_mm=np.array(rain),cell_hargreaves_mm=old['cell_hargreaves_mm'],cell_penman_monteith_mm=old['cell_penman_monteith_mm'])
    regions={}
    for region in p['regions']:
        ix=old[region+'__cell_index'];area=old[region+'__area_km2'];qualified=all(summaries[i]['complete'] for i in ix)
        for key in ['lat','lon','area_km2','T','P','PET','qualified','cell_index','distance_km','power_hargreaves_mm','power_penman_monteith_mm']:arrays[region+'__'+key]=old[region+'__'+key]
        arrays[region+'__matched_temperature_c']=np.array(temperatures)[ix].T;arrays[region+'__matched_rain_mm']=np.array(rain)[ix].T
        regions[region]=dict(fields=len(ix),qualified=qualified,legacy_area_weighted_annual_rain_mm=float(np.average(old[region+'__P'].sum(0),weights=area)),matched_area_weighted_annual_rain_mm=float(np.average(arrays[region+'__matched_rain_mm'].sum(0),weights=area)) if qualified else None)
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'forcing.npz',**arrays)
    with (out/'bins.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(daily[0]));writer.writeheader();writer.writerows(daily)
    with (out/'daily.csv.gz').open('wb') as file:
        with gzip.GzipFile(fileobj=file,filename='',mode='wb',mtime=0) as zipped:zipped.write(buffer.getvalue().encode())
    prior=ROOT/'output/nile_groundwater_sources_20261114';reference=json.loads((prior/'reference.json').read_text());protected=dict(reference['unchanged_sha256'])
    for name in ['reference.json','water_tables.csv','sakha_soils.csv','sakha_flux_checks.csv','review.json']:protected[str((prior/name).relative_to(ROOT))]=sha(prior/name)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    sourcefiles=[SOURCE/'sources.json',ROOT/'data/source/regional_reference_forcing_20261114/sources.json',OLD/'forcing.npz',OLD/'weather.json',OLD/'weather_review.json']
    for path in sourcefiles:pins[str(path.relative_to(ROOT))]=sha(path)
    write(out/'weather.json',dict(status='matched_meteorological_input_preflight_only',cells=summaries,regions=regions,daily_rows=len(daily),bin_rows=len(rows),temperature_mapping=p['temperature_policy'],rain_mapping=p['rain_policy'],river_period_matched=False,field_experiment_scored=False,producers={str(path.relative_to(ROOT)):sha(path) for path in [Path(__file__),plan]},sources=pins,files_sha256={name:sha(out/name) for name in ['forcing.npz','bins.csv','daily.csv.gz']},unchanged_sha256=protected,adopt=False))
    print('Built30samples/54810days/360bins/all1507fields;qualified',all(row['complete'] for row in summaries),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
