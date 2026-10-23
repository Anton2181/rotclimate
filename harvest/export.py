"""Derive farming and settlement assets from one atlas's own climate packet.

No climate simulation is run. Inputs are the same solstice-aligned T12, P12,
D12 and seasonal lapse rates used by station cards. Analysis uses the atlas's
half-source-resolution terrain grid; area totals retain coastal land fractions.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .models import (ROOT, core_term, lore_cores, malaria_fields, occupation_reference, settlement_fields,
                     specification, thermal_reference)

CROP_LABELS = ['Wheat / barley', 'Foxtail millet', 'Paddy rice', 'Date palm', 'No viable staple']
CROP_COLORS = ['#d5b548', '#97a94d', '#419d82', '#b17842', '#b5b1a7']
RAMPS = {
    'people':['#f4ecc4','#e8c46a','#d38a3a','#ad4a2f','#6e2238','#2f1638'],
    'green':['#eee7c8','#c3d188','#78b365','#348a64','#155b51'],
    'water':['#e9dcc0','#c5d4c2','#7ebbb7','#328baf','#165c8f'],
    'disease':['#f2efe3','#f2d79c','#eba05f','#d4583a','#a2283a','#5f1430'],
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def climate_arrays(data, meta):
    blob = (data/'atlas.bin').read_bytes()
    return {key:np.frombuffer(blob, dtype=np.dtype(spec['dtype']),
                             count=int(np.prod(spec['shape'])), offset=spec['offset']).reshape(spec['shape'])
            for key,spec in meta['arrays'].items()}


def physical_metadata(meta):
    return {key:meta[key] for key in ['width','height','mi_per_px','km_per_deg','cell_px','lapse','lapse12',
                                     'lat_center','north_bearing','world','arrays']}


def geometry(meta, shape):
    """Static coast, arable land and river access, shared by all three fits."""
    from rotclimate.geography import source_layers
    from scripts.land_people import ARABLE_BY_TIER
    from scripts.vector_rivers import river_classes
    sources = [ROOT/'data/source'/name for name in ['elevation.png','rivers.png','original/rivers.png']]
    key = dict(shape=list(shape), width_km=meta['width']*meta['mi_per_px']*1.609344,
               arable=ARABLE_BY_TIER, sources={str(p.relative_to(ROOT)):digest(p) for p in sources})
    stamp = hashlib.sha256(json.dumps(key,sort_keys=True).encode()).hexdigest()
    cache = ROOT/'data/cache'/('harvest_geography_'+stamp[:20]+'.npz')
    if cache.exists():
        with np.load(cache) as saved:
            return {k:saved[k] for k in saved.files}, key
    layers = source_layers(); land = layers['land']; h,w = shape
    H,W = land.shape
    if H%h or W%w:
        raise ValueError('Analysis grid must divide the source map exactly')
    sy,sx = H//h,W//w
    block = lambda a: np.asarray(a).reshape(h,sy,w,sx).mean((1,3))
    fraction = block(land.astype(float))
    arable = np.zeros(land.shape, dtype=np.float32)
    for tier,share in ARABLE_BY_TIER.items():
        arable[layers['tier']==tier] = share
    arable = block(arable)/np.maximum(fraction,1e-12)
    km_px = meta['mi_per_px']*1.609344
    water = layers['rivers'] | layers['lake']
    distance = (ndi.distance_transform_edt(~water)*km_px if water.any()
                else np.full(land.shape,np.inf))
    water_distance = block(np.where(land,distance,0))/np.maximum(fraction,1e-12)
    original = np.asarray(Image.open(ROOT/'data/source/original/rivers.png'))[...,3]/255.
    streams,navigable = river_classes(original)
    sampling = km_px*W/original.shape[1]
    dn = ndi.distance_transform_edt(~navigable)*sampling if navigable.any() else np.full(original.shape,np.inf)
    ds = ndi.distance_transform_edt(~streams)*sampling if streams.any() else np.full(original.shape,np.inf)
    irrigated = np.maximum(np.exp(-dn/6), .6*np.exp(-ds/2.5))
    yy,xx = np.mgrid[:h,:w]
    coordinates = [(yy+.5)*original.shape[0]/h-.5,(xx+.5)*original.shape[1]/w-.5]
    irrigation = ndi.map_coordinates(irrigated,coordinates,order=1,mode='nearest')
    result = dict(land_fraction=fraction.astype(np.float32), arable=arable.astype(np.float32),
                  water_distance=water_distance.astype(np.float32), irr=irrigation.astype(np.float32))
    cache.parent.mkdir(parents=True,exist_ok=True)
    np.savez_compressed(cache,**result)
    return result,key


def surface_months(meta, arrays):
    """Interpolate the viewer's sea-level climate, then apply its seasonal lapse."""
    h,w = arrays['elev'].shape
    yy,xx = np.mgrid[:h,:w]
    px,py = (xx+.5)*meta['width']/w,(yy+.5)*meta['height']/h
    coordinates = [py/meta['cell_px']-.5,px/meta['cell_px']-.5]
    sample = lambda key,scale:np.stack([
        ndi.map_coordinates(np.asarray(a,float)*scale,coordinates,order=1,mode='nearest') for a in arrays[key]])
    t = sample('T12',.1)-np.asarray(meta['lapse12'])[:,None,None]*arrays['elev'][None]/1000
    p = np.maximum(sample('P12',1),0)
    d = np.maximum(sample('D12',.1),0)
    bearing = np.radians(meta.get('north_bearing',0))
    latitude = (meta['lat_center']+((px-meta['width']/2)*np.sin(bearing)
                +(meta['height']/2-py)*np.cos(bearing))*meta['mi_per_px']*1.609344/meta['km_per_deg'])
    return t,p,d,latitude


