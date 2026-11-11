"""Recompute a regional ecological tile and enforce overlap before stitching."""
import json
from pathlib import Path
import sys
import numpy as np
from scipy import ndimage as ndi

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from prepare_population_extension import CACHE,CONFIG,OUT,LAT,LON
from polity.population_coverage import population_coverage,require_population_coverage


def density(fields):
    from harvest.models import settlement_fields
    from rotclimate import biomes
    from polity.earth import OCCUPATION_CENTRAL
    land=fields['land'];biome=biomes.classify(np.nan_to_num(fields['T_ann']),np.nan_to_num(fields['P_ann']),land)
    water=np.minimum(-6*np.log(np.maximum(np.nan_to_num(fields['irr_distance']),1e-12)),300.)
    f=settlement_fields(np.nan_to_num(fields['capacity']),np.nan_to_num(fields['npp']),biome,np.nan_to_num(fields['arable']),water,np.nan_to_num(fields['malaria']))
    return np.where(land,np.nan_to_num(f['settlement_base'])*OCCUPATION_CENTRAL,0.)


def compute():
    import land_people_earth as LPE
    import arable_slope_earth as ASE
    sources=json.loads((OUT/'sources.json').read_text())
    if sources['plan_sha256']!=sha(CONFIG/'plan.json'):raise ValueError('Changed extension plan')
    if sources['producer_sha256']!=sha(ROOT/'scripts/prepare_population_extension.py'):raise ValueError('Changed source preparation')
    raw={}
    for name,meta in sources['sources'].items():
        path=ROOT/meta['regional_file']
        if sha(path)!=meta['regional_npz_sha256']:raise ValueError('Changed regional source')
        with np.load(path) as z:raw[name]=z['values']
    with np.load(CACHE/'worldclim_elev.npz') as z:lat,lon=z['lat'],z['lon']
    T,P=raw['tavg'],raw['prec'];D=raw['tmax']-raw['tmin'];elev=raw['elev'];z=raw['etopo60'].astype(float)
    land=np.isfinite(elev)&np.isfinite(T).all(0)&np.isfinite(P).all(0)&np.isfinite(D).all(0)
    if not np.isfinite(D[:,land]).all() or np.any(D[:,land]<0):raise ValueError('Invalid observed daily range')
    print('Regional climate/terrain shapes',T.shape,z.shape,'land',int(land.sum()),flush=True)
    if z.shape!=tuple(v*5 for v in land.shape):raise ValueError('ETOPO/WorldClim grids not aligned')
    LPE.WINDOW=dict(lat=LAT,lon=LON)
    # Supply the validated regional raster to the original unmodified HAND routine.
    ASE.etopo_window=lambda:z
    irrigation,irrigation_distance=LPE.irrigation(land.shape,gate=True)
    fallback,relief=LPE.arable_share(elev)
    m=json.loads((ROOT/'data/arable_slope_model.json').read_text())['params']
    fine_land=z>0;fine_lat=LAT[1]-(np.arange(z.shape[0])+.5)/60
    gy=np.gradient(np.where(fine_land,z,0),111320/60,axis=0)
    gx=np.gradient(np.where(fine_land,z,0),axis=1)/((111320/60)*np.cos(np.radians(fine_lat))[:,None])
    slope=np.degrees(np.arctan(np.hypot(gx,gy)))
    a=m['lo']+(m['hi']-m['lo'])/(1+np.power(np.maximum(slope,1e-6)/m['S0'],m['k']))
    ny,nx=land.shape;block=lambda v:v.reshape(ny,5,nx,5).sum((1,3))
    n=block(fine_land.astype(float))
    arable=np.where(n>0,block(np.where(fine_land,a,0))/np.maximum(n,1),fallback).astype(np.float32)
    print('Computing identical current crop/food rules;FALLOW',LPE.analyse.__globals__['FALLOW'],flush=True)
    annual,crops=LPE.analyse(T[:,land],P[:,land],np.broadcast_to(lat[:,None],land.shape)[land],LPE.TILT,LPE.WS_DAY,
        irrigation[land],arable[land],D[:,land],margins=None)
    fields={}
    for key,values in annual.items():
        field=np.full(land.shape,-1 if key=='main_crop' else np.nan,np.float32);field[land]=values;fields[key]=field
    fields.update(land=land,irr=irrigation,irr_distance=irrigation_distance,arable=arable,relief=relief,lat=lat,lon=lon)
    fields['density']=density(fields)
    np.savez_compressed(OUT/'tile.npz',**fields,crops=np.array(crops))
    with np.load(ROOT/'output/land_people/earth/earth.npz') as archive:old=dict(archive)
    old['density']=density(old)
    rows=np.flatnonzero((lat>=36)&(lat<=44));cols=np.flatnonzero((lon>=122)&(lon<=124))
    gr=np.rint((old['lat'][0]-lat[rows])/(old['lat'][0]-old['lat'][1])).astype(int)
    gc=np.rint((lon[cols]-old['lon'][0])/(old['lon'][1]-old['lon'][0])).astype(int)
    new_land=land[np.ix_(rows,cols)];old_land=old['land'][np.ix_(gr,gc)]
    common=new_land&old_land;checks={}
    for key in ['T_ann','P_ann','PET_ann','aridity','arable','irr','capacity','density']:
        new=fields[key][np.ix_(rows,cols)][common].astype(float);parent=old[key][np.ix_(gr,gc)][common].astype(float)
        finite=np.isfinite(new)&np.isfinite(parent);difference=np.abs(new-parent)
        relative=key in ['PET_ann','aridity','capacity','density']
        denominator=np.where(parent>0,parent,1.) if relative else np.ones_like(parent)
        scaled=difference/denominator
        checks[key]=dict(compared_cells=len(new),finite_cells=int(finite.sum()),max_absolute_difference=float(difference.max()),
            mean_absolute_difference=float(difference.mean()),max_guard_error=float(scaled.max()),tolerance=1e-4,
            guard_metric='relative_where_parent_positive_else_absolute' if relative else 'absolute',
            passed=bool(finite.all() and np.all(scaled<=1e-4)))
    land_check=dict(compared_cells=int(common.size),parent_land_cells=int(old_land.sum()),tile_land_cells=int(new_land.sum()),
        mismatched_land_cells=int((old_land!=new_land).sum()),passed=bool(np.array_equal(old_land,new_land)))
    passes=land_check['passed'] and common.any() and all(v['passed'] for v in checks.values())
    hashes={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'scripts/land_people.py',ROOT/'scripts/land_people_earth.py',
        ROOT/'scripts/arable_slope_earth.py',ROOT/'data/arable_slope_model.json',ROOT/'harvest/models.py',
        ROOT/'rotclimate/biomes.py',ROOT/'data/cache/naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson',
        ROOT/'output/land_people/earth/earth.npz',ROOT/'output/settlement_locations_20261110/han_inputs.npz']}
    result=dict(status='overlap_passed' if passes else 'overlap_failed_no_stitching',adopt=False,
        plan_sha256=sha(CONFIG/'plan.json'),sources_sha256=sha(OUT/'sources.json'),producer_sha256=sha(Path(__file__)),
        frozen_sources=hashes,tile_sha256=sha(OUT/'tile.npz'),crop_margins=None,fallow=float(LPE.analyse.__globals__['FALLOW']),
        overlap_land=land_check,overlap_fields=checks,overlap_pass=bool(passes),new_han_input_created=False,
        physics_calibration_changed=False,population_ledger_changed=False)
    if passes:
        with np.load(ROOT/'output/settlement_locations_20261110/han_inputs.npz') as archive:han=dict(archive)
        covered=population_coverage(han['lat'],han['lon'],old['lat'],old['lon']);required=han['land']&han['allowed'];missing=required&~covered
        tile_covered=population_coverage(han['lat'],han['lon'],lat,lon)
        require_population_coverage(covered|tile_covered,required)
        r=(LAT[1]-han['lat'])*12-.5;c=(han['lon']-LON[0])*12-.5
        sampled=ndi.map_coordinates(fields['density'],[r,c],order=0,mode='nearest')
        if not np.isfinite(sampled[missing]).all():raise ValueError('Nonfinite extension population')
        han['density']=han['density'].copy();han['density'][missing]=sampled[missing]
        han['population_covered']=covered|tile_covered;han['history_covered']=covered
        # Original aridity was computed on the entire regional climate window: keep it.
        np.savez_compressed(OUT/'han_inputs.npz',**han)
        result.update(new_han_input_created=True,new_han_input_sha256=sha(OUT/'han_inputs.npz'),
            filled_required_cells=int(missing.sum()),original_covered_density_unchanged=True,original_aridity_unchanged=True,
            history_still_unsupported_in_extension=True)
    write(OUT/'overlap.json',result)
    print(json.dumps(dict(status=result['status'],land=land_check,fields=checks),indent=2),flush=True)


if __name__=='__main__':compute()
