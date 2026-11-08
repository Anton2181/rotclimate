"""Add isolated cereal-work map packets without modifying frozen atlas inputs."""
from pathlib import Path
import copy
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from atlas_set import active as active_atlases  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)


def main():
    import numpy as np
    from PIL import Image
    from matplotlib.colors import to_rgb
    from harvest.work_maps import cereal_work,tied_harvest_boundaries,boundary_count
    from harvest.crop_sequences import crop_windows
    from harvest.export import climate_arrays,geometry,surface_months
    from population.export import decode_harvest
    from scripts.land_people import CROPS,hargreaves,sunlight_top,bucket
    from local_benchmark_protocol import file_hash,write_json
    sourcepath=ROOT/'research_notes/farm_labour_20261103.json';source=json.loads(sourcepath.read_text())
    scale=source['scenario']['hours_per_workday']/source['scenario']['iugerum_hectares']
    crops=['wheat','barley'];hours=np.array([sum(source['workdays_per_iugerum'][c].values())*scale for c in crops])
    reap=np.array([source['workdays_per_iugerum'][c]['reap']*scale for c in crops])
    producer_files=['harvest/work_maps.py','harvest/crop_sequences.py','harvest/export.py',
        'scripts/land_people.py','population/export.py','scripts/build_cereal_work_maps.py',str(sourcepath.relative_to(ROOT))]
    sources={p:file_hash(ROOT/p) for p in producer_files}
    overall=[];all_inputs={};out=ROOT/'output/cereal_work_maps_20261103';out.mkdir(exist_ok=True)
    for name in active_atlases(['free_fit','earth_fit','whittaker_fit']):
        data=ROOT/'atlases'/name/'data';original=json.loads((data/'atlas.json').read_text())
        packets={}
        modes=['raw']+(['corrected'] if original.get('corrected_climate') else [])
        for mode in modes:
            prefix='' if mode=='raw' else 'corrected/'
            folder=data/prefix;meta=copy.deepcopy(original)
            if mode=='corrected':
                cc=original['corrected_climate']
                for k in ['arrays','lapse12','cell_px','harvest']:meta[k]=cc[k]
            input_paths=[data/'atlas.json',folder/'atlas.bin',folder/'harvest.json',folder/'harvest.bin',data/'crop_model.json']
            inputs={str(p.relative_to(ROOT)):file_hash(p) for p in input_paths}
            all_inputs.update(inputs)
            hm,hf=decode_harvest(folder);land=hf['crop']>0;shape=land.shape
            energy=np.nan_to_num(np.stack([hf['kcal_'+c] for c in crops]),nan=0.)
            work=cereal_work(energy,hours,reap,food_target=1e6)
            work.crop[~land]=0
            arrays=climate_arrays(folder,meta);geo,_=geometry(meta,shape)
            temperature,rain,dtr,latitude=surface_months(meta,arrays)
            selected=np.flatnonzero(land);mask=np.zeros(land.size,np.uint16)
            margin=hm['parameters'].get('margin_reliability');max_drift=0.
            for start in range(0,len(selected),8192):
                index=selected[start:start+8192]
                t,p,d=[a.reshape(12,-1)[:,index] for a in [temperature,rain,dtr]]
                lat=latitude.ravel()[index];irr=geo['irr'].ravel()[index]
                pet=hargreaves(t,d,sunlight_top(lat,meta['world']['tilt'],0));soil=bucket(p,pet)
                keep=rain_keep=None
                if margin:
                    cold=margin['cold_mean_temperature_c'];dry=margin['dry_rain_over_evaporation']
                    keep=np.clip((t.mean(0)-cold[0])/(cold[1]-cold[0]),0,1)
                    aridity=p.sum(0)/np.maximum(pet.sum(0),1)
                    rain_keep=np.clip((aridity-dry[0])/(dry[1]-dry[0]),0,1)
                for ccode,crop in enumerate(crops,1):
                    catalogue=crop_windows(t,p,pet,soil,irr,keep=keep,rain_keep=rain_keep,crops={crop:CROPS[crop]})
                    best,bits=tied_harvest_boundaries(catalogue)
                    exported=hf['kcal_'+crop].ravel()[index]
                    drift=np.abs(best-exported);limit=hm['arrays']['kcal_'+crop]['scale']*.501+1.
                    if np.max(drift)>limit:raise ValueError(f'{name}/{mode}/{crop}: crop response differs from published packet ({drift.max()})')
                    max_drift=max(max_drift,float(drift.max()))
                    chosen=work.crop.ravel()[index]==ccode;mask[index[chosen]]=bits[chosen]
            mask=mask.reshape(shape);counts=boundary_count(mask)
            if np.any((work.crop>0)&(counts==0)):raise ValueError('Productive cereal lacks a retained calendar')
            layers=[];images={};missing='#b7b4ae'
            colors=['#e8efd0','#c2d59a','#8cb98e','#51978a','#387684','#4a5375','#713d60']
            common=('Partial listed field tasks from Columella, to the threshing floor; current atlas single-cereal energy after seed. '
                'Assumed 8-hour workday and approximate 0.25 ha/iugerum. Other staples, threshing, processing, animal care, irrigation work and household duties are outside this budget. '
                'Gray means no positive modeled wheat/barley output, not zero work or uninhabitable land. No population or total subsistence-work estimate.')
            def image(key,values,bounds,labels,palette):
                valid=land&np.isfinite(values)&(work.crop>0)
                rgb=np.empty((*shape,3));rgb[:]=to_rgb(missing)
                codes=np.searchsorted(np.asarray(bounds),np.nan_to_num(values),side='right')
                rgb[valid]=np.asarray([to_rgb(c) for c in palette])[codes[valid]]
                rgb[~land]=[.84,.89,.94]
                filename='farm_work_'+key+'.webp';path=folder/filename
                Image.fromarray(np.rint(rgb*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST).save(path,lossless=True)
                images[prefix+filename]=file_hash(path)
                return dict(value=key,label='',file=prefix+filename,
                    items=[dict(color=c,label=l) for c,l in zip(palette,labels)]+[dict(color=missing,label='No modeled wheat/barley output')])
            variants=[]
            specs=[('hours','Listed field work',work.hours,[100,150,250,500,1000,2000],
                    ['<100 h','100–150 h','150–250 h','250–500 h','500–1,000 h','1,000–2,000 h','≥2,000 h'],
                    'Listed field hours per million net edible kcal; least-work single cereal.'),
                ('land','Cropped land required',work.land,[.5,.75,1,2,5,10],
                    ['<0.5 ha','0.5–0.75 ha','0.75–1 ha','1–2 ha','2–5 ha','5–10 ha','≥10 ha'],
                    'Cropped hectares per million net edible kcal, for the least-work cereal; excludes fallow and landscape arable fractions.')]
            for key,label,value,bounds,labels,caption in specs:
                variant=image(key,value,bounds,labels,colors);variant.update(label=label,caption=caption,note=caption+' '+common);variants.append(variant)
            for days in [10,20,30]:
                staffing=work.reaping/(days*source['scenario']['hours_per_workday'])
                caption=f'Reaping worker equivalents for a million-kcal cereal target over {days} days at 8 hours/day. Supplied harvest window, not a climate-derived deadline or actual staffing estimate.'
                variant=image('staff_'+str(days),staffing,[.25,.5,1,2,4,8],
                    ['<0.25 workers','0.25–0.5','0.5–1','1–2','2–4','4–8','≥8 workers'],colors)
                variant.update(label=f'Harvest staffing · {days} days',caption=caption,note=caption+' '+common);variants.append(variant)
            layers.append(dict(id='farm_cereal_work',label='Cereal field work',group='Food and work',kind='categories',
                file=variants[0]['file'],items=variants[0]['items'],note=variants[0]['note'],controls=[],
                variants=dict(label='Work view',default='hours',options=variants)))
            flex=image('calendar',counts.astype(float),[1.5,2.5,4.5,8.5],
                ['1 boundary','2 boundaries','3–4 boundaries','5–8 boundaries','9–12 boundaries'],
                ['#76557b','#9e8195','#c2afa7','#c3d4be','#5a9386'])
            note=('Distinct harvest-boundary climate bins across all tied maximum-energy windows of the least-work cereal. '
                'These are alternatives in the CURRENT monthly crop response, not harvest probabilities, actual dates, multiple crops or the new daily-development clock. '
                'Ties are retained rather than resolved to one arbitrary calendar. Gray means no modeled wheat/barley output.')
            layers.append(dict(id='farm_cereal_calendars',label='Calendar alternatives',group='Food and work',kind='categories',
                file=flex['file'],items=flex['items'],note=note,controls=[]))
            binary=folder/'farm_work_calendar.bin';binary.write_bytes(mask.astype('<u2').tobytes())
            grid=folder/'farm_work_grid.npz'
            np.savez_compressed(grid,listed_hours_per_million_kcal=work.hours.astype('f4'),
                cropped_ha_per_million_kcal=work.land.astype('f4'),reaping_hours_per_million_kcal=work.reaping.astype('f4'),
                cereal=work.crop,harvest_boundaries=mask,land=land)
            packets[mode]=dict(layers=layers,shape=list(shape),cell_px=hm['cell_px'],
                expected_harvest_fingerprint=meta['harvest']['fingerprint'],
                harvest_metadata=prefix+'harvest.json',harvest_metadata_sha256=file_hash(folder/'harvest.json'),
                harvest_binary_sha256=file_hash(folder/'harvest.bin'),calendar_binary=prefix+binary.name,
                calendar_binary_sha256=file_hash(binary),grid=prefix+grid.name,grid_sha256=file_hash(grid),
                inputs_sha256=inputs,image_sha256=images,
                summary=dict(land_cells=int(land.sum()),cereal_cells=int((work.crop>0).sum()),
                    ambiguous_calendar_cells=int((counts>1).sum()),max_export_quantization_difference_kcal_ha=max_drift,
                    median_listed_hours_per_million_kcal=float(np.nanmedian(work.hours)),
                    wheat_choice_cells=int((work.crop==1).sum()),barley_choice_cells=int((work.crop==2).sum())))
            print(name,mode,packets[mode]['summary'],flush=True)
        manifest=dict(version=1,status='experimental_partial_field_work_maps',food_target_kcal=1e6,crops=crops,
            listed_hours_per_hectare=hours.tolist(),reaping_hours_per_hectare=reap.tolist(),
            hours_per_workday=source['scenario']['hours_per_workday'],source_manifest_sha256=file_hash(sourcepath),
            sources_sha256=sources,packets=packets,scope='Conditional partial cereal field work and current-model calendar ambiguity; no climate, yield, population or total-subsistence validation/adoption.')
        write_json(data/'farm_work.json',manifest)
        overall.append(dict(atlas=name,manifest_sha256=file_hash(data/'farm_work.json'),packets={mode:p['summary'] for mode,p in packets.items()}))
    if any(file_hash(ROOT/p)!=h for p,h in sources.items()):raise ValueError('Map sources changed during build')
    if any(file_hash(ROOT/p)!=h for p,h in all_inputs.items()):raise ValueError('Existing climate/Harvest inputs changed during map build')
    write_json(out/'review.json',dict(status='built',atlases=overall,sources_sha256=sources,existing_climate_and_harvest_inputs_unchanged=True))


if __name__=='__main__':main()
