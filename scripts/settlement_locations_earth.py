"""Development-only fixed-count Earth comparison; no production map adoption.

    python -I scripts/settlement_locations_earth.py prepare han
    python -I scripts/settlement_locations_earth.py run

Current adopted Earth land/people inputs must first be recovered; see the report.
Prepared inputs and SHA256 receipts are retained for portable exact reruns.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.stats import ks_2samp, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from polity import earth as E, settle
from polity.settlement_locations import fixed_count_sites, site_fields

OUT = ROOT/'output/settlement_locations_20261110'
PLAN = ROOT/'calibration/settlement_locations_20261110/plan.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def prepare(name):
    import polity_earth_check as P
    import settlement_model_earth as S
    import population_cores as PC
    from rotclimate.earth import _wc
    OUT.mkdir(parents=True, exist_ok=True)
    spec=P.WINDOWS[name]
    g=E.grid(**spec);lat,lon=g['lat'],g['lon']
    elev=E.sample_global(_wc('elev'),lat,lon)
    g.update(land=np.isfinite(elev),elev=np.nan_to_num(elev,nan=0.0))
    for var in ('tavg','tmin','tmax','prec'):
        g[var]=np.stack([np.nan_to_num(E.sample_global(_wc(var,m+1),lat,lon)) for m in range(12)])
    g['density'],_,_=E.earth_people(lat,lon)
    g['river']=E.rivers(g)&g['land']
    if name=='han':
        seats=E.han_seats();ids,_=E.han_commanderies(g)
        road=np.zeros(g['land'].shape,bool);allowed=ids>=0
    elif name=='rome':
        seats=E.hanson_towns(150)
        road=E.draw_lines(g,[line for _,line in E.itinere_roads(150)])&g['land']
        allowed=E.inside_polygons(g,E.cliopatria('Roman Empire',150))
    else:
        raise ValueError('Unknown pool')
    y,x,ok=P.snap(g,np.array([s['lat'] for s in seats]),np.array([s['lon'] for s in seats]))
    data=S.inputs(g,road,allowed)
    data.update(lat=lat,lon=lon,real=np.unique((y*g['land'].shape[1]+x)[ok]))
    with np.load(ROOT/'output/land_people/earth/earth.npz') as z:
        d=PC.travel_distance(z,PC.CORE_SETS['cradles + Rome'],forest_cost=2.,sea_cost=1.,relief_cost=1.)
    data['history']=S.sample_earth(np.exp(-d/800.),lat,lon)
    path=OUT/(name+'_inputs.npz')
    if path.exists():
        raise ValueError('Prepared input exists; preserve it rather than silently overwriting')
    np.savez_compressed(path,**data)
    sources=[ROOT/'output/land_people/earth/earth.npz',ROOT/'data/cache/arable_slope_earth/arable_5m.npz',
             ROOT/'data/arable_slope_model.json',ROOT/'data/cache/naturalearth_dl/ne_10m_rivers_lake_centerlines.geojson']
    sources += list((ROOT/'data/cache/han_ad2/shp').glob('*')) if name=='han' else [ROOT/'data/cache/hanson2016/cities.xlsx',ROOT/'data/cache/itinere/itinere_roads.gpkg']
    receipt=dict(pool=name,status='exposed_development',shape=list(g['land'].shape),input_sha256=sha(path),
        original_source_sites=len(seats),snapped_inside_window=int(ok.sum()),
        sources={str(p.relative_to(ROOT)):sha(p) for p in sources if p.is_file()},
        reconstruction='Current slope/HAND/FALLOW0.600 inputs; newly paired baseline, not exact Nov7 input restoration.')
    write(OUT/(name+'_preparation.json'),receipt)
    print(json.dumps(receipt,indent=2),flush=True)


def metrics(data,towns):
    """Natural-count metrics; proximity matches can be many-to-one."""
    w=data['land'].shape[1];cell=float(data['cell_km'])
    real=data['real'];real=real[data['allowed'].ravel()[real]]
    obs=np.column_stack(np.unravel_index(real,data['land'].shape))
    pred=np.asarray(towns,dtype=int).reshape(-1,2)
    if len(obs)<2 or len(pred)<2:
        raise ValueError('Metrics require at least two observed and proposed centres')
    ot,pt=cKDTree(obs*cell),cKDTree(pred*cell)
    recall=float(np.mean(pt.query(obs*cell)[0]<=25.))
    precision=float(np.mean(ot.query(pred*cell)[0]<=25.))
    f1=2*recall*precision/max(recall+precision,1e-30)
    # Reproduce the earlier best-prefix proximity diagnostic separately. This
    # caps predictions at the observed count; it never sets the placement budget.
    prefix=pred[:len(obs)]
    prefix_recall=float(np.mean(cKDTree(prefix*cell).query(obs*cell)[0]<=25.))
    prefix_precision=float(np.mean(ot.query(prefix*cell)[0]<=25.))
    prefix_f1=2*prefix_recall*prefix_precision/max(prefix_recall+prefix_precision,1e-30)
    onn=ot.query(obs*cell,k=2)[0][:,1];pnn=pt.query(pred*cell,k=2)[0][:,1]
    # Include partial edge blocks, weighting only by their actual land exposure.
    b=max(1,round(100/cell));h,w=data['land'].shape
    ny,nx=(h+b-1)//b,(w+b-1)//b
    def counts(points):
        return np.bincount((points[:,0]//b)*nx+points[:,1]//b,minlength=ny*nx)
    yy,xx=np.indices((h,w));block=(yy//b)*nx+xx//b
    coverage=np.bincount(block.ravel(),weights=data['allowed'].ravel(),minlength=ny*nx)/np.bincount(block.ravel(),minlength=ny*nx)
    use=coverage>=.3
    pc,oc=counts(pred)[use],counts(obs)[use]
    rank=float(spearmanr(pc,oc).statistic) if np.ptp(pc)>0 and np.ptp(oc)>0 else 0.
    ks=float(ks_2samp(onn,pnn).statistic)
    # Separately report unique matching so proximity recall is not mistaken for
    # recovering that fraction of distinct historical centres.
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import maximum_bipartite_matching
    links=ot.query_ball_tree(pt,25.)
    rr=np.repeat(np.arange(len(obs)),[len(v) for v in links])
    cc=np.array([j for v in links for j in v],dtype=int)
    graph=csr_matrix((np.ones(len(rr)),(rr,cc)),shape=(len(obs),len(pred)))
    matched=int(np.count_nonzero(maximum_bipartite_matching(graph,perm_type='column')>=0))
    return dict(F1=f1,precision=precision,recall=recall,M1=rank,M3=ks,
        composite=(f1+(rank+1)/2+1-ks)/3,n_real=len(obs),n_model=len(pred),
        unique_matches=matched,unique_F1=2*matched/(len(obs)+len(pred)),
        historical_best_prefix=dict(n_model=len(prefix),recall=prefix_recall,precision=prefix_precision,F1=prefix_f1),
        observed_nn_km=np.quantile(onn,[.1,.5,.9]).tolist(),model_nn_km=np.quantile(pnn,[.1,.5,.9]).tolist())


def baseline(data):
    return settle.place_towns(data['density'],data['land'],data['water_km'],data['road'],data['elev'],
        float(data['cell_km']),[],allowed=data['allowed'],seed=1,aridity=data['aridity'])[0]


def run():
    plan=json.loads(PLAN.read_text());rows=[];receipts={};positions={};baselines={}
    files=sorted(OUT.glob('*_inputs.npz'))
    if not files:
        raise ValueError('No prepared Earth pools; run prepare first')
    for file in files:
        name=file.name.removesuffix('_inputs.npz')
        receipt=json.loads((OUT/(name+'_preparation.json')).read_text())
        if receipt['input_sha256']!=sha(file):
            raise ValueError('Changed frozen Earth input: '+name)
        receipts[name]=receipt
        data=dict(np.load(file));towns=baseline(data);count=len(towns)
        baselines[name]=dict(metrics(data,towns),requested=count,shortfall=0)
        positions[name+'__baseline']=np.asarray(towns)
        score,eligible=site_fields(data['density'],data['land'],data['water_km'],data['road'],data['elev'],
            float(data['cell_km']),allowed=data['allowed'],aridity=data['aridity'])
        for stochastic,spacing,history in itertools.product((False,True),(9.,18.,27.),('none','old_cores_L800')):
            key=f'{"draw" if stochastic else "greedy"}_{int(spacing)}km_{history}'
            for seed in plan['location_variants']['seeds'] if stochastic else [1]:
                placed=fixed_count_sites(score,eligible,count,float(data['cell_km']),min_spacing_km=spacing,
                    seed=seed,history=data['history'] if history!='none' else None,stochastic=stochastic)
                row=dict(pool=name,variant=key,seed=seed,requested=count,shortfall=placed.shortfall,
                    **metrics(data,placed.towns))
                rows.append(row);positions[name+'__'+key+'__'+str(seed)]=np.asarray(placed.towns)
            print(name,key,'complete',flush=True)
    ranking=[]
    for variant in sorted({r['variant'] for r in rows}):
        pools={}
        for pool in receipts:
            selected=[r for r in rows if r['pool']==pool and r['variant']==variant]
            pools[pool]={k:float(np.mean([r[k] for r in selected])) for k in ('F1','M1','M3','composite','unique_F1')}
            pools[pool]['seed_range']={k:[min(r[k] for r in selected),max(r[k] for r in selected)] for k in ('F1','M1','M3','composite')}
            pools[pool]['max_shortfall']=max(r['shortfall'] for r in selected)
        ranking.append(dict(variant=variant,pools=pools,composite=float(np.mean([p['composite'] for p in pools.values()])),
                            feasible=all(p['max_shortfall']==0 for p in pools.values())))
    ranking.sort(key=lambda r:(not r['feasible'],-r['composite']))
    np.savez_compressed(OUT/'positions.npz',**positions)
    write(OUT/'results.json',dict(status='development_only',adopt=False,plan_sha256=sha(PLAN),positions_sha256=sha(OUT/'positions.npz'),
        sources={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'polity/settlement_locations.py',ROOT/'polity/settle.py')},
        pools=receipts,baseline=baselines,rows=rows,ranking=ranking,
        development_lead=next((r['variant'] for r in ranking if r['feasible']),None),
        pending='Occupancy assumptions, other development pools and prospective transfer; no atlas settlement/control replacement.'))
    print('Baseline',json.dumps(baselines),flush=True)
    print('Development lead',json.dumps(ranking[0]),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','run'));parser.add_argument('pool',nargs='?',choices=('han','rome'))
    parser.add_argument('--out',type=Path,default=OUT,help='New experiment identity for rebuilding inputs; default replays tracked inputs')
    args=parser.parse_args()
    OUT=args.out.resolve()
    if args.stage=='prepare':
        if args.pool is None:parser.error('prepare requires a pool')
        prepare(args.pool)
    else:run()
