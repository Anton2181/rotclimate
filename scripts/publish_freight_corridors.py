"""Render and verify the completed world-route preview without rerouting it."""
from pathlib import Path
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
    from matplotlib.lines import Line2D
    import matplotlib.patheffects as effects
    from harvest.export import climate_arrays,geometry
    from local_benchmark_protocol import file_hash,write_json
    out=ROOT/'output/freight_corridors_20261103'
    source=out/'review.json';review=json.loads(source.read_text())
    planpath=ROOT/'calibration/freight_corridors_20261103/plan.json'
    if review['production_atlas_changed'] or file_hash(planpath)!=review['plan_sha256']:
        raise ValueError('Preview scope or plan changed')
    for name,expected in {**review['sources_sha256'],**review['inputs_sha256']}.items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Preview source/input changed: '+name)
    if file_hash(out/'freight_corridors.png')!=review['figure_sha256']:
        raise ValueError('Original preview figure changed')
    for route in review['routes']:
        if route['status']!='routed':continue
        if len(route['nodes'])!=len(route['leg_days'])+1 or len(route['nodes'])!=len(route['xy']):
            raise ValueError('Path identities differ')
        if not np.isclose(sum(route['leg_days']),route['travel_days']) or not np.isclose(sum(route['leg_costs']),route['cost_road_km']):
            raise ValueError('Same-path total failed')
    for case in review['provisioning'].values():
        if abs(case['annual_food_ledger_residual'])>1e-6 or case['world_food_production_inferred']:
            raise ValueError('Provisioning scope or ledger failed')
    meta=json.loads((ROOT/'atlases/earth_fit/data/atlas.json').read_text())
    arrays=climate_arrays(ROOT/'atlases/earth_fit/data',meta)
    elev=arrays['elev'];h,w=elev.shape
    geo,_=geometry(meta,elev.shape);land=geo['land_fraction']>.5
    base=np.empty((h,w,3));base[:]=[.81,.88,.94];shade=np.clip(elev/3000,0,1)
    for channel,(low,high) in enumerate(zip([.90,.91,.84],[.65,.68,.62])):
        base[...,channel]=np.where(land,low+(high-low)*shade,base[...,channel])
    # Both transfer categories share the legend's gray; river navigation is purple.
    colors=['#9c4b1e','#006baa','#555555','#62419a','#555555']
    fig,axes=plt.subplots(2,2,figsize=(15,8.2),layout='constrained')
    for ax,(direction,month) in zip(axes.flat,[(d,m) for d in ['A to B','B to A'] for m in [1,7]]):
        ax.imshow(base,origin='upper')
        route=next(r for r in review['routes'] if r['direction']==direction and r['model_month']==month)
        if route['status']=='routed':
            points=np.asarray(route['xy'],float);segments=np.stack([points[:-1],points[1:]],axis=1)
            line=LineCollection(segments,colors=[colors[i] for i in route['leg_modes']],linewidths=1.8,zorder=3)
            line.set_path_effects([effects.Stroke(linewidth=3.8,foreground='white'),effects.Normal()]);ax.add_collection(line)
            ax.set_title(f'{direction} · model month {month}\n{route["cost_road_km"]:,.0f} road-km equivalents; {route["travel_days"]:.1f} days',loc='left',fontsize=11)
        else:ax.set_title(f'{direction} · model month {month}: no route',loc='left')
        for point in review['endpoints']:
            ax.scatter([point['col']],[point['row']],c='white',s=35,edgecolors='#222',zorder=4)
            ax.annotate(point['label'],(point['col'],point['row']),xytext=(5,5),textcoords='offset points',weight='bold',
                path_effects=[effects.Stroke(linewidth=3,foreground='white'),effects.Normal()],zorder=5)
        ax.set(xlim=(-.5,w-.5),ylim=(h-.5,-.5));ax.set_axis_off()
    fig.suptitle('Same-path freight costs and travel times on the raw-r43 geography\nMonthly snapshots · original drawing orientation · capacities and town food budgets remain scenario inputs',fontsize=13)
    fig.legend(handles=[Line2D([0],[0],color=colors[i],lw=2,label=label) for i,label in [(0,'Land'),(1,'Sea'),(3,'River'),(4,'Transfers')]],
               loc='outside lower center',ncol=4,frameon=False)
    figure=out/'freight_corridors_readable.png';fig.savefig(figure,dpi=140);plt.close(fig)
    write_json(out/'presentation.json',dict(status='verified',review_sha256=file_hash(source),
        publisher_sha256=file_hash(Path(__file__)),figure_sha256=file_hash(figure),
        purpose='Render recorded paths with both transfer types matching the gray legend; no rerouting or score selection'))
    print('Verified all recorded same-path totals, source/input hashes and food ledgers; rendered readable routes')


if __name__=='__main__':main()
