"""Raw common-period input review with independent Decimal aggregation."""
import calendar
import csv
import datetime as dt
from decimal import Decimal,localcontext
import gzip
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/matched_regional_weather_20261114'
OLD=ROOT/'output/regional_reference_forcing_20261114'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    r=json.loads((OUT/'weather.json').read_text())
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    receipt=json.loads((ROOT/'data/source/matched_regional_weather_20261114/sources.json').read_text())
    assert receipt['capturer_sha256']==sha(ROOT/'scripts/capture_matched_regional_weather.py')
    assert receipt['parent_capturer_sha256']==sha(ROOT/'scripts/capture_regional_reference_weather.py')
    previous=json.loads((ROOT/'data/source/regional_reference_forcing_20261114/sources.json').read_text());prior={item['cell']['id']:item for item in previous['sources']}
    with np.load(OUT/'forcing.npz') as archive:z={name:archive[name] for name in archive.files}
    with np.load(OLD/'forcing.npz') as archive:old={name:archive[name] for name in archive.files}
    expected_dates={};days=[];d=dt.date(2020,1,1)
    while d<=dt.date(2024,12,31):days.append(d);d+=dt.timedelta(days=1)
    assert len(days)==1827 and sum(d.month==2 and d.day==29 for d in days)==2
    for year in range(2020,2025):
        for month in range(1,13):expected_dates[year,month]=[d.strftime('%Y%m%d') for d in days if d.year==year and d.month==month]
    temperatures=[];rain=[];daily={};overlap_cells=0;maxerror=0.
    with localcontext() as ctx:
        ctx.prec=50
        for item in receipt['sources']:
            cell=item['cell']['id'];assert sha(ROOT/item['file'])==item['sha256']
            raw=json.loads((ROOT/item['file']).read_bytes());olditem=prior[cell];assert sha(ROOT/olditem['file'])==olditem['sha256']
            before=json.loads((ROOT/olditem['file']).read_bytes());p=raw['properties']['parameter'];op=before['properties']['parameter']
            assert raw['geometry']==before['geometry'] and raw['header']['time_standard']=='LST'
            assert raw['parameters']['T2M']['units']=='C' and raw['parameters']['PRECTOTCORR']['units']=='mm/day'
            for parameter in op:
                assert set(p[parameter])==set(op[parameter])
                assert raw['parameters'][parameter]['units']==before['parameters'][parameter]['units']
                for key,value in op[parameter].items():assert p[parameter][key]==value;overlap_cells+=1
            wanted={d.strftime('%Y%m%d') for d in days};assert set(p['PRECTOTCORR'])==wanted==set(p['T2M'])
            t={key:Decimal(str(p['T2M'][key])) for key in wanted};a={key:Decimal(str(p['PRECTOTCORR'][key])) for key in wanted}
            fill=Decimal(str(raw['header']['fill_value']))
            assert all(value.is_finite() and value!=fill and -100<=value<=70 for value in t.values())
            assert all(value.is_finite() and value!=fill and value>=0 for value in a.values())
            tm=[];pm=[]
            for month in range(1,13):
                ts=[];rs=[]
                for year in range(2020,2025):
                    keys=expected_dates[year,month];assert len(keys)==calendar.monthrange(year,month)[1]
                    ts.append(sum(t[key] for key in keys)/len(keys));rs.append(sum(a[key] for key in keys))
                tm.append(float(sum(ts)/5));pm.append(float(sum(rs)/5))
            assert abs(sum(pm)-float(sum(a.values())/5))<1e-9
            temperatures.append(tm);rain.append(pm);daily[cell]=(t,a)
    temperatures=np.array(temperatures);rain=np.array(rain)
    assert list(z['cell_ids'])==[item['cell']['id'] for item in receipt['sources']]==list(old['cell_ids'])
    for key,value in [('cell_temperature_c',temperatures),('cell_rain_mm',rain)]:
        maxerror=max(maxerror,float(np.max(np.abs(z[key]-value))));np.testing.assert_allclose(z[key],value,atol=2e-11,rtol=2e-13)
    for name in ['cell_hargreaves_mm','cell_penman_monteith_mm']:np.testing.assert_array_equal(z[name],old[name])
    cells={name:i for i,name in enumerate(z['cell_ids'])};fieldcells=0;fields=0
    for region,summary in r['regions'].items():
        ix=[]
        for latitude,longitude in zip(z[region+'__lat'],z[region+'__lon']):ix.append(cells[f'n{math.floor(latitude):02d}_e{math.floor(longitude):03d}'])
        np.testing.assert_array_equal(ix,z[region+'__cell_index']);fields+=len(ix)
        for key,expected in [('matched_temperature_c',temperatures[ix].T),('matched_rain_mm',rain[ix].T)]:
            np.testing.assert_allclose(z[region+'__'+key],expected,atol=2e-11,rtol=2e-13);fieldcells+=expected.size
        for key,value in old.items():
            if key.startswith(region+'__'):np.testing.assert_array_equal(z[key],value)
        area=z[region+'__area_km2'];avg=math.fsum(float(area[i])*sum(rain[ix[i]]) for i in range(len(ix)))/math.fsum(area)
        assert abs(avg-summary['matched_area_weighted_annual_rain_mm'])<1e-9 and summary['qualified']
    assert fields==1507 and overlap_cells==438480
    with (OUT/'bins.csv').open() as file:
        rows=list(csv.DictReader(file));assert len(rows)==360
        for row in rows:
            i=cells[row['cell']];m=int(row['month'])-1
            for key,value in [('temperature_c',temperatures[i,m]),('rain_mm',rain[i,m]),('hargreaves_mm',old['cell_hargreaves_mm'][i,m]),('penman_monteith_mm',old['cell_penman_monteith_mm'][i,m])]:assert abs(float(row[key])-value)<2e-11
            assert row['qualified']=='1'
    count=0
    with gzip.open(OUT/'daily.csv.gz','rt',newline='') as file:
        for row in csv.DictReader(file):
            t,p=daily[row['cell']];key=row['date'].replace('-','')
            assert Decimal(row['temperature_c'])==t[key] and Decimal(row['rain_mm'])==p[key] and row['valid']=='1';count+=1
    assert count==54810 and all(c['complete'] and c['weather_overlap_exact'] and c['valid_days']==1827 for c in r['cells'])
    assert not r['field_experiment_scored'] and not r['river_period_matched'] and not r['adopt']
    fresh={}
    for name in ['weather.json','forcing.npz','bins.csv','daily.csv.gz']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    review=dict(status='passed_before_new_field_scores',reviewer_sha256=sha(Path(__file__)),weather_sha256=sha(OUT/'weather.json'),method='No producer import. Raw date/unit/domain/overlap checks,50digit Decimal Gregorian daily/month/year aggregation,scalar containing-tile assignments,all CSV cells and archived controls',weather_overlap_cells=overlap_cells,daily_rows=count,sample_bin_numeric_cells=1440,field_assignment_cells=fieldcells,fields=fields,max_aggregation_error=maxerror,leap_days_per_sample=2,fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),river_period_matched=False,field_experiment_scored=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(review,indent=2)+'\n')
    print('Reviewed438480overlapping weather values,54810new rain/temperature rows,360bins/all1507fields;four fresh exports exact')


if __name__=='__main__':main()
