"""Audit recorded capital/province/commandery communication on four climates."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from scipy import ndimage as ndi
    from polity.administrative_hierarchy import hierarchy,month_graph,parent_times,reply_times,LEGS
    from polity.administrative_world import audit_world
    from polity.transport import ports_of
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/administrative_hierarchy_20261104';origin.mkdir(exist_ok=True)
    ip=ROOT/'output/administrative_inventory_20261104/review.json';inventory=json.loads(ip.read_text())
    for p,h in inventory['sources_sha256'].items():
        if file_hash(ROOT/p)!=h:raise ValueError('Inventory changed: '+p)
    registry=hierarchy(inventory)
    sources={p:file_hash(ROOT/p) for p in ['polity/administrative_hierarchy.py','polity/administrative_world.py',
        'polity/economic_world.py','polity/fields.py','polity/control.py','polity/network.py','polity/transport.py',
        'polity/seasons.py','polity/settle.py','scripts/review_administrative_hierarchy.py']}
    all_inputs={};packets=[]
    for name,mode in [('free_fit','raw'),('earth_fit','raw'),('earth_fit','corrected'),('whittaker_fit','raw')]:
        atlas=ROOT/'atlases'/name;data=atlas/'data';prefix='' if mode=='raw' else 'corrected/'
        folder=origin/(name+'_'+mode);folder.mkdir(exist_ok=True)
        paths=[ip,ROOT/'data/imperial_datasheet_evidence.json',data/'atlas.json',data/prefix/'atlas.bin',
            data/prefix/'harvest.json',data/prefix/'harvest.bin',data/'winds12.npz']
        inputs={str(p.relative_to(ROOT)):file_hash(p) for p in paths};all_inputs.update(inputs)
        # Resume only complete packets with exactly the same identities.
        if (folder/'review.json').exists():
            saved=json.loads((folder/'review.json').read_text())
            if saved.get('inputs_sha256')==inputs and saved.get('sources_sha256')==sources and file_hash(folder/'links.npz')==saved['arrays_sha256']:
                packets.append(dict(atlas=name,climate=mode,review_sha256=file_hash(folder/'review.json')));print('Reused',name,mode,flush=True);continue
        print('Preparing',name,mode,flush=True)
        write_json(origin/'status.json',dict(stage='preparing',atlas=name,climate=mode))
        r,meta=audit_world(atlas,mode);land=r['land'];h,w=land.shape
        _,nearest=ndi.distance_transform_edt(~land,return_indices=True)
        def snap(x,y):
            yy=int(np.clip(y/meta['height']*h,0,h-1));xx=int(np.clip(x/meta['width']*w,0,w-1))
            return int(nearest[0,yy,xx])*w+int(nearest[1,yy,xx])
        nodes={c['source_id']:snap(c['x'],c['y']) for c in inventory['commanderies'] if c['status']=='matched'}
        marked={snap(m['x'],m['y']) for m in inventory['markers'] if m['symbol_verified']}
        marked_positions=[divmod(n,w) for n in sorted(marked)]
        base_ports=set(ports_of(marked_positions,r['statics']['water']))
        near_river=ndi.binary_dilation(r['statics']['basin']>0,iterations=1)
        base_rivers={p for p in marked_positions if near_river[p]}
        # Explicit union makes this an infrastructure addition, not a change
        # of the recorded places or administrative hierarchy.
        cases=[dict(world=dict(r['world'],tracks=np.zeros(land.shape,bool)),ports=base_ports,rivers=base_rivers),
            dict(world=r['world'],ports=base_ports|set(map(tuple,r['ports'])),rivers=base_rivers|set(map(tuple,r['river_places'])))]
        groups={pid:[i for i,c in enumerate(registry['links']) if c['status']=='located' and c['province_id']==pid]
            for pid in registry['provinces'].values()}
        values=np.full((2,12,len(registry['links']),4),np.nan)
        graph_audits=[]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for month in range(12):
                for scenario,case in enumerate(cases):
                    write_json(origin/'status.json',dict(stage='routing',atlas=name,climate=mode,model_month=month+1,scenario=scenario))
                    graph,removed=month_graph(case['world'],r['statics'],r['climate'],month,case['ports'],case['rivers'])
                    reverse=graph.T.tocsr()
                    def route(item):
                        pid,indexes=item
                        if not indexes:return indexes,None
                        return indexes,parent_times(graph,nodes[pid],nodes[registry['capital_id']],
                            [nodes[registry['links'][i]['commandery_id']] for i in indexes],reverse)
                    for indexes,times in pool.map(route,groups.items()):
                        if indexes:values[scenario,month,indexes]=times
                    graph_audits.append(dict(model_month=month+1,scenario=scenario,discarded_parallel_alternatives=removed,
                        ports=len(case['ports']),river_landings=len(case['rivers'])))
                    del graph,reverse
                finite=~np.isnan(values[0,month])
                if np.any(values[1,month][finite]>values[0,month][finite]+1e-7):raise ValueError('Added infrastructure worsened a directed leg')
                print(name,mode,'month',month+1,flush=True)
        local,chain=reply_times(values)
        located=[i for i,c in enumerate(registry['links']) if c['status']=='located']
        nontrivial=[i for i in located if registry['links'][i]['commandery_id']!=registry['capital_id']]
        summaries=[]
        for scenario in range(2):
            worst=np.max(chain[scenario][:,nontrivial],axis=0)
            summaries.append(dict(scenario=scenario,located_seats=len(located),noncapital_seats=len(nontrivial),
                nontrivial_local_links=sum(not registry['links'][i]['local_self_link'] for i in located),
                finite_all_bins=int(np.sum(np.isfinite(worst))),median_worst_reply_days=float(np.median(worst)) if np.isfinite(np.median(worst)) else None,
                budgets=[dict(days=budget,all_bin_seats=int(np.sum(worst<=budget))) for budget in [7,14,30,60]]))
        np.savez_compressed(folder/'links.npz',days=values)
        review=dict(status='isolated_administrative_hierarchy',atlas=name,climate=mode,registry=registry,
            scenarios=['marked_interchanges','proposed_transport'],leg_order=LEGS,summaries=summaries,graph_audits=graph_audits,
            inputs_sha256=inputs,sources_sha256=sources,arrays_sha256=file_hash(folder/'links.npz'),
            harvest_fingerprint=meta['harvest']['fingerprint'],
            scope='Directed additive person-travel under frozen climatological model-month conditions. '
            'Recorded hierarchy, inferred port/river interchange eligibility, current central-density path friction; '
            'alternative includes proposed tracks and interchanges. Parallel edges select minimum days. '
            'Beat-or-wait sea edges, no whole-voyage fair-spell blend, courier relay, institutional processing, food capacity or ownership inference. '
            'Reply via provincial capital sums four legs in the SAME frozen month; not an actual voyage advancing through seasons. '
            '7/14/30/60-day budgets are comparative scenarios, not validated administrative cutoffs.')
        write_json(folder/'review.json',review)
        packets.append(dict(atlas=name,climate=mode,review_sha256=file_hash(folder/'review.json')))
    if any(file_hash(ROOT/p)!=h for p,h in {**all_inputs,**sources}.items()):raise ValueError('Input/source changed during audit')
    write_json(origin/'review.json',dict(status='complete',packets=packets,sources_sha256=sources))
    write_json(origin/'status.json',dict(stage='complete'))


if __name__=='__main__':main()
