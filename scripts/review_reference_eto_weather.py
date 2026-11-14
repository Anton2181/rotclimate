"""Independent scalar/Decimal review of the declared matched-weather audit."""
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reference_eto_scalar import scalar_reference,dewpoint_pressure

OUT=ROOT/'output/reference_eto_20261114'
WEATHER=['T2M','T2M_MAX','T2M_MIN','T2MDEW','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS']


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def stats(rows):
    good=[v for v in rows if v['valid']]
    n=len(good)
    result=dict(expected_days=len(rows),valid_days=n,invalid_days=len(rows)-n)
    names=['pm_total_mm','hargreaves_total_mm','pm_mean_mm_day','hargreaves_mean_mm_day','bias_mm_day','mae_mm_day','rmse_mm_day','hargreaves_over_pm']
    if not n:return {**result,**{name:None for name in names},'cloud_ratio_clipped_days':0,'negative_pm_raw_days':0}
    pm=math.fsum(v['pm_mm_day'] for v in good);har=math.fsum(v['hargreaves_mm_day'] for v in good)
    errors=[v['hargreaves_mm_day']-v['pm_mm_day'] for v in good]
    result.update(pm_total_mm=pm,hargreaves_total_mm=har,pm_mean_mm_day=pm/n,hargreaves_mean_mm_day=har/n,bias_mm_day=math.fsum(errors)/n,mae_mm_day=math.fsum(map(abs,errors))/n,rmse_mm_day=math.sqrt(math.fsum(e*e for e in errors)/n),hargreaves_over_pm=har/pm if pm>0 else None,cloud_ratio_clipped_days=sum(v['rs_ratio_raw']!=v['rs_ratio_used'] for v in good),negative_pm_raw_days=sum(v['pm_raw_mm_day']<0 for v in good))
    return result


