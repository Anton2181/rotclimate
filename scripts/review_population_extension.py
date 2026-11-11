"""Reconstruct the source correction and check new input lineage independently."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from polity import earth as E
from rotclimate.earth import _wc
from harvest.models import settlement_fields
from rotclimate import biomes
from land_people import ARABLE_BY_TIER,FARMED_SHARE,FALLOW,NEED_KCAL

OUT=ROOT/'output/earth_population_extension_20261111'


def people(fields):
    kinds=biomes.classify(np.nan_to_num(fields['T_ann']),np.nan_to_num(fields['P_ann']),fields['land'])
    water=np.minimum(-6.*np.log(np.maximum(np.nan_to_num(fields['irr_distance']),1e-12)),300.)
    f=settlement_fields(np.nan_to_num(fields['capacity']),np.nan_to_num(fields['npp']),kinds,np.nan_to_num(fields['arable']),water,np.nan_to_num(fields['malaria']))
    return np.where(fields['land'],np.nan_to_num(f['settlement_base'])*E.OCCUPATION_CENTRAL,0.)


def main():
    r=json.loads((OUT/'correction.json').read_text());config=ROOT/'calibration/earth_population_extension_20261111'
    for key,path in {'original_plan_sha256':config/'plan.json','correction_plan_sha256':config/'nodata_correction.json',
        'original_overlap_sha256':OUT/'overlap.json','original_tile_sha256':OUT/'tile.npz','producer_sha256':ROOT/'scripts/correct_population_extension.py',
        'current_decoder_sha256':ROOT/'scripts/land_people_earth.py','density_producer_sha256':ROOT/'scripts/compute_population_extension.py',
        'parent_global_sha256':ROOT/'output/land_people/earth/earth.npz','slope_cache_sha256':ROOT/'data/cache/arable_slope_earth/arable_5m.npz',
        'global_patch_sha256':OUT/'global_nodata_patch.npz','old_han_input_sha256':ROOT/'output/settlement_locations_20261110/han_inputs.npz',
        'new_han_input_sha256':OUT/'han_corrected_inputs.npz'}.items():assert r[key]==sha(path),key
    assert json.loads((OUT/'overlap.json').read_text())['status']=='overlap_failed_no_stitching'
    with np.load(ROOT/'output/land_people/earth/earth.npz') as z:old=dict(z)
    with np.load(ROOT/'data/cache/arable_slope_earth/arable_5m.npz') as z:slope=z['arable']
    with np.load(OUT/'global_nodata_patch.npz') as z:patch=dict(z)
    old['density']=people(old);new=dict(old)
    for key in ['arable','relief','capacity','density']:
        np.testing.assert_array_equal(old[key].ravel()[patch['indices']],patch['old_'+key])
        new[key]=old[key].copy();new[key].ravel()[patch['indices']]=patch['new_'+key]
    # Existing independent WorldClim reader already honours declared TIFF NoData.
    elev=_wc('elev')[408:1080,2016:3660]
    expected_relief=ndi.maximum_filter(np.nan_to_num(elev,nan=0),3)-ndi.minimum_filter(np.nan_to_num(elev,nan=0),3)
    tier=1+np.searchsorted([150.,400.,1000.],expected_relief)
    fallback=np.array([ARABLE_BY_TIER[int(k)] for k in tier.ravel()],np.float32).reshape(tier.shape)
    expected_arable=np.where(np.isfinite(slope),slope,fallback).astype(np.float32);land=old['land']
    np.testing.assert_array_equal(new['arable'][land],expected_arable[land])
    np.testing.assert_array_equal(new['relief'][land],expected_relief[land])
    expected_capacity=old['kcal_ha']*new['arable']*FARMED_SHARE*np.where(old['double_crop']>0,1.,FALLOW)*100./NEED_KCAL
    np.testing.assert_allclose(new['capacity'][land],expected_capacity[land],rtol=1e-6,atol=1e-6)
    np.testing.assert_array_equal(new['capacity'][land&(old['arable']==new['arable'])],old['capacity'][land&(old['arable']==new['arable'])])
    np.testing.assert_array_equal(new['density'],people(new))
    masks={key:land&(old[key]!=new[key]) for key in ['arable','relief','capacity','density']}
    for key,mask in masks.items():assert r['global_changed_cells'][key]==int(mask.sum())
    union=np.logical_or.reduce(list(masks.values()));np.testing.assert_array_equal(np.flatnonzero(union),patch['indices'])
    assert r['global_changed_cells']['union']==int(union.sum())
    with np.load(OUT/'tile.npz') as z:tile=dict(z)
    with np.load(ROOT/'data/cache/earth_population_extension_20261111/worldclim_elev.npz') as z:regional_elev=z['values']
    with np.load(ROOT/'data/cache/earth_population_extension_20261111/etopo60.npz') as z:fine=z['values']
    # A separate reconstruction of the legacy-only tile uses the actual sentinel.
    bad=np.where(np.isfinite(regional_elev),regional_elev,-32768.)
    bad_relief=ndi.maximum_filter(bad,3)-ndi.minimum_filter(bad,3)
    bad_tier=np.searchsorted([150.,400.,1000.],bad_relief)+1
    legacy_fallback=np.array([ARABLE_BY_TIER[int(k)] for k in bad_tier.ravel()],np.float32).reshape(bad_tier.shape)
    n=(fine>0).reshape(192,5,168,5).sum((1,3));legacy=dict(tile)
    legacy['arable']=np.where(n>0,tile['arable'],legacy_fallback).astype(np.float32)
    legacy['capacity']=(tile['capacity']*(legacy['arable']/tile['arable'])).astype(np.float32);legacy['density']=people(legacy)
    rows=np.flatnonzero((tile['lat']>=36)&(tile['lat']<=44));cols=np.flatnonzero((tile['lon']>=122)&(tile['lon']<=124))
    gr=np.round((old['lat'][0]-tile['lat'][rows])*12).astype(int);gc=np.round((tile['lon'][cols]-old['lon'][0])*12).astype(int)
    cases=0
    for name,a,b in [('compatibility_reproduction',legacy,old),('corrected_reference_overlap',tile,new)]:
        mask=a['land'][np.ix_(rows,cols)]&b['land'][np.ix_(gr,gc)]
        assert r[name]['land_mismatches']==0 and r[name]['land_cells']==int(mask.sum())==1370
        for key,check in r[name]['fields'].items():
            av=a[key][np.ix_(rows,cols)][mask].astype(float);bv=b[key][np.ix_(gr,gc)][mask].astype(float)
            delta=np.abs(av-bv);error=delta/np.where(bv>0,bv,1) if key in ['PET_ann','aridity','capacity','density'] else delta
            np.testing.assert_allclose(check['max_guard_error'],error.max(),rtol=1e-12,atol=1e-12)
            np.testing.assert_allclose(check['max_absolute_difference'],delta.max(),rtol=1e-12,atol=1e-12)
            assert check['passed']==bool(np.all(error<=1e-4)) and check['tolerance']==1e-4
            cases+=len(av)
        assert r[name]['passed']
    with np.load(ROOT/'output/settlement_locations_20261110/han_inputs.npz') as z:han=dict(z)
    with np.load(OUT/'han_corrected_inputs.npz') as z:target=dict(z)
    # Frozen sampler supplies original population coverage independently.
    _,_,covered=E.earth_people(han['lat'],han['lon']);required=han['allowed']&han['land'];missing=required&~covered
    assert int(missing.sum())==r['filled_required_cells']==1586
    assert target['population_covered'][required].all()
    for key in han:
        if key!='density':np.testing.assert_array_equal(han[key],target[key])
    lat,lon=old['lat'],old['lon'];step=float(lat[0]-lat[1])
    rr=(lat[0]+step/2-han['lat'])/step-.5;cc=(han['lon']-(lon[0]-step/2))/step-.5
    coords=[np.clip(rr,0,len(lat)-1),np.clip(cc,0,len(lon)-1)]
    expected=han['density'].copy();sampled=ndi.map_coordinates(new['density'],coords,order=0)
    expected[covered&han['land']]=sampled[covered&han['land']]
    tr=(48-han['lat'])*12-.5;tc=(han['lon']-120)*12-.5
    local=ndi.map_coordinates(tile['density'],[np.clip(tr,0,191),np.clip(tc,0,167)],order=0)
    expected[missing]=local[missing];np.testing.assert_array_equal(target['density'],expected)
    changed=(target['density']!=han['density'])&covered&han['land']
    source_mask=ndi.map_coordinates(masks['density'].astype(np.uint8),coords,order=0).astype(bool)
    assert not np.any(changed&~source_mask)
    assert int(changed.sum())==r['changed_original_covered_density_cells']==128
    assert r['all_core_history_requires_rebuild_before_point_qualification'] and not r['production_atlas_changed'] and not r['adopt']
    write(OUT/'review.json',dict(status='passed',correction_sha256=sha(OUT/'correction.json'),reviewer_sha256=sha(Path(__file__)),
        both_overlap_reference_cases_checked=2,field_cell_comparisons=cases,all_global_patch_cells_reconstructed=int(union.sum()),
        independently_recomputed_crop_capacity=True,all_required_han_population_cells_covered=True,
        filled_required_cells=1586,changed_original_covered_density_cells=128,all_unrelated_input_arrays_unchanged=True,
        original_failed_gate_retained=True,clipped_history_not_qualified=True,production_adopted=False))
    print('Source correction review passed:',int(union.sum()),'global patch cells',cases,'overlap comparisons;1586 inputs filled,128 covered cells corrected.')


if __name__=='__main__':main()
