"""Attach an adapted FORGE foraging scenario to an existing climate atlas.

The independently resolved analysis grid is coarser than Harvest. Conservative
area averages preserve land and annual dry-matter budgets; no climate is run,
no agricultural support is changed, and finite-horizon density is not a census.
"""
from dataclasses import fields as dataclass_fields
from pathlib import Path
import csv
import hashlib
import json
import math
import shutil
import time
import numpy as np
from PIL import Image
from scipy.sparse import csr_matrix
from harvest.export import (climate_arrays, color_image, geometry, physical_metadata,
                            surface_months, tiers)
from .forcing import ROOT, aquatic_annual, daily_resources, miami_npp, specification

MODES = [
    ('density_people_km2','forage_density','Foraging density','people/km² · finite-horizon foraging scenario',.001,10.,True),
    ('foraging_hours_day','forage_effort','Foraging effort','hours/person/day · final-window annual mean',0.,8.,False),
    ('scarcity_days_year','forage_shortfall','Food shortfall','days/year with an energy shortfall',0.,365.,False),
    ('meat_fraction','forage_carnivory','Meat share','annual animal-food energy fraction (prey and fish) · final-window mean',0.,1.,False),
    ('fish_share','forage_fish','Fish share','share of food energy from coastal and freshwater fish · final-window mean',0.,1.,False)]
PALETTES = {
    'density_people_km2':['#f2eed6','#b9cf91','#639c7b','#2d6b75','#253d5d'],
    'foraging_hours_day':['#e9eed9','#c8d78c','#e4bd62','#c77b43','#903c43'],
    'scarcity_days_year':['#f0eedc','#ead8a2','#dba45e','#c46848','#842f45'],
    'meat_fraction':['#e7e5d5','#bdc19a','#8e9c8c','#5f7a89','#354d73'],
    'fish_share':['#eef0e6','#b9d6d3','#6fb0bd','#2f7f9e','#1f4b72']}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def overlap_matrix(source_size, destination_size):
    """Normalized overlap of equal-width output cells with input pixels."""
    if not isinstance(source_size, int) or not isinstance(destination_size, int) or min(source_size,destination_size)<1:
        raise ValueError('Need positive integer grid dimensions')
    edge=np.linspace(0.,source_size,destination_size+1);rows=[];cols=[];values=[]
    for i,(left,right) in enumerate(zip(edge[:-1],edge[1:])):
        for j in range(max(0,int(np.floor(left))),min(source_size,int(np.ceil(right)))):
            overlap=max(0.,min(right,j+1)-max(left,j))
            if overlap:
                rows.append(i);cols.append(j);values.append(overlap/(right-left))
    return csr_matrix((values,(rows,cols)),shape=(destination_size,source_size))


def area_average(values, shape):
    """Exact equal-area grid averages; arbitrary leading axes are retained."""
    value=np.asarray(values,float)
    if value.ndim<2 or not np.isfinite(value).all():
        raise ValueError('Need finite spatial grid values')
    shape=tuple(int(x) for x in shape)
    if len(shape)!=2 or min(shape)<1:
        raise ValueError('Need a two-dimensional destination shape')
    wy=overlap_matrix(int(value.shape[-2]),shape[0]);wx=overlap_matrix(int(value.shape[-1]),shape[1])
    flat=value.reshape((-1,)+value.shape[-2:])
    result=np.stack([(wx@(wy@plane).T).T for plane in flat])
    return result.reshape(value.shape[:-2]+shape)


def land_average(values, land_fraction, shape):
    value=np.asarray(values,float);fraction=np.asarray(land_fraction,float)
    if value.shape[-2:]!=fraction.shape or not np.isfinite(fraction).all() or ((fraction<0)|(fraction>1)).any():
        raise ValueError('Need finite matching coastal land fractions')
    weight=area_average(fraction,shape)
    numerator=area_average(value*fraction,shape)
    return np.divide(numerator,weight,out=np.zeros_like(numerator),where=weight>0)


