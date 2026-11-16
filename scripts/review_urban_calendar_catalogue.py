"""Independent exact-window eligibility and deterministic calendar selection."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import land_people as LP
from review_urban_earth_calendars import independent_crop

OUT=ROOT/'output/urban_calendar_sensitivity_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116'
RESTORE=ROOT/'output/urban_population_recipe_20261116/restored'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def candidate_energy(T,P,PET,S0,irr,crop,start,length):
    months=np.arange(start,start+length)%12
    temp=T[months];lo,hi=crop['window']
    possible=((temp>=lo)&(temp<=hi)).all(0)&(temp.max(0)>=crop['need_warm'])
    possible&=(np.maximum(temp-crop['base'],0).sum(0)*(365/12)>=crop['heat'])
    requirement=crop['kc']*PET[months].sum(0)+crop.get('flood_mm',0)
    water=np.clip((.8*P[months].sum(0)+S0[start])/np.maximum(requirement,1),0,1)
    smooth=np.clip((water-.3)/(.5-.3),0,1)
    rain=np.clip(1-crop['ky']*(1-water),0,1)*smooth*smooth*(3-2*smooth)
    # Retain original multiplication grouping; these are exact,not near ties.
    rain=np.clip(1-crop['ky']*(1-water),0,1)*(smooth*smooth*(3-2*smooth))
    return np.where(possible,irr+(1-irr)*rain,0)*crop['grain']*1000*crop['edible']*crop['kcal']*(1-crop['seed'])


def derive(T,P,PET,S0,irr,crop,target,forbidden):
    energy,original=independent_crop(T,P,PET,S0,irr,crop)
    np.testing.assert_array_equal(energy,target)
    maximum=np.zeros(len(target));by_boundary=np.zeros((12,len(target)),bool)
    first_window=np.full((12,len(target)),-1,int);count=np.zeros(len(target),np.uint16);windows=[]
    for length in range(crop['months'][0],crop['months'][1]+1):
        for start in range(12):
            value=candidate_energy(T,P,PET,S0,irr,crop,start,length)
            maximum=np.maximum(maximum,value);months=np.arange(start,start+length)%12;b=(start+length)%12
            eligible=(target>0)&(value==target)&~forbidden[months].any(0)
            select=eligible&(first_window[b]<0);first_window[b,select]=len(windows)
            by_boundary[b]|=eligible;count+=eligible;windows.append(months)
    np.testing.assert_array_equal(maximum,target)
    valid=by_boundary.any(0);assert np.array_equal(valid,target>0)
    early=np.where(valid,by_boundary.argmax(0),-1);late=np.where(valid,11-by_boundary[::-1].argmax(0),-1)
    masks={}
    for label,phase in [('earliest',early),('latest',late)]:
        selected=np.full(len(target),-1,int);selected[valid]=first_window[phase[valid],np.flatnonzero(valid)]
        mask=np.zeros((12,len(target)),bool)
        for i,months in enumerate(windows):
            keep=selected==i
            for month in months:mask[month,keep]=True
        masks[label+'_masks']=mask;masks[label+'_boundary']=phase
    bits=sum(by_boundary[m].astype(np.uint16)*(1<<m) for m in range(12)).astype(np.uint16)
    return dict(energy=target,first_masks=original,first_eligible=~(original&forbidden).any(0),
        boundary_bits=bits,window_count=count,**masks)


def main():
    folder=OUT/'catalogue';r=json.loads((folder/'results.json').read_text())
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    assert sha(folder/'windows.npz')==r['windows_sha256']
    x=dict(np.load(folder/'windows.npz'));c=dict(np.load(CAL/'calendars.npz'));w=dict(np.load(CAL/'prepared/inputs.npz'))
    a=dict(np.load(ANNUAL/'wind_1981/prepared/low_central.npz'));f=c['flood_pixels']
    fields=dict(np.load(RESTORE/'basin/fields.npz'));catch=fields['catchment'].ravel()[c['unique_pixels'][f]].astype(int)
    T,P,PET,S0=[w[k] for k in ['T','P','PET','S0']]
    base=derive(T,P,PET,S0,w['irr'],LP.CROPS['barley'],c['base_energy'][1],np.zeros(T.shape,bool))
    flood=derive(T[:,f],P[:,f],PET[:,f],S0[:,f],np.ones(len(f)),LP.CROPS['barley'],c['flood_energy'][1],fields['flow'][:,catch]>1)
    for prefix,expected in [('base',base),('flood',flood)]:
        for name,value in expected.items():np.testing.assert_array_equal(value,x[prefix+'_'+name])
        assert expected['first_eligible'].all()
    inverse=c['inverse'];source=c['source_indices'];valid=a['crop'][source]>0
    lookup=np.full(len(c['unique_pixels']),-1,int);lookup[f]=np.arange(len(f));index=lookup[inverse];on_flood=index>=0
    expected_bits=np.zeros((2,len(source)),np.uint16);counts=np.zeros_like(expected_bits)
    expected_bits[0,valid]=base['boundary_bits'][inverse[valid]];counts[0,valid]=base['window_count'][inverse[valid]]
    expected_bits[1,on_flood]=flood['boundary_bits'][index[on_flood]];counts[1,on_flood]=flood['window_count'][index[on_flood]]
    np.testing.assert_array_equal(expected_bits,x['boundary_bits']);np.testing.assert_array_equal(counts,x['window_count'])
    for timing in ['first','earliest','latest']:
        mask=np.zeros((2,12,len(source)),bool)
        mask[0,:,valid]=base[timing+'_masks'][:,inverse[valid]].T
        mask[1,:,on_flood]=flood[timing+'_masks'][:,index[on_flood]].T
        np.testing.assert_array_equal(mask,x[timing+'_masks'])
        for component in range(2):
            starts=mask[component]&~np.roll(mask[component],1,axis=0)
            ends=mask[component]&~np.roll(mask[component],-1,axis=0);positive=mask[component].any(0)
            assert np.array_equal(starts.sum(0),positive) and np.array_equal(ends.sum(0),positive)
            boundary=np.where(positive,(ends.argmax(0)+1)%12,-1)
            np.testing.assert_array_equal(boundary,x[timing+'_boundary'][component])
    np.testing.assert_array_equal(x['first_boundary'],np.array([c['base_boundary'],c['basin_boundary']]))
    np.testing.assert_array_equal(x['potential'],np.array([c['base_potential_kcal'],c['basin_potential_kcal']]))
    boundary_count=sum(((expected_bits>>m)&1).astype(np.uint8) for m in range(12))
    positive=x['potential']>0;ambiguous=positive&(boundary_count>1)
    assert r['summary']['ambiguous_positive_components']==int(ambiguous.sum())
    assert r['summary']['ambiguous_energy_share']==float(x['potential'][ambiguous].sum()/x['potential'].sum())
    receipt=dict(status='passed_independent_exact_crop_window_catalogue',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(folder/'results.json'),windows_sha256=sha(folder/'windows.npz'),
        baseline_full_precision_energies_and_first_masks_exact=True,exact_tie_sets_and_first_window_per_boundary_exact=True,
        source_component_calendars=2*len(source),positive_components=int(positive.sum()),ambiguous_positive_components=int(ambiguous.sum()),
        flood_eligibility_checked=True,energy_tolerance_used=False,seasonal_food_cases_not_yet_run=True,new_fit=False,adopt=False)
    (folder/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2),flush=True)


if __name__=='__main__':main()
