"""Full-coverage fixed-grid reference forcing; no field results or adoption."""
import argparse
import csv
import datetime as dt
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.reference_eto import extraterrestrial_radiation,saturation_vapour_pressure
from harvest.reference_forcing import daily_from_radiation,mean_year_bin_totals,one_degree_cells
from settlement_locations_earth import sha,write

OUT=ROOT/'output/regional_reference_forcing_20261114'
PLAN=ROOT/'calibration/regional_reference_forcing_20261114/plan.json'
SOURCE=ROOT/'data/source/regional_reference_forcing_20261114/sources.json'
PARAMETERS=['T2M','T2M_MAX','T2M_MIN','T2MDEW','RH2M','WS2M','ALLSKY_SFC_SW_DWN','PS']


def main(out):
    for path in [PLAN,SOURCE,OUT/'core/review.json']:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    plan=json.loads(PLAN.read_text());source=json.loads(SOURCE.read_text());core=json.loads((OUT/'core/review.json').read_text())
    assert source['plan_sha256']==sha(PLAN) and source['capturer_sha256']==sha(ROOT/'scripts/capture_regional_reference_weather.py')
    assert core['status']=='passed_before_regional_eto_and_fields'
    for name,digest in {**core['producers'],**core['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    archive=ROOT/plan['candidate_archive']['file'];assert sha(archive)==plan['candidate_archive']['sha256']
    begin=dt.datetime.strptime(plan['weather_grid']['start'],'%Y%m%d').date();end=dt.datetime.strptime(plan['weather_grid']['end'],'%Y%m%d').date()
    dates=[begin+dt.timedelta(days=i) for i in range((end-begin).days+1)];keys=[d.strftime('%Y%m%d') for d in dates]
    years=np.array([d.year for d in dates]);months=np.array([d.month-1 for d in dates]);day=np.array([d.timetuple().tm_yday for d in dates])
    expected=set(keys);cell_ids=[];cell_rows=[];har=[];pm=[];elevations=[]
    data_arrays={};daily=[];source_pins={str(SOURCE.relative_to(ROOT)):sha(SOURCE)}
    for capture in source['sources']:
        cell=capture['cell'];cell_ids.append(cell['id']);path=ROOT/capture['file'];assert sha(path)==capture['sha256']
        source_pins[capture['file']]=capture['sha256'];raw=json.loads(path.read_bytes());params=raw['properties']['parameter'];fill=raw['header']['fill_value']
        units=raw['parameters'];z=raw['geometry']['coordinates'][2];elevations.append(z)
        for name,want in [('T2M','C'),('T2M_MAX','C'),('T2M_MIN','C'),('T2MDEW','C'),('RH2M','%'),('WS2M','m/s'),('PS','kPa')]:assert units[name]['units']==want,(name,units[name])
        solar_unit=units['ALLSKY_SFC_SW_DWN']['units'];assert solar_unit in ['MJ/m^2/day','kWh/m^2/day','kW-hr/m^2/day']
        factor=1. if solar_unit=='MJ/m^2/day' else 3.6
        values={name:np.array([params[name].get(key,np.nan) for key in keys],float) for name in PARAMETERS}
        assert all(set(params[name])<=expected for name in PARAMETERS)
        flags=[[] for d in dates]
        for name,v in values.items():
            for i in np.flatnonzero(~np.isfinite(v)|(v==fill)):flags[i].append('missing_'+name)
        t,lo,hi,dew=[values[name] for name in ['T2M','T2M_MIN','T2M_MAX','T2MDEW']]
        ea=np.zeros(len(dates))
        for i in range(len(dates)):
            if flags[i]:continue
            if not (-100<t[i]<=70 and -100<lo[i]<=hi[i]<=70 and -100<dew[i]<=70):flags[i].append('temperature_domain')
            if not lo[i]<=t[i]<=hi[i]:flags[i].append('temperature_order')
            if not 0<=values['RH2M'][i]<=100:flags[i].append('relative_humidity_domain')
            if values['WS2M'][i]<0:flags[i].append('negative_wind')
            if values['PS'][i]<=0:flags[i].append('nonpositive_pressure')
            if values['ALLSKY_SFC_SW_DWN'][i]<0:flags[i].append('negative_solar')
            if not flags[i]:
                ea[i]=saturation_vapour_pressure(dew[i]);es=float((saturation_vapour_pressure(lo[i])+saturation_vapour_pressure(hi[i]))/2)
                if ea[i]>es+1e-10:flags[i].append('supersaturated_mean')
        valid=np.array([not flag for flag in flags]);complete=bool(valid.all())
        ra=extraterrestrial_radiation(cell['latitude'],day)['ra_mj_m2_day']
        result={}
        if valid.any():
            good=daily_from_radiation(t[valid],lo[valid],hi[valid],ea[valid],values['WS2M'][valid],values['PS'][valid],values['ALLSKY_SFC_SW_DWN'][valid]*factor,ra[valid],z)
            for name,v in good.items():
                result[name]=np.full(len(dates),np.nan);result[name][valid]=v
        for i,date in enumerate(dates):
            daily.append(dict(cell=cell['id'],date=date.isoformat(),valid=int(valid[i]),qa=';'.join(flags[i]),**{name:values[name][i] for name in PARAMETERS},**{name:(float(v[i]) if valid[i] else '') for name,v in result.items()}))
        har_totals=mean_year_bin_totals(years,months,result['hargreaves_mm_day']) if complete else np.full(12,np.nan)
        pm_totals=mean_year_bin_totals(years,months,result['pm_mm_day']) if complete else np.full(12,np.nan)
        har.append(har_totals);pm.append(pm_totals)
        cell_rows.append(dict(cell=cell['id'],latitude=cell['latitude'],longitude=cell['longitude'],grid_elevation_m=z,expected_days=len(dates),valid_days=int(valid.sum()),complete=complete,solar_source_units=solar_unit,solar_to_mj_factor=factor,cloud_ratio_clipped_days=int(np.count_nonzero(result['rs_ratio_raw'][valid]!=result['rs_ratio_used'][valid])) if valid.any() else 0,negative_pm_raw_days=int(np.count_nonzero(result['pm_raw_mm_day'][valid]<0)) if valid.any() else 0,hargreaves_mean_annual_mm=float(har_totals.sum()) if complete else None,pm_mean_annual_mm=float(pm_totals.sum()) if complete else None,qa_counts={flag:sum(flag in f for f in flags) for flag in sorted({flag for f in flags for flag in f})}))
        print(cell['id'],int(valid.sum()),'/',len(dates),'qualified weather days',flush=True)
    cells=np.array(cell_ids);har=np.array(har);pm=np.array(pm);lookup={name:i for i,name in enumerate(cell_ids)}
    data_arrays.update(cell_ids=cells,cell_latitude=np.array([r['latitude'] for r in cell_rows]),cell_longitude=np.array([r['longitude'] for r in cell_rows]),cell_grid_elevation_m=np.array(elevations),cell_hargreaves_mm=har,cell_penman_monteith_mm=pm)
    assignments=[];regions={}
    with np.load(archive) as old:
        for region in plan['regions']:
            lat=old[region+'__lat'];lon=old[region+'__lon'];area=old[region+'__area_km2'];a,b=one_degree_cells(lat,lon)
            ids=[f'n{la:02d}_e{lo:03d}' for la,lo in zip(a,b)];indices=np.array([lookup[name] for name in ids],int)
            cell_lat=a+.5;cell_lon=b+.5
            phi=np.deg2rad(lat);phi_cell=np.deg2rad(cell_lat);angle=np.sin((phi_cell-phi)/2)**2+np.cos(phi)*np.cos(phi_cell)*np.sin(np.deg2rad(cell_lon-lon)/2)**2
            distance=2*6371.0088*np.arcsin(np.sqrt(np.clip(angle,0,1)))
            for i in range(len(lat)):
                assignments.append(dict(region=region,field=i,latitude=lat[i],longitude=lon[i],area_km2=area[i],cell=ids[i],cell_latitude=cell_lat[i],cell_longitude=cell_lon[i],distance_km=distance[i],source_grid_elevation_m=elevations[indices[i]],source_complete=int(cell_rows[indices[i]]['complete'])))
            for name in ['lat','lon','area_km2','T','P','PET','qualified']:data_arrays[region+'__'+name]=old[region+'__'+name]
            data_arrays[region+'__cell_index']=indices;data_arrays[region+'__distance_km']=distance
            data_arrays[region+'__power_hargreaves_mm']=har[indices].T;data_arrays[region+'__power_penman_monteith_mm']=pm[indices].T
            complete=all(cell_rows[i]['complete'] for i in indices)
            regions[region]=dict(candidate_fields=len(lat),candidate_area_km2=float(area.sum()),weather_cells=len(set(indices)),source_complete=complete,area_weighted_distance_km=float(np.average(distance,weights=area)),maximum_distance_km=float(distance.max()),legacy_area_weighted_annual_eto_mm=float(np.average(old[region+'__PET'].sum(0),weights=area)),power_hargreaves_area_weighted_annual_eto_mm=float(np.average(har[indices].sum(1),weights=area)) if complete else None,power_penman_monteith_area_weighted_annual_eto_mm=float(np.average(pm[indices].sum(1),weights=area)) if complete else None)
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'forcing.npz',**data_arrays)
    with (out/'assignments.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(assignments[0]));writer.writeheader();writer.writerows(assignments)
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(daily[0]));writer.writeheader();writer.writerows(daily)
    with (out/'weather_daily.csv.gz').open('wb') as file:
        with gzip.GzipFile(fileobj=file,filename='',mode='wb',mtime=0) as zipped:zipped.write(buffer.getvalue().encode())
    paths=[Path(__file__),ROOT/'harvest/reference_forcing.py',ROOT/'harvest/reference_eto.py',PLAN]
    write(out/'weather.json',dict(status='complete_grid_forcing_development_only',regions=regions,cells=cell_rows,daily_weather_rows=len(daily),field_assignments=len(assignments),temporal_mapping='Five-year average of Gregorian month totals mapped conservatively to twelve equal model bins; leap-day amounts retained',fantasy_adapter=dict(required=['mean/min/max temperature','actual vapour pressure','2m wind','surface pressure','surface solar radiation','world extraterrestrial radiation','elevation'],legacy_harvest_cache_contract='Tm/Pm plus geometry and learned DTR; near-surface wind/vapour/solar inputs are not supplied by that adapter',invented_weather=False,default_connected=False),producers={str(p.relative_to(ROOT)):sha(p) for p in paths},sources={**source_pins,str((OUT/'core/review.json').relative_to(ROOT)):sha(OUT/'core/review.json')},files_sha256={name:sha(out/name) for name in ['forcing.npz','assignments.csv','weather_daily.csv.gz']},unchanged_sha256=core['unchanged_sha256'],adopt=False))
    print('Wrote30cells,54810weather rows,1507field assignments;both basins complete:',all(v['source_complete'] for v in regions.values()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