def pack_fields(fields, land, path):
    """Lossless float32 packet; finite real zero remains distinct from ocean."""
    blob=bytearray();descriptors={};land=np.asarray(land,bool)
    boolean={'converged','floor_limited','unsupported'}
    for name,value in fields.items():
        value=np.asarray(value)
        if value.shape!=land.shape or not np.isfinite(value[land]).all():
            raise ValueError('Invalid foraging output: '+name)
        if name in boolean:
            if not np.isin(value[land],[0,1]).all():raise ValueError('Invalid boolean scenario status')
            packed=np.where(land,value,255).astype('u1');dtype='uint8';nodata=255
        else:
            packed=np.where(land,value,np.nan).astype('<f4');dtype='float32';nodata=None
        while len(blob)%4:blob.append(0)
        descriptors[name]=dict(dtype=dtype,offset_bytes=len(blob),shape=list(land.shape),scale=1.,offset=0.,nodata=nodata)
        blob.extend(packed.tobytes())
    Path(path).write_bytes(blob)
    return descriptors


def province_fractions(data, fine_land_fraction, shape):
    """Conservative within-cell province areas, including unassigned land."""
    hm=json.loads((data/'harvest.json').read_text());s=hm['arrays']['hex_id']
    raw=np.frombuffer((data/'harvest.bin').read_bytes(),dtype=np.dtype(s['dtype']),
                      count=int(np.prod(s['shape'])),offset=s['offset_bytes']).reshape(s['shape'])
    if raw.shape!=fine_land_fraction.shape:raise ValueError('Province and input geography grids differ')
    lookup=np.zeros(int(raw.max())+1,np.uint16)
    names=['Outside province grid']
    for i,province in enumerate(hm['provinces'],1):
        names.append(province['name']);lookup[np.asarray(province['hexes'],int)]=i
    ids=lookup[raw]
    fractions=np.stack([area_average(fine_land_fraction*(ids==i),shape) for i in range(len(names))])
    np.testing.assert_allclose(fractions.sum(0),area_average(fine_land_fraction,shape),rtol=2e-13,atol=2e-14)
    return names,fractions


def aggregates(fields, land_fraction, cell_area_km2, province_names, province_fraction):
    area=np.asarray(land_fraction,float)*cell_area_km2
    density=np.asarray(fields['density_people_km2'],float)
    supported=np.asarray(fields.get('unsupported',np.zeros(area.shape)),bool)
    converged=np.asarray(fields['converged'],bool)
    total_area=float(area.sum());population=float((density*area).sum())
    def mean(key, weights=area):
        return float((np.asarray(fields[key],float)*weights).sum()/max(float(weights.sum()),1e-30))
    summary=dict(total_scenario_people=population,land_km2=total_area,
        mean_density_people_km2=population/max(total_area,1e-30),
        converged_scenario_people=float((density*area*converged).sum()),
        converged_land_share=float((area*converged).sum()/max(total_area,1e-30)),
        unsupported_land_share=float((area*supported).sum()/max(total_area,1e-30)),
        mean_foraging_hours_day=mean('foraging_hours_day',density*area),
        mean_scarcity_days_year=mean('scarcity_days_year',density*area),
        mean_meat_fraction=mean('meat_fraction',density*area),
        mean_fish_share=mean('fish_share',density*area) if 'fish_share' in fields else None,
        aggregation='Scenario people are density times coastal land area. Effort, scarcity and diet means are weighted by scenario people; convergence shares are weighted by land area.')
    provinces=[]
    for name,fraction in zip(province_names,province_fraction):
        own=fraction*cell_area_km2;land=float(own.sum())
        if land<=0:continue
        people=float((own*density).sum())
        provinces.append(dict(province=name,area_km2=land,scenario_people=people,
            converged_scenario_people=float((own*density*converged).sum()),
            mean_density_people_km2=people/land,
            converged_land_share=float((own*converged).sum()/land)))
    np.testing.assert_allclose(sum(p['area_km2'] for p in provinces),total_area,rtol=2e-13,atol=1e-7)
    np.testing.assert_allclose(sum(p['scenario_people'] for p in provinces),population,rtol=2e-13,atol=1e-7)
    return summary,provinces


