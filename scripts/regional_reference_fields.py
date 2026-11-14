"""All declared paired field cases under regional reference-demand substitution."""
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

OUT=ROOT/'output/regional_reference_forcing_20261114'
BASE=ROOT/'output/daily_river_fields_20261114'
PLAN=ROOT/'calibration/regional_reference_forcing_20261114/plan.json'
FORCING=None
BASE_PREPARE=D.prepare


def load_inputs():
    global FORCING
    D.load_inputs()
    with np.load(OUT/'forcing.npz') as archive:FORCING={name:archive[name] for name in archive.files}


def run_case(spec):
    region,calendar,capture,forcing=spec
    if FORCING is None:load_inputs()
    base_spec=(region,'barley',1.5,calendar,.15,200.,1.,capture)
    def prepare(s):
        f,clock,eligible,a,opts=BASE_PREPARE(s)
        if forcing!='legacy_archive':
            totals=FORCING[region+'__'+forcing+'_mm']
            a['eto_mm_day']=clock.repeat_bin_values(totals/np.diff(clock.bin_edges_days)[:,None])
        return f,clock,eligible,a,opts
    saved=D.prepare;D.prepare=prepare
    try:row,fields,monthly,daily=D.run_case(base_spec)
    finally:D.prepare=saved
    parent=row['case'];row.update(case=parent+'__'+forcing,parent_case=parent,forcing=forcing)
    if forcing=='legacy_archive':
        with np.load(BASE/'fields.npz') as old:
            for name,value in fields.items():np.testing.assert_array_equal(value,old[parent+'__'+name],err_msg=parent+' '+name)
            for name,value in monthly.items():np.testing.assert_array_equal(value,old[parent+'__monthly_'+name],err_msg=parent+' monthly '+name)
            for name,value in daily.items():np.testing.assert_array_equal(value,old[parent+'__daily_'+name],err_msg=parent+' daily '+name)
        row['legacy_arrays_byte_values_equal']=True
    else:row['legacy_arrays_byte_values_equal']=None
    return row,fields,monthly,daily


def main(out,workers):
    for path in [PLAN,OUT/'weather.json',OUT/'weather_review.json',OUT/'forcing.npz']:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Freeze reviewed regional forcing before field outputs'
    weather=json.loads((OUT/'weather.json').read_text());review=json.loads((OUT/'weather_review.json').read_text())
    assert review['status']=='passed_before_field_comparison' and review['weather_sha256']==sha(OUT/'weather.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_regional_reference_weather.py')
    assert all(region['source_complete'] for region in weather['regions'].values()),'Incomplete assigned weather remains unscored; no selective field removal'
    for name,digest in {**weather['producers'],**weather['sources'],**weather['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in review['fresh_byte_exact'].items():assert sha(OUT/name)==digest,name
    baseline=json.loads((BASE/'results.json').read_text())
    for name,digest in baseline['producers'].items():assert sha(ROOT/name)==digest,name
    specs=list(itertools.product(D.REGIONS,['old','fractional'],[False,True],['legacy_archive','power_hargreaves','power_penman_monteith']))
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
        print('Completed',number,'/24',case,'root coverage',row['root_coverage'],flush=True)
    if workers!=1:pool.shutdown()
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'fields.npz',**arrays)
    with (out/'fields.csv.gz').open('wb') as file:
        with gzip.GzipFile(fileobj=file,filename='',mode='wb',mtime=0) as zipped:zipped.write(buffer.getvalue().encode())
    paths=[Path(__file__),ROOT/'scripts/daily_river_fields.py',ROOT/'harvest/river_fields.py',ROOT/'harvest/field_clock.py',ROOT/'harvest/soil_drying.py',ROOT/'harvest/flood_water.py',ROOT/'scripts/land_people.py',PLAN]
    source_paths=[OUT/'weather.json',OUT/'weather_review.json',OUT/'forcing.npz',BASE/'results.json',BASE/'fields.npz']
    write(out/'results.json',dict(status='regional_evaporation_only_field_development',rows=rows,weather_sha256=sha(OUT/'weather.json'),producers={str(p.relative_to(ROOT)):sha(p) for p in paths},sources={str(p.relative_to(ROOT)):sha(p) for p in source_paths},files_sha256={name:sha(out/name) for name in ['fields.npz','fields.csv.gz']},unchanged_sha256=weather['unchanged_sha256'],legacy_cases_replayed=8,all_candidates_consume_water=True,forcing_epoch_mismatch_declared=True,independent_regional_validation=False,harvest_or_population_scored=False,adopt=False))
    print('Wrote all24paired field cases;periodic',sum(r['periodic'] for r in rows))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT);parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args();main(args.out,args.workers)
