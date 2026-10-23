"""Add a separate, reproducible population experiment to an existing climate atlas."""
import csv
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from harvest.export import climate_arrays,geometry,color_image,RAMPS,physical_metadata
from .models import allocate,market_access,attraction_fields

ROOT=Path(__file__).resolve().parents[1]
DEFINITIONS=[
    ('density','Allocated population','people/km² · supplied population budget',.1,300,True,'people'),
    ('pressure','Population pressure','% of local environmental food support',0,100,False,'pressure'),
    ('headroom','Spare food support','additional people/km² within local support',.1,300,True,'green'),
    ('shift','Settlement redistribution','× same-total uniform occupation',.1,10,True,'shift'),
    ('travel','Walking to market','walking hours · no roads or boats',0,120,False,'water'),
    ('attraction','Settlement attraction','relative environmental and market attraction, 0–100',0,100,False,'green')]
COLORS={**RAMPS,'pressure':['#e9efce','#c5d48c','#e9c36a','#d88442','#96394d'],
        'shift':['#224d86','#79b3c9','#f1ecdb','#dc9c61','#962d41']}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode_harvest(data):
    meta=json.loads((data/'harvest.json').read_text());blob=(data/'harvest.bin').read_bytes();arrays={}
    for name,s in meta['arrays'].items():
        raw=np.frombuffer(blob,dtype=np.dtype(s['dtype']),count=int(np.prod(s['shape'])),offset=s['offset_bytes']).reshape(s['shape'])
        value=raw.astype(float)*s['scale']+s['offset']
        arrays[name]=np.where(raw==s['nodata'],0,value) if s['nodata'] is not None else np.nan_to_num(value)
    return meta,arrays


def views(fields,requested,pattern='markets',disease='endemic'):
    area=fields['area'].astype(float);capacity=fields['capacity_absent' if disease=='absent' else 'capacity'].astype(float)
    weight=np.ones(area.shape) if pattern=='dispersed' else fields['rural' if pattern=='rural' else 'attraction']
    people,unmet=allocate(capacity*area,weight,requested)
    density=np.divide(people,area,out=np.zeros(area.shape),where=area>0)
    uniform=capacity*min(requested/max(float((capacity*area).sum()),1e-30),1)
    return dict(density=density,pressure=np.divide(density*100,capacity,out=np.zeros(area.shape),where=capacity>0),
                headroom=np.maximum(capacity-density,0),shift=np.divide(density,uniform,out=np.ones(area.shape),where=uniform>0),
                travel=fields['travel'],attraction=fields['attraction']*100),people,unmet