def map_aquatic_inputs(atlas, meta, native_shape, shape, aquatic):
    """The aquatic addendum's inputs on the map: coast weight, sea surface and freshwater index per analysis cell."""
    from scipy import ndimage as ndi
    from rotclimate.config import Params
    from rotclimate.ebm import ZonalClimate
    from rotclimate.geography import source_layers
    from scripts.vector_rivers import river_classes
    layers = source_layers(); land = layers['land']; H, W = land.shape
    km_px = meta['mi_per_px']*1.609344*meta['width']/W
    water = ~land                                         # sea and lakes, as WorldClim leaves both empty
    coast = np.exp(-ndi.distance_transform_edt(~water)*km_px/aquatic['coast_scale_km'])
    radius = aquatic['radius_km']/km_px
    r = int(np.ceil(radius)); yy, xx = np.mgrid[-r:r+1, -r:r+1]; disc = (np.hypot(yy, xx) <= radius).astype(float)
    original = np.asarray(Image.open(ROOT/'data/source/original/rivers.png'))[..., 3]/255.
    streams, navigable = river_classes(original)
    lines = streams | navigable
    sampling = meta['mi_per_px']*1.609344*meta['width']/original.shape[1]
    ys, xs = np.nonzero(lines)
    river_km = np.zeros((H, W))
    np.add.at(river_km, (np.minimum((ys+.5)*H/original.shape[0], H-1).astype(int),
                         np.minimum((xs+.5)*W/original.shape[1], W-1).astype(int)), 1.12*sampling*aquatic['map_river_scale'])
    from scipy.signal import fftconvolve
    disc_km2 = disc.sum()*km_px**2
    rivers = np.maximum(fftconvolve(river_km, disc, mode='same'), 0)*100./disc_km2
    lakes = np.clip(fftconvolve(layers['lake'].astype(float), disc, mode='same')/disc.sum(), 0, 1)
    fresh = rivers + aquatic['lake_weight']*lakes
    fine_fraction = land.astype(float)
    def to_analysis(value):
        return land_average(value, fine_fraction, shape)
    p = Params.from_json(atlas/'params.json'); zonal = ZonalClimate(p)
    h, w = shape
    py, px = np.mgrid[:h, :w]
    px = (px+.5)*meta['width']/w; py = (py+.5)*meta['height']/h
    bearing = np.radians(meta.get('north_bearing', 0))
    latitude = (meta['lat_center']+((px-meta['width']/2)*np.sin(bearing)+(meta['height']/2-py)*np.cos(bearing))
                *meta['mi_per_px']*1.609344/meta['km_per_deg'])
    days = (np.arange(36)+.5)*p.year_days/36
    sst = np.mean([zonal.ocean(latitude, d) for d in days], axis=0)+p.sst_offset
    return dict(coast_weight=to_analysis(coast), sst_c=sst, w_fresh=to_analysis(fresh),
                river_index=to_analysis(rivers), lake_share=to_analysis(lakes))


LIFEWAY_COLORS = {'hunting': (0.66, 0.42, 0.22), 'gathering': (0.45, 0.60, 0.25), 'fishing': (0.20, 0.47, 0.66)}
LIFEWAY_LABELS = {'hunting': 'Hunters', 'gathering': 'Gatherers', 'fishing': 'Fishers'}


