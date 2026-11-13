"""Independent regex/Decimal/scalar audit of the gauge phase preflight.

Does not import the production parser, year filter or phase implementation.
"""
import csv
from decimal import Decimal, localcontext
import hashlib
import html
import json
from pathlib import Path
import re
import subprocess
import sys
import numpy as np
from scipy.io import netcdf_file

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/flood_basin_seasonality_20261113'
CACHE=ROOT/'data/cache/flood_basin_seasonality_20261113'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result=json.loads((OUT/'results.json').read_text())
    plan=json.loads((ROOT/'calibration/flood_basin_seasonality_20261113/plan.json').read_text())
    controls=json.loads((OUT/'controls.json').read_text())
    assert controls['status']=='passed_before_phase_outputs' and '15 passed' in controls['output']
    for name,digest in {**result['sources'],**result['producers'],**result['unchanged_atlas_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():assert sha(OUT/name)==digest,name
    fields=np.load(OUT/'fields.npz');all_source=[];checked=0
    with localcontext() as context:
        context.prec=40
        for spec in plan['sources'][:2]:
            key=spec['id'];row=next(r for r in result['rows'] if r['id']==key)
            source=[]
            for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',(CACHE/(key+'.html')).read_text(),re.S):
                cells=[html.unescape(re.sub('<[^>]+>','',v)).strip() for v in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.S)]
                if cells and re.fullmatch(r'\d{4}-\d{2}-\d{2}',cells[0]):
                    assert len(cells)==2;source.append(cells)
            assert len(source)==row['source_rows']
            all_source.extend([[key,*v] for v in source])
            years=[];values=[];excluded=[]
            for year in range(spec['primary_years'][0],spec['primary_years'][1]+1):
                records=[(int(d[5:7]),v) for d,v in source if int(d[:4])==year]
                months=[m for m,_ in records];reasons=[];parsed=[]
                if len(records)!=12:reasons.append('not_twelve_records')
                if len(months)!=len(set(months)):reasons.append('duplicate_month')
                for month,text in records:
                    try:value=Decimal(text)
                    except Exception:value=Decimal('NaN')
                    if not value.is_finite() or value<0:reasons.append('invalid_or_qualified_flow')
                    parsed.append((month,value))
                if reasons:excluded.append(dict(year=year,records=len(records),reasons=sorted(set(reasons))))
                else:years.append(year);values.append([v for _,v in sorted(parsed)])
            assert years==row['complete_years'] and excluded==row['excluded_years']
            np.testing.assert_array_equal(fields[key+'__complete_years'],years)
            np.testing.assert_array_equal(fields[key+'__monthly_flow'],np.asarray(values,dtype=float))
            mean=[sum(v[m] for v in values)/len(values) for m in range(12)]
            np.testing.assert_allclose(np.asarray(mean,dtype=float),row['mean_monthly_flow_m3s'],rtol=1e-14)
            np.testing.assert_allclose(fields[key+'__mean_flow'],np.asarray(mean,dtype=float),rtol=1e-14)
            assert row['peak_month']==mean.index(max(mean))+1
            excess=[max(Decimal(0),v-sum(mean)/12) for v in mean];total=sum(excess)
            for duration in range(3,10):
                phase=next(p for p in row['phase'] if p['crop_months']==duration)
                for sow in range(12):
                    before=sum(excess[(sow-d)%12] for d in (1,2,3))/total
                    during=sum(excess[(sow+d)%12] for d in range(duration))/total
                    expected=[before,during,max(Decimal(0),before-during)]
                    for name,value in zip(('pre_sowing_excess_share','standing_crop_excess_share','compatibility'),expected):
                        assert abs(float(value)-phase[name][sow])<2e-14
                        assert abs(float(value)-fields[key+f'__crop{duration}__'+name][sow])<2e-14
                        if duration==5 and sow==10:assert abs(float(value)-row['november_illustration'][name])<2e-14
                    checked+=1
            assert bool(fields[key+'__crop5__seasonal_excess_present'])
    with (OUT/'gauge_monthly.csv').open() as f:assert list(csv.reader(f))[1:]==all_source
    with (OUT/'phase.csv').open() as f:
        csv_rows=list(csv.DictReader(f));assert len(csv_rows)==checked
        for v in csv_rows:
            row=next(r for r in result['rows'] if r['id']==v['station']);phase=next(p for p in row['phase'] if p['crop_months']==int(v['crop_months']))
            for name in ('pre_sowing_excess_share','standing_crop_excess_share','compatibility'):assert float(v[name])==phase[name][int(v['sowing_month'])-1]
    indus=result['rows'][2]
    with netcdf_file(CACHE/'dai.nc','r',mmap=False) as nc:
        names=[a.tobytes().split(b'\x00')[0].strip() for a in nc.variables['riv_name'][:]]
        i=names.index(b'Indus');assert names.count(b'Indus')==1
        assert int(nc.variables['yrb'][i])==indus['author_record_start']==1936
        assert int(nc.variables['yre'][i])==indus['author_record_end']==2000
        assert int(nc.variables['id'][i])==indus['station_id']
    assert not indus['qualified_for_phase'] and not indus['phase_values_inspected']
    assert not result['heldout_phase_qualified'] and not result['adopt'] and not result['irrigation_or_harvest_scores_computed']
    assert not any(k.startswith('indus') for k in fields.files)
    fresh=OUT/'fresh'
    subprocess.run([sys.executable,str(ROOT/'scripts/flood_basin_seasonality.py'),'--out',str(fresh)],check=True,cwd=ROOT)
    exact={}
    for name in ['results.json',*result['files_sha256']]:
        assert (fresh/name).read_bytes()==(OUT/name).read_bytes(),name
        exact[name]=sha(OUT/name)
    review=dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),independent_method='Regex raw HTML, Decimal complete-year means and scalar cyclic fractions; production functions not imported',source_monthly_rows=len(all_source),cyclic_rows=checked,scalar_phase_values=checked*3,heldout='Indus unscored; author coverage1936-2000 cannot supply1900-1931',protected_atlas_files=len(result['unchanged_atlas_sha256']),fresh_byte_exact=exact)
    (OUT/'review.json').write_text(json.dumps(review,indent=2)+'\n');print(review)


if __name__=='__main__':main()
