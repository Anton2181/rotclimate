"""Measure isolated parallel-edge aggregation effects on current-world freight."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from scipy.sparse.csgraph import dijkstra
    from polity.economic_world import prepare
    from polity.freight_corridors import month_freight_network
    from polity.trade import cost_network
    from local_benchmark_protocol import file_hash,write_json
    out=ROOT/'output/parallel_freight_20261103';out.mkdir(exist_ok=True)
    planpath=ROOT/'calibration/parallel_freight_20261103/plan.json';plan=json.loads(planpath.read_text())
    for name,expected in plan['inputs_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Declared input changed: '+name)
    sources={name:file_hash(ROOT/name) for name in plan['source_files']}
    write_json(out/'status.json',dict(stage='preparing_current_atlas'))
    world=prepare(ROOT/'atlases/earth_fit');w=world['land'].shape[1]
    marked=sorted({t['row']*w+t['col'] for t in world['towns'] if 'x_px' in t})
    indices=np.linspace(0,len(marked)-1,min(plan['marked_source_count'],len(marked))).round().astype(int)
    nodes=[marked[i] for i in indices]
    earlier=json.loads((ROOT/'output/freight_corridors_20261103/review.json').read_text())
    nodes=sorted(set(nodes+[e['node'] for e in earlier['endpoints']]))
    people=np.where(world['land']&(world['claim']>=0),world['density'],0.).ravel()*world['cell_km']**2
    results=[];samples=[]
    for month in plan['model_months']:
        write_json(out/'status.json',dict(stage='routing',model_month=month))
        new=month_freight_network(world['world'],world['statics'],world['climate'],month-1,world['ports'],world['river_places'])
        old=cost_network(world['world'],world['statics'],world['climate'],month-1,world['ports'],world['river_places'])
        legacy=old.base[:-1,:-1].tocsr()
        if legacy.shape!=new.base.shape or not np.array_equal(legacy.indptr,new.base.indptr) or not np.array_equal(legacy.indices,new.base.indices):
            raise ValueError('Topology changed: aggregation is not isolated')
        if not np.array_equal(old.river_cells,new.river_cells):raise ValueError('River identities changed')
        delta=legacy.data-new.base.data
        if np.min(delta)<-1e-9:raise ValueError('A selected alternative is dearer than its legacy sum')
        changed=delta>1e-8
        if int(changed.sum())!=new.parallel_pair_count:raise ValueError('Unexpected changed edge count')
        monthly=[]
        for source in nodes:
            oldcost=dijkstra(legacy,directed=True,indices=source)[:len(people)]
            newcost=dijkstra(new.base,directed=True,indices=source)[:len(people)]
            if not np.array_equal(np.isfinite(oldcost),np.isfinite(newcost)):raise ValueError('Reachability changed')
            finite=np.isfinite(oldcost);difference=oldcost[finite]-newcost[finite]
            if np.min(difference)<-1e-7:raise ValueError('Cheaper alternatives made a shortest path dearer')
            reachable_people=people[finite]
            local={}
            for scale in plan['market_access_scales_road_km']:
                oldma=float(np.dot(np.exp(-oldcost[finite]/scale),reachable_people))
                newma=float(np.dot(np.exp(-newcost[finite]/scale),reachable_people))
                local[str(scale)]=dict(legacy=oldma,alternatives=newma,relative_change=None if oldma==0 else newma/oldma-1)
            material=difference>plan['material_cost_change_road_km']
            entry=dict(model_month=month,source_node=source,reachable_physical_cells=int(finite.sum()),
                cells_reduced_by_more_than_threshold=int(material.sum()),
                maximum_cost_reduction=float(difference.max()),mean_cost_reduction=float(difference.mean()),
                reachable_people_fraction_with_material_reduction=0. if reachable_people.sum()==0 else float(reachable_people[material].sum()/reachable_people.sum()),
                market_access=local)
            monthly.append(entry)
            for destination in nodes:
                if destination==source:continue
                if np.isfinite(oldcost[destination]):
                    samples.append(dict(model_month=month,origin=source,destination=destination,
                        legacy_cost=float(oldcost[destination]),alternative_cost=float(newcost[destination])))
                else:samples.append(dict(model_month=month,origin=source,destination=destination,status='unreachable'))
        results.append(dict(model_month=month,changed_directed_pairs=int(changed.sum()),
            minimum_edge_difference=float(delta.min()),maximum_edge_difference=float(delta.max()),sources=monthly))
        write_json(out/'checkpoint.json',dict(results=results,pair_samples=samples))
        print('Completed isolated aggregation audit month',month,flush=True)
        del old,new,legacy
    if any(file_hash(ROOT/name)!=expected for name,expected in sources.items()):raise ValueError('Sources changed during audit')
    review=dict(status='paired_current_world_freight_audit',production_atlas_changed=False,
        plan_sha256=file_hash(planpath),inputs_sha256=plan['inputs_sha256'],sources_sha256=sources,
        source_nodes=nodes,results=results,pair_samples=samples,
        scope='Fixed source sample, not all-world town-pair validation. Identical topology and coefficients; only duplicate edge sum versus least-cost alternative. Legacy trade geography, claim population and market-access scales. Market access is discounted catchment population, not town size, food tonnage, population growth or observed economic accuracy.')
    write_json(out/'review.json',review);write_json(out/'status.json',dict(stage='complete',review_sha256=file_hash(out/'review.json')))
    print(json.dumps(dict(sources=len(nodes),months=len(results),
        maximum_pair_cost_reduction=max((r['legacy_cost']-r['alternative_cost'] for r in samples if 'legacy_cost' in r),default=0.),
        maximum_market_access_relative_change=max((s['market_access']['270']['relative_change'] or 0. for r in results for s in r['sources']),default=0.)),indent=2))


if __name__=='__main__':main()
