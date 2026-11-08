"""Worldwide source-evidence and same-site seasonal coverage audit.

No sovereignty assignment, road authority sources, strength multiplier,
military supply or inferred mobile polity is introduced.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import gzip
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from atlas_set import active as active_atlases  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)


def main():
    import numpy as np
    from scipy import ndimage as ndi
    from polity.coverage_audit import source_inventory,node_memberships,site_codes,merge_site,seasonal_mask,aggregate_words,SCENARIOS,BUDGETS
    from polity.administrative_world import audit_world
    from polity.administrative_hierarchy import month_graph
    from polity import fields as F
    from harvest.export import geometry
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/world_coverage_20261104';origin.mkdir(exist_ok=True)
    ip=ROOT/'output/administrative_inventory_20261104/review.json';ap=ROOT/'data/polity_affiliation_aliases.json'
    inventory=json.loads(ip.read_text());aliases=json.loads(ap.read_text())
    for p,h in inventory['sources_sha256'].items():
        if file_hash(ROOT/p)!=h:raise ValueError('Inventory changed: '+p)
    sources={p:file_hash(ROOT/p) for p in ['polity/coverage_audit.py','polity/administrative_hierarchy.py','polity/administrative_world.py',
        'polity/economic_world.py','polity/fields.py','polity/control.py','polity/network.py','polity/transport.py','polity/seasons.py','polity/settle.py',
        'harvest/export.py','population/export.py','scripts/review_world_coverage.py','data/polity_affiliation_aliases.json',
        'data/source/ravages_v8/borders_fill.png','data/source/ravages_v8/polities.json']}
    summaries=[];all_inputs={};popcount=np.array([i.bit_count() for i in range(4096)],np.uint8)
    for name,mode in active_atlases([('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]):
        atlas=ROOT/'atlases'/name;data=atlas/'data';prefix='' if mode=='raw' else 'corrected/'
        folder=origin/(name+'_'+mode);folder.mkdir(exist_ok=True)
        paths=[ip,ap,data/'atlas.json',data/prefix/'atlas.bin',data/prefix/'harvest.json',data/prefix/'harvest.bin',data/'winds12.npz']
        inputs={str(p.relative_to(ROOT)):file_hash(p) for p in paths};all_inputs.update(inputs)
        binary=folder/'coverage.bin.gz';rp=folder/'review.json'
        if rp.exists() and binary.exists():
            old=json.loads(rp.read_text())
            if old.get('inputs_sha256')==inputs and old.get('sources_sha256')==sources and file_hash(binary)==old['binary_sha256']:
                summaries.append(dict(atlas=name,climate=mode,review_sha256=file_hash(rp),summaries=old['summaries']));print('Reused',name,mode,flush=True);continue
        print('Preparing',name,mode,flush=True);write_json(origin/'status.json',dict(stage='preparing',atlas=name,climate=mode))
        r,meta=audit_world(atlas,mode);land=r['land'];h,w=land.shape;land_nodes=np.flatnonzero(land.ravel());n=len(land_nodes)
        ids,info=F.polity_fills(land.shape)
        actors=sorted({d['name'].split(' (')[0] for d in info.values() if d['name']})
        claim_names={i:d['name'].split(' (')[0] for i,d in info.items() if d['name']}
        _,nearest=ndi.distance_transform_edt(~land,return_indices=True)
        def snap(x,y):
            yy=int(np.clip(y/meta['height']*h,0,h-1));xx=int(np.clip(x/meta['width']*w,0,w-1))
            return int(nearest[0,yy,xx])*w+int(nearest[1,yy,xx])
        def claim_actor(node):return claim_names.get(int(ids.ravel()[node]))
        records=source_inventory(inventory,aliases,actors)
        generated={t['row']*w+t['col'] for t in r['towns'] if 'x_px' not in t}
        nodes,counts,records=node_memberships(records,generated,claim_actor,snap,actors)
        # Sources alone vary: the SAME central-density friction, generated
        # tracks, ports and river landings are used in every source scenario.
        words=np.zeros((3,len(actors),2,n),np.uint32);unknown=np.zeros((2,n),np.uint32);first_month=0
        cp=folder/'partial.npz';ci=folder/'partial.json'
        if cp.exists() and ci.exists():
            checkpoint=json.loads(ci.read_text())
            if checkpoint.get('inputs_sha256')==inputs and checkpoint.get('sources_sha256')==sources and file_hash(cp)==checkpoint['arrays_sha256']:
                with np.load(cp) as saved:
                    if saved['words'].shape!=words.shape or saved['unknown'].shape!=unknown.shape:raise ValueError('Checkpoint shape changed')
                    words=saved['words'];unknown=saved['unknown'];first_month=int(saved['next_month'])
                if not 0<=first_month<=12:raise ValueError('Invalid checkpoint month')
                print('Resumed at month',first_month+1,flush=True)
        graph_audits=[]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for month in range(first_month,12):
                write_json(origin/'status.json',dict(stage='routing',atlas=name,climate=mode,model_month=month+1,sites=len(nodes)))
                graph,removed=month_graph(r['world'],r['statics'],r['climate'],month,r['ports'],r['river_places']);reverse=graph.T.tocsr()
                codes=np.zeros((3,len(actors),2,n),np.uint8);un=np.zeros((2,n),np.uint8)
                def route(node):return site_codes(graph,reverse,node,land_nodes)
                keys=sorted(nodes)
                for key,result in zip(keys,pool.map(route,keys)):merge_site(codes,un,nodes[key],result)
                if np.any(codes[:,:,1]>codes[:,:,0]):raise ValueError('Same-site return exceeds outward coverage')
                if np.any(codes[1]<codes[0]) or np.any(codes[2]<codes[1]):raise ValueError('Source addition reduced coverage')
                words|=codes.astype(np.uint32)<<(2*month);unknown|=un.astype(np.uint32)<<(2*month)
                graph_audits.append(dict(model_month=month+1,discarded_parallel_alternatives=removed))
                del graph,reverse,codes,un
                if (month+1)%3==0:
                    np.savez_compressed(cp,words=words,unknown=unknown,next_month=month+1)
                    write_json(ci,dict(inputs_sha256=inputs,sources_sha256=sources,arrays_sha256=file_hash(cp)))
                print(name,mode,'month',month+1,'sites',len(nodes),flush=True)
        lookup=np.zeros(land.size,np.uint32);lookup[land_nodes]=np.arange(1,n+1,dtype=np.uint32)
        raw=lookup.astype('<u4').tobytes()+words.astype('<u4').tobytes()+unknown.astype('<u4').tobytes()
        binary.write_bytes(gzip.compress(raw,compresslevel=6,mtime=0))
        geo,_=geometry(meta,land.shape);area=geo['land_fraction'].ravel()[land_nodes].astype(float);area/=area.sum()
        results=[]
        for s,scenario in enumerate(SCENARIOS):
            both=aggregate_words(words[s,:,1]);out=aggregate_words(words[s,:,0])
            for b,budget in enumerate(BUDGETS):
                mask=seasonal_mask(both,b);outmask=seasonal_mask(out,b);overlap=np.zeros(n,np.uint16)
                for month in range(12):
                    count=np.sum(((words[s,:,1]>>(2*month))&3)>=(3-b),axis=0)
                    overlap|=(count>=2).astype(np.uint16)<<month
                results.append(dict(scenario=scenario,per_leg_days=budget,mean_any_actor_bins=float(np.sum(popcount[mask]*area)),
                    all12_any_actor_land_share=float(area[mask==4095].sum()),overlap_any_bin_land_share=float(area[overlap>0].sum()),
                    outward_without_same_site_return_land_share=float(area[(outmask&~mask)>0].sum())))
        actor_meta=[]
        for a,actor in enumerate(actors):
            colour=next(d['rgb'] for d in info.values() if d['name'] and d['name'].split(' (')[0]==actor)
            actor_meta.append(dict(name=actor,color='#%02x%02x%02x'%tuple(colour),source_counts=counts[:,a].tolist(),
                evidence_inventory='no affiliated marked sites recorded' if counts[0,a]==0 else 'provisional linked-site inventory'))
        review=dict(status='isolated_worldwide_coverage_audit',atlas=name,climate=mode,shape=list(land.shape),land_cells=n,
            cell_px=meta['width']/w,actors=actor_meta,scenarios=SCENARIOS,budgets_days=BUDGETS,records=records,
            unknown_marked_sites=sum(bool(v['unknown']) for v in nodes.values()),unique_routed_sites=len(nodes),
            binary_sha256=file_hash(binary),raw_bytes=len(raw),words_shape=list(words.shape),
            offsets=dict(lookup=0,words=lookup.nbytes,unknown=lookup.nbytes+words.nbytes),
            inventory_sha256=file_hash(ip),inputs_sha256=inputs,sources_sha256=sources,
            expected_harvest_fingerprint=meta['harvest']['fingerprint'],summaries=results,graph_audits=graph_audits,
            scope='Provisional source evidence and person-travel scenarios, not ownership, military control or absent communities. '
            'No road-cell authority sources; no extra refuge/rank/power multipliers. Same-site return uses max(outward,return) within each supplied per-leg budget. '
            'Common central-density transport includes proposed tracks/ports; source scenarios isolate affiliation/site additions only. '
            'Additive beat-or-wait sailing and minimum parallel alternatives; all conditions held at one model month. '
            'Unknown marked sites are a separate evidence signal, never an invented polity. Missing actor inventories are unscored, not zero actual control.')
        write_json(rp,review)
        cp.unlink(missing_ok=True);ci.unlink(missing_ok=True)
        summaries.append(dict(atlas=name,climate=mode,review_sha256=file_hash(rp),summaries=results))
        print(name,mode,'complete; compressed bytes',binary.stat().st_size,flush=True)
    if any(file_hash(ROOT/p)!=h for p,h in {**sources,**all_inputs}.items()):raise ValueError('Coverage source/input changed during run')
    write_json(origin/'review.json',dict(status='complete',packets=summaries,sources_sha256=sources))
    write_json(origin/'status.json',dict(stage='complete'))


if __name__=='__main__':main()