def lifeway_fields(fields):
    """F14: class probabilities from the frozen lifeway model (data/forager_lifeways.json) and expected residential moves."""
    path = ROOT/'data/forager_lifeways.json'
    if not path.exists():
        return None
    model = json.loads(path.read_text())
    fish = np.asarray(fields['mean_fish_share'], float); meat = np.asarray(fields['mean_meat_fraction'], float)
    density = np.asarray(fields['density_people_km2'], float)
    X = np.stack([np.log10(np.maximum(density, 1e-4)), (1-fish)*meat, (1-fish)*(1-meat), fish,
                  np.asarray(fields['mean_scarcity_days_year'], float)/365.0,
                  np.log10(np.maximum(np.asarray(fields['annual_npp_gdm_m2'], float), 1.0))], -1)
    z = (X-np.array(model['mean']))/np.array(model['std'])
    logits = z @ np.array(model['coef']).T + np.array(model['intercept'])
    logits -= logits.max(-1, keepdims=True)
    prob = np.exp(logits); prob /= prob.sum(-1, keepdims=True)
    moves = 10**(model['moves']['a']+model['moves']['b']*np.log10(np.maximum(density, 1e-4)))
    return dict(classes=model['classes'], prob=prob, moves=moves, source=model['source'])


def lifeway_layers(data, fields, land, elevation, meta, coast):
    lw = lifeway_fields(fields)
    if lw is None:
        return []
    k = lw['prob'].argmax(-1); conf = lw['prob'].max(-1)
    rgb = np.ones(land.shape+(3,))*np.array([0.93, 0.93, 0.90])
    for i, name in enumerate(lw['classes']):
        m = land & (k == i)
        # paler where the classes are close (confidence 1/3 to 1)
        w = np.clip((conf-1/3)/(2/3), 0.25, 1.0)[m][:, None]
        rgb[m] = w*np.array(LIFEWAY_COLORS[name])+(1-w)*np.array([0.93, 0.93, 0.90])
    rgb[~land] = [0.84, 0.89, 0.94]
    image = Image.fromarray((np.clip(rgb, 0, 1)*255).astype('uint8')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
    pixels = np.asarray(image).copy()
    if coast.shape == pixels.shape[:2]: pixels[~coast] = [214, 227, 240]
    Image.fromarray(pixels).save(data/'forage_lifeway.webp', 'WEBP', quality=88, method=4)
    shares = {name: float(((k == i) & land).sum()/max(land.sum(), 1)) for i, name in enumerate(lw['classes'])}
    note = ('Which food a forager band would live on mostly, from the FORGE scenario: a map from its density, food shares, '
            'shortfall and plant productivity to Binford\'s dominant food, fitted on 280 recorded hunter-gatherer groups and '
            'tested on each culture area held out (65 % right, kappa 0.48). Paler where the classes are close.')
    layers = [dict(id='forage_lifeway', file='forage_lifeway.webp', label='Forager lifeways', kind='categories', group='Foraging',
                   items=[dict(color='#%02x%02x%02x' % tuple(int(255*c) for c in LIFEWAY_COLORS[n]),
                               label=f"{LIFEWAY_LABELS[n]} · {100*shares[n]:.0f}%") for n in lw['classes']],
                   note=note, controls=[])]
    palette = ['#f3eedc', '#d8c48f', '#c08a52', '#9a5a3a', '#5e3430']; lo, hi = 0.5, 30.0
    tier = tiers(palette, lo, hi, True)
    for suffix, use in [('', None), ('_tiers', tier)]:
        rgb = color_image(np.asarray(lw['moves'], np.float32), land, elevation, palette, lo, hi, True, tiered=use)
        image = Image.fromarray((np.clip(rgb, 0, 1)*255).astype('uint8')).resize((meta['width'], meta['height']), Image.Resampling.NEAREST)
        pixels = np.asarray(image).copy()
        if coast.shape == pixels.shape[:2]: pixels[~coast] = [214, 227, 240]
        Image.fromarray(pixels).save(data/('forage_moves'+suffix+'.webp'), 'WEBP', quality=88, method=4)
    tier['file'] = 'forage_moves_tiers.webp'
    layers.append(dict(id='forage_moves', file='forage_moves.webp', label='Camp moves', kind='ramp', group='Foraging',
                       unit='expected residential moves per year (from the scenario density, as among Binford\'s groups)',
                       vmin=lo, vmax=hi, stops=palette, log=True, tiers=tier, controls=[],
                       note='Sparser foragers move camp more often (Spearman -0.45 among 211 recorded groups); a guide, not a prediction for any one band.'))
    return layers


def images_and_layers(data, fields, land, elevation, meta):
    layers=[]
    from rotclimate.geography import source_layers
    coast=source_layers()['land']
    for key,id,label,unit,lo,hi,log in MODES:
        palette=PALETTES[key];tier=tiers(palette,lo,hi,log)
        for suffix,use_tiers in [('',None),('_tiers',tier)]:
            rgb=color_image(fields[key],land,elevation,palette,lo,hi,log,tiered=use_tiers)
            image=Image.fromarray((np.clip(rgb,0,1)*255).astype('uint8')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST)
            pixels=np.asarray(image).copy()
            if coast.shape==pixels.shape[:2]:pixels[~coast]=[214,227,240]
            Image.fromarray(pixels).save(data/(id+suffix+'.webp'),'WEBP',quality=88,method=4)
        tier['file']=id+'_tiers.webp'
        layers.append(dict(id=id,file=id+'.webp',label=label,kind='ramp',group='Foraging',
            unit=unit,vmin=lo,vmax=hi,stops=palette,log=log,tiers=tier,controls=[],
            note='Adapted FORGE human model with Miami productivity and explicit vegetation/prey proxies. Finite-horizon scenario; check local convergence. It is separate from c.200 AD farming and census allocation.'))
    layers+=lifeway_layers(data,fields,land,elevation,meta,coast)
    return layers


def export(atlas, *, coarsen=4, chunk_cells=512, years=None, force=False):
    """Build a reproducible resource scenario, preserving all existing climate data."""
    from .models import ForagingParams, simulate_foraging
    atlas=Path(atlas);data=atlas/'data';meta=json.loads((data/'atlas.json').read_text());spec=specification()
    if not isinstance(coarsen,int) or coarsen<1 or not isinstance(chunk_cells,int) or chunk_cells<1:
        raise ValueError('Need positive integer analysis coarsening and chunk size')
    run=dict(spec['run']);run['years']=int(years if years is not None else run['years'])
    if run['years']<1:raise ValueError('Need a positive simulation horizon')
    native=climate_arrays(data,meta);native_shape=native['elev'].shape
    shape=(math.ceil(native_shape[0]/coarsen),math.ceil(native_shape[1]/coarsen))
    sources=[*sorted((ROOT/'foraging').glob('*.py')),ROOT/'data/foraging_model.json',
             ROOT/'harvest/export.py',ROOT/'rotclimate/geography.py',ROOT/'scripts/land_people.py',
             ROOT/'scripts/vector_rivers.py',ROOT/'data/source/elevation.png',ROOT/'data/source/rivers.png',
             ROOT/'data/source/original/rivers.png']
    if (ROOT/'data/forager_lifeways.json').exists():
        sources.append(ROOT/'data/forager_lifeways.json')
    aquatic=spec.get('aquatic')
    if aquatic:
        sources+=[ROOT/'rotclimate/ebm.py',ROOT/'rotclimate/config.py']
    inputs=dict(climate_sha256=sha(data/'atlas.bin'),physical_metadata=physical_metadata(meta),
        world_params_sha256=sha(atlas/'params.json') if aquatic else None,
        province_metadata_sha256=sha(data/'harvest.json'),province_binary_sha256=sha(data/'harvest.bin'),
        native_shape=list(native_shape),analysis_shape=list(shape),run=run,
        sources={str(p.relative_to(ROOT)):sha(p) for p in sources})
    fingerprint=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    target=data/'foraging.json'
    if target.exists() and not force:
        previous=json.loads(target.read_text())
        if (previous.get('fingerprint')==fingerprint and meta.get('foraging',{}).get('fingerprint')==fingerprint
                and all((data/(id+s+'.webp')).exists() for _,id,*_ in MODES for s in ['', '_tiers'])
                and (not (ROOT/'data/forager_lifeways.json').exists() or (data/'forage_lifeway.webp').exists())
                and (data/'foraging.bin').exists() and sha(data/'foraging.bin')==previous.get('binary_sha256')):
            print('Foraging scenario already matches '+str(atlas),flush=True);return previous
    print('Building adapted foraging scenario on '+str(shape)+' grid: '+str(atlas),flush=True)
    geo,geo_inputs=geometry(meta,native_shape);fine_fraction=geo['land_fraction'].astype(float)
    t,p,_,_=surface_months(meta,native);fine_npp=miami_npp(t,p)
    land_fraction=area_average(fine_fraction,shape);land=land_fraction>0
    temperature=land_average(t,fine_fraction,shape);precipitation=land_average(p,fine_fraction,shape)
    npp=land_average(fine_npp,fine_fraction,shape);elev=land_average(native['elev'],fine_fraction,shape)
    width_km=meta['width']*meta['mi_per_px']*1.609344;height_km=meta['height']*meta['mi_per_px']*1.609344
    cell_area=width_km*height_km/(shape[0]*shape[1])
    np.testing.assert_allclose((npp*land_fraction).sum()*cell_area,
        (fine_npp*fine_fraction).sum()*width_km*height_km/np.prod(native_shape),rtol=3e-13)
    adapter=dict(spec['adapter'])
    aq=map_aquatic_inputs(atlas,meta,native_shape,shape,aquatic) if aquatic else None
    if aq is not None:
        aq['annual_aquatic_kgdm_km2']=aquatic_annual(aq['coast_weight'],aq['sst_c'],aq['w_fresh'],aquatic)
    kernel_keys={f.name for f in dataclass_fields(ForagingParams)}
    kernel=spec['kernel_parameters']
    if set(kernel)-kernel_keys:raise ValueError('Unknown kernel parameter names: '+str(set(kernel)-kernel_keys))
    params=ForagingParams(**kernel)
    index=np.flatnonzero(land);results={};diagnostics=[];started=time.monotonic()
    for start in range(0,len(index),chunk_cells):
        selected=index[start:start+chunk_cells]
        forcing=daily_resources(temperature.reshape(12,-1)[:,selected],precipitation.reshape(12,-1)[:,selected],npp.ravel()[selected],adapter)
        plant,meat,fish=forcing['plant_supply'],forcing['meat_supply'],None
        if aq is not None:
            plant=plant*aquatic['terrestrial_scale'];meat=meat*aquatic['terrestrial_scale']
            fish=np.broadcast_to(aq['annual_aquatic_kgdm_km2'].ravel()[selected]/plant.shape[0],plant.shape).copy()
        output=simulate_foraging(plant,meat,params=params,aquatic_supply=fish,**run)
        output['fish_share']=output['mean_fish_share']
        for key,value in output.items():
            array=np.asarray(value)
            if array.shape!=(len(selected),):continue
            if not (np.issubdtype(array.dtype,np.number) or np.issubdtype(array.dtype,np.bool_)):continue
            if key not in results:results[key]=np.zeros(land.size)
            results[key][selected]=array
        for key in ['annual_plant_kgdm_km2','annual_meat_kgdm_km2','phenology_uniform_fallback']:
            if key not in results:results[key]=np.zeros(land.size)
            results[key][selected]=forcing[key]
        diagnostic={k:float(v) for k,v in output.items() if np.asarray(v).ndim==0 and np.issubdtype(np.asarray(v).dtype,np.number)}
        diagnostics.append(dict(first_cell=int(start),cells=int(len(selected)),**diagnostic))
        if start==0 or start+chunk_cells>=len(index) or start//chunk_cells%10==0:
            print(f'  {min(start+chunk_cells,len(index))}/{len(index)} land cells; {time.monotonic()-started:.1f}s',flush=True)
    fields={key:value.reshape(shape) for key,value in results.items()}
    for key,*_ in MODES:
        if key not in fields:raise ValueError('Kernel did not produce required mode: '+key)
    for key in ['converged','floor_limited','unsupported']:
        if key not in fields:raise ValueError('Kernel did not produce required status: '+key)
    fields.update(land_fraction=land_fraction,annual_npp_gdm_m2=npp,cell_area_km2=land_fraction*cell_area)
    if aq is not None:
        fields.update({'aquatic_'+k:np.where(land,v,0.) for k,v in aq.items()})
    # Match stored precision before computing every published total or map.
    fields={k:np.asarray(v,dtype=np.uint8 if k in ['converged','floor_limited','unsupported'] else np.float32) for k,v in fields.items()}
    names,province_fraction=province_fractions(data,fine_fraction,shape)
    summary,provinces=aggregates(fields,land_fraction,cell_area,names,province_fraction)
    arrays=pack_fields(fields,land,data/'foraging.bin');layers=images_and_layers(data,fields,land,elev,meta)
    info=dict(version=1,fingerprint=fingerprint,inputs=inputs,binary_sha256=sha(data/'foraging.bin'),
        shape=list(shape),width=meta['width'],height=meta['height'],
        cell_width_px=meta['width']/shape[1],cell_height_px=meta['height']/shape[0],
        analysis_resolution_note='Independent area-averaged foraging grid; climate resolution and accuracy are unchanged.',
        model_note=spec['model_note'],sources=spec['sources'],report_url='../../reports/FORAGING_20261027.md',
        summary=summary,provinces=provinces,arrays=arrays,parameters=spec,
        run=run,chunk_cells=chunk_cells,diagnostics=diagnostics,seconds=time.monotonic()-started,
        original_climate_sha256=inputs['climate_sha256'],geography_inputs=geo_inputs)
    target.write_text(json.dumps(info,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
    (data/'foraging_model.json').write_bytes((ROOT/'data/foraging_model.json').read_bytes())
    with (data/'foraging_provinces.csv').open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['province','area_km2','scenario_people','converged_scenario_people','mean_density_people_km2','converged_land_share'])
        writer.writeheader();writer.writerows(provinces)
    meta['layers']=[l for l in meta['layers'] if not l['id'].startswith('forage_')]+layers
    meta['foraging']=dict(metadata='foraging.json',binary='foraging.bin',fingerprint=fingerprint)
    (data/'atlas.json').write_text(json.dumps(meta,ensure_ascii=False))
    assert sha(data/'atlas.bin')==inputs['climate_sha256'],'Climate binary changed during foraging export'
    if (ROOT/'atlas/foraging.js').exists():shutil.copyfile(ROOT/'atlas/foraging.js',atlas/'foraging.js')
    print(json.dumps(summary,indent=2),flush=True)
    return info


def attach(staging, atlas):
    """Publish only foraging assets after checking the live input packets."""
    staging,atlas=Path(staging),Path(atlas)
    source=staging/'data';target=atlas/'data'
    sm=json.loads((source/'atlas.json').read_text());live=json.loads((target/'atlas.json').read_text())
    info=json.loads((source/'foraging.json').read_text())
    if (sha(target/'atlas.bin')!=info['inputs']['climate_sha256']
            or sha(target/'harvest.bin')!=info['inputs']['province_binary_sha256']
            or sha(target/'harvest.json')!=info['inputs']['province_metadata_sha256']
            or physical_metadata(live)!=info['inputs']['physical_metadata']):
        raise ValueError('Live climate/agricultural inputs changed since foraging staging')
    from .validation import verify
    verify(source,sm)
    assets=[p for p in source.iterdir() if p.name.startswith(('foraging','forage_')) and p.is_file()]
    for file in assets:
        temporary=target/(file.name+'.tmp');shutil.copyfile(file,temporary);temporary.replace(target/file.name)
    live['layers']=[l for l in live['layers'] if not l['id'].startswith('forage_')]+[l for l in sm['layers'] if l['id'].startswith('forage_')]
    live['foraging']=sm['foraging']
    temporary=target/'atlas.json.tmp';temporary.write_text(json.dumps(live,ensure_ascii=False));temporary.replace(target/'atlas.json')
    if (ROOT/'atlas/foraging.js').exists():shutil.copyfile(ROOT/'atlas/foraging.js',atlas/'foraging.js')
    return verify(target,live)