def export(atlas):
    atlas=Path(atlas);data=atlas/'data';meta=json.loads((data/'atlas.json').read_text())
    sources=['population/models.py','population/export.py','atlas/population.js','data/population_model.json',
             'harvest/export.py','rotclimate/geography.py','scripts/vector_rivers.py',
             'data/source/elevation.png','data/source/rivers.png','data/source/original/rivers.png']
    inputs=dict(climate_sha256=sha(data/'atlas.bin'),harvest_sha256=sha(data/'harvest.bin'),
                harvest_metadata_sha256=sha(data/'harvest.json'),physical_metadata=physical_metadata(meta),places=meta['places'],
                sources={p:sha(ROOT/p) for p in sources})
    fingerprint=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    if (data/'population.json').exists():
        previous=json.loads((data/'population.json').read_text())
        if previous.get('fingerprint')==fingerprint and meta.get('population',{}).get('fingerprint')==fingerprint:
            if all((data/p).exists() for p in ['population.bin','population_model.json','population_provinces.csv']+
                   ['pop_'+d[0]+'.webp' for d in DEFINITIONS]):
                shutil.copy(ROOT/'atlas/population.js',atlas/'population.js')
                print('Population export already matches '+str(atlas),flush=True);return
    print('Building population allocation and walking access: '+str(atlas),flush=True)
    hm,hf=decode_harvest(data);arrays=climate_arrays(data,meta);geo,_=geometry(meta,arrays['elev'].shape)
    land=geo['land_fraction']>0;h,w=land.shape
    cell_km=meta['width']/w*meta['mi_per_px']*1.609344
    spec=json.loads((ROOT/'data/population_model.json').read_text())
    # Snap coastal named places to nearest analysis land. Keep the distance explicit.
    _,nearest=ndi.distance_transform_edt(~land,return_indices=True)
    places=[];snaps=[]
    for p in meta['places']:
        y=min(h-1,max(0,int(p['y']/meta['height']*h)));x=min(w-1,max(0,int(p['x']/meta['width']*w)))
        yy,xx=int(nearest[0,y,x]),int(nearest[1,y,x]);places.append((yy,xx))
        snaps.append(dict(name=p['name'],row=yy,column=xx,snap_km=float(np.hypot(yy-y,xx-x)*cell_km)))
    hours,market=market_access(arrays['elev'],land,cell_km,places,spec['walking_off_path_factor'])
    rural,attraction=attraction_fields(arrays['elev'],land,geo['water_distance'],hours,cell_km,spec)
    province_names=[p['name'] for p in hm['provinces']]
    lookup=np.zeros(int(hf['hex_id'].max())+1,np.uint16)
    for i,p in enumerate(hm['provinces'],1):lookup[p['hexes']]=i
    fields=dict(area=geo['land_fraction']*cell_km**2,capacity=np.maximum(hf['settlement_base'],0),
                capacity_absent=np.maximum(hf['settlement_no_malaria'],0),rural=rural,attraction=attraction,
                travel=np.where(land,hours,-1),market=market,province=lookup[hf['hex_id'].astype(int)])
    # Store exactly the floats used in default maps and validation, not higher-precision precursors.
    fields={k:np.asarray(v,dtype='<u2' if k in ['market','province'] else '<f4') for k,v in fields.items()}
    blob=bytearray();descriptors={}
    for key,value in fields.items():
        while len(blob)%4:blob.append(0)
        descriptors[key]=dict(dtype='uint16' if key in ['market','province'] else 'float32',offset=len(blob),shape=list(value.shape))
        blob.extend(value.tobytes())
    (data/'population.bin').write_bytes(blob)
    default=round(hm['summary']['population']['endemic']['central']/1000)*1000;maps,people,unmet=views(fields,default)
    notes={
        'density':'A supplied population budget allocated within local food support. This is a scenario, not a historical census.',
        'pressure':'Allocated population divided by the same local environmental support used by the allocator. 100% is its local ceiling.',
        'headroom':'Local environmental food support minus allocated residents. It is spare support, not a prediction of migration.',
        'shift':'Redistribution relative to uniform occupation with the same supported total. Above 1× concentrates people here; below 1× disperses them elsewhere.',
        'travel':'Directed Tobler off-path walking time to a named place. Grey land has no overland connection to a named market. No roads, ships or bridges.',
        'attraction':'Scenario weights for water access, slope and market walking time. These are relative preferences, not measured historical settlement probabilities.'}
    layers=[]
    for key,label,unit,lo,hi,log,palette in DEFINITIONS:
        colors=COLORS[palette];image=color_image(maps[key],land,arrays['elev'],colors,lo,hi,log)
        if key=='travel':image[land & (hours<0)]=[.69,.69,.69]
        file='pop_'+key+'.webp'
        Image.fromarray((np.clip(image,0,1)*255).astype('uint8')).resize((meta['width'],meta['height'])).save(data/file,'WEBP',quality=88,method=4)
        dynamic=key not in ['travel','attraction']
        layers.append(dict(id='pop_'+key,file=file,label=label,unit=unit,group='Population',kind='ramp',
                           stops=colors,vmin=lo,vmax=hi,log=log,note=notes[key],
                           controls=['disease'] if dynamic else [],population_dynamic=dynamic))
    totals=dict(requested=default,allocated=float(people.sum()),unallocated=unmet,
                capacity=float((fields['capacity'].astype(float)*fields['area']).sum()),
                capacity_absent=float((fields['capacity_absent'].astype(float)*fields['area']).sum()),
                unreachable_land_km2=float(fields['area'][land & (hours<0)].sum()))
    pm=dict(version=1,fingerprint=fingerprint,inputs=inputs,binary_sha256=sha(data/'population.bin'),shape=list(land.shape),width=meta['width'],height=meta['height'],
            arrays=descriptors,default_population=default,default_pattern='markets',markets=snaps,provinces=province_names,summary=totals)
    (data/'population.json').write_text(json.dumps(pm,separators=(',',':'),allow_nan=False)+'\n')
    shutil.copy(ROOT/'data/population_model.json',data/'population_model.json')
    with (data/'population_provinces.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['province','area_km2','allocated_people','local_support_people'])
        for i,name in enumerate(['Outside province grid']+province_names):
            mask=fields['province']==i
            if not fields['area'][mask].sum():continue
            writer.writerow([name,float(fields['area'][mask].sum()),float(people[mask].sum()),
                             float((fields['capacity'][mask].astype(float)*fields['area'][mask]).sum())])
    meta['layers']=[l for l in meta['layers'] if not l['id'].startswith('pop_')]+layers
    meta['population']=dict(metadata='population.json',binary='population.bin',fingerprint=fingerprint)
    (data/'atlas.json').write_text(json.dumps(meta,ensure_ascii=False))
    shutil.copy(ROOT/'atlas/population.js',atlas/'population.js')
    print(json.dumps(totals,indent=2),flush=True)