def derive(meta, arrays):
    from scripts.land_people import analyse
    geo,geo_inputs = geometry(meta,arrays['elev'].shape)
    land = geo['land_fraction']>0
    t,p,d,latitude = surface_months(meta,arrays)
    if not all(np.isfinite(a[:,land]).all() for a in [t,p,d]):
        raise ValueError('Nonfinite climate on analysis land')
    # T12/P12 start at the winter solstice, so radiation uses solstice day 0.
    margin = specification().get('margin_reliability')
    margins = (tuple(margin['cold_mean_temperature_c']),tuple(margin['dry_rain_over_evaporation'])) if margin else None
    result,names = analyse(t[:,land],p[:,land],latitude[land],meta['world']['tilt'],0,
                           geo['irr'][land],geo['arable'][land],d[:,land],margins=margins)
    result.update(malaria_fields(t[:,land],p[:,land],geo['irr'][land]))
    result.update(settlement_fields(result.pop('capacity'),result['npp'],arrays['biome'][land],
                                    geo['arable'][land],geo['water_distance'][land],result['malaria']))
    fields = {}
    for key,value in result.items():
        full = np.full(land.shape,np.nan,dtype=np.float32);full[land]=value
        fields[key]=full
    fields['irr']=np.where(land,geo['irr'],np.nan)
    fields['arable']=np.where(land,geo['arable'],np.nan)
    raw = np.nan_to_num(fields['main_crop'],nan=-1).astype(int)
    crop = np.full(land.shape,5,dtype=np.uint8)
    for i,name in enumerate(names):
        crop[raw==i]={'wheat':1,'barley':1,'millet':2,'rice':3,'dates':4}[name]
    crop[~land]=0;fields['crop']=crop
    # the same people drawn toward the campaign's old heartlands (exp(-D / 800 km), as
    # tested on Earth with the historical cores), keeping each scenario's total
    shape=land.shape;cell_km=meta['width']*meta['mi_per_px']*1.609344/shape[1]
    biome=np.asarray(arrays['biome']);elev=np.asarray(arrays['elev'],float)
    term=core_term(land,biome,elev,cell_km,lore_cores(meta['width'],meta['height'],shape))
    weight=geo['land_fraction'].astype(float)
    for base,cored in [('settlement_base','settlement_cored'),('settlement_no_malaria','settlement_cored_no_malaria')]:
        b=np.nan_to_num(fields[base]);t=b*term
        fields[cored]=np.where(land,t*np.sum(b*weight)/max(np.sum(t*weight),1e-9),np.nan).astype(np.float32)
    return fields,geo,names,geo_inputs


