"""Finite local cereal support feeds settlement allocation and actor-source reach.

Isolated scenario. Does not retrain climate, fit town sizes, or infer sovereignty.
"""
from pathlib import Path
import csv
import gzip
import json
import sys
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from atlas_set import active  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)


def candidates(r,registry,shape,cell_px,market_rows):
    import numpy as np
    from scipy.optimize import linear_sum_assignment
    from polity import fields as F
    raw=F.settlements(shape)
    records=[v for v in registry['records'] if v.get('symbol_verified') and 'node' in v]
    marked=[v for v in r['towns'] if 'x_px' in v]
    if len(raw)!=len(records) or len(marked)!=len(raw):raise ValueError('Marked inventory is not bijective')
    distance=np.array([[np.hypot(t['col']-s['x']/cell_px,t['row']-s['y']/cell_px) if t['kind']==s['kind'] else 1e6 for s in records] for t in raw])
    rows,cols=linear_sum_assignment(distance)
    if np.max(distance[rows,cols])>2:raise ValueError('Marked evidence exceeds two-cell join tolerance')
    joined={}
    for i,j in zip(rows,cols):
        t=raw[i];matches=[v for v in marked if v['kind']==t['kind'] and v['x_px']==t['x_px'] and v['y_px']==t['y_px']]
        if len(matches)!=1:raise ValueError('Ambiguous marked component')
        # Require a unique compatible nearby registry item, not a fuzzy name.
        if np.sum(distance[i]<=2)!=1:raise ValueError('Ambiguous evidence location')
        node=matches[0]['row']*shape[1]+matches[0]['col']
        joined.setdefault(node,[]).append(dict(records[j],join_distance_cells=float(distance[i,j])))
    market={}
    for row in market_rows:
        node=int(row['row'])*shape[1]+int(row['col'])
        v=market.setdefault(node,dict(market_ids=[],served_people=0.))
        v['market_ids'].append(int(row['market_id']));v['served_people']+=float(row['inbound_catchment_people'])
    if set(market)!={t['row']*shape[1]+t['col'] for t in r['towns']}:raise ValueError('Published market candidate geography changed')
    _,info=F.polity_fills(shape)
    names=sorted({v['name'].split(' (')[0] for v in info.values() if v['name']})
    actors=[dict(name=n,color=next(v['hex'] for v in info.values() if v['name'] and v['name'].split(' (')[0]==n)) for n in names]
    sites=[]
    for node,v in sorted(market.items()):
        evidence=joined.get(node,[]);known={e['actor'] for e in evidence if e.get('actor')}
        claim=int(r['claim'].ravel()[node]);painted=names[claim] if claim>=0 else None
        actor=next(iter(known)) if len(known)==1 else None
        if evidence:basis='marked evidence' if actor else 'marked affiliation unresolved or conflicting'
        else:actor=painted;basis='generated-site painted-claim hypothesis' if actor else 'unresolved'
        sites.append(dict(id='node_'+str(node),node=node,row=node//shape[1],column=node%shape[1],
            name=' / '.join(e['name'] for e in evidence) if evidence else 'Proposed site '+str(node),
            actor=actor,actor_index=names.index(actor) if actor in names else -1,affiliation_basis=basis,
            painted_claim=painted,marked=bool(evidence),evidence_ids=[e['id'] for e in evidence],
            join_distance_cells=[e['join_distance_cells'] for e in evidence],**v))
    return sites,actors


