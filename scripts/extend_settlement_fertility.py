"""Feed the soil-fertility factor into the existing food → settlement → source chain.

Retain all nine earlier cases exactly (six integration + three work cases), including
their actor masks. New fertility cases share the year-store case's transport, calendar,
dispatch and fixed rural need; only cereal production changes (annual x F per cell,
data/settlement_fertility_model.json, factors from scripts/fertility_integration.py maps).
"""
from pathlib import Path
import gzip
import json
import sys
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from polity.administrative_world import audit_world
    from polity.administrative_hierarchy import month_graph
    from polity import control as C,seasons as S
    from polity.sustained_presence import fixed_path_days,stored_collection
    from polity.settlement_support import allocate_settlement,paired_reach
    from harvest.field_support import fixed_rural_food
    from harvest.export import geometry
    from population.export import decode_harvest
    from land_people import FARMED_SHARE,FALLOW
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/settlement_fertility_20261106';origin.mkdir(exist_ok=True)
    baseline=ROOT/'output/settlement_labour_20261105';ls=json.loads((ROOT/'data/settlement_fertility_model.json').read_text());reviews=[]
    factors_dir=ROOT/'output/fertility_integration_20261106'
    new_sources=['scripts/extend_settlement_fertility.py','harvest/field_support.py','data/settlement_fertility_model.json','harvest/fertility_regimes.py','harvest/soil_fertility.py','scripts/fertility_integration.py','output/soil_fertility_round2_20261106/selection.json','output/fertility_integration_20261106/earth_census.json']
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';original=json.loads((data/'atlas.json').read_text())
        for mode in ['raw']+(['corrected'] if original.get('corrected_climate') else []):
            folder=data/('corrected' if mode=='corrected' else '');old=baseline/(name+'_'+mode);out=origin/(name+'_'+mode);out.mkdir(exist_ok=True)
            br=json.loads((old/'review.json').read_text())
            for p,h in {**br['sources_sha256'],**br['inputs_sha256']}.items():
                if file_hash(ROOT/p)!=h:raise ValueError('Baseline source changed: '+p)
            for p,h in br['artifacts_sha256'].items():
                if file_hash(old/p)!=h:raise ValueError('Baseline artifact changed: '+p)
            sources={**br['sources_sha256'],**{p:file_hash(ROOT/p) for p in new_sources}}
            fpath=factors_dir/(name+'_'+mode+'_factors.npz')
            inputs={**br['inputs_sha256'],str((old/'review.json').relative_to(ROOT)):file_hash(old/'review.json'),str((old/'settled_reach.json.gz').relative_to(ROOT)):file_hash(old/'settled_reach.json.gz'),str((old/'settled_reach.bin.gz').relative_to(ROOT)):file_hash(old/'settled_reach.bin.gz'),str(fpath.relative_to(ROOT)):file_hash(fpath)}
            rp=out/'review.json'
            if rp.exists():
                review=json.loads(rp.read_text())
                if review['sources_sha256']==sources and review['inputs_sha256']==inputs and all((out/p).exists() and file_hash(out/p)==h for p,h in review['artifacts_sha256'].items()):reviews.append(review['summary']);print('Reused',name,mode,flush=True);continue
            print('Preparing fertility',name,mode,flush=True)
            model=json.loads(gzip.decompress((old/'settled_reach.json.gz').read_bytes()));spec=model['specification'];sites=model['sites'];actors=model['actors'];n=len(sites)
            r,meta=audit_world(data.parent,mode);land=r['land'];shape=land.shape;h,w=shape;st=r['statics'];cl=r['climate'];z=r['elev'];road=r['world']['road']
            nodes=np.array([s['node'] for s in sites]);actoridx=np.array([s['actor_index'] for s in sites]);affiliated=actoridx>=0
            if set(nodes)!={t['row']*w+t['col'] for t in r['towns']}:raise ValueError('Candidate transport geography differs')
            raw=gzip.decompress((old/'settled_reach.bin.gz').read_bytes());oldlookup=np.frombuffer(raw,'<u4',count=land.size);oldassign=np.frombuffer(raw,'<u2',count=land.size,offset=br['offsets']['catchments']);oldmasks=np.frombuffer(raw,'<u2',offset=br['offsets']['masks']).reshape(br['masks_shape'])
            def graph(m):
                cross=np.where(st['basin']>0,S.CROSS_DAYS*(1+S.FLOOD_GAIN*S.flood_index(cl['flow'][m][st['basin']])),0.)
                a,b,d=C.foot_edges(z,land,road,S.month_terrain(st['eta'],cl,m),r['cell_km'],np.full(shape,C.OFF_PATH),road_factor=1+(S.MUD_ROAD-1)*cl['mud'][m],cross=cross)
                return csr_matrix((d,(a,b)),shape=(land.size,land.size))
            base=graph(spec['collection_base_bin']);days,parent,source=dijkstra(base.T.tocsr(),indices=nodes,min_only=True,return_predecessors=True,directed=True)
            parent[nodes]=nodes;lookup=np.zeros(land.size,np.uint16);lookup[nodes]=np.arange(1,n+1)
            valid=land.ravel()&np.isfinite(days)&(days<=spec['collection_maximum_days_each_way']);assignment=np.zeros(land.size,np.uint16);assignment[valid]=lookup[source[valid]]
            if not np.array_equal(assignment,oldassign):raise ValueError('Food collection partition changed')
            order=np.flatnonzero(valid&(parent!=np.arange(land.size)));order=order[np.argsort(days[order])];access=np.zeros((12,land.size),bool)
            for month in range(12):
                g=base if month==spec['collection_base_bin'] else graph(month);outward,inward=fixed_path_days(g,parent,order)
                access[month]=valid&(outward<=spec['collection_maximum_days_each_way'])&(inward<=spec['collection_maximum_days_each_way'])
            del base,g
            hm,hf=decode_harvest(folder);geo,_=geometry(meta,shape);area=geo['land_fraction']*r['cell_km']**2
            with np.load(folder/'farm_work_grid.npz') as crops:
                crop=crops['cereal'];bits=crops['harvest_boundaries']
            with np.load(fpath) as fz:fgrids={k:np.nan_to_num(fz[k],nan=1.).astype(float).ravel() for k in fz.files if k.startswith('F_')};transfer_t_ha=float(fz['transfer_t_ha'])
            kcal=np.where(crop==1,hf['kcal_wheat'],np.where(crop==2,hf['kcal_barley'],0));annual=np.where(land,kcal*100*area*hf['arable']*FARMED_SHARE*FALLOW,0).ravel();idx=np.flatnonzero(annual>0)
            fixed_need=annual[idx]*spec['rural_demand_fraction_of_cereal_production'];request=np.array([s['civilian_request_people'] for s in sites]);new_cases=[];active=[];cell_fields={}
            for c in ls['cases']:
                F=fgrids[c['factor']][idx];produced=annual[idx]*F
                rr=fixed_rural_food(produced,bits.ravel()[idx],fixed_need,reserve_days=spec['rural_store_demand_days'],loss_fraction_year=spec['annual_stored_energy_loss_fraction'],year_days=spec['year_days'])
                available=rr.exportable;freight=np.bincount(assignment[idx],weights=available.sum(0),minlength=n+1)[1:]
                flow=stored_collection(available,assignment[idx],access[:,idx],n,collection_fraction=.1,freight_capacity=freight,retention=spec['delivery_retention'],delay_bins=spec['delivery_delay_bins'],store_days=365.,loss_fraction_year=spec['annual_stored_energy_loss_fraction'],year_days=spec['year_days'])
                p=allocate_settlement(flow['arrivals'],request,affiliated,institutional_request=spec['institutional_request_people'],minimum_community=spec['minimum_community_people'],kcal_day=spec['ration_kcal_person_day'],store_days=spec['destination_store_demand_days'],loss_fraction_year=spec['annual_stored_energy_loss_fraction'],year_days=spec['year_days']);year=p.food_year
                rural=dict(harvested_kcal=float(rr.harvest.sum()),fixed_need_kcal=float(fixed_need.sum()),consumed_kcal=float(rr.year.consumed.sum()),storage_loss_kcal=float(rr.year.spoiled.sum()),unmet_kcal=float(rr.year.unmet.sum()),overflow_kcal=float(rr.year.overflow.sum()),max_ledger_residual=float(np.max(abs(rr.year.ledger_residual))))
                uncollected=rural['overflow_kcal']-float(flow['departures'].sum())-flow['collection_storage_loss'];residual=rural['harvested_kcal']-rural['consumed_kcal']-rural['storage_loss_kcal']-uncollected-flow['collection_storage_loss']-flow['transport_loss']-float(year.consumed.sum()+year.spoiled.sum()+year.overflow.sum())
                if abs(residual)>1e-7*max(1,rural['harvested_kcal']):raise ValueError('Fertility-food ledger does not close')
                ledger=dict(uncollected_kcal=uncollected,origin_loss_kcal=flow['collection_storage_loss'],transport_loss_kcal=flow['transport_loss'],resident_consumed_kcal=float(year.consumed.sum()),destination_loss_kcal=float(year.spoiled.sum()),destination_unused_kcal=float(year.overflow.sum()),joint_residual_kcal=residual,origin_max_residual_kcal=flow['max_collection_ledger_residual'],destination_max_residual_kcal=float(np.max(abs(year.ledger_residual))))
                fert_summary=dict(reference_production_kcal=float(annual[idx].sum()),produced_kcal=float(produced.sum()),production_ratio=float(produced.sum()/annual[idx].sum()),factor_median=float(np.median(F)),factor_p10=float(np.percentile(F,10)),factor_p90=float(np.percentile(F,90)),rural_deficit_cells=int(np.sum(rr.year.unmet>1e-8*np.maximum(rr.year.needed,1))))
                need=np.broadcast_to(p.total_people*spec['ration_kcal_person_day']*spec['year_days']/12,(12,n))
                new_cases.append(dict(**c,food_constrained=True,origin_store_flow_days=365.,collection_fraction=.1,labour_constrained=False,fertility_constrained=True,input_n_kg_ha_yr=ls['input_n_kg_ha_yr'],transfer_t_ha=transfer_t_ha if c['regime']=='transfer' else 0.,fertility_summary=fert_summary,rural_ledger=rural,food_ceiling_people=p.food_ceiling_people.tolist(),civilian_people=p.civilian_people.tolist(),institutional_people=p.institutional_people.tolist(),institutional_active=p.institutional_active.tolist(),community_viable=p.community_viable.tolist(),monthly_arrivals_kcal=flow['arrivals'].T.tolist(),monthly_need_kcal=need.T.tolist(),stock_path_kcal=year.stock_path.T.tolist(),ledger=ledger));active.append(p.institutional_active)
                cell_fields[c['id']+'_factor']=F;cell_fields[c['id']+'_produced_kcal']=produced
                cell_fields[c['id']+'_rural_unmet_kcal']=rr.year.unmet;cell_fields[c['id']+'_exportable_kcal']=available.sum(0)
                print(name,mode,c['id'],'production',round(fert_summary['production_ratio'],4),'staffed',p.institutional_active.sum(),flush=True)
            landnodes=np.flatnonzero(land);nland=len(landnodes);masks=np.zeros((len(new_cases),len(actors),nland),np.uint16);use=np.flatnonzero(np.logical_or.reduce(active))
            for month in range(12):
                g,_=month_graph(r['world'],st,cl,month,r['ports'],r['river_places']);reverse=g.T.tocsr()
                def reach(j):
                    outward=dijkstra(g,directed=True,indices=int(nodes[j]),limit=spec['patrol_days_each_leg'])[landnodes];inward=dijkstra(reverse,directed=True,indices=int(nodes[j]),limit=spec['patrol_days_each_leg'])[landnodes]
                    return j,np.flatnonzero(paired_reach(outward,inward,leg_days=spec['patrol_days_each_leg'],ration_days=spec['patrol_ration_days']))
                with ThreadPoolExecutor(max_workers=4) as pool:
                    for j,covered in pool.map(reach,use):
                        for k in range(len(new_cases)):
                            if active[k][j]:masks[k,actoridx[j],covered]|=1<<month
                print(name,mode,'fertility reach bin',month+1,flush=True)
            combined=np.concatenate([oldmasks,masks]);binary=out/'settled_reach.bin.gz';binary.write_bytes(gzip.compress(oldlookup.astype('<u4').tobytes()+oldassign.astype('<u2').tobytes()+combined.astype('<u2').tobytes(),mtime=0))
            pop=np.array([i.bit_count() for i in range(4096)],np.uint8);weights=area.ravel()[landnodes];summaries=[]
            for k,c in enumerate(new_cases):
                union=np.bitwise_or.reduce(masks[k],axis=0);bins=pop[union];actor_summary=[]
                for a,actor in enumerate(actors):actor_summary.append(dict(actor=actor['name'],active_sources=int(np.sum(active[k]&(actoridx==a))),candidate_sources=int(np.sum(actoridx==a)),inventory_scored=bool(np.any(actoridx==a)),all_bin_area_km2=float(weights[pop[masks[k,a]]==12].sum())))
                summaries.append(dict(id=c['id'],civilian_people=float(np.sum(c['civilian_people'])),institutional_people=float(np.sum(c['institutional_people'])),viable_communities=int(np.sum(c['community_viable'])),active_sources=int(np.sum(active[k])),all_bin_any_actor_area_km2=float(weights[bins==12].sum()),any_bin_area_km2=float(weights[bins>0].sum()),area_weighted_access_bins=float(np.sum(weights*bins)/weights.sum()),actors=actor_summary))
            model['cases']+=new_cases;model['summaries']+=summaries;model['fertility_specification']=ls
            payload=out/'settled_reach.json.gz';payload.write_bytes(gzip.compress(json.dumps(model,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0))
            workgrid=out/'fertility_support.npz';np.savez_compressed(workgrid,cell_index=idx,reference_production_kcal=annual[idx],fixed_rural_need_kcal=fixed_need,**cell_fields)
            summary=dict(br['summary']);summary['cases']=model['summaries'];review=dict(br);review.update(inputs_sha256=inputs,sources_sha256=sources,artifacts_sha256={p.name:file_hash(p) for p in [binary,payload,workgrid]},masks_shape=list(combined.shape),raw_bytes=land.size*6+combined.nbytes,summary=summary)
            write_json(rp,review);reviews.append(summary)
    write_json(origin/'summary.json',dict(status='computed',reviews=reviews))


if __name__=='__main__':main()
