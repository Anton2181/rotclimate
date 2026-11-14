"""Declared paired T/P/ETo fields with exact ETo-only archived controls."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
import gzip
import io
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import daily_river_fields as D
from settlement_locations_earth import sha,write

OUT=ROOT/'output/matched_regional_fields_20261114'
INPUT=ROOT/'output/matched_regional_weather_20261114'
CONTROL=ROOT/'output/regional_reference_forcing_20261114'
PLAN=ROOT/'calibration/matched_regional_weather_20261114/field_plan.json'
FORCING=None
BASE_PREPARE=D.prepare


def load_inputs():
    global FORCING
    D.load_inputs()
    with np.load(INPUT/'forcing.npz') as archive:FORCING={name:archive[name] for name in archive.files}


def run_case(spec):
    region,calendar,capture,method,meteorology=spec
    if FORCING is None:load_inputs()
    base=(region,'barley',1.5,calendar,.15,200.,1.,capture)
    original=D.STATIC[region];f=dict(original)
    if meteorology=='matched':
        f['T']=FORCING[region+'__matched_temperature_c'];f['P']=FORCING[region+'__matched_rain_mm']
    D.STATIC[region]=f
    def prepare(s):
        fields,clock,eligible,a,opts=BASE_PREPARE(s)
        totals=FORCING[region+'__power_'+method+'_mm']
        a['eto_mm_day']=clock.repeat_bin_values(totals/np.diff(clock.bin_edges_days)[:,None])
        return fields,clock,eligible,a,opts
    saved=D.prepare;D.prepare=prepare
    try:row,fields,monthly,daily=D.run_case(base)
    finally:D.prepare=saved;D.STATIC[region]=original
    parent=row['case']+'__power_'+method
    row.update(case=row['case']+'__'+meteorology+'_'+method,parent_case=parent,method=method,meteorology=meteorology)
    if meteorology=='eto_only':
        with np.load(CONTROL/'fields.npz') as old:
            for name,value in fields.items():np.testing.assert_array_equal(value,old[parent+'__'+name],err_msg=parent+' '+name)
            for name,value in monthly.items():np.testing.assert_array_equal(value,old[parent+'__monthly_'+name],err_msg=parent+' monthly '+name)
            for name,value in daily.items():np.testing.assert_array_equal(value,old[parent+'__daily_'+name],err_msg=parent+' daily '+name)
        row['archived_arrays_exact']=True
    else:row['archived_arrays_exact']=None
    return row,fields,monthly,daily


def main(out,workers):
    for path in [PLAN,INPUT/'weather.json',INPUT/'review.json',INPUT/'forcing.npz']:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Freeze reviewed input preflight before field scoring'
    weather=json.loads((INPUT/'weather.json').read_text());review=json.loads((INPUT/'review.json').read_text())
    assert review['status']=='passed_before_new_field_scores' and review['weather_sha256']==sha(INPUT/'weather.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_matched_regional_weather.py')
    assert all(row['qualified'] for row in weather['regions'].values())
    for name,digest in {**weather['producers'],**weather['sources'],**weather['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(INPUT/name)==digest,name
    control=json.loads((CONTROL/'results.json').read_text())
    for name,digest in {**control['producers'],**control['sources']}.items():assert sha(ROOT/name)==digest,name
    specs=list(itertools.product(D.REGIONS,['old','fractional'],[False,True],['hargreaves','penman_monteith'],['eto_only','matched']));assert len(specs)==32
    rows=[];arrays={};buffer=io.StringIO(newline='');writer=csv.writer(buffer)
    columns=['case','field','latitude','longitude','area_km2','eligible','root_coverage',*['initial_'+k for k in D.STOCKS],*['final_'+k for k in D.STOCKS],*['annual_'+k for k in D.FLUXES]]
    writer.writerow(columns);load_inputs()
    if workers==1:records=map(run_case,specs)
    else:
        pool=ProcessPoolExecutor(max_workers=workers,initializer=load_inputs);records=pool.map(run_case,specs,chunksize=1)
    for number,(row,fields,monthly,daily) in enumerate(records,1):
        case=row['case'];region=row['region'];rows.append(row)
        for name,value in fields.items():arrays[case+'__'+name]=value
        for name,value in monthly.items():arrays[case+'__monthly_'+name]=value
        for name,value in daily.items():arrays[case+'__daily_'+name]=value
        f=D.STATIC[region]
        for i in range(row['candidate_fields']):writer.writerow([case,i,f['lat'][i],f['lon'][i],f['area_km2'][i],int(fields['eligible'][i]),fields['root_coverage'][i] if fields['eligible'][i] and row['periodic'] else '',*[fields[name][i] for name in columns[7:]]])
        print('Completed',number,'/32',case,'coverage',row['root_coverage'],flush=True)
    if workers!=1:pool.shutdown()
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'fields.npz',**arrays)
    with (out/'fields.csv.gz').open('wb') as file:
        with gzip.GzipFile(fileobj=file,filename='',mode='wb',mtime=0) as zipped:zipped.write(buffer.getvalue().encode())
    protected=dict(weather['unchanged_sha256'])
    for name,digest in review['fresh_byte_exact'].items():protected[str((INPUT/name).relative_to(ROOT))]=digest
    protected[str((INPUT/'review.json').relative_to(ROOT))]=sha(INPUT/'review.json')
    paths=[Path(__file__),ROOT/'scripts/daily_river_fields.py',ROOT/'harvest/river_fields.py',ROOT/'harvest/field_clock.py',ROOT/'harvest/soil_drying.py',ROOT/'harvest/flood_water.py',ROOT/'scripts/land_people.py',PLAN]
    sources=[INPUT/'weather.json',INPUT/'review.json',INPUT/'forcing.npz',CONTROL/'results.json',CONTROL/'fields.npz']
    write(out/'results.json',dict(status='paired_matched_meteorology_field_development',rows=rows,producers={str(p.relative_to(ROOT)):sha(p) for p in paths},sources={str(p.relative_to(ROOT)):sha(p) for p in sources},files_sha256={name:sha(out/name) for name in ['fields.npz','fields.csv.gz']},unchanged_sha256=protected,archived_cases_exact=16,all_candidates_consume_water=True,meteorology_period_matched=True,river_period_matched=False,independent_regional_validation=False,harvest_or_population_scored=False,groundwater_enabled=False,adopt=False))
    print('Wrote32paired cases;periodic',sum(r['periodic'] for r in rows))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT);parser.add_argument('--workers',type=int,default=4);args=parser.parse_args();main(args.out,args.workers)
