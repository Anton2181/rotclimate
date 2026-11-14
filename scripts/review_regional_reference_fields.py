"""Independent scalar replay of all regional ETo field substitutions."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_daily_river_fields import reference,STOCKS,FLUXES
from land_people import CROPS

OUT=ROOT/'output/regional_reference_forcing_20261114'
BASE=ROOT/'output/daily_river_fields_20261114'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text());assert len(r['rows'])==24
    for name,digest in {**r['producers'],**r['sources'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    weather=json.loads((OUT/'weather.json').read_text());wr=json.loads((OUT/'weather_review.json').read_text())
    assert wr['status']=='passed_before_field_comparison' and wr['weather_sha256']==sha(OUT/'weather.json')
    assert wr['reviewer_sha256']==sha(ROOT/'scripts/review_regional_reference_weather.py')
    baseline=json.loads((BASE/'results.json').read_text())
    for name,digest in {**baseline['producers'],**baseline['sources']}.items():assert sha(ROOT/name)==digest,name
    prior=json.loads((BASE/'review.json').read_text());assert prior['reviewer_sha256']==sha(ROOT/'scripts/review_daily_river_fields.py')
    with np.load(OUT/'fields.npz') as archive:z={name:archive[name] for name in archive.files}
    with np.load(OUT/'forcing.npz') as archive:f={name:archive[name] for name in archive.files}
    with np.load(BASE/'fields.npz') as archive:old={name:archive[name] for name in archive.files}
    phase=json.loads((ROOT/'output/flood_basin_seasonality_20261113/results.json').read_text())
    columns=['initial_'+k for k in STOCKS]+['final_'+k for k in STOCKS]+['annual_'+k for k in FLUXES]
    month_names=FLUXES+['river_requested_m3','river_delivered_m3','river_loss_m3','river_outlet_m3']
    maxstate=0.;maxmass=0.;steps=0;legacy=0
    for row in r['rows']:
        case=row['case'];region=row['region'];parent=row['parent_case']
        assert row['crop']=='barley' and row['root_depth_m']==1.5 and row['bare_background']==.15 and row['pond_capacity_mm']==200 and row['efficiency']==1
        assert row['forcing'] in ['legacy_archive','power_hargreaves','power_penman_monteith']
        area=f[region+'__area_km2']*1e6;T=f[region+'__T'];P=f[region+'__P']
        PET=f[region+'__PET'] if row['forcing']=='legacy_archive' else f[region+'__'+row['forcing']+'_mm']
        begin=365*(10 if row['calendar']=='old' else 10.5)/12;end=365*(3 if row['calendar']=='old' else 2.5)/12;flood=365*7/12
        bins=np.linspace(0,365,13);edges=np.unique(np.r_[bins,np.arange(0,365),begin,end,flood])
        dt=np.diff(edges);binid=np.searchsorted(bins,edges[:-1],side='right')-1
        crop=(edges[:-1]>=begin)|(edges[1:]<=end);capture=(edges[:-1]>=flood)&(edges[1:]<=begin)
        c=CROPS['barley'];eligible=[]
        for i in range(len(area)):
            temperatures=T[binid[crop],i]
            heat=math.fsum(max(float(value)-c['base'],0)*float(days) for value,days in zip(temperatures,dt[crop]))
            eligible.append(bool(np.all((temperatures>=c['window'][0])&(temperatures<=c['window'][1]))) and temperatures.max()>=c['need_warm'] and heat>=c['heat'])
        eligible=np.array(eligible,bool);np.testing.assert_array_equal(eligible,z[case+'__eligible'])
        np.testing.assert_array_equal(eligible,old[parent+'__eligible'])
        gauge='aswan' if region=='nile' else 'hit'
        q=next(v for v in phase['rows'] if v['id']==gauge)['mean_monthly_flow_m3s'];mean=math.fsum(q)/12
        source=np.array([max(value-mean,0)*365/12*86400 for value in q])[binid]*dt/(365/12)
        annual,monthly,daily,years,residual,mass=reference(P,PET,area,dt,binid,crop,capture,eligible,source,1.5,.15,200.,1.,row['capture'],c['kc'])
        assert years==row['spinup_years'] and (residual<=1e-6)==row['periodic']
        maxmass=max(maxmass,float(mass));assert mass<1e-8
        for j,name in enumerate(columns):
            maxstate=max(maxstate,float(np.max(np.abs(z[case+'__'+name]-annual[j]))))
            np.testing.assert_allclose(z[case+'__'+name],annual[j],atol=2e-8,rtol=2e-10,err_msg=case+' '+name)
        for j,name in enumerate(month_names):np.testing.assert_allclose(z[case+'__monthly_'+name],monthly[j],atol=.01,rtol=2e-10,err_msg=case+' '+name)
        for j,name in enumerate(STOCKS):np.testing.assert_allclose(z[case+'__daily_'+name],daily[j],atol=.01,rtol=2e-10,err_msg=case+' '+name)
        cov=np.divide(annual[12],annual[13],out=np.zeros(len(area)),where=annual[13]>0)
        np.testing.assert_allclose(z[case+'__root_coverage'],cov,atol=2e-10)
        assert math.isclose(row['root_coverage'],float(np.average(cov[eligible],weights=area[eligible])),abs_tol=2e-10)
        assert math.isclose(row['eligible_area_km2'],math.fsum(area[eligible])/1e6,abs_tol=1e-7)
        assert math.isclose(row['adequate_root_area_km2'],math.fsum(area[eligible&(cov>=.95)])/1e6,abs_tol=1e-7)
        assert abs(row['joint_mass_residual_m3'])<.01
        if row['forcing']=='legacy_archive':
            for name in ['eligible','root_coverage',*columns]:np.testing.assert_array_equal(z[case+'__'+name],old[parent+'__'+name])
            for name in month_names:np.testing.assert_array_equal(z[case+'__monthly_'+name],old[parent+'__monthly_'+name])
            for name in STOCKS:np.testing.assert_array_equal(z[case+'__daily_'+name],old[parent+'__daily_'+name])
            assert row['legacy_arrays_byte_values_equal'];legacy+=1
        steps+=len(dt)*len(area)
    bycase={v['case']:v for v in r['rows']};csv_rows=0
    with gzip.open(OUT/'fields.csv.gz','rt',newline='') as file:
        for row in csv.DictReader(file):
            case=row['case'];i=int(row['field']);region=bycase[case]['region']
            for name,key in [('latitude','lat'),('longitude','lon'),('area_km2','area_km2')]:assert float(row[name])==f[region+'__'+key][i]
            ok=bool(z[case+'__eligible'][i]);assert int(row['eligible'])==ok
            if ok:assert float(row['root_coverage'])==z[case+'__root_coverage'][i]
            else:assert row['root_coverage']==''
            for name in columns:assert float(row[name])==z[case+'__'+name][i]
            csv_rows+=1
    assert csv_rows==18084 and legacy==8
    fresh={}
    for name in ['results.json','fields.npz','fields.csv.gz']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    assert not r['adopt'] and not r['harvest_or_population_scored'] and not r['independent_regional_validation']
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),scalar_field_reviewer_sha256=sha(ROOT/'scripts/review_daily_river_fields.py'),results_sha256=sha(OUT/'results.json'),weather_review_sha256=sha(OUT/'weather_review.json'),method='Reviewed independent scalar soil/pond/node kernel with only PET input changed; separate raw eligibility/clock/gauge setup; all annual field states/fluxes, monthly/daily basin arrays and CSV cells checked; producers/forcing adapter not imported',scenario_rows=24,final_cycle_field_steps=steps,max_annual_field_error_mm=maxstate,max_scalar_daily_mass_residual_mm=maxmass,csv_rows=csv_rows,legacy_cases_exact=legacy,fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Passed24paired cases;',steps,'final-cycle field steps;',csv_rows,'CSVrows;8exact legacy controls;fresh files byte-exact')


if __name__=='__main__':main()
