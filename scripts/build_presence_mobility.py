"""Conserved site-food support and closed single-herd resource circuits."""
from pathlib import Path
from dataclasses import asdict
import copy
import csv
import gzip
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from scipy import ndimage as ndi
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from PIL import Image
    from matplotlib.colors import to_rgb
    from harvest.export import climate_arrays,geometry,surface_months
    from population.export import decode_harvest
    from harvest.models import biome_factor
    from harvest.pasture import forage_allocation,seasonal_forage
    from harvest.seasonal_mobility import seasonal_circuit
    from polity.sustained_presence import rural_cereal,fixed_path_days,stored_collection,site_food
    from harvest.food_stocks import periodic_food_year,minimum_zero_loss_capacity
    from polity import fields as F,control as C,seasons as S,network as N
    from rotclimate.geography import target_fullres
    from scripts.land_people import FARMED_SHARE,FALLOW
    from local_benchmark_protocol import file_hash,write_json
    from regional_resource_circuits import regional_experiments

    spec=json.loads((ROOT/'data/presence_mobility_model.json').read_text());ps=spec['presence'];ms=spec['mobility']
    graze=json.loads((ROOT/'data/harvest_model.json').read_text())['grazing']
    phenology=json.loads((ROOT/'data/pasture_model.json').read_text())['phenology']
    sourcepaths=['scripts/build_presence_mobility.py','polity/sustained_presence.py','harvest/seasonal_mobility.py',
        'harvest/food_stocks.py','harvest/pasture.py','harvest/export.py','harvest/models.py','population/export.py',
        'polity/fields.py','polity/control.py','polity/seasons.py','polity/network.py','polity/transport.py',
        'scripts/land_people.py','rotclimate/geography.py','scripts/vector_rivers.py',
        'data/presence_mobility_model.json','data/harvest_model.json','data/pasture_model.json',
        'research_notes/presence_mobility_20261104.json','research_notes/presence_mobility_scale_20261104.json',
        'scripts/regional_resource_circuits.py','harvest/mobility_landscape.py','data/source/elevation.png','data/source/rivers.png',
        'data/source/original/rivers.png','data/source/ravages_v8/roads.png']
    sources={p:file_hash(ROOT/p) for p in sourcepaths}
    origin=ROOT/'output/presence_mobility_scale_20261104';origin.mkdir(exist_ok=True)
    # Reuse earlier geography-only examples: never select on mobility gains.
    pilots=json.loads((ROOT/'atlases/earth_fit/data/pasture.json').read_text())['packets']['raw']['pilots']
    write_json(origin/'protocol.json',dict(status='declared_before_run',specification=spec,pilots=[{k:p[k] for k in ['id','label','row','column','x','y','map_claim']} for p in pilots],
        selection='Reuse fixed Earth-raw resource examples from the pasture milestone. No outcome-based relocation or polity-to-livelihood assignment.',sources_sha256=sources))
    reviews=[];allinputs={}
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';original=json.loads((data/'atlas.json').read_text());packets={}
        for mode in ['raw']+(['corrected'] if original.get('corrected_climate') else []):
            prefix='' if mode=='raw' else 'corrected/';folder=data/prefix;out=origin/(name+'_'+mode);out.mkdir(exist_ok=True)
            inputs={str(p.relative_to(ROOT)):file_hash(p) for p in [data/'atlas.json',folder/'atlas.bin',folder/'harvest.json',folder/'harvest.bin',
                folder/'farm_work_grid.npz',folder/'coverage_sources.json',data/'winds12.npz',ROOT/'atlases/earth_fit/data/pasture.json']}
            allinputs.update(inputs)
            reviewpath=out/'review.json';payloadpath=folder/'presence_mobility.json.gz';gridpath=folder/'presence_catchments.bin.gz'
            if reviewpath.exists() and payloadpath.exists() and gridpath.exists():
                review=json.loads(reviewpath.read_text())
                if review.get('sources_sha256')==sources and review.get('inputs_sha256')==inputs and all(file_hash(data/p)==h for p,h in review['public_sha256'].items()):
                    packets[mode]=review['packet'];reviews.append(dict(atlas=name,climate=mode,summary=review['summary'],review_sha256=file_hash(reviewpath)));print('Reused',name,mode,flush=True);continue
            print('Preparing',name,mode,flush=True)
            meta=copy.deepcopy(original)
            if mode=='corrected':
                for k in ['arrays','lapse12','cell_px','harvest']:meta[k]=original['corrected_climate'][k]
            hm,hf=decode_harvest(folder);arrays=climate_arrays(folder,meta);shape=hf['arable'].shape;h,w=shape
            geo,_=geometry(meta,shape);land=geo['land_fraction']>.5;cell_km=meta['width']/w*meta['mi_per_px']*1.609344
            area=geo['land_fraction']*cell_km**2;z=np.asarray(arrays['elev'],float)
            records=json.loads((folder/'coverage_sources.json').read_text())['records'];sites=[];seen=set()
            for record in records:
                if not record.get('symbol_verified') or 'node' not in record:continue
                if record['node'] in seen:raise ValueError('Coincident sources require explicit grouping')
                seen.add(record['node']);sites.append({k:record.get(k) for k in ['id','name','kind','actor','status','x','y','node']})
            nodes=np.array([s['node'] for s in sites],int)
            if not np.all(land.ravel()[nodes]):raise ValueError('Source not on majority-land grid')
            road=F.block_any(F.rgba('roads.png')[...,3]>0,shape)&land
            swamp=np.asarray(Image.fromarray((target_fullres()==5).astype('u1')*255).resize((w,h),Image.Resampling.BOX))>127
            world=dict(elev=z,land=land,biome=np.asarray(arrays['biome']),swamp=swamp,density=np.zeros(shape),cell_km=cell_km,
                tilt=float(meta['world']['tilt']),river=F.navigable_rivers(shape),road=road,**F.map_climate(data,meta,arrays,shape))
            st=N.statics(world);cl=N.climate(world,st)
            # No density feedback, inferred tracks, ferries, river or sea freight.
            def graph(month):
                flood=S.flood_index(cl['flow'][month][st['basin']])
                cross=np.where(st['basin']>0,S.CROSS_DAYS*(1+S.FLOOD_GAIN*flood),0.)
                r,c,d=C.foot_edges(z,land,road,S.month_terrain(st['eta'],cl,month),cell_km,
                    np.full(shape,C.OFF_PATH),road_factor=1+(S.MUD_ROAD-1)*cl['mud'][month],cross=cross)
                return csr_matrix((d,(r,c)),shape=(land.size,land.size))
            base=graph(ps['fixed_path_base_month'])
            days,parent,source=dijkstra(base.T.tocsr(),indices=nodes,min_only=True,return_predecessors=True,directed=True)
            parent[nodes]=nodes;lookup=np.zeros(land.size,np.uint16);lookup[nodes]=np.arange(1,len(nodes)+1)
            valid=land.ravel()&np.isfinite(days)&(days<=ps['maximum_collection_days_each_way'])
            assignment=np.zeros(land.size,np.uint16);assignment[valid]=lookup[source[valid]]
            order=np.flatnonzero(valid&(parent!=np.arange(land.size)));order=order[np.argsort(days[order])]
            _,back=fixed_path_days(base,parent,order)
            access=np.zeros((12,land.size),bool)
            for month in range(12):
                g=base if month==ps['fixed_path_base_month'] else graph(month)
                outward,inward=fixed_path_days(g,parent,order)
                access[month]=valid&(outward<=ps['maximum_collection_days_each_way'])&(inward<=ps['maximum_collection_days_each_way'])
                print(name,mode,'collection paths',month+1,flush=True)
            # A fixed, base-bin catchment is a collection experiment. It is
            # neither an ownership partition nor a globally exhaustive market.
            assignment=assignment.reshape(shape);gridpath.write_bytes(gzip.compress(assignment.astype('<u2').tobytes(),mtime=0))
            cereal=np.load(folder/'farm_work_grid.npz');crop=cereal['cereal'];bits=cereal['harvest_boundaries']
            kcal=np.where(crop==1,hf['kcal_wheat'],np.where(crop==2,hf['kcal_barley'],0))
            annual=kcal*100*area*hf['arable']*FARMED_SHARE*FALLOW
            annual=np.where(land,annual,0);idx=np.flatnonzero(annual>0)
            rural={};supply={};exportable={};balances={}
            ruralkeys=sorted({(c['calendar'],c.get('rural_store_days',ps['rural_store_demand_days'])) for c in ps['scenarios']})
            for calendar,ruraldays in ruralkeys:
                print(name,mode,'rural ledgers',calendar,ruraldays,flush=True)
                rr=rural_cereal(annual.ravel()[idx],bits.ravel()[idx],demand_fraction=ps['rural_demand_fraction_of_single_cereal_energy'],
                    reserve_days=ruraldays,loss_fraction_year=ps['stored_energy_loss_fraction_year'],calendar=calendar)
                # Never export from a cell unable to meet its declared rural
                # demand over the entire repeating year, even if it overflows.
                protected=rr.year.unmet<=1e-8*np.maximum(annual.ravel()[idx],1)
                available=rr.exportable
                flow=stored_collection(available,assignment.ravel()[idx],access[:,idx],len(sites),
                    collection_fraction=ps['collection_fraction_of_rural_overflow'],freight_capacity=ps['freight_kcal_per_site_per_bin'],
                    retention=ps['delivery_retention'],delay_bins=ps['delivery_delay_bins'],
                    store_days=ps['export_store_days_of_annual_exportable_supply'],loss_fraction_year=ps['stored_energy_loss_fraction_year'])
                key=(calendar,ruraldays)
                rural[key]=dict(harvested=float(rr.harvest.sum()),rural_consumed=float(rr.year.consumed.sum()),rural_unmet=float(rr.year.unmet.sum()),
                    rural_storage_loss=float(rr.year.spoiled.sum()),rural_overflow=float(rr.year.overflow.sum()),
                    max_cell_ledger_residual=float(np.max(np.abs(rr.year.ledger_residual))),export_withheld_for_rural_deficit=float(np.sum(rr.overflow[:,~protected])))
                supply[key]=flow;exportable[key]=available;del rr
            variants=[]
            for case in ps['scenarios']:
                key=(case['calendar'],case.get('rural_store_days',ps['rural_store_demand_days']))
                flow=supply[key];departures=flow['departures'].copy();closed=[]
                if any(k in case for k in ['freight_multiplier','export_store_days','collection_fraction']):
                    flow=stored_collection(exportable[key],assignment.ravel()[idx],access[:,idx],len(sites),
                        collection_fraction=case.get('collection_fraction',ps['collection_fraction_of_rural_overflow']),freight_capacity=ps['freight_kcal_per_site_per_bin']*case.get('freight_multiplier',1),
                        retention=ps['delivery_retention'],delay_bins=ps['delivery_delay_bins'],
                        store_days=case.get('export_store_days',ps['export_store_days_of_annual_exportable_supply']),loss_fraction_year=ps['stored_energy_loss_fraction_year'])
                    departures=flow['departures'].copy()
                if case['closure_bins']:
                    # Interrupt the TWO BUSIEST consecutive dispatch bins at
                    # each source. This is a deliberate stress, not a forecast.
                    scores=departures+np.roll(departures,-1,axis=0);start=np.argmax(scores,axis=0)
                    opened=np.ones_like(departures,bool)
                    for site,startbin in enumerate(start):
                        bins=[int((startbin+k)%12) for k in range(case['closure_bins'])];opened[bins,site]=False;closed.append(bins)
                    flow=stored_collection(exportable[key],assignment.ravel()[idx],access[:,idx],len(sites),
                        collection_fraction=ps['collection_fraction_of_rural_overflow'],freight_capacity=ps['freight_kcal_per_site_per_bin'],
                        retention=ps['delivery_retention'],delay_bins=ps['delivery_delay_bins'],
                        store_days=ps['export_store_days_of_annual_exportable_supply'],loss_fraction_year=ps['stored_energy_loss_fraction_year'],dispatch_open=opened)
                    departures=flow['departures']
                arrivals=np.roll(departures,ps['delivery_delay_bins'],axis=0)*ps['delivery_retention']
                year,met=site_food(arrivals,people=case['people'],kcal_day=ps['ration_kcal_person_day'],reserve_days=case['reserve_days'],
                    loss_fraction_year=ps['stored_energy_loss_fraction_year'])
                minimum=minimum_zero_loss_capacity(arrivals,np.full_like(arrivals,case['people']*ps['ration_kcal_person_day']*spec['year_days']/12))/(case['people']*ps['ration_kcal_person_day'])
                rows=[]
                for j,site in enumerate(sites):
                    rows.append(dict(site_id=site['id'],monthly_arrivals_kcal=arrivals[:,j].tolist(),monthly_need_met=met[:,j].tolist(),
                        monthly_unmet_kcal=year.unmet_path[:,j].tolist(),stock_path_kcal=year.stock_path[:,j].tolist(),
                        annual_need_met=float(year.consumed[j]/year.needed[j]),worst_bin_need_met=float(met[:,j].min()),
                        minimum_zero_loss_store_demand_days=float(minimum[j]) if np.isfinite(minimum[j]) else None,
                        annual_supply_insufficient=bool(not np.isfinite(minimum[j])),
                        shortfall_bins=int(np.sum(met[:,j]<1-1e-8)),closed_dispatch_bins=closed[j] if closed else [],
                        annual_delivered_kcal=float(arrivals[:,j].sum()),annual_site_loss_kcal=float(year.spoiled[j]),annual_site_unused_kcal=float(year.overflow[j])))
                rr=rural[key];unused=rr['rural_overflow']-float(departures.sum())-flow['collection_storage_loss']
                transportloss=float(departures.sum()*(1-ps['delivery_retention']))
                residual=rr['harvested']-rr['rural_consumed']-rr['rural_storage_loss']-unused-flow['collection_storage_loss']-transportloss-float(year.consumed.sum()+year.spoiled.sum()+year.overflow.sum())
                if abs(residual)>1e-7*max(1,rr['harvested']):raise RuntimeError('Combined rural/freight/site ledger failed')
                balances[case['id']]=dict(**rr,uncollected_or_unavailable=unused,departed=float(departures.sum()),transport_loss=transportloss,
                    collection_storage_loss=flow['collection_storage_loss'],collection_max_ledger_residual=flow['max_collection_ledger_residual'],
                    site_consumed=float(year.consumed.sum()),site_storage_loss=float(year.spoiled.sum()),site_unused=float(year.overflow.sum()),
                    combined_ledger_residual=residual,site_max_ledger_residual=float(np.max(np.abs(year.ledger_residual))))
                variants.append(dict(**case,sites=rows))
            # Fresh forage and cropped land share are exactly the earlier
            # resource assumptions. Human food and forage scenarios aren't
            # summed into any demographic or authority output.
            temperature,rain,_,_=surface_months(meta,arrays)
            edible=biome_factor(arrays['biome'],graze['edible_forage_share'])
            dm,_,_=forage_allocation(hf['npp'],hf['arable'],edible,farmed_share=FARMED_SHARE,
                aboveground_share=graze['aboveground_npp_share'],usable_share=graze['sustainable_use'])
            forage,resolved=seasonal_forage(temperature,rain,dm,temperature_floor=phenology['temperature_floor_c'],
                temperature_span=phenology['temperature_span_c'],rain_half=phenology['rain_half_saturation_mm'])
            experiments=[]
            for pilot in pilots:
                print(name,mode,'circuit',pilot['id'],flush=True)
                cy,cx=pilot['row'],pilot['column'];radius=ms['landscape_radius_cells']
                ys,xs=np.mgrid[max(0,cy-radius):min(h,cy+radius+1),max(0,cx-radius):min(w,cx+radius+1)]
                chosen=land[ys,xs]&resolved[ys,xs]&((ys-cy)**2+(xs-cx)**2<=radius**2)
                rows,cols=ys[chosen],xs[chosen];patches=rows*w+cols
                if not len(patches) or not np.any(patches==cy*w+cx):
                    experiments.append(dict(id=pilot['id'],label=pilot['label'],status='home_not_traversable'));continue
                home=int(np.flatnonzero(patches==cy*w+cx)[0]);n=len(patches);local={int(p):i for i,p in enumerate(patches)}
                rr=[];cc=[];dd=[]
                for i,(y,x) in enumerate(zip(rows,cols)):
                    for dy,dx in [(a,b) for a in [-1,0,1] for b in [-1,0,1] if a or b]:
                        target=(int(y)+dy)*w+int(x)+dx
                        if target not in local:continue
                        if dy and dx and ((int(y)+dy)*w+int(x) not in local or int(y)*w+int(x)+dx not in local):continue
                        j=local[target];distance=cell_km*np.hypot(dy,dx);slope=(z[rows[j],cols[j]]-z[y,x])/(1000*distance)
                        speed=ms['reference_level_speed_km_day']*np.exp(-3.5*(abs(slope+.05)-.05))
                        rr.append(i);cc.append(j);dd.append(distance/speed)
                routegraph=csr_matrix((dd,(rr,cc)),shape=(n,n));travel,predecessor=dijkstra(routegraph,directed=True,return_predecessors=True)
                travel[travel>ms['maximum_move_days_per_bin']]=np.inf;np.fill_diagonal(travel,0)
                monthly=forage[:,rows,cols]*area[rows,cols]
                patchrecords=[dict(row=int(y),column=int(x),x=float((x+.5)*meta['width']/w),y=float((y+.5)*meta['height']/h),
                    land_area_km2=float(area[y,x]),water_distance_km=float(geo['water_distance'][y,x]),monthly_dm_kg=monthly[:,i].tolist()) for i,(y,x) in enumerate(zip(rows,cols))]
                cases=[];daily=ms['reference_feed_units']*ms['intake_kg_dm_reference_unit_day']
                for wc in ms['water_scenarios']:
                    threshold=wc['maximum_mapped_water_distance_km'];allowed=np.ones(n,bool) if threshold is None else geo['water_distance'][rows,cols]<=threshold
                    kwargs=dict(daily_need=daily,reserve_days=ms['reserve_days'],reserve_quantum_days=ms['reserve_quantum_days'],year_days=spec['year_days'])
                    mobile=seasonal_circuit(monthly,travel,home,allowed=allowed,**kwargs)
                    stationary=seasonal_circuit(monthly[:,home,None],np.zeros((1,1)),0,allowed=np.array([allowed[home]]),**kwargs)
                    fixed=periodic_food_year(monthly,np.full_like(monthly,daily*spec['year_days']/12),daily*ms['reserve_days'],step_days=spec['year_days']/12)
                    fixed_met=np.where(allowed,1-fixed.unmet/(daily*spec['year_days']),-1)
                    fixed_i=int(np.argmax(fixed_met)) if allowed.any() else None
                    def encode(circuit,stationary=False):
                        if circuit is None:return None
                        record={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in asdict(circuit).items()}
                        if stationary:record['locations']=[home]*12
                        previous=home;segments=[]
                        for destination in record['locations']:
                            path=[int(destination)]
                            while path[-1]!=previous:
                                p=int(predecessor[previous,path[-1]])
                                if p<0 or len(path)>n:raise ValueError('Missing physical circuit path')
                                path.append(p)
                            segments.append(path[::-1]);previous=destination
                        record['segments']=segments
                        record.update(annual_need_met=float(circuit.consumed.sum()/(daily*spec['year_days'])),
                            shortage_bins=int(np.sum(circuit.unmet>1e-8*daily)),moves=int(np.sum(circuit.travel_days>0)),total_travel_days=float(circuit.travel_days.sum()))
                        return record
                    if mobile is not None and stationary is not None and mobile.objective_unmet>stationary.objective_unmet+1e-6:raise ValueError('Mobility excluded the stationary control')
                    cases.append(dict(**wc,status='conditional_circuit' if mobile is not None else 'home_excluded_by_water_scenario',mobile=encode(mobile),stationary=encode(stationary,True),
                        best_fixed_base_continuous=dict(patch=fixed_i,annual_need_met=float(fixed_met[fixed_i])) if fixed_i is not None else None))
                experiments.append(dict(id=pilot['id'],label=pilot['label'],map_claim=pilot['map_claim'],home=home,status='scored_resource_landscape',patches=patchrecords,
                    ground_edges=[[int(a),int(b),float(d)] for a,b,d in zip(rr,cc,dd)],cases=cases))
            regional=regional_experiments(pilots,z,land,resolved,forage,area,geo['water_distance'],meta,spec)
            payload=dict(version=2,atlas=name,climate=mode,sites=sites,presence=variants,mobility=experiments,mobility_scales=regional,
                specification=spec,balances=balances,shape=list(shape),cell_px=meta['width']/w)
            payloadpath.write_bytes(gzip.compress(json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode(),mtime=0))
            # One map button per mechanism; details in the scenario panel.
            palette=['#914d55','#b47c64','#d2af79','#ced3a4','#83ae98','#287877'];labels=['<25% of need','25–50%','50–75%','75–90%','90–99.9%','All bins supplied']
            items=[dict(color=c,label=l) for c,l in zip(palette,labels)]
            images={};options=[]
            for case in variants:
                value=np.array([s['worst_bin_need_met'] for s in case['sites']]);rgb=np.empty((*shape,3));rgb[:]=to_rgb('#b7b4ae');rgb[~land]=[.84,.89,.94]
                codes=np.searchsorted([.25,.5,.75,.9,1-1e-8],value);selected=assignment>0
                rgb[selected]=np.array([to_rgb(c) for c in palette])[codes[assignment[selected]-1]]
                filename='presence_'+case['id']+'.webp';Image.fromarray(np.rint(rgb*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST).save(folder/filename,lossless=True)
                images[prefix+filename]=file_hash(folder/filename)
                options.append(dict(value=case['id'],label=case['label'],file=prefix+filename,items=items+[dict(color='#b7b4ae',label='Outside fixed collection areas / unscored')],
                    caption='Worst-bin food need met at the receiving marked site; its fixed collection area shares that site colour. These are not control polygons.',
                    note=spec['scope']+' Single wheat/barley crop, rural meals protected before collection; no rice, millet, dates, second crop, animals, fish or external imports. Grey does not mean empty or uninhabitable.'))
            layers=[dict(id='presence_food',label='Sustained presence',group='Political reach',kind='categories',controls=[],file=options[0]['file'],items=options[0]['items'],note=options[0]['note'],
                variants=dict(label='Provisioning scenario',default='stores90',options=options))]
            mobility_options=[]
            for view,label in [('circuits','Closed resource circuits'),('water','Water sensitivity')]:
                scale_files={};scale_water_files={}
                for scale,examples in [('local',experiments),*regional.items()]:
                    scale_water_files[scale]={}
                    for wc in ms['water_scenarios']:
                        if view=='water' and wc['id']!='water_unknown':
                            scale_water_files[scale][wc['id']]=scale_files[scale];continue
                        rgb=np.empty((*shape,3));rgb[:]=to_rgb('#b7b4ae');rgb[~land]=[.84,.89,.94]
                        for experiment in examples:
                            if experiment['status']!='scored_resource_landscape':continue
                            pp=experiment['patches'];values=np.array([p['water_distance_km'] for p in pp]);colors=['#286f70','#9eb599','#d0b27b','#a36a59']
                            if view=='circuits':
                                case=next(c for c in experiment['cases'] if c['id']==wc['id'])
                                if case['mobile'] is None:continue
                                counts=np.bincount(case['mobile']['locations'],minlength=len(pp));values=counts;bounds=[.5,3.5,8.5];colors=['#e5decd','#afc6ad','#5d9c8e','#285f72']
                            else:bounds=[10,25,50]
                            for p,c in zip(pp,np.searchsorted(bounds,values)):rgb[p['row'],p['column']]=to_rgb(colors[c])
                        filename='mobility_'+('' if scale=='local' else scale+'_')+('' if wc['id']=='water_unknown' else wc['id']+'_')+view+'.webp'
                        Image.fromarray(np.rint(rgb*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST).save(folder/filename,lossless=True)
                        images[prefix+filename]=file_hash(folder/filename);scale_water_files[scale][wc['id']]=prefix+filename
                        if wc['id']=='water_unknown':scale_files[scale]=prefix+filename
                labels2=['Not visited','1–3 bins','4–8 bins','9–12 bins'] if view=='circuits' else ['≤10 km','10–25 km','25–50 km','>50 km']
                mobility_options.append(dict(value=view,label=label,file=scale_files['local'],scale_files=scale_files,scale_water_files=scale_water_files,items=[dict(color=c,label=l) for c,l in zip(colors,labels2)]+[dict(color='#b7b4ae',label='Outside sampled resource patches / unscored')],
                    caption='Four fixed resource landscapes only. Select a landscape below for its closed seasonal route and feed ledger.',
                    note='One unsplit herd of 100 dry-matter reference units; 7-day carried feed, actual transit meals before arrival, no free initial stock. Fresh growth at the selected destination is used once; unused growth expires. Water distances do not establish potable volume, permanence or access rights. Scenarios run independently; they are not jointly allocated herds or predicted communities.'))
            layers.append(dict(id='mobility_circuits',label='Seasonal circuits',group='Livelihoods',kind='categories',controls=[],file=mobility_options[0]['file'],items=mobility_options[0]['items'],note=mobility_options[0]['note'],
                variants=dict(label='Mobility view',default='circuits',options=mobility_options)))
            packet=dict(layers=layers,shape=list(shape),cell_px=meta['width']/w,
                scales=[dict(id='local',label='Local · all bases'),*ms['regional_scales']],
                payload=prefix+payloadpath.name,payload_sha256=file_hash(payloadpath),catchments=prefix+gridpath.name,catchments_sha256=file_hash(gridpath),
                image_sha256=images,
                expected_harvest_fingerprint=meta['harvest']['fingerprint'],expected_harvest_binary_sha256=file_hash(folder/'harvest.bin'))
            summary=dict(marked_sources=len(sites),affiliation_unresolved=sum(s['actor'] is None for s in sites),
                collection_land_cells=int(np.sum(assignment>0)),collection_area_km2=float(area[assignment>0].sum()),
                fully_supplied_sites={v['id']:sum(s['shortfall_bins']==0 for s in v['sites']) for v in variants},
                maximum_combined_ledger_relative_residual=max(abs(b['combined_ledger_residual'])/max(1,b['harvested']) for b in balances.values()),
                regional_circuits={k:[dict(id=e['id'],bases=len(e['patches']),ground_cells=len(e['ground_nodes']),
                    mobile=e['cases'][0]['mobile']['annual_need_met'],fixed=e['cases'][0]['best_fixed_base_continuous']['annual_need_met'],
                    resource_upper_bound=e['cases'][0]['resource_upper_bound']['annual_need_met']) for e in values] for k,values in regional.items()},
                circuits=[dict(id=e['id'],cases=[dict(water=c['id'],status=c['status'],mobile=c['mobile']['annual_need_met'] if c['mobile'] else None,stationary=c['stationary']['annual_need_met'] if c['stationary'] else None) for c in e.get('cases',[])]) for e in experiments])
            public={prefix+payloadpath.name:file_hash(payloadpath),prefix+gridpath.name:file_hash(gridpath),**images}
            write_json(reviewpath,dict(status='complete',inputs_sha256=inputs,sources_sha256=sources,public_sha256=public,packet=packet,summary=summary))
            packets[mode]=packet;reviews.append(dict(atlas=name,climate=mode,summary=summary,review_sha256=file_hash(reviewpath)))
            print(name,mode,summary,flush=True)
        write_json(data/'presence_mobility.json',dict(version=1,status='conditional_food_and_resource_circuits',specification=spec,packets=packets,sources_sha256=sources))
    if any(file_hash(ROOT/p)!=h for p,h in {**sources,**allinputs}.items()):raise ValueError('Frozen source/input changed during build')
    write_json(origin/'review.json',dict(status='complete',packets=reviews,sources_sha256=sources,existing_climate_population_ownership_unchanged=True))


if __name__=='__main__':main()
