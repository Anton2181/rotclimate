"""Frozen S1c adaptive spacing and history-prior sensitivity on exposed Earth pools."""
import argparse
import itertools
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.settlement_locations import site_fields
from polity.settlement_intensity import adaptive_count_sites
from settlement_locations_earth import metrics,sha,write

PLAN=ROOT/'calibration/settlement_intensity_20261110/plan.json'
ORIGINAL=ROOT/'output/settlement_locations_20261110'
OUT=ROOT/'output/settlement_intensity_20261110'


def quality(row,location_weight=.6):
    return float(location_weight*row['unique_F1']+(1-location_weight)*.5*((row['M1']+1)/2+1-row['M3']))


def means(rows):
    keys=['unique_F1','F1','M1','M3']
    m={k:float(np.mean([r[k] for r in rows])) for k in keys}
    return dict(m,Q=quality(m),max_shortfall=max(r['shortfall'] for r in rows),
        seed_range={k:[min(r[k] for r in rows),max(r[k] for r in rows)] for k in keys})


def run(out=OUT):
    plan=json.loads(PLAN.read_text());grid=plan['grid']
    original=json.loads((ORIGINAL/'results.json').read_text())
    for name,digest in original['sources'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Original experiment source changed: '+name)
    if sha(ORIGINAL/'positions.npz')!=original['positions_sha256']:
        raise ValueError('Original archived positions changed')
    out.mkdir(parents=True,exist_ok=True)
    rows=[];positions={};inputs={}
    for pool,receipt in original['pools'].items():
        path=ORIGINAL/(pool+'_inputs.npz')
        if sha(path)!=receipt['input_sha256']:raise ValueError('Changed Earth input')
        inputs[pool]=dict(path=str(path.relative_to(ROOT)),sha256=receipt['input_sha256'])
        x=dict(np.load(path));count=original['baseline'][pool]['requested']
        score,eligible=site_fields(x['density'],x['land'],x['water_km'],x['road'],x['elev'],float(x['cell_km']),allowed=x['allowed'],aridity=x['aridity'])
        for scale,coef,stochastic in itertools.product(grid['history_scale_km'],grid['spacing_coefficient'],grid['stochastic']):
            history=x['history']**(800./scale)
            name=f'{"draw" if stochastic else "greedy"}_c{coef:g}_L{scale}'
            seeds=grid['seeds_stochastic'] if stochastic else grid['seeds_deterministic']
            for seed in seeds:
                placed=adaptive_count_sites(score,eligible,count,float(x['cell_km']),history=history,
                    coefficient=coef,seed=seed,stochastic=stochastic)
                row=dict(pool=pool,variant=name,scale_km=scale,coefficient=coef,stochastic=stochastic,
                    seed=seed,requested=count,shortfall=placed.shortfall,**metrics(x,placed.towns))
                row['Q']=quality(row);rows.append(row)
                positions[pool+'__'+name+'__'+str(seed)]=np.asarray(placed.towns)
            print(pool,name,'complete',flush=True)
    if len(rows)!=grid['evaluations']:raise ValueError('Incomplete declared grid')
    ranking=[]
    for name in sorted({r['variant'] for r in rows}):
        pools={p:means([r for r in rows if r['variant']==name and r['pool']==p]) for p in inputs}
        mean={k:float(np.mean([r[k] for r in pools.values()])) for k in ['unique_F1','F1','M1','M3']}
        ranking.append(dict(variant=name,family='adaptive',pools=pools,mean=mean,Q=quality(mean),
                            feasible=all(r['max_shortfall']==0 for r in pools.values())))
    references=[]
    for ref in original['ranking']:
        mean={k:float(np.mean([r[k] for r in ref['pools'].values()])) for k in ['unique_F1','F1','M1','M3']}
        references.append(dict(variant=ref['variant'],family='fixed',pools=ref['pools'],mean=mean,Q=quality(mean),feasible=ref['feasible']))
    mean={k:float(np.mean([r[k] for r in original['baseline'].values()])) for k in ['unique_F1','F1','M1','M3']}
    references.append(dict(variant='production_baseline',family='production',pools=original['baseline'],mean=mean,Q=quality(mean),feasible=True))
    ranking.sort(key=lambda r:(not r['feasible'],-r['Q'],r['variant']))
    references.sort(key=lambda r:(not r['feasible'],-r['Q'],r['variant']))
    available=[r for r in ranking+references if r['feasible']]
    best_new=next((r for r in ranking if r['feasible']),None)
    frontier=[]
    def vector(r):return np.array([r['mean']['unique_F1'],r['mean']['M1'],-r['mean']['M3']])
    for row in available:
        a=vector(row)
        if not any(np.all(vector(other)>=a) and np.any(vector(other)>a) for other in available):
            frontier.append(row['variant'])
    sensitivity={}
    for weight in (.4,.6,.8):
        leader=max(available,key=lambda r:quality(r['mean'],weight))
        sensitivity[str(weight)]=dict(variant=leader['variant'],family=leader['family'],Q=quality(leader['mean'],weight))
    np.savez_compressed(out/'positions.npz',**positions)
    result=dict(status='exposed_development_only',adopt=False,plan_sha256=sha(PLAN),inputs=inputs,
        original_results_sha256=sha(ORIGINAL/'results.json'),positions_sha256=sha(out/'positions.npz'),
        sources={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'polity/settlement_intensity.py',ROOT/'scripts/settlement_locations_earth.py']},
        rows=rows,ranking=ranking,references=references,pareto_frontier=frontier,location_weight_sensitivity=sensitivity,
        development_lead=best_new['variant'] if best_new else None,
        improves_best_fixed_Q=bool(best_new and best_new['Q']>references[0]['Q']),
        new_Q_gain=best_new['Q']-references[0]['Q'] if best_new else None,
        caveat='Relative centre intensity is not population or occupation age. Both pools exposed. Transfer and joint food/staffing/control integration remain pending.')
    write(out/'results.json',result)
    print('Best adaptive',json.dumps(best_new),flush=True)
    print('Best fixed',json.dumps(references[0]),flush=True)
    print('History/seed grid',len(rows),'evaluations; objective sensitivity',sensitivity,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    run(parser.parse_args().out)