def main():
    r=json.loads((OUT/'results.json').read_text())
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    core=json.loads((OUT/'core/review.json').read_text())
    for name,digest in core['producers'].items():assert sha(ROOT/name)==digest,name
    assert core['status']=='passed_before_weather_eto_outputs' and '159 passed' in core['controls_stdout']
    plan=json.loads((ROOT/'calibration/reference_eto_20261114/plan.json').read_text())
    source=json.loads((ROOT/'data/source/reference_eto_20261114/sources.json').read_text())
    assert source['plan_sha256']==sha(ROOT/'calibration/reference_eto_20261114/plan.json')
    assert source['capturer_sha256']==sha(ROOT/'scripts/capture_reference_eto_sources.py')
    start=dt.datetime.strptime(plan['weather']['start'],'%Y%m%d').date();end=dt.datetime.strptime(plan['weather']['end'],'%Y%m%d').date()
    dates=[start+dt.timedelta(days=i) for i in range((end-start).days+1)]
    with (OUT/'daily.csv').open() as file:actual=list(csv.DictReader(file))
    assert len(actual)==5481==r['daily_rows']
    cursor=0;all_rows=[];errors={};aggregate_error=0.;scalar_cells=0
    for capture in source['sources']:
        path=ROOT/capture['file'];assert sha(path)==capture['sha256']
        data=json.loads(path.read_bytes());site=capture['site'];parameters=data['properties']['parameter']
        semantic=json.dumps(dict(parameters=parameters,geometry=data['geometry'],units=data['parameters'],fill_value=data['header']['fill_value']),sort_keys=True,separators=(',',':')).encode()
        assert hashlib.sha256(semantic).hexdigest()==capture['semantic_sha256']
        z=data['geometry']['coordinates'][2];fill=data['header']['fill_value']
        factor=1. if data['parameters']['ALLSKY_SFC_SW_DWN']['units']=='MJ/m^2/day' else 3.6
        for date in dates:
            exported=actual[cursor];cursor+=1
            assert exported['site']==site['id'] and exported['date']==date.isoformat()
            day=date.timetuple().tm_yday;assert int(exported['day_of_year'])==day
            values={name:parameters[name].get(date.strftime('%Y%m%d')) for name in WEATHER}
            flags=[]
            for name,value in values.items():
                assert exported[name]==('' if value is None else str(value)) or value is not None and float(exported[name])==value
                if value is None or not math.isfinite(value) or value==fill:flags.append('missing_'+name)
            if not flags:
                t,lo,hi,dew=[values[name] for name in ['T2M','T2M_MIN','T2M_MAX','T2MDEW']]
                if not (-100<t<=70 and -100<lo<=hi<=70 and -100<dew<=70):flags.append('temperature_domain')
                if not lo<=t<=hi:flags.append('temperature_order')
                if not 0<=values['RH2M']<=100:flags.append('relative_humidity_domain')
                if values['WS2M']<0:flags.append('negative_wind')
                if values['PS']<=0:flags.append('nonpositive_pressure')
                if values['ALLSKY_SFC_SW_DWN']<0:flags.append('negative_solar')
                if not flags:
                    vap=dewpoint_pressure(dew);es=(dewpoint_pressure(lo)+dewpoint_pressure(hi))/2
                    if vap>es+1e-10:flags.append('supersaturated_mean')
            assert int(exported['valid'])==int(not flags) and exported['qa']==';'.join(flags)
            row=dict(site=site['id'],date=date.isoformat(),valid=not flags,**values)
            if not flags:
                solar=values['ALLSKY_SFC_SW_DWN']*factor
                assert float(exported['solar_mj_m2_day'])==solar
                reference=scalar_reference(t,lo,hi,vap,values['WS2M'],values['PS'],solar,site['latitude'],day,z)
                for name,value in reference.items():
                    error=abs(float(exported[name])-value);errors[name]=max(errors.get(name,0.),error)
                    assert error<2e-10,(site['id'],date,name,error)
                    scalar_cells+=1
                row.update(reference)
            all_rows.append(row)
    def compare(actual,expected):
        nonlocal aggregate_error
        for name,value in expected.items():
            if value is None:assert actual[name] is None
            elif isinstance(value,int):assert actual[name]==value,(name,actual[name],value)
            else:
                error=abs(actual[name]-value);aggregate_error=max(aggregate_error,error)
                assert error<2e-8,(name,actual[name],value)
    assert len(r['monthly'])==180 and len(r['yearly'])==15 and len(r['climatology'])==36 and len(r['summaries'])==3
    for table,fields in [('monthly',['site','year','month']),('yearly',['site','year'])]:
        for aggregate in r[table]:
            selected=[row for row in all_rows if row['site']==aggregate['site'] and int(row['date'][:4])==aggregate['year'] and (table=='yearly' or int(row['date'][5:7])==aggregate['month'])]
            compare(aggregate,stats(selected))
    for site in plan['sites']:
        selected=[row for row in all_rows if row['site']==site['id']]
        summary=next(v for v in r['summaries'] if v['site']==site['id'])
        expected_stats=stats(selected);compare(summary,expected_stats)
        compare(summary['nov_mar'],stats([row for row in selected if int(row['date'][5:7]) in (11,12,1,2,3)]))
        assert summary['qa_counts']=={} and summary['valid_days']==1827
        compare(summary,dict(pm_mean_annual_mm=expected_stats['pm_total_mm']/5,hargreaves_mean_annual_mm=expected_stats['hargreaves_total_mm']/5))
        legacy_total=0.
        for month in range(1,13):
            rows=[row for row in selected if int(row['date'][5:7])==month]
            actual_month=next(v for v in r['climatology'] if v['site']==site['id'] and v['month']==month)
            compare(actual_month,stats(rows));n=len(rows)
            mean_t=math.fsum(v['T2M'] for v in rows)/n
            mean_dtr=math.fsum(v['T2M_MAX']-v['T2M_MIN'] for v in rows)/n
            mean_ra=math.fsum(v['ra_mj_m2_day'] for v in rows)/n
            monthly_har=.0023*max(mean_t+17.8,0)*math.sqrt(mean_dtr)*.408*mean_ra
            phi=math.radians(site['latitude']);time=(month-.5)*365/12
            decl=-math.radians(23.44)*math.cos(2*math.pi*(time-355)/365)
            sunset=math.acos(max(-1,min(1,-math.tan(phi)*math.tan(decl))))
            legacy_ra=1440/math.pi*.0820*(sunset*math.sin(phi)*math.sin(decl)+math.cos(phi)*math.cos(decl)*math.sin(sunset))
            legacy_har=.0023*max(mean_t+17.8,0)*math.sqrt(mean_dtr)*.408*legacy_ra
            expected=dict(temperature_mean_c=mean_t,dtr_mean_c=mean_dtr,ra_mean_mj_m2_day=mean_ra,monthly_mean_weather_hargreaves_mm_day=monthly_har,atlas_style_hargreaves_mm_day=legacy_har,atlas_style_ra_mj_m2_day=legacy_ra,aggregation_effect_mm_day=monthly_har-stats(rows)['hargreaves_mean_mm_day'],geometry_effect_mm_day=legacy_har-monthly_har)
            compare(actual_month,expected);legacy_total+=legacy_har*n
        compare(summary,dict(atlas_style_mean_annual_mm=legacy_total/5))
    fresh={}
    for name in ['results.json','daily.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    assert not r['adopt'] and not r['earth_fields_scored'] and not r['independent_regional_validation']
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),scalar_sha256=sha(ROOT/'scripts/reference_eto_scalar.py'),results_sha256=sha(OUT/'results.json'),method='Independent raw-source/date/unit/QA parsing; scalar FAO solar geometry and 40-digit Decimal equations, no producer/component import; all daily cells and temporal/atlas-style aggregates checked',daily_rows=cursor,scalar_numeric_cells=scalar_cells,max_daily_error_by_quantity=errors,site_year_month_rows=180,site_year_rows=15,climatology_rows=36,max_aggregate_numeric_error=aggregate_error,protected_files=len(r['unchanged_sha256']),fresh_byte_exact=fresh,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Passed all5481dailyrows;',scalar_cells,'independent numeric cells;180monthly,15yearly,36climatology rows;fresh files byte-exact')


if __name__=='__main__':main()
