"""Separate compatibility replay from a declared coastal NoData correction."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from compute_population_extension import density
from prepare_population_extension import CACHE,CONFIG,OUT,LAT,LON
from polity.population_coverage import population_coverage,require_population_coverage


def compare(tile,parent):
    lat,lon=tile['lat'],tile['lon'];rows=np.flatnonzero((lat>=36)&(lat<=44));cols=np.flatnonzero((lon>=122)&(lon<=124))
    gr=np.rint((parent['lat'][0]-lat[rows])*12).astype(int);gc=np.rint((lon[cols]-parent['lon'][0])*12).astype(int)
    a=tile['land'][np.ix_(rows,cols)];b=parent['land'][np.ix_(gr,gc)];mask=a&b
    checks={}
    for key in ['T_ann','P_ann','PET_ann','aridity','arable','irr','capacity','density']:
        x=tile[key][np.ix_(rows,cols)][mask].astype(float);y=parent[key][np.ix_(gr,gc)][mask].astype(float)
        d=np.abs(x-y);relative=key in ['PET_ann','aridity','capacity','density']
        e=d/np.where(y>0,y,1) if relative else d
        checks[key]=dict(cells=len(x),max_absolute_difference=float(d.max()),mean_absolute_difference=float(d.mean()),
            max_guard_error=float(e.max()),tolerance=1e-4,passed=bool(np.isfinite(x).all() and np.isfinite(y).all() and np.all(e<=1e-4)))
    return dict(land_mismatches=int((a!=b).sum()),land_cells=int(mask.sum()),fields=checks,
        passed=bool(np.array_equal(a,b) and mask.any() and all(v['passed'] for v in checks.values())))


def sample(field,lat,lon,source_lat,source_lon):
    step=float(source_lat[0]-source_lat[1])
    r=(source_lat[0]+step/2-lat)/step-.5;c=(lon-(source_lon[0]-step/2))/step-.5
    return ndi.map_coordinates(np.asarray(field,float),[np.clip(r,0,len(source_lat)-1),np.clip(c,0,len(source_lon)-1)],order=0)


def main():
    import land_people_earth as LPE
    from polity import earth as E
    original_overlap=sha(OUT/'overlap.json');original_tile=sha(OUT/'tile.npz')
    initial=json.loads((OUT/'overlap.json').read_text())
    assert initial['status']=='overlap_failed_no_stitching' and not initial['new_han_input_created']
    # The old full source file remains recoverable at its declared Git snapshot.
    old_source=subprocess.check_output(['git','show','e552238f:scripts/land_people_earth.py'],cwd=ROOT)
    assert hashlib.sha256(old_source).hexdigest()==initial['frozen_sources']['scripts/land_people_earth.py']
    path=ROOT/'data/cache/worldclim/wc2.1_5m_elev.zip'
    with zipfile.ZipFile(path) as archive:
        with Image.open(io.BytesIO(archive.read('wc2.1_5m_elev.tif'))) as im:nodata=float(str(im.tag_v2[42113]).strip('\x00 '))
    if nodata!=-32768.:raise ValueError('NoData source differs from declared correction')
    with np.load(OUT/'tile.npz') as z:tile=dict(z)
    with np.load(ROOT/'output/land_people/earth/earth.npz') as z:parent=dict(z)
    parent['density']=density(parent)
    with np.load(CACHE/'worldclim_elev.npz') as z:elev=z['values']
    with np.load(CACHE/'etopo60.npz') as z:fine=z['values']
    ny,nx=tile['land'].shape;n=(fine>0).reshape(ny,5,nx,5).sum((1,3))
    legacy_fallback,legacy_relief=LPE.arable_share(np.where(np.isfinite(elev),elev,nodata))
    legacy_tile=dict(tile)
    legacy_tile['arable']=np.where(n>0,tile['arable'],legacy_fallback).astype(np.float32)
    legacy_tile['relief']=legacy_relief
    legacy_tile['capacity']=(tile['capacity']*(legacy_tile['arable']/tile['arable'])).astype(np.float32)
    legacy_tile['density']=density(legacy_tile)
    compatibility=compare(legacy_tile,parent)
    # Rebuild only the original global fallback, keeping finite slope evidence.
    rs,cs=LPE.window_slices();global_elev=LPE.wc('elev')[rs,cs]
    corrected_fallback,corrected_relief=LPE.arable_share(global_elev)
    global_legacy_fallback,global_legacy_relief=LPE.arable_share(np.where(np.isfinite(global_elev),global_elev,nodata))
    with np.load(ROOT/'data/cache/arable_slope_earth/arable_5m.npz') as z:slope=z['arable']
    old_rule=np.where(np.isfinite(slope),slope,global_legacy_fallback).astype(np.float32)
    if not np.array_equal(old_rule[parent['land']],parent['arable'][parent['land']]):raise ValueError('Frozen global arable source provenance does not reproduce')
    if not np.array_equal(global_legacy_relief[parent['land']],parent['relief'][parent['land']]):raise ValueError('Frozen global relief provenance does not reproduce')
    corrected=dict(parent);new_arable=np.where(np.isfinite(slope),slope,corrected_fallback).astype(np.float32)
    corrected['arable']=np.where(parent['land'],new_arable,parent['arable']).astype(np.float32)
    corrected['relief']=np.where(parent['land'],corrected_relief,parent['relief']).astype(np.float32)
    corrected['capacity']=(parent['capacity']*(corrected['arable']/parent['arable'])).astype(np.float32)
    corrected['density']=density(corrected)
    fixed=compare(tile,corrected)
    land=parent['land'];arable_changed=land&(parent['arable']!=corrected['arable'])
    relief_changed=land&(parent['relief']!=corrected['relief'])
    capacity_changed=land&(parent['capacity']!=corrected['capacity'])
    people_changed=land&(parent['density']!=corrected['density'])
    changed=arable_changed|relief_changed|capacity_changed|people_changed;indices=np.flatnonzero(changed)
    sparse=dict(indices=indices,shape=np.array(land.shape))
    for key in ['arable','relief','capacity','density']:
        sparse['old_'+key]=parent[key].ravel()[indices];sparse['new_'+key]=corrected[key].ravel()[indices]
    np.savez_compressed(OUT/'global_nodata_patch.npz',**sparse)
    result=dict(status='corrected_reference_overlap_passed' if fixed['passed'] else 'corrected_reference_overlap_failed',adopt=False,
        original_plan_sha256=sha(CONFIG/'plan.json'),correction_plan_sha256=sha(CONFIG/'nodata_correction.json'),
        original_overlap_sha256=original_overlap,original_tile_sha256=original_tile,producer_sha256=sha(Path(__file__)),
        current_decoder_sha256=sha(ROOT/'scripts/land_people_earth.py'),density_producer_sha256=sha(ROOT/'scripts/compute_population_extension.py'),
        baseline_snapshot='e552238f',original_decoder_sha256=hashlib.sha256(old_source).hexdigest(),declared_elevation_nodata=nodata,
        parent_global_sha256=sha(ROOT/'output/land_people/earth/earth.npz'),slope_cache_sha256=sha(ROOT/'data/cache/arable_slope_earth/arable_5m.npz'),
        compatibility_reproduction=compatibility,corrected_reference_overlap=fixed,
        global_changed_cells=dict(arable=int(arable_changed.sum()),relief=int(relief_changed.sum()),capacity=int(capacity_changed.sum()),density=int(people_changed.sum()),union=len(indices)),
        global_patch_sha256=sha(OUT/'global_nodata_patch.npz'),new_han_input_created=False,
        old_global_archive_overwritten=False,physics_parameters_fitted=False,production_atlas_changed=False)
    if compatibility['passed'] and fixed['passed']:
        old_path=ROOT/'output/settlement_locations_20261110/han_inputs.npz'
        with np.load(old_path) as z:han=dict(z)
        covered=population_coverage(han['lat'],han['lon'],parent['lat'],parent['lon']);required=han['allowed']&han['land']
        regional_covered=population_coverage(han['lat'],han['lon'],tile['lat'],tile['lon'])
        missing=required&~covered;require_population_coverage(covered|regional_covered,required)
        old_sample=sample(parent['density'],han['lat'],han['lon'],parent['lat'],parent['lon'])
        if not np.array_equal(old_sample[covered&han['land']],han['density'][covered&han['land']]):raise ValueError('Original covered Han density did not reconstruct exactly')
        new_sample=sample(corrected['density'],han['lat'],han['lon'],parent['lat'],parent['lon'])
        extension=sample(tile['density'],han['lat'],han['lon'],tile['lat'],tile['lon'])
        output=dict(han);output['density']=han['density'].copy();output['density'][covered&han['land']]=new_sample[covered&han['land']]
        output['density'][missing]=extension[missing]
        output['population_covered']=covered|missing;output['history_covered']=covered
        if not np.isfinite(output['density'][required]).all():raise ValueError('Nonfinite corrected Han population')
        for key in han:
            if key!='density' and not np.array_equal(output[key],han[key],equal_nan=True):raise ValueError('Changed unrelated Han input: '+key)
        np.savez_compressed(OUT/'han_corrected_inputs.npz',**output)
        result.update(new_han_input_created=True,old_han_input_sha256=sha(old_path),new_han_input_sha256=sha(OUT/'han_corrected_inputs.npz'),
            filled_required_cells=int(missing.sum()),changed_original_covered_density_cells=int(((output['density']!=han['density'])&covered&han['land']).sum()),
            changed_original_covered_required_density_cells=int(((output['density']!=han['density'])&covered&required).sum()),
            all_other_han_input_arrays_unchanged=True,all_required_population_cells_covered=True,
            all_core_history_requires_rebuild_before_point_qualification=True)
    assert sha(OUT/'overlap.json')==original_overlap and sha(OUT/'tile.npz')==original_tile
    write(OUT/'correction.json',result)
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
