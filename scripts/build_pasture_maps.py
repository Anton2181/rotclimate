"""Add worldwide feed-resource diagnostics without changing frozen atlases."""
from pathlib import Path
import copy
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from atlas_set import active  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)


def main():
    import numpy as np
    from scipy import ndimage as ndi
    from PIL import Image
    from matplotlib.colors import to_rgb
    from harvest.pasture import forage_allocation,seasonal_forage,feed_diagnostics
    from harvest.export import climate_arrays,geometry,surface_months
    from harvest.models import biome_factor
    from population.export import decode_harvest
    from scripts.land_people import FARMED_SHARE
    from polity.fields import polity_fills
    from local_benchmark_protocol import file_hash,write_json
    spec=json.loads((ROOT/'data/pasture_model.json').read_text());old=json.loads((ROOT/'data/harvest_model.json').read_text())
    source_paths=['harvest/pasture.py','harvest/food_stocks.py','harvest/export.py','harvest/models.py','population/export.py',
        'scripts/land_people.py','scripts/build_pasture_maps.py','data/pasture_model.json','data/harvest_model.json',
        'research_notes/pasture_20261104.json','polity/fields.py','data/source/ravages_v8/polities.json','data/source/ravages_v8/borders_fill.png',
        'data/source/elevation.png','data/source/rivers.png','data/source/original/rivers.png']
    sources={p:file_hash(ROOT/p) for p in source_paths};out=ROOT/'output/pasture_maps_20261104';out.mkdir(exist_ok=True)
    # Freeze geographic examples BEFORE evaluating the new diagnostics. They
    # illustrate physical contexts, not ethnographic or validation samples.
    earth=ROOT/'atlases/earth_fit/data';em=json.loads((earth/'atlas.json').read_text());eh,ef=decode_harvest(earth)
    ea=climate_arrays(earth,em);shape=ef['npp'].shape;eg,_=geometry(em,shape);land=eg['land_fraction']>0
    ids,info=polity_fills(shape);named=np.isin(ids,[i for i,d in info.items() if d['name']]);imperial=np.isin(ids,[i for i,d in info.items() if (d['name'] or '').startswith('Xšāça')])
    yy,xx=np.mgrid[:shape[0],:shape[1]];pilots=[]
    tarani=np.isin(ids,[i for i,d in info.items() if d['name']=='Kingdom of Tarani'])
    tribal=np.isin(ids,[i for i,d in info.items() if d['name']=='Tribes of the Neck'])
    masks=[('nonimperial_agricultural','Tarani agricultural resource landscape',tarani&(ef['crop_capacity']>ef['pastoral_capacity']),(.2,.5)),
        ('seasonal_grassland','Grassland resource landscape',~imperial&np.isin(ea['biome'],[1,8])&(ef['pastoral_capacity']>0),(.5,.18)),
        ('outside_named_claims','Mixed resources outside named claims',ndi.binary_erosion(~named,iterations=3)&(ef['crop_capacity']>0)&(ef['pastoral_capacity']>0),(.2,.7)),
        ('tribal_claim','Tribes of the Neck resource landscape',tribal&(ef['pastoral_capacity']>0),(.15,.4))]
    for key,label,mask,anchor in masks:
        mask=mask&land
        if not mask.any():pilots.append(dict(id=key,label=label,status='no_matching_land'));continue
        score=(xx/shape[1]-anchor[0])**2+(yy/shape[0]-anchor[1])**2;score[~mask]=np.inf
        row,col=np.unravel_index(np.argmin(score),shape);pid=int(ids[row,col])
        pilots.append(dict(id=key,label=label,status='selected',row=int(row),column=int(col),anchor=list(anchor),
            map_claim=info.get(pid,{}).get('name'),x=float((col+.5)*em['width']/shape[1]),y=float((row+.5)*em['height']/shape[0])))
    protocol=dict(status='fixed_geographic_examples',selection='Nearest eligible grid cell to declared drawing-fraction anchors using published Earth-raw fields; no tuning on new reserve/feed outputs. Context labels do not assign livelihoods or institutions.',
        pilots=pilots,sources_sha256=sources)
    write_json(out/'protocol.json',protocol)
    all_inputs={};overall=[]
    for name in active(['free_fit','earth_fit','whittaker_fit']):
        data=ROOT/'atlases'/name/'data';original=json.loads((data/'atlas.json').read_text());packets={}
        for mode in ['raw']+(['corrected'] if original.get('corrected_climate') else []):
            print('Building',name,mode,flush=True);prefix='' if mode=='raw' else 'corrected/';folder=data/prefix
            meta=copy.deepcopy(original)
            if mode=='corrected':
                for k in ['arrays','lapse12','cell_px','harvest']:meta[k]=original['corrected_climate'][k]
            paths=[data/'atlas.json',folder/'atlas.bin',folder/'harvest.json',folder/'harvest.bin']
            inputs={str(p.relative_to(ROOT)):file_hash(p) for p in paths};all_inputs.update(inputs)
            hm,hf=decode_harvest(folder);arrays=climate_arrays(folder,meta);geo,_=geometry(meta,hf['npp'].shape);land=geo['land_fraction']>0
            temperature,rain,_,_=surface_months(meta,arrays);index=np.flatnonzero(land)
            graze=old['grazing'];edible=biome_factor(arrays['biome'],graze['edible_forage_share']).ravel()[index]
            annual,cropped,remaining=forage_allocation(hf['npp'].ravel()[index],hf['arable'].ravel()[index],edible,
                farmed_share=FARMED_SHARE,aboveground_share=graze['aboveground_npp_share'],usable_share=graze['sustainable_use'])
            ph=spec['phenology'];supply,resolved=seasonal_forage(temperature.reshape(12,-1)[:,index],rain.reshape(12,-1)[:,index],annual,
                temperature_floor=ph['temperature_floor_c'],temperature_span=ph['temperature_span_c'],rain_half=ph['rain_half_saturation_mm'])
            budget=feed_diagnostics(supply,intake_kg_day=spec['reference_intake_kg_dm_day'],year_days=spec['year_days'],
                demand_fraction=spec['test_demand_fraction_of_annual_supply'],buffer_days=spec['test_buffer_days'])
            fields={}
            for key,value in [('annual_dm',annual),('lean_fraction',budget.lean_growth_fraction),('reserve_days',budget.minimum_reserve_days),
                ('shortfall_bins',budget.shortfall_bins),('water_distance',geo['water_distance'].ravel()[index])]:
                full=np.full(land.shape,np.nan);full.ravel()[index]=value;fields[key]=full
            # Quantization is explicit and checked; complete float grids remain
            # downloadable. Unavailable seasonal values stay nodata, not zero.
            blob=bytearray();descriptors={}
            for key,scale,dtype,nodata in [('annual_dm',1.,'<f4',None),('lean_fraction',1/60000,'<u2',65535),
                ('reserve_days',.01,'<u2',65535),('water_distance',.1,'<u2',65535),('shortfall_bins',1.,'u1',255)]:
                value=fields[key];valid=land&np.isfinite(value);packed=np.full(land.shape,np.nan if nodata is None else nodata,dtype=dtype)
                if dtype=='<f4':
                    packed[valid]=value[valid];np.testing.assert_allclose(packed[valid],value[valid],rtol=1e-6)
                else:
                    q=np.rint(value[valid]/scale)
                    if np.any((q<0)|(q>=nodata)):raise ValueError('Pasture field exceeds encoding: '+key)
                    packed[valid]=q.astype(dtype)
                    if np.any(np.abs(packed[valid]*scale-value[valid])>scale*.501):raise ValueError('Pasture quantization changed values')
                descriptors[key]=dict(offset=len(blob),dtype={'<u2':'uint16','<f4':'float32','u1':'uint8'}[dtype],scale=scale,nodata=nodata)
                blob.extend(packed.tobytes())
            descriptors['land']=dict(offset=len(blob),dtype='uint8',scale=1.,nodata=0);blob.extend(land.astype('u1').tobytes())
            binary=folder/'pasture.bin';binary.write_bytes(blob)
            grid=folder/'pasture_grid.npz';np.savez_compressed(grid,**{k:v.astype('f4') for k,v in fields.items()},land=land)
            colours=['#eee8d5','#d2d69b','#a5c18b','#73ac94','#438b87','#285f72']
            stress=['#286f70','#72a58c','#b8bd7d','#d5af65','#b8795a','#824754'];images={}
            common=('Dry-matter resource scenarios across all land, independent of political claims. '
                'Annual supply inherits current NPP and forage assumptions; seasonal growth is an uncalibrated proxy. '
                'No protein/energy adequacy, herd dynamics, mobility or human population is inferred. Grey is unresolved seasonality or no forage where a ratio is undefined.')
            def image(key,value,bounds,labels,palette,note):
                valid=land&np.isfinite(value);rgb=np.full((*land.shape,3),to_rgb('#b7b4ae'))
                codes=np.searchsorted(bounds,np.nan_to_num(value),side='right');rgb[valid]=np.array([to_rgb(c) for c in palette])[codes[valid]];rgb[~land]=[.84,.89,.94]
                filename='pasture_'+key+'.webp';Image.fromarray(np.rint(rgb*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST).save(folder/filename,lossless=True)
                images[prefix+filename]=file_hash(folder/filename)
                return dict(value=key,label=note[0],file=prefix+filename,items=[dict(color=c,label=l) for c,l in zip(palette,labels)]+[dict(color='#b7b4ae',label='Unavailable / undefined')],note=note[1]+' '+common,caption=note[1])
            unit=spec['reference_intake_kg_dm_day']*spec['year_days']
            annual_views=[image('annual_dm',fields['annual_dm']/1000,[5,15,30,60,120],['<5 tonnes/km²','5–15','15–30','30–60','60–120','≥120'],colours,
                ('Usable forage · annual dry matter','Annual usable forage tonnes DM per km² of land, after the assigned cropped area is excluded. No crop residues are added.')),
                image('feed_units',fields['annual_dm']/unit,[1,3,10,25,50],['<1 reference unit/km²','1–3','3–10','10–25','25–50','≥50'],colours,
                ('Annual feed equivalents','Annual DM divided by 6.25 kg/day ×365 days for a 250 kg reference animal. This is a feed-equivalent unit, not sustainable or nutritionally adequate livestock.'))]
            seasonal_views=[image('lean_fraction',fields['lean_fraction'],[.01,.1,.25,.5,.75],['<1% of mean new growth','1–10%','10–25%','25–50%','50–75%','≥75%'],stress[::-1],
                ('Lean-bin new growth','Least monthly new forage production as a share of average monthly production. Standing forage and stored feed can bridge a low-growth bin; this is not a starvation forecast.')),
                image('reserve_days',fields['reserve_days'],[1,30,90,180,270],['<1 demand-day','1–30','30–90','90–180','180–270','≥270'],stress,
                ('Minimum zero-loss feed reserve','Smallest repeating zero-loss reserve for constant test demand equal to half annual usable DM. Units: days of that declared demand. Standing forage and cut fodder are not distinguished.')),
                image('shortfall_bins',fields['shortfall_bins'],[.5,1.5,3.5,6.5,9.5],['No shortfall bins','1 bin','2–3','4–6','7–9','10–12'],stress,
                ('With a 90-demand-day buffer','Bins with unmet DM demand in a repeating zero-loss year with a 90-demand-day reserve capacity. Same half-annual test demand; no free inherited food. This is not famine or animal mortality.'))]
            water=image('water_distance',fields['water_distance'],[1.6,3.2,10,25,50],['<1.6 km','1.6–3.2','3.2–10','10–25','25–50','≥50'],stress,
                ('Mapped water proximity','Mean land distance to mapped rivers/lakes, not a route or measured drinkable water supply. Wells, water permanence, salinity and species-specific watering needs are unknown; no universal grazing exclusion is imposed.'))
            layers=[]
            for key,label,views in [('annual','Pasture resources',annual_views),('seasonal','Seasonal feed',seasonal_views),('water','Water proximity',[water])]:
                layer=dict(id='pasture_'+key,label=label,group='Livelihoods',kind='categories',controls=[],file=views[0]['file'],items=views[0]['items'],note=views[0]['note'])
                if len(views)>1:layer['variants']=dict(label='Resource view',default=views[0]['value'],options=views)
                layers.append(layer)
            samples=[]
            for p in pilots:
                if p['status']!='selected':continue
                row,col=p['row'],p['column'];flat=row*shape[1]+col;j=np.searchsorted(index,flat)
                samples.append(dict(**p,annual_dm=float(fields['annual_dm'][row,col]),monthly_dm=[float(v) if np.isfinite(v) else None for v in supply[:,j]],
                    **{k:float(v[row,col]) if np.isfinite(v[row,col]) else None for k,v in fields.items() if k!='annual_dm'}))
            area=geo['land_fraction']*(meta['width']/shape[1]*meta['mi_per_px']*1.609344)**2
            summary=dict(land_cells=int(land.sum()),seasonally_unresolved_cells=int(np.sum(~resolved)),
                median_minimum_reserve_days=float(np.nanmedian(fields['reserve_days'])),
                area_share_needing_more_than_90_days=float(np.sum(area*(fields['reserve_days']>90))/np.sum(area)),
                maximum_dm_ledger_residual=budget.maximum_ledger_residual,
                all_land_annual_dm_kg=float(np.nansum(fields['annual_dm']*area)),
                annual_dm_outside_named_claims_kg=float(np.nansum(fields['annual_dm']*area*~named)))
            packets[mode]=dict(layers=layers,shape=list(shape),cell_px=meta['width']/shape[1],fields=descriptors,
                binary=prefix+binary.name,binary_sha256=file_hash(binary),grid=prefix+grid.name,grid_sha256=file_hash(grid),image_sha256=images,
                expected_harvest_fingerprint=meta['harvest']['fingerprint'],expected_harvest_binary_sha256=file_hash(folder/'harvest.bin'),
                inputs_sha256=inputs,summary=summary,pilots=samples)
            print(name,mode,summary,flush=True)
        manifest=dict(version=1,status='conditional_dm_resource_diagnostics',specification=spec,packets=packets,sources_sha256=sources,
            pilot_protocol_sha256=file_hash(out/'protocol.json'),existing_climate_population_ownership_unchanged=True)
        write_json(data/'pasture.json',manifest);overall.append(dict(atlas=name,manifest_sha256=file_hash(data/'pasture.json'),summaries={m:p['summary'] for m,p in packets.items()}))
    if any(file_hash(ROOT/p)!=h for p,h in {**sources,**all_inputs}.items()):raise ValueError('Pasture source/input changed during build')
    write_json(out/'review.json',dict(status='complete',atlases=overall,sources_sha256=sources,protocol_sha256=file_hash(out/'protocol.json')))


if __name__=='__main__':main()
