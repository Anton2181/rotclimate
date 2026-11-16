"""Exact crop-window catalogue and four declared fixed-request timing trials."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import land_people as LP
from harvest.exact_crop_windows import exact_crop_windows
from harvest.food_stocks import FoodYear
from polity.earth_component_work import component_work
from polity.earth_fixed_food import fixed_request_food
from urban_earth_monthly import inspect

OUT=ROOT/'output/urban_calendar_sensitivity_20261116'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
WORK=ROOT/'output/urban_component_work_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
RESTORE=ROOT/'output/urban_population_recipe_20261116/restored'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_calendar_sensitivity.json'
KCAL=912500.


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def bits(mask):return np.sum(mask.astype(np.uint16)*(1<<np.arange(12,dtype=np.uint16))[:,None],axis=0,dtype=np.uint16)


def gate():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    expected={};protected={}
    for folder,status in [(MONTHLY,'passed_fixed_request_Earth_monthly_food_portability_pilot'),
                          (WORK,'passed_paired_annual_component_work_primary_and_stress'),
                          (CAL,'passed_original_model_calendar_recovery_component_work_gate_open')]:
        q=read(folder/'qualification.json');assert q['status']==status
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q.get(key,{}).items():expected[str(prefix/name)]=digest
        protected.update(q.get('protected_sha256',{}))
    previous=read(CAL/'results.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',CAL),('protected_sha256',ROOT)]:
        for name,digest in previous[key].items():expected[str(prefix/name)]=digest
    protected.update(previous['protected_sha256'])
    for name,digest in expected.items():assert sha(name)==digest,name
    paths=[Path(__file__),PLAN,MONTHLY/'qualification.json',WORK/'qualification.json',CAL/'qualification.json',
        CAL/'calendars.npz',CAL/'prepared/inputs.npz',RESTORE/'grid/earth.npz',RESTORE/'basin/fields.npz',
        ROOT/'harvest/exact_crop_windows.py',ROOT/'tests/test_exact_crop_windows.py',ROOT/'scripts/land_people.py',
        ROOT/'polity/earth_fixed_food.py',ROOT/'polity/earth_component_work.py',ROOT/'scripts/urban_earth_monthly.py']
    return {str(p.relative_to(ROOT)):sha(p) for p in paths},protected


def catalogue():
    sources,protected=gate();folder=OUT/'catalogue';folder.mkdir(parents=True,exist_ok=True)
    assert not (folder/'results.json').exists(),'Preserve completed catalogue; use an isolated OUT'
    c=dict(np.load(CAL/'calendars.npz'));w=dict(np.load(CAL/'prepared/inputs.npz'))
    fields=dict(np.load(RESTORE/'basin/fields.npz'));grid=dict(np.load(RESTORE/'grid/earth.npz'))
    a=dict(np.load(ANNUAL/'wind_1981/prepared/low_central.npz'))
    source=c['source_indices'];inverse=c['inverse'];f=c['flood_pixels']
    assert np.all(a['crop'][source][a['crop'][source]>0]==2) and np.all(c['winter_crop']==2)
    T,P,PET,S0=[w[k] for k in ['T','P','PET','S0']]
    base=exact_crop_windows(T,P,PET,S0,w['irr'],LP.CROPS['barley'])
    catchment=fields['catchment'].ravel()[c['unique_pixels'][f]].astype(int)
    forbidden=fields['flow'][:,catchment]>1
    flood=exact_crop_windows(T[:,f],P[:,f],PET[:,f],S0[:,f],np.ones(len(f)),LP.CROPS['barley'],forbidden=forbidden)
    for result,energy,mask in [(base,c['base_energy'][1],c['base_masks'][1]),(flood,c['flood_energy'][1],c['flood_masks'][1])]:
        np.testing.assert_array_equal(result.energy,energy);np.testing.assert_array_equal(result.first_masks,mask)
        assert result.first_eligible.all()
    np.testing.assert_array_equal(base.energy.astype(np.float32),grid['kcal_barley'].ravel()[c['unique_pixels']])
    np.testing.assert_array_equal(flood.energy*w['arable'][f]*100/1.1e6,fields['basin_unit_capacity'].ravel()[c['unique_pixels'][f]])
    arrays={}
    for prefix,result in [('base',base),('flood',flood)]:
        for name,value in asdict(result).items():arrays[prefix+'_'+name]=value
    lookup=np.full(len(c['unique_pixels']),-1,int);lookup[f]=np.arange(len(f))
    flood_index=lookup[inverse];on_flood=flood_index>=0;base_valid=a['crop'][source]>0
    potential=np.array([c['base_potential_kcal'],c['basin_potential_kcal']])
    boundary_bits=np.zeros((2,len(source)),np.uint16);window_count=np.zeros_like(boundary_bits)
    boundary_bits[0,base_valid]=base.boundary_bits[inverse[base_valid]]
    window_count[0,base_valid]=base.window_count[inverse[base_valid]]
    boundary_bits[1,on_flood]=flood.boundary_bits[flood_index[on_flood]]
    window_count[1,on_flood]=flood.window_count[flood_index[on_flood]]
    for timing in ['first','earliest','latest']:
        masks=np.zeros((2,12,len(source)),bool)
        masks[0,:,base_valid]=getattr(base,timing+'_masks')[:,inverse[base_valid]].T
        masks[1,:,on_flood]=getattr(flood,timing+'_masks')[:,flood_index[on_flood]].T
        boundary=np.full((2,len(source)),-1,np.int8)
        for component in range(2):
            ends=masks[component]&~np.roll(masks[component],-1,axis=0);valid=masks[component].any(0)
            assert np.all(ends.sum(0)==valid)
            boundary[component,valid]=(ends[:,valid].argmax(0)+1)%12
        arrays[timing+'_masks']=masks;arrays[timing+'_boundary']=boundary
    np.testing.assert_array_equal(arrays['first_boundary'],np.array([c['base_boundary'],c['basin_boundary']]))
    boundary_count=sum(((boundary_bits>>m)&1).astype(np.uint8) for m in range(12))
    positive=potential>0;ambiguous=positive&(boundary_count>1)
    assert np.all(boundary_bits[positive]>0)
    arrays.update(source_indices=source,potential=potential,boundary_bits=boundary_bits,window_count=window_count)
    np.savez_compressed(folder/'windows.npz',**arrays)
    summary=dict(positive_components=int(positive.sum()),ambiguous_positive_components=int(ambiguous.sum()),
        ambiguous_energy_share=float(potential[ambiguous].sum()/potential.sum()),
        base_ambiguous_components=int(ambiguous[0].sum()),flood_ambiguous_components=int(ambiguous[1].sum()),
        flood_ambiguous_energy_share=float(potential[1,ambiguous[1]].sum()/potential[1].sum()),
        earliest_changed_components=int(((arrays['earliest_boundary']!=arrays['first_boundary'])&positive).sum()),
        latest_changed_components=int(((arrays['latest_boundary']!=arrays['first_boundary'])&positive).sum()))
    write(folder/'results.json',dict(status='exact_equal_energy_catalogue_pending_independent_review',
        sources_sha256=sources,protected_sha256=protected,windows_sha256=sha(folder/'windows.npz'),
        original_energy_and_first_masks_exact=True,full_precision_equality_only=True,flood_original_and_alternatives_eligible=True,
        summary=summary,new_fit=False,new_validation_claim=False,adopt=False))
    print('Exact catalogue',json.dumps(summary),flush=True)


def flatten(food):
    result={}
    for name,value in food.items():
        if isinstance(value,FoodYear):
            for key,array in asdict(value).items():
                if array is not None:result[name+'__'+key]=array
        else:result[name]=value
    return result


def build(reading):
    sources,protected=gate();folder=OUT/'catalogue'
    cr=read(folder/'review.json');assert cr['status']=='passed_independent_exact_crop_window_catalogue'
    assert cr['results_sha256']==sha(folder/'results.json') and cr['windows_sha256']==sha(folder/'windows.npz')
    sources[str((folder/'review.json').relative_to(ROOT))]=sha(folder/'review.json')
    sources[str((folder/'windows.npz').relative_to(ROOT))]=sha(folder/'windows.npz')
    paths=[MONTHLY/'cases'/reading/'fields.npz',MONTHLY/'cases'/reading/'results.json',
        WORK/'hours600/cases'/f'{reading}.npz',ANNUAL/'wind_1981/prepared'/f'low_{reading}.npz']
    for path in paths:sources[str(path.relative_to(ROOT))]=sha(path)
    baseline=dict(np.load(paths[0]));parent=read(paths[1]);b=dict(np.load(paths[2]));a=dict(np.load(paths[3]))
    windows=dict(np.load(folder/'windows.npz'));source=baseline['source_indices']
    between=np.maximum(1-a['between'].astype(float)/270,0)
    for season in range(4):np.fill_diagonal(between[season],0)
    args=[baseline['rural'],baseline['request'],baseline['owner'],baseline['retention'],between]
    replay=fixed_request_food(baseline['produced_components'],windows['first_boundary'],*args,marketed_share=parent['marketed_share'])
    for name,value in flatten(replay).items():np.testing.assert_array_equal(value,baseline[name])
    control=OUT/'controls';control.mkdir(parents=True,exist_ok=True)
    write(control/f'{reading}.json',dict(status='passed_original_monthly_food_all_arrays_byte_exact',reading=reading,
        baseline_fields_sha256=sha(paths[0]),arrays_exact=len(flatten(replay)),sources_sha256=sources,adopt=False))
    for timing in ['earliest','latest']:
        out=OUT/'cases'/f'{reading}_{timing}';out.mkdir(parents=True,exist_ok=True)
        assert not (out/'results.json').exists(),'Preserve completed food cases; use an isolated OUT'
        boundary=windows[timing+'_boundary']
        work=component_work(b['potential'],b['raw_area'],np.array([0.,336.,208.])[b['crops']],
            np.array([0.,48.,32.])[b['crops']],boundary,baseline['rural'],hours=600)
        for key in ['active_area','workers','annual_available','annual_used','required_listed','required_reaping','retained','produced_components','produced_total']:
            np.testing.assert_array_equal(getattr(work,key),b['B_'+key])
        assert np.all(work.monthly_peak_used<=work.peak_available+1e-8*np.maximum(1,work.peak_available))
        food=fixed_request_food(work.produced_components,boundary,*args,marketed_share=parent['marketed_share'])
        audit=inspect(food,baseline['rural'],baseline['request'],work)
        values=dict(baseline);values.update(flatten(food));values['boundary']=boundary
        values['work_monthly_peak_used']=work.monthly_peak_used
        np.savez_compressed(out/'fields.npz',**values)
        result=dict(parent);result.update(status='exact_energy_timing_case_pending_independent_review',timing=timing,
            sources_sha256=sources,protected_sha256=protected,fields_sha256=sha(out/'fields.npz'),monthly_audit=audit,
            original_monthly_control_all_arrays_exact=True,grain_work_and_requests_unchanged=True,shipment_rows=len(food['shipments']))
        lat=a['lat'].ravel()[a['nodes']];lon=a['grid_lon'].ravel()[a['nodes']]
        egypt=(lon>=29)&(lon<=32.6)&(lat<=32)
        masks={'all':np.ones(len(lat),bool),'west':a['lon']<=np.median(a['lon']),'east':a['lon']>np.median(a['lon']),
               'egypt_proper':egypt,'other':~egypt}
        for name,mask in masks.items():
            region=dict(parent['regions'][name]);region['monthly_meals_person_years']=float(food['town_food'].consumed[mask].sum()/KCAL)
            region['monthly_meal_fraction']=region['monthly_meals_person_years']/region['requested_people']
            result['regions']=dict(result['regions']);result['regions'][name]=region
        write(out/'results.json',result)
        print(reading,timing,audit['town_meal_fraction'],audit['rural_unmet_person_years'],flush=True)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--catalogue',action='store_true');p.add_argument('--reading',choices=['central','low']);args=p.parse_args()
    assert args.catalogue!=(args.reading is not None)
    try:
        if args.catalogue:catalogue()
        else:build(args.reading)
    except BaseException as error:
        OUT.mkdir(parents=True,exist_ok=True);path=OUT/('catalogue_failure.json' if args.catalogue else f'{args.reading}_failure.json')
        if not path.exists():write(path,dict(status='preserved_calendar_sensitivity_failure',error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__)),adopt=False))
        raise