def pack_fields(fields,land,hexes,path):
    keys = ['crop_capacity','pastoral_capacity','food_capacity','kcal_ha','lgp_days','npp','irr',
            'aridity','malaria','malaria_months','clearance','access','health','settlement_base',
            'settlement_no_malaria','settlement_cored','livability','livability_no_malaria','arable',
            'kcal_wheat','kcal_barley','kcal_millet','kcal_rice','kcal_dates']
    blob = bytearray(); descriptors = {}
    for key in keys+['crop','double_crop','hex_id']:
        value = hexes if key=='hex_id' else fields[key]
        if key in ['crop','hex_id']:
            arr = np.where(land,value,0).astype('<u2' if key=='hex_id' else 'u1')
            dtype = 'uint16' if key=='hex_id' else 'uint8'; scale=1.;offset=0.;nodata=0
        elif key=='double_crop':
            arr=np.where(land,value,255).astype('u1');dtype='uint8';scale=1.;offset=0.;nodata=255
        elif key=='aridity':
            arr=np.where(land,value,np.nan).astype('<f4');dtype='float32';scale=1.;offset=0.;nodata=None
        else:
            maximum=max(float(np.nanmax(value[land])),1.)
            scale=maximum/65534;offset=-scale;nodata=0;dtype='uint16'
            arr=np.where(land,np.round(np.nan_to_num(value)/scale)+1,0).astype('<u2')
        while len(blob)%4:blob.append(0)
        descriptors[key]=dict(dtype=dtype,offset_bytes=len(blob),shape=list(arr.shape),
                              scale=scale,offset=offset,nodata=nodata)
        blob.extend(arr.tobytes())
    path.write_bytes(blob)
    return descriptors


def aggregates(fields,geo,meta):
    from scripts.land_people_hexes import hex_index
    grid=json.loads((ROOT/'data/hexgrid.json').read_text())
    shape=fields['crop'].shape
    index=hex_index(shape,4401/shape[1],grid)
    area=geo['land_fraction'].astype(float)*(meta['width']/shape[1]*meta['mi_per_px']*1.609344)**2
    land=area>0
    political=json.loads((ROOT/'ravages/data.json').read_text())
    occupation=occupation_reference()
    fractions=occupation['scenarios']
    total=lambda value:float(np.sum(np.nan_to_num(value)*area))
    totals={k:total(fields[k]) for k in ['crop_capacity','pastoral_capacity','food_capacity',
                                       'settlement_base','settlement_no_malaria']}
    totals['land_km2']=float(area.sum())
    totals['population']={disease:{name:totals[base]*fraction for name,fraction in fractions.items()}
                          for disease,base in [('endemic','settlement_base'),('absent','settlement_no_malaria')]}
    totals['crops']=[float(area[(fields['crop']==i)].sum()/area.sum()) for i in range(1,6)]
    totals['double_crop_share']=float(np.sum(np.nan_to_num(fields['double_crop'])*area)/area.sum())
    totals['mean_malaria']=float(total(fields['malaria'])/float(area.sum()))
    counts=np.bincount(index[land],weights=area[land])
    keys=['crop_capacity','food_capacity','pastoral_capacity','settlement_base','settlement_no_malaria',
          'malaria','lgp_days','irr','aridity']
    sums={k:np.bincount(index[land],weights=np.nan_to_num(fields[k][land])*area[land],minlength=len(counts))
          for k in keys}
    hexes={};provinces={}
    for hid in np.flatnonzero(counts):
        if not hid:continue
        rec=political['hexes'].get(str(hid),['','','',''])
        level,wealth=political['economy']['max'].get(str(hid),[None,None])
        row=dict(area_km2=float(counts[hid]),province=rec[1] or 'Unassigned',commandery=rec[0],
                 region=rec[2],terrain=rec[3],sheet_settlement=level,sheet_wealth=wealth,
                 **{k:float(sums[k][hid]/counts[hid]) for k in keys})
        hexes[str(hid)]=row
        name=row['province'];prov=provinces.setdefault(name,dict(name=name,hexes=[],area_km2=0.,
                  crop_capacity_people=0.,food_capacity_people=0.,settlement_base=0.,settlement_no_malaria=0.,
                  sheet_area=0.,sheet_settlement=0.,sheet_wealth=0.))
        prov['hexes'].append(int(hid));prov['area_km2']+=float(counts[hid])
        prov['crop_capacity_people']+=float(sums['crop_capacity'][hid])
        prov['food_capacity_people']+=float(sums['food_capacity'][hid])
        for key in ['settlement_base','settlement_no_malaria']:prov[key]+=float(sums[key][hid])
        if level is not None and wealth is not None:
            prov['sheet_area']+=float(counts[hid])
            prov['sheet_settlement']+=float(level*counts[hid])
            prov['sheet_wealth']+=float(wealth*counts[hid])
    for p in provinces.values():
        for key in ['sheet_settlement','sheet_wealth']:
            p[key]=p[key]/p['sheet_area'] if p['sheet_area'] else None
        mask=np.isin(index,p['hexes']) & land
        p['crops']=[float(area[mask & (fields['crop']==i)].sum()/p['area_km2']) for i in range(1,6)]
    from scipy.stats import spearmanr
    sheet=[h for h in hexes.values() if h['sheet_settlement'] is not None and h['sheet_wealth'] is not None]
    def rank_correlation(key,other):
        x=[h[key] for h in sheet];y=[h['sheet_'+other] for h in sheet]
        return float(spearmanr(x,y).statistic) if len(set(x))>1 and len(set(y))>1 else None
    correlations={key:{other:rank_correlation(key,other)
                       for other in ['settlement','wealth']}
                  for key in ['crop_capacity','food_capacity','settlement_base']}
    return (dict(summary=totals,occupation=occupation,hexes=hexes,
                provinces=sorted(provinces.values(),key=lambda p:-p['settlement_base']),
                hexgrid=grid,sheet_check=dict(hexes=len(sheet),correlations=correlations,
                note='Unweighted ranks of land-area means per sheet hex. Sheet values are not inputs to the climate or settlement model.')),
                index,area)