def main():
    import numpy as np
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    from polity.administrative_world import audit_world
    from polity.administrative_hierarchy import month_graph
    from polity import control as C,seasons as S
    from polity.sustained_presence import rural_cereal,fixed_path_days,stored_collection
    from polity.settlement_support import allocate_settlement,paired_reach
    from harvest.export import geometry
    from population.export import decode_harvest
    from land_people import FARMED_SHARE,FALLOW
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/settlement_integration_20261104';origin.mkdir(exist_ok=True)
    spec=json.loads((ROOT/'data/settlement_integration_model.json').read_text())
    sourcepaths=['scripts/review_settlement_integration.py','polity/settlement_support.py','data/settlement_integration_model.json',
        'polity/administrative_world.py','polity/economic_world.py','polity/administrative_hierarchy.py','polity/fields.py',
        'polity/control.py','polity/seasons.py','polity/network.py','polity/transport.py','polity/settle.py','polity/sustained_presence.py',
        'harvest/food_stocks.py','harvest/export.py','population/export.py','scripts/land_people.py',
        'data/source/elevation.png','data/source/rivers.png','data/source/original/rivers.png','data/source/ravages_v8/roads.png',
        'data/source/ravages_v8/settlements.png','data/source/ravages_v8/borders_fill.png','data/source/ravages_v8/polities.json']
    sourcepaths+=['rotclimate/geography.py','polity/trade.py','polity/inventory.py'] if (ROOT/'polity/inventory.py').exists() else ['rotclimate/geography.py','polity/trade.py']
    sources={p:file_hash(ROOT/p) for p in sourcepaths}
    reviews=[]
    for name in active(['free_fit','earth_fit','whittaker_fit']):
        data=ROOT/'atlases'/name/'data';original=json.loads((data/'atlas.json').read_text())
        for mode in ['raw']+(['corrected'] if original.get('corrected_climate') else []):
            folder=data/('corrected' if mode=='corrected' else '');out=origin/(name+'_'+mode);out.mkdir(exist_ok=True)
            paths=[data/'atlas.json',data/'winds12.npz',folder/'atlas.bin',folder/'harvest.json',folder/'harvest.bin',folder/'farm_work_grid.npz',folder/'coverage_sources.json',folder/'market_hinterlands.csv']
            inputs={str(p.relative_to(ROOT)):file_hash(p) for p in paths}
            reviewpath=out/'review.json'
            if reviewpath.exists():
                old=json.loads(reviewpath.read_text())
                if old['sources_sha256']==sources and old['inputs_sha256']==inputs and all(file_hash(out/p)==h for p,h in old['artifacts_sha256'].items()):
                    reviews.append(old['summary']);print('Reused',name,mode,flush=True);continue
            print('Preparing',name,mode,flush=True);r,meta=audit_world(data.parent,mode)
            shape=r['land'].shape;h,w=shape;cell_px=meta['width']/w
            with (folder/'market_hinterlands.csv').open() as f:market=list(csv.DictReader(f))
            sites,actors=candidates(r,json.loads((folder/'coverage_sources.json').read_text()),shape,cell_px,market)
            nodes=np.array([s['node'] for s in sites]);actoridx=np.array([s['actor_index'] for s in sites]);n=len(sites)
            for s in sites:s['civilian_request_people']=max(spec['minimum_civilian_request_people'],spec['civilian_request_share_of_served_people']*s['served_people'])
            request=np.array([s['civilian_request_people'] for s in sites]);affiliated=actoridx>=0
            z=r['elev'];land=r['land'];st=r['statics'];cl=r['climate'];road=r['world']['road']
            def collection_graph(m):
                cross=np.where(st['basin']>0,S.CROSS_DAYS*(1+S.FLOOD_GAIN*S.flood_index(cl['flow'][m][st['basin']])),0.)
                a,b,d=C.foot_edges(z,land,road,S.month_terrain(st['eta'],cl,m),r['cell_km'],np.full(shape,C.OFF_PATH),road_factor=1+(S.MUD_ROAD-1)*cl['mud'][m],cross=cross)
                return csr_matrix((d,(a,b)),shape=(land.size,land.size))
            base=collection_graph(spec['collection_base_bin'])
            days,parent,source=dijkstra(base.T.tocsr(),indices=nodes,min_only=True,return_predecessors=True,directed=True)
            parent[nodes]=nodes;lookup=np.zeros(land.size,np.uint16);lookup[nodes]=np.arange(1,n+1)
            valid=land.ravel()&np.isfinite(days)&(days<=spec['collection_maximum_days_each_way'])
            assignment=np.zeros(land.size,np.uint16);assignment[valid]=lookup[source[valid]]
            order=np.flatnonzero(valid&(parent!=np.arange(land.size)));order=order[np.argsort(days[order])]
            access=np.zeros((12,land.size),bool)
            for m in range(12):
                g=base if m==spec['collection_base_bin'] else collection_graph(m)
                outward,inward=fixed_path_days(g,parent,order)
                access[m]=valid&(outward<=spec['collection_maximum_days_each_way'])&(inward<=spec['collection_maximum_days_each_way'])
            del base,g
            hm,hf=decode_harvest(folder);geo,_=geometry(meta,shape);area=geo['land_fraction']*r['cell_km']**2
            with np.load(folder/'farm_work_grid.npz') as crops:crop=crops['cereal'];bits=crops['harvest_boundaries']
            kcal=np.where(crop==1,hf['kcal_wheat'],np.where(crop==2,hf['kcal_barley'],0))
            annual=np.where(land,kcal*100*area*hf['arable']*FARMED_SHARE*FALLOW,0).ravel();idx=np.flatnonzero(annual>0)
            rr=rural_cereal(annual[idx],bits.ravel()[idx],demand_fraction=spec['rural_demand_fraction_of_cereal_production'],reserve_days=spec['rural_store_demand_days'],loss_fraction_year=spec['annual_stored_energy_loss_fraction'],calendar='first')
            available=rr.exportable
            rural=dict(harvested_kcal=float(rr.harvest.sum()),consumed_kcal=float(rr.year.consumed.sum()),storage_loss_kcal=float(rr.year.spoiled.sum()),unmet_kcal=float(rr.year.unmet.sum()),overflow_kcal=float(rr.year.overflow.sum()),max_ledger_residual=float(np.max(abs(rr.year.ledger_residual))))
            # Finite nonbinding cargo ceiling, not measured transport throughput.
            freight=np.bincount(assignment[idx],weights=available.sum(0),minlength=n+1)[1:]
            cases=[dict(id='reference',label='Transport-matched reference · food unconstrained',food_constrained=False,
                civilian_people=request.tolist(),institutional_people=np.where(affiliated,spec['institutional_request_people'],0).tolist(),institutional_active=affiliated.tolist(),community_viable=[True]*n)]
            active=[affiliated]
            for c in spec['cases']:
                flow=stored_collection(available,assignment[idx],access[:,idx],n,collection_fraction=c['collection_fraction'],freight_capacity=freight,
                    retention=spec['delivery_retention'],delay_bins=spec['delivery_delay_bins'],store_days=c['origin_store_flow_days'],loss_fraction_year=spec['annual_stored_energy_loss_fraction'])
                p=allocate_settlement(flow['arrivals'],request,affiliated,institutional_request=c.get('institutional_request_people',spec['institutional_request_people']),minimum_community=spec['minimum_community_people'],kcal_day=spec['ration_kcal_person_day'],store_days=spec['destination_store_demand_days'],loss_fraction_year=spec['annual_stored_energy_loss_fraction'])
                year=p.food_year;uncollected=rural['overflow_kcal']-float(flow['departures'].sum())-flow['collection_storage_loss']
                residual=rural['harvested_kcal']-rural['consumed_kcal']-rural['storage_loss_kcal']-uncollected-flow['collection_storage_loss']-flow['transport_loss']-float(year.consumed.sum()+year.spoiled.sum()+year.overflow.sum())
                if abs(residual)>1e-7*max(1,rural['harvested_kcal']):raise RuntimeError('Joint grain ledger does not close')
                ledger=dict(uncollected_kcal=uncollected,origin_loss_kcal=flow['collection_storage_loss'],transport_loss_kcal=flow['transport_loss'],resident_consumed_kcal=float(year.consumed.sum()),destination_loss_kcal=float(year.spoiled.sum()),destination_unused_kcal=float(year.overflow.sum()),joint_residual_kcal=residual,origin_max_residual_kcal=flow['max_collection_ledger_residual'],destination_max_residual_kcal=float(np.max(abs(year.ledger_residual))))
                cases.append(dict(**c,food_constrained=True,food_ceiling_people=p.food_ceiling_people.tolist(),civilian_people=p.civilian_people.tolist(),institutional_people=p.institutional_people.tolist(),institutional_active=p.institutional_active.tolist(),community_viable=p.community_viable.tolist(),monthly_arrivals_kcal=flow['arrivals'].T.tolist(),monthly_need_kcal=(np.broadcast_to(p.total_people*2500*365/12,(12,n))).T.tolist(),stock_path_kcal=year.stock_path.T.tolist(),ledger=ledger))
                active.append(p.institutional_active);print(name,mode,c['id'],'communities',p.community_viable.sum(),'staffed',p.institutional_active.sum(),flush=True)
            del rr,available,access,hf,flow
            landnodes=np.flatnonzero(land);nland=len(landnodes);masks=np.zeros((len(cases),len(actors),nland),np.uint16)
            # A source has the same travel footprint across all cases. Only
            # the resident cohort's feasibility changes whether it emits reach.
            use=np.flatnonzero(affiliated)
            for m in range(12):
                g,_=month_graph(r['world'],st,cl,m,r['ports'],r['river_places']);reverse=g.T.tocsr()
                def reach(j):
                    outward=dijkstra(g,directed=True,indices=int(nodes[j]),limit=spec['patrol_days_each_leg'])[landnodes]
                    inward=dijkstra(reverse,directed=True,indices=int(nodes[j]),limit=spec['patrol_days_each_leg'])[landnodes]
                    return j,np.flatnonzero(paired_reach(outward,inward,leg_days=spec['patrol_days_each_leg'],ration_days=spec['patrol_ration_days']))
                with ThreadPoolExecutor(max_workers=4) as pool:
                    for j,covered in pool.map(reach,use):
                        a=actoridx[j]
                        for c in range(len(cases)):
                            if active[c][j]:masks[c,a,covered]|=1<<m
                print(name,mode,'paired reach bin',m+1,flush=True)
            full_lookup=np.zeros(land.size,np.uint32);full_lookup[landnodes]=np.arange(1,nland+1)
            raw=full_lookup.astype('<u4').tobytes()+assignment.astype('<u2').tobytes()+masks.astype('<u2').tobytes()
            binary=out/'settled_reach.bin.gz';binary.write_bytes(gzip.compress(raw,mtime=0));del raw
            pop=np.array([i.bit_count() for i in range(4096)],np.uint8)
            summaries=[];weights=area.ravel()[landnodes]
            for k,c in enumerate(cases):
                union=np.bitwise_or.reduce(masks[k],axis=0);bins=pop[union]
                actor_summary=[]
                for a,actor in enumerate(actors):
                    actor_summary.append(dict(actor=actor['name'],active_sources=int(np.sum(active[k]&(actoridx==a))),candidate_sources=int(np.sum(actoridx==a)),inventory_scored=bool(np.any(actoridx==a)),all_bin_area_km2=float(weights[pop[masks[k,a]]==12].sum())))
                summaries.append(dict(id=c['id'],civilian_people=float(np.sum(c['civilian_people'])),institutional_people=float(np.sum(c['institutional_people'])),viable_communities=int(np.sum(c['community_viable'])),active_sources=int(np.sum(active[k])),all_bin_any_actor_area_km2=float(weights[bins==12].sum()),any_bin_area_km2=float(weights[bins>0].sum()),area_weighted_access_bins=float(np.sum(weights*bins)/weights.sum()),actors=actor_summary))
            model=dict(version=1,atlas=name,climate=mode,shape=list(shape),specification=spec,sites=sites,actors=actors,cases=cases,rural_ledger=rural,summaries=summaries)
            payload=out/'settled_reach.json.gz';payload.write_bytes(gzip.compress(json.dumps(model,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0))
            summary=dict(atlas=name,climate=mode,candidate_sites=n,merged_market_rows=len(market)-n,marked_sites=sum(s['marked'] for s in sites),unaffiliated_sites=int(np.sum(~affiliated)),cases=summaries)
            write_json(reviewpath,dict(version=1,inputs_sha256=inputs,sources_sha256=sources,artifacts_sha256={p.name:file_hash(p) for p in [binary,payload]},shape=list(shape),cell_px=cell_px,land_cells=nland,masks_shape=list(masks.shape),offsets=dict(catchments=land.size*4,masks=land.size*6),raw_bytes=land.size*6+masks.nbytes,expected_harvest_fingerprint=meta['harvest']['fingerprint'],summary=summary))
            reviews.append(summary)
    write_json(origin/'summary.json',dict(status='computed',reviews=reviews))


if __name__=='__main__':main()
