"""Declared matched-weather reference-method comparison; no harvest adoption."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.reference_eto import daily_reference,saturation_vapour_pressure
from land_people import DAYS,hargreaves,sunlight_top
from land_people_earth import TILT,WS_DAY
from settlement_locations_earth import sha,write

PLAN=ROOT/'calibration/reference_eto_20261114/plan.json'
SOURCE=ROOT/'data/source/reference_eto_20261114/sources.json'
OUT=ROOT/'output/reference_eto_20261114'
WEATHER=['T2M','T2M_MAX','T2M_MIN','T2MDEW','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS']
MODEL=['ra_mj_m2_day','daylight_hours','rso_mj_m2_day','rs_ratio_raw','rs_ratio_used','rns_mj_m2_day','rnl_mj_m2_day','rn_mj_m2_day','es_kpa','ea_kpa','vpd_kpa','delta_kpa_c','gamma_kpa_c','pm_radiation_mm_day','pm_aerodynamic_mm_day','pm_raw_mm_day','pm_mm_day','hargreaves_mm_day']


def statistics(rows):
    valid=[r for r in rows if r['valid']]
    result=dict(expected_days=len(rows),valid_days=len(valid),invalid_days=len(rows)-len(valid))
    if not valid:
        return {**result,**{key:None for key in ['pm_total_mm','hargreaves_total_mm','pm_mean_mm_day','hargreaves_mean_mm_day','bias_mm_day','mae_mm_day','rmse_mm_day','hargreaves_over_pm']},'cloud_ratio_clipped_days':0,'negative_pm_raw_days':0}
    pm=np.array([r['pm_mm_day'] for r in valid]);har=np.array([r['hargreaves_mm_day'] for r in valid]);error=har-pm
    result.update(pm_total_mm=float(pm.sum()),hargreaves_total_mm=float(har.sum()),pm_mean_mm_day=float(pm.mean()),hargreaves_mean_mm_day=float(har.mean()),bias_mm_day=float(error.mean()),mae_mm_day=float(np.abs(error).mean()),rmse_mm_day=float(np.sqrt(np.mean(error**2))),hargreaves_over_pm=float(har.sum()/pm.sum()) if pm.sum()>0 else None,cloud_ratio_clipped_days=sum(r['rs_ratio_raw']!=r['rs_ratio_used'] for r in valid),negative_pm_raw_days=sum(r['pm_raw_mm_day']<0 for r in valid))
    return result


def main(out):
    for path in [PLAN,SOURCE,OUT/'core/review.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Freeze protocol/source/preflight before outputs'
    core=json.loads((OUT/'core/review.json').read_text());assert core['status']=='passed_before_weather_eto_outputs'
    for name,digest in core['producers'].items():assert sha(ROOT/name)==digest,name
    plan=json.loads(PLAN.read_text());receipt=json.loads(SOURCE.read_text())
    assert receipt['plan_sha256']==sha(PLAN)
    assert receipt['capturer_sha256']==sha(ROOT/'scripts/capture_reference_eto_sources.py')
    base=ROOT/'output/crop_stage_20261114';previous=json.loads((base/'reference.json').read_text())
    protected=dict(previous['unchanged_sha256'])
    for name in ['reference.json','intervals.csv','review.json']:protected[str((base/name).relative_to(ROOT))]=sha(base/name)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    begin=dt.datetime.strptime(plan['weather']['start'],'%Y%m%d').date();end=dt.datetime.strptime(plan['weather']['end'],'%Y%m%d').date()
    dates=[begin+dt.timedelta(days=i) for i in range((end-begin).days+1)]
    expected={day.strftime('%Y%m%d') for day in dates}
    daily=[];monthly=[];yearly=[];climatology=[];summaries=[];source_pins={str(SOURCE.relative_to(ROOT)):sha(SOURCE)}
    for capture in receipt['sources']:
        site=capture['site'];path=ROOT/capture['file'];assert sha(path)==capture['sha256'],path
        source_pins[capture['file']]=capture['sha256'];data=json.loads(path.read_bytes())
        assert data['header']['time_standard']=='LST' and len(data['geometry']['coordinates'])==3
        elevation=float(data['geometry']['coordinates'][2]);units=data['parameters']
        for key,wanted in [('T2M','C'),('T2M_MAX','C'),('T2M_MIN','C'),('T2MDEW','C'),('RH2M','%'),('WS2M','m/s'),('PS','kPa')]:assert units[key]['units']==wanted,(key,units[key])
        solar_unit=units['ALLSKY_SFC_SW_DWN']['units']
        assert solar_unit in ['MJ/m^2/day','kW-hr/m^2/day','kWh/m^2/day'],solar_unit
        factor=1. if solar_unit=='MJ/m^2/day' else 3.6
        params=data['properties']['parameter'];fill=data['header']['fill_value']
        assert all(set(params[key])<=expected for key in WEATHER),'Unexpected date outside declared capture'
        site_rows=[]
        for date in dates:
            key=date.strftime('%Y%m%d');values={name:params[name].get(key) for name in WEATHER};flags=[]
            for name,value in values.items():
                if value is None or not np.isfinite(value) or value==fill:flags.append('missing_'+name)
            row=dict(site=site['id'],date=date.isoformat(),day_of_year=date.timetuple().tm_yday,valid=0,qa='',**values,solar_mj_m2_day=None,**{name:None for name in MODEL})
            if not flags:
                t,lo,hi,dew=values['T2M'],values['T2M_MIN'],values['T2M_MAX'],values['T2MDEW']
                if not -100<t<=70 or not -100<lo<=hi<=70 or not -100<dew<=70:flags.append('temperature_domain')
                if not lo<=t<=hi:flags.append('temperature_order')
                if not 0<=values['RH2M']<=100:flags.append('relative_humidity_domain')
                if values['WS2M']<0:flags.append('negative_wind')
                if values['PS']<=0:flags.append('nonpositive_pressure')
                if values['ALLSKY_SFC_SW_DWN']<0:flags.append('negative_solar')
                if not flags:
                    ea=float(saturation_vapour_pressure(dew));es=float((saturation_vapour_pressure(lo)+saturation_vapour_pressure(hi))/2)
                    if ea>es+1e-10:flags.append('supersaturated_mean')
                if not flags:
                    solar=values['ALLSKY_SFC_SW_DWN']*factor
                    result=daily_reference(t,lo,hi,ea,values['WS2M'],values['PS'],solar,site['latitude'],row['day_of_year'],elevation)
                    row.update(valid=1,solar_mj_m2_day=solar,**{name:float(value) for name,value in result.items()})
            row['qa']=';'.join(flags);daily.append(row);site_rows.append(row)
        for year in range(2020,2025):
            year_rows=[r for r in site_rows if r['date'].startswith(str(year))]
            yearly.append(dict(site=site['id'],year=year,**statistics(year_rows)))
            for month in range(1,13):
                rows=[r for r in year_rows if int(r['date'][5:7])==month]
                monthly.append(dict(site=site['id'],year=year,month=month,**statistics(rows)))
        site_climate=[]
        for month in range(1,13):
            group=[r for r in site_rows if int(r['date'][5:7])==month]
            valid=[r for r in group if r['valid']]
            means={name:float(np.mean([r[name] for r in valid])) if valid else None for name in ['T2M','ra_mj_m2_day']}
            dtr=float(np.mean([r['T2M_MAX']-r['T2M_MIN'] for r in valid])) if valid else None
            row=dict(site=site['id'],month=month,**statistics(group),temperature_mean_c=means['T2M'],dtr_mean_c=dtr,ra_mean_mj_m2_day=means['ra_mj_m2_day'])
            row['monthly_mean_weather_hargreaves_mm_day']=float(.0023*max(means['T2M']+17.8,0)*np.sqrt(dtr)*.408*means['ra_mj_m2_day']) if valid else None
            site_climate.append(row)
        if all(r['valid_days'] for r in site_climate):
            t=np.array([r['temperature_mean_c'] for r in site_climate]);dtr=np.array([r['dtr_mean_c'] for r in site_climate])
            radiation=sunlight_top(np.array(site['latitude']),TILT,WS_DAY)
            legacy=hargreaves(t,dtr,radiation)/DAYS
            for i,r in enumerate(site_climate):
                r['atlas_style_hargreaves_mm_day']=float(legacy[i]);r['atlas_style_ra_mj_m2_day']=float(radiation[i]/.408)
                r['aggregation_effect_mm_day']=r['monthly_mean_weather_hargreaves_mm_day']-r['hargreaves_mean_mm_day']
                r['geometry_effect_mm_day']=r['atlas_style_hargreaves_mm_day']-r['monthly_mean_weather_hargreaves_mm_day']
        else:
            for r in site_climate:
                for key in ['atlas_style_hargreaves_mm_day','atlas_style_ra_mj_m2_day','aggregation_effect_mm_day','geometry_effect_mm_day']:r[key]=None
        climatology.extend(site_climate)
        summary=dict(site=site['id'],latitude=site['latitude'],longitude=site['longitude'],grid_elevation_m=elevation,solar_source_units=solar_unit,solar_to_mj_factor=factor,**statistics(site_rows))
        summary['pm_mean_annual_mm']=summary['pm_total_mm']/5 if summary['pm_total_mm'] is not None else None
        summary['hargreaves_mean_annual_mm']=summary['hargreaves_total_mm']/5 if summary['hargreaves_total_mm'] is not None else None
        summary['atlas_style_mean_annual_mm']=float(sum(r['atlas_style_hargreaves_mm_day']*r['valid_days'] for r in site_climate)/5) if all(r['atlas_style_hargreaves_mm_day'] is not None for r in site_climate) else None
        summary['nov_mar']=statistics([r for r in site_rows if int(r['date'][5:7]) in [11,12,1,2,3]])
        summary['qa_counts']={flag:sum(flag in r['qa'].split(';') for r in site_rows) for flag in sorted({flag for r in site_rows for flag in r['qa'].split(';') if flag})}
        summaries.append(summary)
        print(site['id'],summary['valid_days'],'/',len(site_rows),'valid;Hargreaves/PM',summary['hargreaves_over_pm'],flush=True)
    out.mkdir(parents=True,exist_ok=True)
    with (out/'daily.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(daily[0]));writer.writeheader();writer.writerows(daily)
    paths=[Path(__file__),ROOT/'harvest/reference_eto.py',ROOT/'scripts/land_people.py',ROOT/'scripts/land_people_earth.py',PLAN]
    fao_sources={name:dict(value) for name,value in plan['sources'].items()}
    fao_sources['fao56_ch3.html']['locator']+='; Equation52 Hargreaves and regional verification/high-wind limitations'
    fao_sources['fao56_ch4.html']['locator']='Example18 daily Uccle calculation; daily-reference methodology'
    write(out/'results.json',dict(status='reference_method_comparison_development_only',summaries=summaries,monthly=monthly,yearly=yearly,climatology=climatology,daily_rows=len(daily),daily_fields=list(daily[0]),methods=dict(reference='FAO56 daily grass Penman-Monteith with dewpoint and bounded cloudiness',comparison='Daily Hargreaves with identical weather and FAO radiation',atlas_style='Unchanged monthly hargreaves/sunlight_top applied to matched modern monthly weather; no legacy climate fields replaced'),producers={str(p.relative_to(ROOT)):sha(p) for p in paths},sources={**source_pins,str((OUT/'core/review.json').relative_to(ROOT)):sha(OUT/'core/review.json')},fao_sources=fao_sources,source_locator_note='Frozen protocol locates Equation52 under Chapter4; its actual location is Chapter3. Both chapters were pinned before weather capture; methods and source bytes are unchanged.',files_sha256={'daily.csv':sha(out/'daily.csv')},unchanged_sha256=protected,weather_is_gridded=True,independent_regional_validation=False,earth_fields_scored=False,adopt=False))
    print('Retained',len(daily),'daily rows;',len(monthly),'site-year-months;',len(climatology),'climatological months')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
