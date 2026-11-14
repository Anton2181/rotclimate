"""Independent complete-source reference ETo, bin aggregation and mapping review."""
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_eto_scalar import scalar_reference,dewpoint_pressure

OUT=ROOT/'output/regional_reference_forcing_20261114'
PARAMETERS=['T2M','T2M_MAX','T2M_MIN','T2MDEW','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    r=json.loads((OUT/'weather.json').read_text())
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    core=json.loads((OUT/'core/review.json').read_text())
    for name,digest in core['producers'].items():assert sha(ROOT/name)==digest,name
    assert '182 passed' in core['controls_stdout']
    plan=json.loads((ROOT/'calibration/regional_reference_forcing_20261114/plan.json').read_text())
    source=json.loads((ROOT/'data/source/regional_reference_forcing_20261114/sources.json').read_text())
    assert source['plan_sha256']==sha(ROOT/'calibration/regional_reference_forcing_20261114/plan.json')
    assert source['capturer_sha256']==sha(ROOT/'scripts/capture_regional_reference_weather.py')
    assert [v['cell'] for v in source['sources']]==plan['weather_grid']['cells']
    with np.load(OUT/'forcing.npz') as archive:z={name:archive[name] for name in archive.files}
    dates=[dt.date(2020,1,1)+dt.timedelta(days=i) for i in range(1827)]
    maxdaily=0.;maxbin=0.;cells=0;daycount=0;bins_h=[];bins_p=[]
    with gzip.open(OUT/'weather_daily.csv.gz','rt',newline='') as file:
        exported=csv.DictReader(file)
        for index,capture in enumerate(source['sources']):
            cell=capture['cell'];assert z['cell_ids'][index]==cell['id']
            raw=json.loads((ROOT/capture['file']).read_bytes());parameters=raw['properties']['parameter'];fill=raw['header']['fill_value']
            assert raw['geometry']['coordinates'][:2]==[cell['longitude'],cell['latitude']]
            for name,wanted in [('T2M','C'),('T2M_MAX','C'),('T2M_MIN','C'),('T2MDEW','C'),('RH2M','%'),('WS2M','m/s'),('PS','kPa')]:assert raw['parameters'][name]['units']==wanted
            assert raw['parameters']['ALLSKY_SFC_SW_DWN']['units'] in ['MJ/m^2/day','kWh/m^2/day','kW-hr/m^2/day']
            semantic=json.dumps(dict(parameters=parameters,geometry=raw['geometry'],units=raw['parameters'],fill_value=fill),sort_keys=True,separators=(',',':')).encode()
            assert hashlib.sha256(semantic).hexdigest()==capture['semantic_sha256']
            elevation=raw['geometry']['coordinates'][2];factor=1. if raw['parameters']['ALLSKY_SFC_SW_DWN']['units']=='MJ/m^2/day' else 3.6
            amounts_h={m:[] for m in range(1,13)};amounts_p={m:[] for m in range(1,13)};clipped=0;negative=0
            for date in dates:
                row=next(exported);assert row['cell']==cell['id'] and row['date']==date.isoformat()
                values={name:parameters[name].get(date.strftime('%Y%m%d')) for name in PARAMETERS}
                assert all(v is not None and math.isfinite(v) and v!=fill for v in values.values()),'Incomplete cell stays unscored'
                for name,value in values.items():assert float(row[name])==value
                t,lo,hi,dew=[values[name] for name in ['T2M','T2M_MIN','T2M_MAX','T2MDEW']]
                assert -100<lo<=t<=hi<=70 and -100<dew<=70 and 0<=values['RH2M']<=100
                assert values['WS2M']>=0 and values['PS']>0 and values['ALLSKY_SFC_SW_DWN']>=0
                vap=dewpoint_pressure(dew);es=(dewpoint_pressure(lo)+dewpoint_pressure(hi))/2;assert vap<=es+1e-10
                assert row['valid']=='1' and row['qa']==''
                ref=scalar_reference(t,lo,hi,vap,values['WS2M'],values['PS'],values['ALLSKY_SFC_SW_DWN']*factor,cell['latitude'],date.timetuple().tm_yday,elevation)
                for name,value in ref.items():
                    if name=='daylight_hours':continue
                    error=abs(float(row[name])-value);maxdaily=max(maxdaily,error);cells+=1
                    assert error<2e-10,(cell['id'],date,name,error)
                amounts_h[date.month].append(ref['hargreaves_mm_day']);amounts_p[date.month].append(ref['pm_mm_day'])
                clipped+=ref['rs_ratio_raw']!=ref['rs_ratio_used'];negative+=ref['pm_raw_mm_day']<0;daycount+=1
            h=np.array([math.fsum(amounts_h[m])/5 for m in range(1,13)])
            p=np.array([math.fsum(amounts_p[m])/5 for m in range(1,13)])
            bins_h.append(h);bins_p.append(p)
            for name,expected in [('cell_hargreaves_mm',h),('cell_penman_monteith_mm',p)]:
                maxbin=max(maxbin,float(np.max(np.abs(z[name][index]-expected))))
                np.testing.assert_allclose(z[name][index],expected,atol=2e-10,rtol=2e-12)
            meta=next(v for v in r['cells'] if v['cell']==cell['id'])
            assert meta['complete'] and meta['valid_days']==1827 and meta['cloud_ratio_clipped_days']==clipped and meta['negative_pm_raw_days']==negative
            assert math.isclose(meta['hargreaves_mean_annual_mm'],math.fsum(h),abs_tol=1e-8)
            assert math.isclose(meta['pm_mean_annual_mm'],math.fsum(p),abs_tol=1e-8)
            assert not meta['qa_counts']
        assert next(exported,None) is None
    assert daycount==54810==r['daily_weather_rows']
    with (OUT/'assignments.csv').open() as file:assignment=list(csv.DictReader(file))
    assert len(assignment)==1507==r['field_assignments']
    lookup={name:i for i,name in enumerate(z['cell_ids'])};cursor=0;maxdistance=0.
    with np.load(ROOT/plan['candidate_archive']['file']) as old:
        for region in plan['regions']:
            for name in ['lat','lon','area_km2','T','P','PET','qualified']:np.testing.assert_array_equal(z[region+'__'+name],old[region+'__'+name])
            area=old[region+'__area_km2'];distances=[];indices=[]
            for i,(lat,lon,weight) in enumerate(zip(old[region+'__lat'],old[region+'__lon'],area)):
                a,b=math.floor(lat),math.floor(lon);cell=f'n{a:02d}_e{b:03d}';index=lookup[cell];indices.append(index)
                row=assignment[cursor];cursor+=1
                assert row['region']==region and int(row['field'])==i and row['cell']==cell and row['source_complete']=='1'
                assert float(row['latitude'])==lat and float(row['longitude'])==lon and float(row['area_km2'])==weight
                phi,other=math.radians(lat),math.radians(a+.5)
                chord=math.sin((other-phi)/2)**2+math.cos(phi)*math.cos(other)*math.sin(math.radians(b+.5-lon)/2)**2
                distance=2*6371.0088*math.asin(math.sqrt(max(0,min(1,chord))));distances.append(distance)
                maxdistance=max(maxdistance,abs(float(row['distance_km'])-distance))
                assert abs(float(row['distance_km'])-distance)<1e-8
                assert float(row['cell_latitude'])==a+.5 and float(row['cell_longitude'])==b+.5
                assert float(row['source_grid_elevation_m'])==z['cell_grid_elevation_m'][index]
            np.testing.assert_array_equal(indices,z[region+'__cell_index'])
            np.testing.assert_allclose(z[region+'__power_hargreaves_mm'],np.array(bins_h)[indices].T,atol=2e-10,rtol=2e-12)
            np.testing.assert_allclose(z[region+'__power_penman_monteith_mm'],np.array(bins_p)[indices].T,atol=2e-10,rtol=2e-12)
            meta=r['regions'][region]
            assert meta['source_complete'] and meta['candidate_fields']==len(area) and meta['weather_cells']==15
            assert math.isclose(meta['candidate_area_km2'],math.fsum(area),abs_tol=1e-7)
            assert math.isclose(meta['area_weighted_distance_km'],math.fsum(d*w for d,w in zip(distances,area))/math.fsum(area),abs_tol=1e-8)
            assert math.isclose(meta['maximum_distance_km'],max(distances),abs_tol=1e-8)
            for key,values in [('legacy_area_weighted_annual_eto_mm',old[region+'__PET'].sum(0)),('power_hargreaves_area_weighted_annual_eto_mm',np.array(bins_h)[indices].sum(1)),('power_penman_monteith_area_weighted_annual_eto_mm',np.array(bins_p)[indices].sum(1))]:
                assert math.isclose(meta[key],math.fsum(v*w for v,w in zip(values,area))/math.fsum(area),abs_tol=1e-7)
    fresh={}
    for name in ['weather.json','forcing.npz','assignments.csv','weather_daily.csv.gz']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    receipt=dict(status='passed_before_field_comparison',reviewer_sha256=sha(Path(__file__)),scalar_sha256=sha(ROOT/'scripts/reference_eto_scalar.py'),weather_sha256=sha(OUT/'weather.json'),method='Independent raw-weather/date/QA/units, scalar Earth solar/Decimal ETo, Gregorian monthly sums and field-to-grid geometry; producer/shared adapter not imported',weather_cells=30,daily_weather_rows=daycount,scalar_numeric_cells=cells,max_daily_numeric_error=maxdaily,max_monthly_amount_error_mm=maxbin,field_assignments=cursor,max_assignment_distance_error_km=maxdistance,fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),adopt=False)
    (OUT/'weather_review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Passed full30cell weather:',daycount,'days;',cells,'numeric cells;1507assignments;four fresh exports byte-exact')


if __name__=='__main__':main()
