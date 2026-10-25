"""Bounded real-map comparison of historical and directed economic contracts."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from scipy.stats import spearmanr
from local_benchmark_protocol import file_hash, freeze, write_json
from polity.economic_world import prepare
from polity import trade as T
from polity.directed_trade import inbound_catchments, gravity_routes


def route_matrix(edges):
    # Undirected normalized traffic is comparable with the historical export,
    # whose child/parent tuples encode path trees rather than shipping direction.
    a,b,v=edges
    out={}
    for i,j,w in zip(a,b,v):
        key=(min(int(i),int(j)),max(int(i),int(j)))
        out[key]=out.get(key,0.)+float(w)
    total=sum(out.values())
    return {k:v/total for k,v in out.items()} if total else {}


def plot(folder,name,land,people,old,new):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    changed=(old!=new).reshape(land.shape)
    eligible=people.reshape(land.shape)>0
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),constrained_layout=True)
    for ax,values,label in [(axes[0],people.reshape(land.shape),'Eligible claimed-land population per cell'),
                            (axes[1],changed.astype(float),'Changed market assignment (orange)')]:
        image=np.where(land,values,np.nan)
        if ax is axes[0]:
            image=np.where(eligible,np.log10(1+values),np.nan)
            im=ax.imshow(image,cmap='YlGnBu',interpolation='nearest')
            fig.colorbar(im,ax=ax,shrink=.65,label='log10(1 + people per cell)')
        else:
            from matplotlib.colors import ListedColormap
            image=np.where(eligible,values,np.nan)
            ax.imshow(image,cmap=ListedColormap(['#e2ded2','#c85f36']),vmin=0,vmax=1,interpolation='nearest')
        ax.set_facecolor('#d6e3f0');ax.set_title(label,fontsize=11);ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle(name.replace('_',' ').title()+': bringing goods into town instead of sending them out',fontsize=13)
    fig.supxlabel('Same climate, people and costs; changed market ownership does not create population. Scenario sensitivity, not historical validation.',fontsize=9)
    fig.savefig(folder/'market_changes.png',dpi=145);plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('atlas')
    a=ap.parse_args();name=a.atlas
    plan_path=ROOT/'calibration/directed_trade_20261025/plan.json';plan=json.loads(plan_path.read_text())
    if name not in plan['atlases']:raise ValueError('Atlas outside the declared comparison')
    atlas=ROOT/'atlases'/name;folder=ROOT/'output/directed_trade_20261025'/name
    folder.mkdir(parents=True,exist_ok=True)
    cache=ROOT/'output/polity_map'/f'{name}.npz'
    paths=list((ROOT/'polity').glob('*.py'))+[Path(__file__),plan_path,cache]
    paths += [atlas/'data'/n for n in ['atlas.json','atlas.bin','winds12.npz','harvest.json','harvest.bin']]
    paths += [p for p in (ROOT/'data/source').rglob('*') if p.is_file()]
    fingerprint=freeze(folder/'protocol.json',dict(atlas=name,plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths}))
    started=time.monotonic();print(name+': preparing existing economic world',flush=True)
    r=prepare(atlas)
    nodes=np.array([t['row']*r['land'].shape[1]+t['col'] for t in r['towns']],np.int64)
    with np.load(cache) as saved:
        for key in ['land','elev','density','claim']:
            if not np.array_equal(r[key],saved[key],equal_nan=True):raise ValueError('Prepared input differs from export: '+key)
        if not np.array_equal(nodes,saved['towns'][:,0]*r['land'].shape[1]+saved['towns'][:,1]):
            raise ValueError('Prepared settlement nodes differ from export')
        if r['cell_km']!=float(saved['cell_km']):raise ValueError('Cell area differs from export')
    towns=np.unique(nodes)
    people=(np.where(r['land']&(r['claim']>=0),r['density'],0.)*r['cell_km']**2).ravel()
    print(name+': inputs exactly reproduce cached export; building seasonal freight graphs',flush=True)
    nets=[T.cost_network(r['world'],r['statics'],r['climate'],m,r['ports'],r['river_places']) for m in T.TRADE_MONTHS]
    old_mass,old_owner=T.catchments(nets[2],towns,people)
    new_mass,new_owner=inbound_catchments(nets[2],towns,people)
    for mass,owner in [(old_mass,old_owner),(new_mass,new_owner)]:
        if not np.isclose(mass.sum(),people[owner>=0].sum(),rtol=1e-12,atol=1e-6):
            raise ValueError('Assigned population does not equal reachable population')
    result=dict(identity=fingerprint,complete=False,inputs_exact=True,physical_towns=len(towns),
                merged_duplicate_records=len(nodes)-len(towns),eligible_people=float(people.sum()),
                historical_assigned_people=float(old_mass.sum()),inbound_assigned_people=float(new_mass.sum()),
                changed_market_people=float(people[old_owner!=new_owner].sum()),
                changed_share=float(people[old_owner!=new_owner].sum()/max(people.sum(),1.)),
                catchment_rank=float(spearmanr(old_mass,new_mass).statistic),
                note='Same population; market assignments and relative gravity weights only. Not town-size or historical-population validation.')
    plot(folder,name,r['land'],people,old_owner,new_owner)
    write_json(folder/'review.json',result)
    print(name+f': {result["changed_share"]:.1%} of eligible people change market; map saved; checking bounded routes',flush=True)
    subset=np.lexsort((towns,-old_mass))[:12]
    small_towns,small_mass=towns[subset],old_mass[subset]
    original=T.flows(nets,small_towns,small_mass,scale=T.COST_SCALE,sources=len(subset))
    directed=gravity_routes(nets,small_towns,small_mass,sources=len(subset))
    permuted=gravity_routes(nets,small_towns[::-1],small_mass[::-1],sources=len(subset))
    def directed_dict(edges):return {(int(i),int(j)):float(w) for i,j,w in zip(*edges)}
    d,p=directed_dict(directed),directed_dict(permuted)
    keys=set(d)|set(p);error=sum(abs(d.get(k,0)-p.get(k,0)) for k in keys)/max(sum(d.values()),1.)
    if error>1e-12:raise ValueError('Directed routes depend on town record order')
    old,new=route_matrix(original),route_matrix(directed)
    result.update(complete=True,route_town_subset=len(subset),permutation_relative_error=error,
                  normalized_undirected_route_l1=sum(abs(old.get(k,0)-new.get(k,0)) for k in set(old)|set(new)),
                  seconds=time.monotonic()-started,image_sha256=file_hash(folder/'market_changes.png'))
    write_json(folder/'review.json',result);print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