def color_image(value,land,elevation,stops,lo,hi,log=False):
    from matplotlib.colors import to_rgb
    colors=np.asarray([to_rgb(c) for c in stops])
    v=np.nan_to_num(value,nan=lo)
    x=(np.log(np.maximum(v,lo))-np.log(lo))/(np.log(hi)-np.log(lo)) if log else (v-lo)/(hi-lo)
    x=np.clip(x,0,1)*(len(colors)-1);i=np.minimum(x.astype(int),len(colors)-2)
    rgb=colors[i]+(colors[i+1]-colors[i])*(x-i)[...,None]
    gy,gx=np.gradient(elevation.astype(float))
    shade=np.clip(.96-.00018*gx+.00022*gy,.78,1.08)
    rgb=np.clip(rgb*shade[...,None],0,1)
    rgb[~land]=[.84,.89,.94]
    return rgb


def images_and_layers(fields,geo,meta,arrays,data):
    land=geo['land_fraction']>0;elevation=arrays['elev'];layers=[]
    def save(rgb,filename):
        image=Image.fromarray((np.clip(rgb,0,1)*255).astype(np.uint8))
        image=image.resize((meta['width'],meta['height']),Image.Resampling.NEAREST)
        # Source coast remains sharp, even though analysis uses coastal fractions.
        from rotclimate.geography import source_layers
        pixels=np.array(image);pixels[~source_layers()['land']]=[214,227,240]
        Image.fromarray(pixels).save(data/filename,'WEBP',quality=88,method=4)
    def ramp(key,label,unit,lo,hi,palette,log=False,note=''):
        filename='land_'+key+'.webp'
        save(color_image(fields[key],land,elevation,RAMPS[palette],lo,hi,log),filename)
        item=dict(id='land_'+key,file=filename,label=label,kind='ramp',group='Harvest',
                  unit=unit,vmin=lo,vmax=hi,stops=RAMPS[palette],note=note,log=log)
        layers.append(item);return item
    ramp('crop_capacity','Crop food capacity','people/km² · fully developed low-input crop farming',.1,1000,'people',True,
         'A food-production ceiling with period yields, seed, fallow and draft/storage costs; not a census.')
    ramp('food_capacity','Mixed food capacity','people/km² · crop capacity plus a grazing allowance',.1,1000,'people',True)
    ramp('pastoral_capacity','Grazing allowance','people/km² · uncertain forage-energy allowance',.01,30,'green',True)
    kcal=dict(fields);kcal['kcal_ha']=fields['kcal_ha']/1e6
    original=fields['kcal_ha'];fields['kcal_ha']=kcal['kcal_ha']
    ramp('kcal_ha','Food per hectare','million edible kcal/ha/year, after seed',0,8,'green')
    fields['kcal_ha']=original
    ramp('lgp_days','Growing season','days/year warm and wet enough by the FAO growing-period rule',0,365,'green')
    ramp('irr','Irrigation reach','fraction potentially irrigable near the drawn rivers',0,1,'water')
    ramp('npp','Wild productivity','g dry matter/m²/year · Miami productivity model',0,3000,'green')
    ramp('aridity','Rain / evaporation','annual precipitation / Hargreaves evaporation demand',0,3,'water')
    ramp('malaria','Malaria potential','relative warm/wet physiological potential, 0–1; not infection prevalence',0,1,'disease',
         note='Mordecai 2013 thermal traits with an explicit rainfall/irrigation moisture gate.')
    ramp('malaria_months','Malaria season','months/year at least 25% of the warm/wet physiological optimum',0,12,'disease')
    from matplotlib.colors import to_rgb
    crop=np.zeros((*land.shape,3));crop[:]=[.84,.89,.94]
    for i,color in enumerate(CROP_COLORS,1):crop[fields['crop']==i]=to_rgb(color)
    yy,xx=np.mgrid[:land.shape[0],:land.shape[1]]
    hatch=land & (np.nan_to_num(fields['double_crop'])>0) & ((xx+yy)%7==0)
    crop[hatch]=crop[hatch]*.65
    save(crop,'land_crop.webp')
    layers.append(dict(id='land_crop',file='land_crop.webp',label='Staple crops',kind='categories',group='Harvest',
                       items=[dict(color=c,label=l) for c,l in zip(CROP_COLORS,CROP_LABELS)],
                       note='Diagonal hatching marks a compatible second crop. Crop labels follow the winning crop pair.'))
    occupation=occupation_reference()['scenarios']
    density=ramp('settlement_base','Expected density','people/km² · c.200 AD settlement scenario',.1,300,'people',True)
    density['id']='land_density';density['scenario_files']={}
    livability=ramp('livability','Settlement potential','environmental settlement potential, 0–100; not living standards',0,100,'green')
    livability['scenario_files']={}
    for disease,base,index in [('endemic','settlement_base','livability'),('absent','settlement_no_malaria','livability_no_malaria')]:
        for scenario,fraction in occupation.items():
            file=f'land_density_{scenario}_{disease}.webp'
            save(color_image(fields[base]*fraction,land,elevation,RAMPS['people'],.1,300,True),file)
            density['scenario_files'][scenario+'_'+disease]=file
        file='land_livability_'+disease+'.webp'
        save(color_image(fields[index],land,elevation,RAMPS['green'],0,100),file)
        for scenario in occupation:livability['scenario_files'][scenario+'_'+disease]=file
    density['file']=density['scenario_files']['central_endemic']
    livability['file']=livability['scenario_files']['central_endemic']
    cored=ramp('settlement_cored','Density around the old heartlands',
               'people/km² · c.200 AD scenario, the same people drawn toward the lore heartlands',.1,300,'people',True,
               'Heartlands from the campaign lore (data/lore_cores.json); occupation falls as exp(-D / 800 km) with '
               'travel through forest and relief, as tested on Earth with the historical cores.')
    cored['id']='land_density_cores';cored['scenario_files']={}
    for disease,base in [('endemic','settlement_cored'),('absent','settlement_cored_no_malaria')]:
        for scenario,fraction in occupation.items():
            file=f'land_density_cores_{scenario}_{disease}.webp'
            save(color_image(fields[base]*fraction,land,elevation,RAMPS['people'],.1,300,True),file)
            cored['scenario_files'][scenario+'_'+disease]=file
    cored['file']=cored['scenario_files']['central_endemic']
    return layers


