"""Exact seed-1 people provenance and seasonal freight controls, without a new fit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.sparse import coo_matrix,save_npz
from scipy.sparse.csgraph import dijkstra

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity import settlement_sizes as Z,trade as T,wide_supply as W,release3_placement as P
from polity.administrative_world import audit_world

OUT=ROOT/'output/urban_candidate_seasonal_20261116'
BASE=ROOT/'output/urban_hierarchy_candidate_20261116'
SUPPLY=ROOT/'output/urban_candidate_supply_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/seasonal_coupling.json'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n')


def origins(mode,model,reading,out):
    with np.load(BASE/f'{model}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
    sites=json.loads((BASE/f'{model}/placed_{mode}_sites.json').read_text())['sites']
    land=f['land'];people=f['people'];cell=float(f['cell_km']);centres=np.array([[s['row'],s['column']] for s in sites])
    (cells,owner,weight),H=Z.hinterlands(centres,land,people,cell)
    np.testing.assert_array_equal(H,f['hinterland_people'])
    source=np.flatnonzero(land);lookup=np.full(people.size,-1,int);lookup[source]=np.arange(len(source))
    own=f['from_own_hinterland_'+reading];wide=f['from_wider_region_'+reading]
    frac=np.divide(own,H,out=np.zeros_like(own),where=H>0)
    amount=weight*people.ravel()[cells]*frac[owner]
    rows=[lookup[cells]];cols=[owner];values=[amount]
    rural=(people.ravel()-np.bincount(cells,weights=amount,minlength=people.size)).reshape(land.shape)
    desired=Z.residents(f['area_ha'],reading);excess=desired-own;yy,xx=np.indices(land.shape)
    for i in np.argsort(-excess,kind='stable'):
        if excess[i]<=0:break
        d2=((yy-centres[i,0])**2+(xx-centres[i,1])**2)*cell**2
        for radius in [120.,240.,480.,960.,1920.]:
            mask=land&(d2<=radius**2);pool=float(rural[mask].sum())
            if pool>=4*excess[i]:break
        draw=min(excess[i],.25*pool)
        assert draw==wide[i] and radius==f['wider_radius_km_'+reading][i]
        local=np.flatnonzero(mask);moved=rural.ravel()[local]*(draw/pool)
        rows.append(lookup[local]);cols.append(np.full(len(local),i));values.append(moved)
        rural[mask]*=1-draw/pool
    M=coo_matrix((np.concatenate(values),(np.concatenate(rows),np.concatenate(cols))),shape=(len(source),len(sites))).tocsr()
    M.eliminate_zeros();total=np.asarray(M.sum(0)).ravel();physical_rural=people.ravel()[source]-np.asarray(M.sum(1)).ravel()
    np.testing.assert_allclose(total,f['residents_'+reading],atol=1e-7,rtol=1e-12)
    np.testing.assert_allclose(physical_rural,f['rural_'+reading].ravel()[source],atol=1e-8,rtol=1e-12)
    np.testing.assert_array_equal(rural,f['rural_'+reading])
    assert physical_rural.min()>=-1e-8
    path=out/f'people_{mode}_{model}_{reading}.npz';save_npz(path,M)
    return dict(sites=len(sites),links=int(M.nnz),source_cells=len(source),
        max_resident_difference=float(np.max(np.abs(total-f['residents_'+reading]))),
        max_rural_difference=float(np.max(np.abs(physical_rural-f['rural_'+reading].ravel()[source]))),
        canonical_sequential_rural_replay_exact=True,matrix_sha256=sha(path))


def network(mode,out):
    target=out/f'network_{mode}.npz'
    with np.load(SUPPLY/'network'/f'{mode}.npz') as z:reference={k:z[k] for k in z.files}
    sites=json.loads((BASE/f'control/placed_{mode}_sites.json').read_text())['sites'];nodes=np.array([s['node'] for s in sites])
    if target.exists():
        with np.load(target) as z:
            np.testing.assert_array_equal(z['between'].mean(0),reference['between']);np.testing.assert_array_equal(z['owner'],reference['owner']);np.testing.assert_array_equal(z['share'],reference['share'])
        return dict(seasons=4,nodes=len(nodes),annual_mean_exact=True,owner_share_exact=True,sha256=sha(target))
    print(mode,'reconstructing four separate freight seasons',flush=True)
    r,_=audit_world(ROOT/'atlases/earth_fit',mode)
    np.testing.assert_array_equal(r['world']['tracks'],reference['tracks'])
    assert {t['row']*r['land'].shape[1]+t['col'] for t in r['towns']}==set(nodes.tolist())
    lookup=np.full(r['land'].size,-1,int);lookup[nodes]=np.arange(len(nodes));owners=[];shares=[];between=[]
    for month in T.TRADE_MONTHS:
        net=T.cost_network(r['world'],r['statics'],r['climate'],month,r['ports'],r['river_places'])
        d,_,src=dijkstra(net.base.T.tocsr(),directed=True,indices=nodes,min_only=True,return_predecessors=True,limit=W.VALUE_LIMIT_ROAD_KM)
        d,src=d[:r['land'].size],src[:r['land'].size];valid=np.isfinite(d)&(src>=0);o=np.full(r['land'].size,-1,int);o[valid]=lookup[src[valid]]
        owners.append(o);shares.append(np.where(o>=0,W.delivered_share(d),0.))
        b=np.zeros((len(nodes),len(nodes)))
        for s,c in T.costs_from(net,nodes,limit=W.VALUE_LIMIT_ROAD_KM,batch=48):b[lookup[s]]=W.delivered_share(c[:,nodes])
        np.fill_diagonal(b,0.);between.append(b)
        print(mode,'season',month,'complete',flush=True)
    between=np.array(between);owners=np.array(owners);shares=np.array(shares)
    np.testing.assert_array_equal(between.mean(0),reference['between']);np.testing.assert_array_equal(owners,reference['owner']);np.testing.assert_array_equal(shares,reference['share'])
    np.savez_compressed(target,between=between,owner=owners,share=shares,nodes=nodes)
    return dict(seasons=4,nodes=len(nodes),annual_mean_exact=True,owner_share_exact=True,sha256=sha(target))


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert os.environ.get('ROTCLIMATE_FOREST_TRAVEL','0') in ('','0')
    previous=json.loads((SUPPLY/'results.json').read_text());review=json.loads((SUPPLY/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(SUPPLY/'results.json')
    for name,digest in {**previous['sources_sha256'],**previous['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    out=OUT/'prepared';out.mkdir(parents=True,exist_ok=True)
    P.OUT=SUPPLY/'packets/control';P.install();networks={m:network(m,out) for m in ['raw','corrected']}
    provenance={}
    for mode in ['raw','corrected']:
        for model in ['control','candidate']:
            for reading in ['central','low']:
                key=f'{mode}_{model}_{reading}';print('reconstructing people',key,flush=True);provenance[key]=origins(mode,model,reading,out)
    sources={**previous['sources_sha256'],str(PLAN.relative_to(ROOT)):sha(PLAN),str(Path(__file__).relative_to(ROOT)):sha(Path(__file__)),
        str((SUPPLY/'results.json').relative_to(ROOT)):sha(SUPPLY/'results.json'),str((SUPPLY/'review.json').relative_to(ROOT)):sha(SUPPLY/'review.json')}
    write(OUT/'preparation.json',dict(status='passed_exact_people_and_seasonal_network_controls',sources_sha256=sources,
        protected_sha256=previous['protected_sha256'],networks=networks,provenance=provenance,adopt=False))


if __name__=='__main__':main()
