"""Independent source-pixel, crop-window, physical partition and timing review."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import land_people as LP
import land_people_earth as L

OUT=ROOT/'output/urban_earth_calendars_20261116'
PRIOR=ROOT/'output/urban_seasonal_transfer_20261116'
RESTORE=ROOT/'output/urban_population_recipe_20261116/restored'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def independent_crop(T,P,PET,S0,irr,spec):
    """Enumerate and rank the declared crop windows without the crop_yield function."""
    best=np.zeros(T.shape[1]);mask=np.zeros(T.shape,bool)
    for length in range(spec['months'][0],spec['months'][1]+1):
        for start in range(12):
            months=np.arange(start,start+length)%12
            temperatures=T[months]
            suitable=((temperatures>=spec['window'][0])&(temperatures<=spec['window'][1])).all(0)
            suitable&=(temperatures.max(0)>=spec['need_warm'])
            suitable&=(np.maximum(temperatures-spec['base'],0).sum(0)*(365/12)>=spec['heat'])
            demand=spec['kc']*PET[months].sum(0)+spec.get('flood_mm',0)
            water=np.clip((.8*P[months].sum(0)+S0[start])/np.maximum(demand,1),0,1)
            t=np.clip((water-.3)/(.5-.3),0,1)
            rain=np.clip(1-spec['ky']*(1-water),0,1)*(t*t*(3-2*t))
            energy=np.where(suitable,irr+(1-irr)*rain,0)*spec['grain']*1000*spec['edible']*spec['kcal']*(1-spec['seed'])
            better=energy>best;best[better]=energy[better];mask[:,better]=False
            for month in months:mask[month,better]=True
    return best,mask


def boundary(mask):
    occupied=mask.sum(0);starts=mask&~np.roll(mask,1,axis=0);ends=mask&~np.roll(mask,-1,axis=0)
    assert np.all(starts.sum(0)==(occupied>0)) and np.all(ends.sum(0)==(occupied>0))
    return np.where(occupied>0,starts.argmax(0),-1),np.where(occupied>0,(ends.argmax(0)+1)%12,-1)


def main():
    result=json.loads((OUT/'results.json').read_text())
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',OUT),('protected_sha256',ROOT)]:
        for name,digest in result[key].items():assert sha(prefix/name)==digest,name
    a=dict(np.load(OUT/'calendars.npz'));weather=dict(np.load(OUT/'prepared/inputs.npz'))
    annual=dict(np.load(PRIOR/'wind_1981/prepared/low_central.npz'))
    grid=dict(np.load(RESTORE/'grid/earth.npz'));fields=dict(np.load(RESTORE/'basin/fields.npz'))
    source=np.flatnonzero(annual['land']&annual['allowed']);np.testing.assert_array_equal(source,a['source_indices'])
    # Independently map by explicit source-pixel centres and half-up nearest rounding.
    step=float(grid['lat'][0]-grid['lat'][1])
    row=np.floor(np.clip((grid['lat'][0]-annual['lat'].ravel()[source])/step,0,len(grid['lat'])-1)+.5).astype(int)
    col=np.floor(np.clip((annual['grid_lon'].ravel()[source]-grid['lon'][0])/step,0,len(grid['lon'])-1)+.5).astype(int)
    pixels=row*len(grid['lon'])+col;np.testing.assert_array_equal(pixels,a['source_pixels'])
    unique,inverse=np.unique(pixels,return_inverse=True)
    np.testing.assert_array_equal(unique,a['unique_pixels']);np.testing.assert_array_equal(inverse,a['inverse'])
    rr,cc=np.unravel_index(unique,grid['land'].shape);rs,cs=L.window_slices()
    for month in range(1,13):
        for key,var in [('T','tavg'),('P','prec')]:np.testing.assert_array_equal(weather[key][month-1],L.wc(var,month)[rs,cs][rr,cc])
        np.testing.assert_array_equal(weather['D'][month-1],(L.wc('tmax',month)[rs,cs]-L.wc('tmin',month)[rs,cs])[rr,cc])
    assert weather['T'].dtype==weather['P'].dtype==weather['D'].dtype==np.float32
    np.testing.assert_array_equal(weather['lat'],grid['lat'][rr]);np.testing.assert_array_equal(weather['irr'],grid['irr'].ravel()[unique])
    np.testing.assert_array_equal(weather['arable'],grid['arable'].ravel()[unique])
    # Independently replay the two-pass bucket; retain the original float32 monthly saves.
    stored=np.zeros_like(weather['P']);state=np.full(len(unique),50.)
    for repeat in range(2):
        for m in range(12):
            stored[m]=state
            state=np.minimum(100,np.maximum(state+weather['P'][m]-np.minimum(weather['PET'][m],weather['P'][m]+state),0))
    np.testing.assert_array_equal(stored,weather['S0'])
    T,P,PET,S0=[weather[k] for k in ['T','P','PET','S0']]
    for i,crop in enumerate(['wheat','barley']):
        energy,mask=independent_crop(T,P,PET,S0,weather['irr'],LP.CROPS[crop])
        np.testing.assert_array_equal(energy,a['base_energy'][i]);np.testing.assert_array_equal(mask,a['base_masks'][i])
        np.testing.assert_array_equal(energy.astype(np.float32),grid['kcal_'+crop].ravel()[unique])
        f=a['flood_pixels'];energy,mask=independent_crop(T[:,f],P[:,f],PET[:,f],S0[:,f],np.ones(len(f)),LP.CROPS[crop])
        np.testing.assert_array_equal(energy,a['flood_energy'][i]);np.testing.assert_array_equal(mask,a['flood_masks'][i])
    unit=a['flood_energy'].max(0)*weather['arable'][a['flood_pixels']]*100/1.1e6
    np.testing.assert_array_equal(unit,fields['basin_unit_capacity'].ravel()[unique[a['flood_pixels']]])
    chosen=annual['crop'][source].astype(int)-1;valid=chosen>=0
    base_mask=np.zeros((12,len(source)),bool);base_mask[:,valid]=a['base_masks'][chosen[valid],:,inverse[valid]].T
    for key,value in zip(['base_start','base_boundary'],boundary(base_mask)):np.testing.assert_array_equal(a[key],value)
    s=fields['s'].ravel()[pixels];flood=s>0;lookup=np.full(len(unique),-1,int);lookup[a['flood_pixels']]=np.arange(len(a['flood_pixels']))
    index=lookup[inverse];winter=np.where(a['flood_energy'].max(0)>0,a['flood_energy'].argmax(0)+1,0)
    basin_mask=np.zeros_like(base_mask);basin_mask[:,flood]=a['flood_masks'][winter[index[flood]]-1,:,index[flood]].T
    for key,value in zip(['basin_start','basin_boundary'],boundary(basin_mask)):np.testing.assert_array_equal(a[key],value)
    base,basin=a['base_potential_kcal'],a['basin_potential_kcal'];total=annual['potential_kcal'][source]
    np.testing.assert_allclose(base+basin,total,rtol=1e-12,atol=.001)
    np.testing.assert_array_equal(base,annual['nonbasin_potential_kcal'][source]);np.testing.assert_array_equal(basin,annual['basin_potential_kcal'][source])
    assert np.all(a['base_boundary'][base>0]>=0) and np.all(a['basin_boundary'][basin>0]>=0)
    catchment=fields['catchment'].ravel()[pixels].astype(int);np.testing.assert_array_equal(catchment,a['catchment'])
    overlaps=(basin_mask&(fields['flow'][:,catchment]>1)).any(0)&(basin>0)
    np.testing.assert_array_equal(overlaps,a['flood_overlap']);assert not overlaps.any()
    timing=json.loads((RESTORE/'basin/basins.json').read_text())['last_flood_month']
    for cell in np.flatnonzero(flood):assert a['last_flood_month'][cell]==timing[str(catchment[cell])]
    monthly=list(csv.DictReader((OUT/'monthly_energy.csv').open()))
    for month,row in enumerate(monthly):
        for name,energy,phase in [('base',base,a['base_boundary']),('basin',basin,a['basin_boundary'])]:
            expected=energy[phase==month].sum()/912500
            assert abs(float(row[name+'_potential_person_years'])-expected)<1e-7
            grown=(energy*a['annual_grown_fraction'])[phase==month].sum()/912500
            assert abs(float(row[name+'_annual_work_limited_person_years'])-grown)<1e-7
    assert abs(sum(float(row[k]) for row in monthly for k in ['base_potential_person_years','basin_potential_person_years'])-total.sum()/912500)<1e-6
    both=(base>0)&(basin>0);different=both&(a['base_boundary']!=a['basin_boundary'])
    # Read-only implication of actual physical cropped-area partitions. This does NOT change work/production.
    area=100*float(annual['cell_km'])**2*annual['arable'].ravel()[source]
    original_hectares=area*.36
    component_hectares=area*((1-s)*.36+s*.95)
    ratio=np.divide(component_hectares,original_hectares,out=np.ones_like(area),where=original_hectares>0)
    # Evaluate the clean comparison on cells with both positive components; no assumption about sowing failed crop areas.
    comparison=ratio[both]
    receipt=dict(status='passed_original_model_calendar_and_source_partition_review',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),calendars_sha256=sha(OUT/'calendars.npz'),
        original_engine_energy_and_masks_independently_exact=True,base_float32_energy_values_exact=int(a['base_energy'].size),
        basin_float64_unit_capacity_exact=True,weather_source_month_fields_exact=36,
        active_sources=len(source),positive_sources=int((total>0).sum()),zero_production_sources=int((total==0).sum()),
        component_energy_calendar_coverage=1.,basin_sources=int(flood.sum()),basin_high_flow_overlap_sources=int(overlaps.sum()),
        positive_base_and_basin_sources=int(both.sum()),different_component_harvest_sources=int(different.sum()),
        different_harvest_basin_energy_share=float(basin[different].sum()/basin.sum()),
        different_harvest_world_energy_share=float((base[different]+basin[different]).sum()/total.sum()),
        work_partition_gap=dict(interpretation='The annual blended-yield work recipe charges0.36arable hectares per physical-cell hectare. Separate physical component sowing at0.36nonbasin/0.95basin implies different work. This diagnostic changes no annual work or grain and does not decide the new seasonal work allocation.',
            both_positive_sources=int(both.sum()),physical_component_to_annual_task_area_ratio_min=float(comparison.min()),
            ratio_median=float(np.median(comparison)),ratio_max=float(comparison.max()),
            both_positive_additional_potential_barley_listed_hours=float(((component_hectares-original_hectares)*208)[both].sum()),
            next_gate='Declare whether to preserve the annual work scenario with an explicit component task partition or test revised physical cropped-area work with a separate annual control. Never charge independent full-cell workers to each harvest.'),
        observed_calendar_validation=False,seasonal_trial_performed=False,seasonal_trial_ready=False,new_fit=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