def export(atlas):
    atlas=Path(atlas);data=atlas/'data';meta=json.loads((data/'atlas.json').read_text())
    arrays=climate_arrays(data,meta)
    sources=[ROOT/p for p in ['harvest/models.py','harvest/export.py','scripts/land_people.py',
             'scripts/land_people_hexes.py','scripts/vector_rivers.py','data/harvest_model.json',
             'data/harvest_sources.json','data/settlement_reference_regions.json','data/hexgrid.json','ravages/data.json',
             'data/source/elevation.png','data/source/rivers.png','data/source/original/rivers.png',
             'land/earth.webp']]
    identity=dict(climate_sha256=digest(data/'atlas.bin'),metadata=physical_metadata(meta),
                  sources={str(p.relative_to(ROOT)):digest(p) for p in sources})
    fingerprint=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()
    previous=data/'harvest_provenance.json'
    if previous.exists() and json.loads(previous.read_text()).get('fingerprint')==fingerprint:
        required={'harvest.json','harvest.bin','harvest_model.json','harvest_sources.json',
                  'settlement_reference_regions.json','crop_model.json','earth_crop_reference.webp',
                  'provinces_people.csv','places_harvest.csv'}
        for layer in meta['layers']:
            if layer['id'].startswith('land_'):
                required.update([layer['file'],*layer.get('scenario_files',{}).values()])
        if meta.get('harvest',{}).get('fingerprint')==fingerprint and all((data/name).is_file() for name in required):
            print('Harvest export already matches climate and source fingerprint',flush=True);return
    print('Deriving crops, disease and settlement from '+str(atlas),flush=True)
    fields,geo,names,geo_inputs=derive(meta,arrays)
    info,index,area=aggregates(fields,geo,meta)
    binary=pack_fields(fields,area>0,index,data/'harvest.bin')
    layers=images_and_layers(fields,geo,meta,arrays,data)
    info.update(width=meta['width'],height=meta['height'],shape=list(area.shape),
                cell_px=meta['width']/area.shape[1],arrays=binary,crop_labels=CROP_LABELS,
                crop_colors=CROP_COLORS,parameters=specification(),thermal_peak_c=thermal_reference()[1])
    (data/'harvest.json').write_text(json.dumps(info,ensure_ascii=False,separators=(',',':'),allow_nan=False))
    for name in ['harvest_model.json','harvest_sources.json','settlement_reference_regions.json']:
        (data/name).write_bytes((ROOT/'data'/name).read_bytes())
    from scripts.land_people import CROPS,DATES,FARMED_SHARE,FALLOW,NEED_KCAL,ARABLE_BY_TIER
    crop_model=dict(crops=CROPS,date_palm=DATES,farmed_share=FARMED_SHARE,single_crop_sown_share=FALLOW,
                    kcal_per_person_year=NEED_KCAL,arable_by_terrain_tier=ARABLE_BY_TIER,
                    soil_bucket_mm=100.,effective_rain_fraction=.8,second_crop_weight=.5,
                    note='Parameters actually used by the inherited Harvest crop model. Period yields are assumptions, not modern GAEZ rasters. See scripts/land_people.py for the full calculation.')
    (data/'crop_model.json').write_text(json.dumps(crop_model,indent=2)+'\n')
    (data/'earth_crop_reference.webp').write_bytes((ROOT/'land/earth.webp').read_bytes())
    meta['layers']=[l for l in meta['layers'] if not l['id'].startswith('land_')]+layers
    meta['harvest']=dict(metadata='harvest.json',binary='harvest.bin',fingerprint=fingerprint,
                          technology=specification()['technology'])
    (data/'atlas.json').write_text(json.dumps(meta,ensure_ascii=False))
    summary_path=atlas/'summary.json'
    if summary_path.exists():
        summary=json.loads(summary_path.read_text());summary['harvest']=info['summary']
        summary_path.write_text(json.dumps(summary,indent=1)+'\n')
    with (data/'provinces_people.csv').open('w',newline='',encoding='utf-8') as file:
        keys=['province','area_km2','crop_capacity_people','food_capacity_people']+[f'{s}_{disease}_people'
                for disease in ['endemic','absent'] for s in info['occupation']['scenarios']]
        writer=csv.DictWriter(file,fieldnames=keys,lineterminator='\n');writer.writeheader()
        for p in info['provinces']:
            row=dict(province=p['name'],area_km2=round(p['area_km2'],2),
                     crop_capacity_people=round(p['crop_capacity_people']),food_capacity_people=round(p['food_capacity_people']))
            for disease,base in [('endemic','settlement_base'),('absent','settlement_no_malaria')]:
                row.update({f'{s}_{disease}_people':round(p[base]*f) for s,f in info['occupation']['scenarios'].items()})
            writer.writerow(row)
    with (data/'places_harvest.csv').open('w',newline='',encoding='utf-8') as file:
        keys=['name','crop_capacity','pastoral_capacity','food_capacity','expected_central_per_km2',
              'livability','malaria','malaria_months','lgp_days','irr','staple_crop']
        writer=csv.DictWriter(file,fieldnames=keys,lineterminator='\n');writer.writeheader()
        for place in meta['places']:
            x=min(area.shape[1]-1,max(0,int(place['x']/info['cell_px'])))
            y=min(area.shape[0]-1,max(0,int(place['y']/info['cell_px'])))
            if not area[y,x]>0:continue
            row={k:round(float(fields[k][y,x]),4) for k in keys if k in fields}
            row.update(name=place['name'],expected_central_per_km2=round(float(fields['settlement_base'][y,x])*info['occupation']['scenarios']['central'],4),
                       staple_crop=CROP_LABELS[int(fields['crop'][y,x])-1])
            writer.writerow(row)
    provenance=dict(fingerprint=fingerprint,inputs=identity,geography=geo_inputs,
                     note='Derived from the exported climate packet; no additional climate simulation. Population values are scenarios.')
    (data/'harvest_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps(info['summary'],indent=2),flush=True)
