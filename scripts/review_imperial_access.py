"""Separate imperial source assumptions and seasonal reliability on all climates."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]

CASES=['recorded_centres','marked_places','proposed_towns','proposed_tracks','road_sources','forts_legions']


def main():
    import numpy as np
    from scipy import ndimage as ndi
    from harvest.export import geometry
    from population.export import decode_harvest
    from polity.administrative_world import audit_world
    from polity.seasonal_access import seasonal_access
    from polity import fields as F,network as N
    from local_benchmark_protocol import file_hash,write_json
    inventory_path=ROOT/'output/administrative_inventory_20261104/review.json'
    inventory=json.loads(inventory_path.read_text())
    for p,h in inventory['sources_sha256'].items():
        if file_hash(ROOT/p)!=h:raise ValueError('Inventory source changed: '+p)
    sources={p:file_hash(ROOT/p) for p in ['polity/administration.py','polity/administrative_world.py',
        'polity/seasonal_access.py','polity/economic_world.py','polity/fields.py','polity/control.py',
        'polity/network.py','polity/transport.py','polity/seasons.py','polity/settle.py','scripts/review_imperial_access.py']}
    out=ROOT/'output/imperial_access_20261104';out.mkdir(exist_ok=True)
    summaries=[];all_inputs={}
    for name in ['free_fit','earth_fit','whittaker_fit']:
        atlas=ROOT/'atlases'/name;original=json.loads((atlas/'data/atlas.json').read_text())
        modes=['raw']+(['corrected'] if original.get('corrected_climate') else [])
        for mode in modes:
            folder=out/(name+'_'+mode);folder.mkdir(exist_ok=True)
            data=atlas/'data';prefix='' if mode=='raw' else 'corrected/'
            paths=[data/'atlas.json',data/prefix/'atlas.bin',data/prefix/'harvest.json',data/prefix/'harvest.bin',data/'winds12.npz',inventory_path]
            inputs={str(p.relative_to(ROOT)):file_hash(p) for p in paths};all_inputs.update(inputs)
            print('Preparing',name,mode,flush=True)
            write_json(out/'status.json',dict(stage='preparing',atlas=name,climate=mode))
            r,meta=audit_world(atlas,mode);shape=r['land'].shape;h,w=shape
            ids,info=F.polity_fills(shape)
            imperial_ids=[i for i,d in info.items() if d['name'] and d['name'].split(' (')[0]=='Xšāça']
            claim=r['land']&np.isin(ids,imperial_ids)
            _,nearest=ndi.distance_transform_edt(~r['land'],return_indices=True)
            def snap(x,y):
                row=int(np.clip(y/meta['height']*h,0,h-1));col=int(np.clip(x/meta['width']*w,0,w-1))
                return int(nearest[0,row,col])*w+int(nearest[1,row,col])
            centres=set(snap(c['x'],c['y']) for c in inventory['commanderies'] if c['status']=='matched')
            marked=set(centres);forts=set()
            for m in inventory['markers']:
                if not m['symbol_verified']:continue
                node=snap(m['x'],m['y']);is_imperial=m['kind'].startswith('imperial') or m['kind']=='major imperial city'
                if claim.ravel()[node] or is_imperial:marked.add(node)
                if m['kind']=='imperial fort':forts.add(node)
            forts.update(snap(m['x'],m['y']) for m in inventory['legions'])
            proposed=set(t['row']*w+t['col'] for t in r['towns'] if 'x_px' not in t and claim[t['row'],t['col']])
            roads=set(np.flatnonzero((r['world']['road']&claim).ravel()).tolist())
            sets=[centres,marked,marked|proposed,marked|proposed,marked|proposed|roads,forts]
            source_nodes=[np.array(sorted(s),np.int64) for s in sets]
            monthly=np.full((6,12,h,w),np.inf,np.float32)
            world_without=dict(r['world'],tracks=np.zeros(shape,bool))
            for month in range(12):
                write_json(out/'status.json',dict(stage='routing',atlas=name,climate=mode,model_month=month+1))
                for tracks,cases in [(False,[0,1,2]),(True,[3,4,5])]:
                    world=r['world'] if tracks else world_without
                    net=N.month_network(world,r['statics'],r['climate'],month,r['ports'],r['river_places'])
                    for case in cases:monthly[case,month]=net.days(source_nodes[case]).reshape(shape)
                    del net
                # Source additions and added tracks must not worsen travel.
                for earlier,later in [(0,1),(1,2),(2,3),(3,4)]:
                    if np.any(monthly[later,month]>monthly[earlier,month]+1e-5):raise ValueError('An expanded source/track scenario worsened access')
                print(name,mode,'model month',month+1,flush=True)
            metrics=[seasonal_access(days,threshold=2.) for days in monthly]
            # A small declared seed ensemble; transport for the main audit
            # remains fixed within each scenario. Recurrence is not probability.
            geo,_=geometry(meta,shape);hm,hf=decode_harvest(data/prefix)
            marked_legacy=[(t['row'],t['col']) for t in r['towns'] if 'x_px' in t]
            recurrence=np.zeros(shape,np.uint8);ensemble=[]
            for seed in [1,2,3]:
                towns,_,_=F.place_towns(r['density'],r['land'],geo['water_distance'],r['world']['road'],r['elev'],r['cell_km'],marked_legacy,
                    allowed=r['land']&(ids>0),seed=seed,aridity=hf['aridity'],dry_water_km=F.map_dry_water_km())
                points=np.zeros(shape,bool)
                for y,x in towns:points[y,x]=True
                recurrence+=(ndi.distance_transform_edt(~points)*r['cell_km']<=10)&r['land']
                ensemble.append(dict(seed=seed,proposed_towns=len(towns),imperial_towns=sum(bool(claim[y,x]) for y,x in towns)))
            result=dict(status='isolated_imperial_access_scenarios',atlas=name,climate=mode,cases=CASES,
                shape=list(shape),cell_px=meta['width']/w,source_counts=dict(zip(CASES,map(len,source_nodes))),
                inventory_sha256=file_hash(inventory_path),matched_commanderies=inventory['matched_commanderies'],
                listed_commanderies=len(inventory['commanderies']),unresolved_commanderies=inventory['unresolved_commanderies'],
                harvest_fingerprint=meta['harvest']['fingerprint'],inputs_sha256=inputs,sources_sha256=sources,
                summaries={},ensemble=ensemble,
                scope='Imperial access scenarios, not political allegiance, military strength or new de facto ownership. Only confirmed commandery positions included. Same ports and river landings in all cases, including hypothetical proposed-town ports. Tracks isolated separately. Existing transport and painted imperial source filter reused; no independent border validation. Twelve equal climatological seasonal bins, not weather probabilities.')
            people=np.where(claim,r['density'],0.)
            for case,m in zip(CASES,metrics):
                result['summaries'][case]=dict(imperial_claim_cells=int(claim.sum()),
                    mean_months_in_claim=float(m.accessible_months[claim].mean()),
                    population_weighted_months=float(np.sum(m.accessible_months*people)/max(people.sum(),1e-9)),
                    twelve_month_claim_share=float(np.mean(m.accessible_months[claim]==12)),
                    annual_held_with_seasonal_isolation_cells=int(np.sum(claim&m.annual_threshold&(m.longest_isolation>0))))
            arrays=dict(land=r['land'],imperial_claim=claim,elev=r['elev'],density=r['density'],proposal_recurrence=recurrence,
                access_masks=np.stack([m.access_mask for m in metrics]),accessible_months=np.stack([m.accessible_months for m in metrics]),
                longest_isolation=np.stack([m.longest_isolation for m in metrics]),effective_days=np.stack([m.effective_days for m in metrics]),
                annual_threshold=np.stack([m.annual_threshold for m in metrics]))
            np.savez_compressed(folder/'fields.npz',**arrays)
            result['arrays_sha256']=file_hash(folder/'fields.npz');write_json(folder/'review.json',result)
            summaries.append(dict(atlas=name,climate=mode,review_sha256=file_hash(folder/'review.json'),summaries=result['summaries']))
    if any(file_hash(ROOT/p)!=h for p,h in {**sources,**all_inputs}.items()):raise ValueError('Audit source/input changed during run')
    write_json(out/'review.json',dict(status='complete',packets=summaries,sources_sha256=sources))
    write_json(out/'status.json',dict(stage='complete'))


if __name__=='__main__':main()
