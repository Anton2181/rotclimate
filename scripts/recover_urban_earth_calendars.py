"""Original-engine crop-calendar provenance; no seasonal supply simulation."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import land_people as LP
import land_people_earth as L

PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_calendar_recovery.json'
PRIOR=ROOT/'output/urban_seasonal_transfer_20261116'
RESTORED=ROOT/'output/urban_population_recipe_20261116/restored'
OUT=ROOT/'output/urban_earth_calendars_20261116'
KCAL=912500.


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def bits(mask):return np.sum(mask.astype(np.uint16)*(1<<np.arange(12,dtype=np.uint16))[:,None],axis=0,dtype=np.uint16)


def phase(mask):
    start=mask&~np.roll(mask,1,axis=0);end=mask&~np.roll(mask,-1,axis=0)
    valid=mask.any(0)
    assert np.all(start.sum(0)==valid) and np.all(end.sum(0)==valid)
    return np.where(valid,start.argmax(0),-1),np.where(valid,(end.argmax(0)+1)%12,-1)


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    previous=read(PRIOR/'results.json');review=read(PRIOR/'wind_1981/review.json')
    assert previous['qualified_annual_cases']==6 and review['status']=='passed_exact_annual_controls_and_independent_primary_flow_audit'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PRIOR),('protected_sha256',ROOT)]:
        for name,digest in previous[key].items():assert sha(prefix/name)==digest,name
    OUT.mkdir(parents=True,exist_ok=True);prepared=OUT/'prepared';prepared.mkdir(exist_ok=True)
    assert not (OUT/'results.json').exists(),'Preserve completed results; use a new isolated OUT for a fresh reconstruction'
    grid=dict(np.load(RESTORED/'grid/earth.npz'));basin=dict(np.load(RESTORED/'basin/fields.npz'))
    annual_path=PRIOR/'wind_1981/prepared/low_central.npz';annual=dict(np.load(annual_path))
    source=np.flatnonzero(annual['land']&annual['allowed']);step=float(grid['lat'][0]-grid['lat'][1])
    r=(grid['lat'][0]+step/2-annual['lat'])/step-.5
    c=(annual['grid_lon']-(grid['lon'][0]-step/2))/step-.5
    assert ((r.ravel()[source]>=-.5)&(r.ravel()[source]<=len(grid['lat'])-.5)&(c.ravel()[source]>=-.5)&(c.ravel()[source]<=len(grid['lon'])-.5)).all()
    indices=np.arange(grid['land'].size,dtype=np.int32).reshape(grid['land'].shape)
    sampled=ndi.map_coordinates(indices,[np.clip(r,0,len(grid['lat'])-1),np.clip(c,0,len(grid['lon'])-1)],order=0).ravel()[source]
    unique,inverse=np.unique(sampled,return_inverse=True);assert grid['land'].ravel()[unique].all()
    rr,cc=np.unravel_index(unique,grid['land'].shape);rs,cs=L.window_slices()
    assert len(unique)==54324 and len(source)==56378
    fields={k:[] for k in ['T','P','D']}
    for m in range(1,13):
        fields['T'].append(L.wc('tavg',m)[rs,cs][rr,cc]);fields['P'].append(L.wc('prec',m)[rs,cs][rr,cc])
        fields['D'].append((L.wc('tmax',m)[rs,cs]-L.wc('tmin',m)[rs,cs])[rr,cc])
        print('crop-source weather month',m,flush=True)
    T,P,D=[np.stack(fields[k]) for k in ['T','P','D']]
    lat=grid['lat'][rr];irr=grid['irr'].ravel()[unique];arable=grid['arable'].ravel()[unique]
    PET=LP.hargreaves(T,D,LP.sunlight_top(lat,L.TILT,L.WS_DAY));S0=LP.bucket(P,PET)
    base_energy=[];base_masks=[]
    for crop in ['wheat','barley']:
        energy,mask=LP.crop_yield(T,P,PET,S0,irr,LP.CROPS[crop])
        np.testing.assert_array_equal(energy.astype(np.float32),grid['kcal_'+crop].ravel()[unique])
        base_energy.append(energy);base_masks.append(mask);phase(mask)
    base_energy=np.array(base_energy);base_masks=np.array(base_masks)
    flood_pixels=np.flatnonzero(basin['s'].ravel()[unique]>0)
    flooded_energy=[];flooded_masks=[]
    for crop in ['wheat','barley']:
        energy,mask=LP.crop_yield(T[:,flood_pixels],P[:,flood_pixels],PET[:,flood_pixels],S0[:,flood_pixels],
                                  np.ones(len(flood_pixels)),LP.CROPS[crop])
        flooded_energy.append(energy);flooded_masks.append(mask);phase(mask)
    flooded_energy=np.array(flooded_energy);flooded_masks=np.array(flooded_masks)
    winter=flooded_energy.max(0)
    unit=winter*arable[flood_pixels]*100./LP.NEED_KCAL
    np.testing.assert_array_equal(unit,basin['basin_unit_capacity'].ravel()[unique[flood_pixels]])
    winter_crop=np.where(winter>0,flooded_energy.argmax(0)+1,0).astype(np.uint8)
    winter_ties=(winter>0)&(flooded_energy[0]==flooded_energy[1])
    # np.maximum retained energy only; wheat-first identity is an explicit reporting convention for a tie.
    choice=annual['crop'][source].astype(int)-1;valid=choice>=0
    base_selected=np.zeros((12,len(source)),bool)
    base_selected[:,valid]=base_masks[choice[valid],:,inverse[valid]].T
    flood_lookup=np.full(len(unique),-1,int);flood_lookup[flood_pixels]=np.arange(len(flood_pixels))
    flood_index=flood_lookup[inverse];flood=flood_index>=0
    basin_selected=np.zeros_like(base_selected)
    basin_selected[:,flood]=flooded_masks[winter_crop[flood_index[flood]]-1,:,flood_index[flood]].T
    base_start,base_boundary=phase(base_selected);basin_start,basin_boundary=phase(basin_selected)
    base_potential=annual['nonbasin_potential_kcal'][source];basin_potential=annual['basin_potential_kcal'][source]
    total=annual['potential_kcal'][source]
    np.testing.assert_allclose(base_potential+basin_potential,total,rtol=1e-12,atol=.001)
    assert np.all(base_boundary[base_potential>0]>=0) and np.all(basin_boundary[basin_potential>0]>=0)
    assert np.all(basin_potential[~flood]==0)
    catchment=basin['catchment'].ravel()[sampled].astype(int)
    high_flow=(basin['flow'][:,catchment]>1)&flood
    overlaps=(basin_selected&high_flow).any(0)&(basin_potential>0)
    maximum_crop=np.zeros(len(source),np.uint8);maximum_crop[flood]=winter_crop[flood_index[flood]]
    mismatch=(basin_potential>0)&(maximum_crop!=annual['crop'][source])
    flood_timing=read(RESTORED/'basin/basins.json');last=np.full(len(source),-1,int)
    for k,value in flood_timing['last_flood_month'].items():
        if value is not None:last[catchment==int(k)]=value
    fraction=np.divide(annual['grown_kcal'][source],total,out=np.zeros_like(total),where=total>0)
    monthly=[]
    for month in range(12):
        base=base_boundary==month;flood_month=basin_boundary==month
        monthly.append(dict(boundary_month=month+1,label=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][month],
            base_potential_person_years=float(base_potential[base].sum()/KCAL),
            basin_potential_person_years=float(basin_potential[flood_month].sum()/KCAL),
            base_annual_work_limited_person_years=float((base_potential*fraction)[base].sum()/KCAL),
            basin_annual_work_limited_person_years=float((basin_potential*fraction)[flood_month].sum()/KCAL)))
    table(OUT/'monthly_energy.csv',monthly)
    np.savez_compressed(prepared/'inputs.npz',T=T,P=P,D=D,PET=PET,S0=S0,lat=lat,irr=irr,arable=arable)
    np.savez_compressed(OUT/'calendars.npz',source_indices=source,source_pixels=sampled,unique_pixels=unique,inverse=inverse,
        base_energy=base_energy,base_masks=base_masks,flood_pixels=flood_pixels,flood_energy=flooded_energy,flood_masks=flooded_masks,
        winter_crop=winter_crop,winter_ties=winter_ties,base_start=base_start,base_boundary=base_boundary,
        basin_start=basin_start,basin_boundary=basin_boundary,base_potential_kcal=base_potential,basin_potential_kcal=basin_potential,
        annual_grown_fraction=fraction,catchment=catchment,last_flood_month=last,flood_overlap=overlaps,
        basin_crop_differs_from_mixed_work=mismatch,basin_crop=maximum_crop)
    paths=[Path(__file__),PLAN,PRIOR/'results.json',PRIOR/'wind_1981/review.json',annual_path,
           RESTORED/'grid/earth.npz',RESTORED/'basin/fields.npz',RESTORED/'basin/basins.json',
           ROOT/'scripts/land_people.py',ROOT/'scripts/land_people_earth.py',ROOT/'scripts/floodplain_earth.py']
    paths += [ROOT/s['path'] for s in read(ROOT/'data/earth_harvest_public_sources_20261113.json')['sources']]
    crops=['wheat','barley'];residuals={c:float(abs(base_energy[i]-grid['kcal_'+c].ravel()[unique]).max()) for i,c in enumerate(crops)}
    result=dict(status='reconstructed_model_calendars_pending_independent_review',producer_sha256=sha(Path(__file__)),
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=previous['protected_sha256'],
        files_sha256={str(p.relative_to(OUT)):sha(p) for p in [OUT/'calendars.npz',prepared/'inputs.npz',OUT/'monthly_energy.csv']},
        active_sources=len(source),unique_crop_source_pixels=len(unique),positive_sources=int((total>0).sum()),zero_production_sources=int((total==0).sum()),
        base_crop_energies_float32_bitexact=True,full_precision_vs_stored_kcal_ha_max_absolute_residual=residuals,
        basin_unit_capacity_float64_bitexact=True,calendar_coverage_of_component_energy=1.,
        basin_sources=int(flood.sum()),basin_positive_sources=int((basin_potential>0).sum()),
        basin_energy_share=float(basin_potential.sum()/total.sum()),
        basin_crop_differs_from_mixed_work_sources=int(mismatch.sum()),
        basin_crop_differs_from_mixed_work_energy_share=float(basin_potential[mismatch].sum()/basin_potential.sum()),
        basin_crop_tie_pixels=int(winter_ties.sum()),
        basin_window_overlaps_high_flow_sources=int(overlaps.sum()),
        basin_window_overlaps_high_flow_energy_share=float(basin_potential[overlaps].sum()/basin_potential.sum()),
        flood_check='Any growing bin with saved catchment flow>1; a model timing diagnostic,not observed inundation or a new sowing constraint.',
        month_convention='Original Earth January-indexed WorldClim bins; harvest at next-bin boundary after the last occupied growth bin. Original tilt23.44/solar ws_day355 unchanged.',
        calendar_selection='Original first strict best window; no tie optimization. Winter crop identity uses wheat-first for exact energy ties as reporting convention only.',
        seasonal_trial_performed=False,seasonal_trial_ready=False,new_validation_claim=False,new_fit=False,adopt=False)
    for name,digest in result['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if not k.endswith('sha256')},indent=2),flush=True)


if __name__=='__main__':
    try:main()
    except BaseException as error:
        OUT.mkdir(parents=True,exist_ok=True)
        path=OUT/'failure.json'
        if not path.exists():path.write_text(json.dumps(dict(status='preserved_calendar_recovery_failure',error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__)),adopt=False),indent=2)+'\n')
        raise
