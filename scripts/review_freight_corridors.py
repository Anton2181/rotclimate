"""Preview coherent seasonal freight cost/time on the actual raw-r43 geography."""
from pathlib import Path
from collections import Counter
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    import matplotlib.patheffects as effects
    from matplotlib.lines import Line2D
    from polity.economic_world import prepare
    from polity.freight_corridors import MODES,month_freight_network
    from polity.food_transport import FoodRoute,provision_food
    from local_benchmark_protocol import file_hash,write_json
    out=ROOT/'output/freight_corridors_20261103';out.mkdir(exist_ok=True)
    planpath=ROOT/'calibration/freight_corridors_20261103/plan.json';plan=json.loads(planpath.read_text())
    for name,expected in plan['inputs_sha256'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Declared route input changed: '+name)
    sources={name:file_hash(ROOT/name) for name in plan['source_files']}
    write_json(out/'status.json',dict(stage='preparing_current_atlas',plan_sha256=file_hash(planpath)))
    print('Preparing the current raw-r43 transport geography',flush=True)
    r=prepare(ROOT/'atlases/earth_fit');h,w=r['land'].shape
    ports=set(map(tuple,r['ports']))
    eligible=sorted({(t['row'],t['col']) for t in r['towns'] if 'x_px' in t and (t['row'],t['col']) in ports})
    if len(eligible)<2:raise ValueError('Two distinct marked ports required')
    anchors=[]
    for x,y in plan['anchor_target_fractions']:
        selected=min((p for p in eligible if p not in anchors),key=lambda p:((p[1]-x*w)**2+(p[0]-y*h)**2,p))
        anchors.append(selected)
    nodes=[y*w+x for y,x in anchors]
    meta=json.loads((ROOT/'atlases/earth_fit/data/atlas.json').read_text())
    if meta.get('physics_profile')!='r43':raise ValueError('This dated preview requires raw r43')
    endpoint_info=[]
    for label,(y,x),node in zip(['A','B'],anchors,nodes):
        nearby=min(meta['places'],key=lambda p:(p['x']/meta['width']*w-x)**2+(p['y']/meta['height']*h-y)**2)
        endpoint_info.append(dict(label=label,row=y,col=x,node=node,nearest_named_place=nearby['name']))
    records=[];audit=[]
    for month in range(12):
        write_json(out/'status.json',dict(stage='routing',model_month=month+1))
        net=month_freight_network(r['world'],r['statics'],r['climate'],month,r['ports'],r['river_places'])
        if not np.array_equal(net.river_cells,r['statics']['river_cells']):raise ValueError('Auxiliary river identities changed')
        audit.append(dict(model_month=month+1,selected_legs=len(net.costs),
            parallel_pairs=net.parallel_pair_count,discarded_parallel_legs=net.discarded_parallel_legs,
            maximum_summed_to_selected_cost_ratio=net.maximum_sum_to_selected_cost_ratio))
        for direction,origin,destination in [('A to B',nodes[0],nodes[1]),('B to A',nodes[1],nodes[0])]:
            path=net.paths(origin,[destination])[destination]
            if path is None:
                records.append(dict(model_month=month+1,direction=direction,status='unreachable'));continue
            cells=net.physical_cells(path.nodes)
            y,x=np.divmod(cells,w)
            records.append(dict(model_month=month+1,direction=direction,status='routed',
                cost_road_km=path.cost_road_km,travel_days=path.travel_days,mode_days=path.mode_days,
                nodes=path.nodes.tolist(),physical_path_cells=cells.tolist(),
                xy=np.column_stack([x,y]).tolist(),leg_modes=net.modes[path.leg_indices].tolist(),
                leg_costs=net.costs[path.leg_indices].tolist(),leg_days=net.days[path.leg_indices].tolist()))
        print('Completed paired model-month snapshot',month+1,flush=True)
        del net
    # Prescribed food budget from the manufactured example, moved between
    # the anchors only to test the connector. It is NOT local world production.
    source=ROOT/'output/seasonal_food_system_20261103/receipt.json';food=json.loads(source.read_text())
    supply=np.zeros((73,2))
    for crop in food['cases']['Ample farm storage']['seasons']:
        supply[crop['harvest_boundary']//5,0]+=crop['net_harvest_energy']
    need=np.broadcast_to([5.,2.],(73,2)).copy()
    months=np.floor((np.arange(73)+.5)*12/73).astype(int)+1
    provisioning={}
    for direction in ['A to B','B to A']:
        routes=[];omitted=[]
        for record in records:
            if record['direction']!=direction:continue
            if record['status']!='routed':omitted.append(record['model_month']);continue
            delay=max(1,int(np.ceil(record['travel_days']/5)))
            if delay>=73:omitted.append(record['model_month']);continue
            routes.append(FoodRoute(0,1,delay,np.where(months==record['model_month'],4.,0.),record['cost_road_km'],1.))
        result=provision_food(supply,need,routes,storage_capacity=[365,30],priority=[0,1])
        provisioning[direction]=dict(farm_consumed=float(result.consumed[:,0].sum()),farm_need=365.,
            town_consumed=float(result.consumed[:,1].sum()),town_need=146.,spilled=float(result.spilled.sum()),
            normalized_freight_cost=result.transport_cost,annual_food_ledger_residual=result.annual_ledger_residual,
            omitted_months=omitted,route_capacity_assumed=True,world_food_production_inferred=False)
    # Clear sea paths: a white casing and mode-colored line, separate panels
    # for direction/season, so overlapping routes are never distinguished by
    # tiny dashed marks alone. No outcome-based choice of displayed months.
    base=np.empty((h,w,3));base[:]=[.81,.88,.94]
    shade=np.clip(r['elev']/3000,0,1)
    for channel,(low,high) in enumerate(zip([.90,.91,.84],[.65,.68,.62])):
        base[...,channel]=np.where(r['land'],low+(high-low)*shade,base[...,channel])
    colors=['#9c4b1e','#006baa','#62419a','#62419a','#555555']
    fig,axes=plt.subplots(2,2,figsize=(15,8.2),layout='constrained')
    for ax,(direction,month) in zip(axes.flat,[(d,m) for d in ['A to B','B to A'] for m in [1,7]]):
        ax.imshow(base,origin='upper');record=next(q for q in records if q['direction']==direction and q['model_month']==month)
        if record['status']=='routed':
            points=np.asarray(record['xy'],float);segments=np.stack([points[:-1],points[1:]],axis=1)
            line=LineCollection(segments,colors=[colors[i] for i in record['leg_modes']],linewidths=1.8,zorder=3)
            line.set_path_effects([effects.Stroke(linewidth=3.8,foreground='white'),effects.Normal()]);ax.add_collection(line)
            ax.set_title(f'{direction} · model month {month}\n{record["cost_road_km"]:,.0f} road-km equivalents; {record["travel_days"]:.1f} days',loc='left',fontsize=11)
        else:ax.set_title(f'{direction} · model month {month}: no route',loc='left')
        for endpoint in endpoint_info:
            ax.scatter([endpoint['col']],[endpoint['row']],c='white',s=35,edgecolors='#222',zorder=4)
            ax.annotate(endpoint['label'],(endpoint['col'],endpoint['row']),xytext=(5,5),textcoords='offset points',
                weight='bold',path_effects=[effects.Stroke(linewidth=3,foreground='white'),effects.Normal()],zorder=5)
        ax.set(xlim=(0,w),ylim=(h,0));ax.set_axis_off()
    fig.suptitle('Same-path freight costs and travel times on the raw-r43 geography\nMonthly snapshots · original drawing orientation · capacities and town food budgets remain scenario inputs',fontsize=13)
    fig.legend(handles=[Line2D([0],[0],color=colors[i],lw=2,label=label) for i,label in [(0,'Land'),(1,'Sea'),(3,'River'),(4,'Transfers')]],
               loc='outside lower center',ncol=4,frameon=False)
    image=out/'freight_corridors.png';fig.savefig(image,dpi=140);plt.close(fig)
    if any(file_hash(ROOT/name)!=expected for name,expected in sources.items()):raise ValueError('Route sources changed during preview')
    review=dict(status='current_world_route_connector_preview',production_atlas_changed=False,
        endpoints=endpoint_info,routes=records,graph_audits=audit,provisioning=provisioning,
        source_food_scenario_sha256=file_hash(source),plan_sha256=file_hash(planpath),
        sources_sha256=sources,inputs_sha256=plan['inputs_sha256'],figure_sha256=file_hash(image),
        scope='Cost and time follow the identical directed legs of one least-cost path; that path is not claimed fastest. Parallel legs are alternatives, legacy graphs unchanged. Static monthly edgewise sailing expectation, no whole-voyage weather-spell model or weather evolution during transit. Capacity4 food units/5days, retention1, storage365/30 and food budgets are specified scenarios, not inferred from world production or town population. A/B production budgets deliberately identical; only route geography changes. Freight objective uses a homogeneous normalized cargo-energy unit, not currency or tonnes.')
    write_json(out/'review.json',review);write_json(out/'status.json',dict(stage='complete',review_sha256=file_hash(out/'review.json')))
    print(json.dumps(dict(endpoints=endpoint_info,provisioning=provisioning,parallel_pairs=[a['parallel_pairs'] for a in audit]),indent=2))


if __name__=='__main__':main()
