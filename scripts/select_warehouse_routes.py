"""Freeze bounded route selections from funded, original monthly grain records."""
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_warehouse_routes_20261117'
PARENT=ROOT/'output/urban_shared_store_readiness_20261117'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_route_provenance_controls.json'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    q=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    OUT.mkdir(exist_ok=True);assert not (OUT/'selection.json').exists(),'Preserve pre-route selection'
    sources={str(p.relative_to(ROOT)):sha(p) for p in [PLAN,Path(__file__),PARENT/'qualification.json']}
    routes=[];empty=[]
    for reading in ['central','low']:
        paths=[ANNUAL/'prepared'/f'low_{reading}.npz',MONTHLY/'cases'/reading/'fields.npz']
        sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
        with np.load(paths[0]) as a,np.load(paths[1]) as m:
            nodes=a['nodes'];dist=a['dist'];between=a['between']
            origins=m['source_indices'];owner=m['owner'];retention=m['retention'];departures=m['departures'];shipments=m['shipments']
            for quarter in range(4):
                amounts=departures[quarter*3:quarter*3+3].sum(0)
                valid=np.flatnonzero((amounts>0)&(owner[quarter]>=0)&(retention[quarter]>0))
                if len(valid):
                    index=min(valid,key=lambda i:(-float(amounts[i]),int(origins[i])))
                    target=int(owner[quarter,index]);origin=int(origins[index]);destination=int(nodes[target])
                    routes.append(dict(id=f'{reading}_q{quarter}_source',reading=reading,quarter=quarter,month=quarter*3,kind='source',
                        origin=origin,destination=destination,source_index=int(index),town_index=target,
                        sent_kcal=float(amounts[index]),saved_cost=float(dist[quarter,origin]),retention=float(retention[quarter,index])))
                else:empty.append(dict(reading=reading,quarter=quarter,kind='source'))
                pairs={}
                for month,i,j,sent,got in shipments:
                    if int(month)//3!=quarter:continue
                    i,j=int(i),int(j)
                    assert sent>0 and got>0 and between[quarter,i,j]<270
                    pairs[i,j]=pairs.get((i,j),0.)+float(sent)
                if pairs:
                    i,j=min(pairs,key=lambda pair:(-pairs[pair],int(nodes[pair[0]]),int(nodes[pair[1]])))
                    cost=float(between[quarter,i,j])
                    routes.append(dict(id=f'{reading}_q{quarter}_intertown',reading=reading,quarter=quarter,month=quarter*3,kind='intertown',
                        origin=int(nodes[i]),destination=int(nodes[j]),sender_index=i,receiver_index=j,sent_kcal=pairs[i,j],
                        saved_cost=cost,retention=max(0.,1-cost/270)))
                else:empty.append(dict(reading=reading,quarter=quarter,kind='intertown'))
    assert len(routes)<=16
    write(OUT/'selection.json',dict(status='frozen_funded_original_routes_before_any_graph_or_dijkstra',sources_sha256=sources,
        routes=routes,empty_groups=empty,food_kernel_calls=0,dijkstra_calls=0,graph_rebuilds=0,new_Earth_food_scenarios=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False))
    print('Frozen',len(routes),'routes;',len(empty),'empty groups',flush=True)


if __name__=='__main__':main()
