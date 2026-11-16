"""Sole painted northern-steppe target; isolated bounded world/planet experiment."""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[_key]='1'
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import pickle
import subprocess
import sys
import time

import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from rotclimate.config import Params
from rotclimate import calibrate as C
from rotclimate.model import ClimateModel,ensemble_mean
from rotclimate.koppen import monthly_stats,climate_indices,classify,CODES
from rotclimate.score import memberships,evaluate
from scipy.ndimage import label

FOLDER=ROOT/'calibration/northern_steppe_only_20261116'
OUT=ROOT/'output/northern_steppe_only_20261116'
PLAN=FOLDER/'plan.json'
SPACE=[(n,(-182.5 if n=='perihelion_after_solstice' else lo),(182.5 if n=='perihelion_after_solstice' else hi))
       for n,lo,hi in C.SPACE_WORLD_PLUS if not n.startswith('tier') and n!='far_pole_land']+[('ebm_land_scale',.4,1.8)]


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def metrics(result):
    p=result.params;g=result.grid
    st=monthly_stats(result.T,result.P,result.days,p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
    ix=climate_indices(st['Tm'],st['Pm'],st['summer'])
    mem=memberships(ix)['cold_dry']; mask=g.inmap & g.land & (g.target==2)
    if not mask.any():raise ValueError('Empty steppe target')
    score=float(mem[mask].mean()); kop=classify(st['Tm'],st['Pm'],st['summer'])
    k=[CODES[int(i)] for i in kop[mask]]
    return dict(score=score,target_cells=int(mask.sum()),
        MAT=float(np.median(ix['MAT'][mask])),MAP=float(np.median(ix['MAP'][mask])),
        aridity=float(np.median(ix['aridity'][mask])),Tcold=float(np.median(ix['Tcold'][mask])),Thot=float(np.median(ix['Thot'][mask])),
        BSk_share=k.count('BSk')/len(k),BWk_share=k.count('BWk')/len(k),
        cold_dry_koppen_share=sum(v in ('BSk','BWk') for v in k)/len(k),
        monthly_T_median=[float(np.median(v[mask])) for v in st['Tm']],
        monthly_P_median=[float(np.median(v[mask])) for v in st['Pm']])


def score_job(job):
    index,x,base=job;t=time.monotonic()
    C._set_space(SPACE);p=C.decode(np.asarray(x),Params(**base))
    row=dict(eval=index,x=list(map(float,x)),params=asdict(p))
    try:
        result=ClimateModel(p).run();m=metrics(result)
        passed=bool(result.numerics and result.numerics['all_checks_passed'])
        if not passed or not np.isfinite(m['score']):raise ValueError('Numerical or nonfinite score failure')
        row.update(m,numerics_passed=True,
            numerics_sha256=hashlib.sha256(json.dumps(result.numerics,sort_keys=True).encode()).hexdigest())
    except Exception as e:row.update(score=-1.,numerics_passed=False,error=f'{type(e).__name__}: {e}')
    row['seconds']=time.monotonic()-t
    return row


def frozen_protocol(plan):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes(),'Commit exact declaration first'
    base=Params.from_json(ROOT/plan['baseline'].split(' (')[0])
    inputs=[PLAN,Path(__file__),ROOT/'atlases/earth_fit/params.json',ROOT/base.terrain_file,*sorted((ROOT/'rotclimate').glob('*.py'))]
    inputs += [p for p in sorted((ROOT/'data/source').rglob('*')) if p.is_file()]
    protected=[p for p in sorted((ROOT/'atlases/earth_fit').rglob('*')) if p.is_file()]
    protocol=dict(plan_sha256=sha(PLAN),base=asdict(base),space=SPACE,
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},
        protected_sha256={str(p.relative_to(ROOT)):sha(p) for p in protected},
        objective_weights=dict(cold_dry=1,cold_wet=0,warm_wet=0,med=0,swamp=0,tree=0,hot_dry=0,
            spill_precision=0,realism=0))
    path=FOLDER/'protocol.json'
    if path.exists():assert json.loads(path.read_text())==json.loads(json.dumps(protocol))
    else:write(path,protocol)
    return base,protocol


def search(plan,base,resume):
    import cma
    OUT.mkdir(parents=True,exist_ok=True);C._set_space(SPACE)
    start=base.replace(downsample=plan['search']['downsample'],beyond_seed=1)
    x0=C.encode(start);roundtrip=C.decode(x0,start)
    for key in asdict(start):assert getattr(roundtrip,key)==getattr(start,key) or (isinstance(getattr(start,key),(float,int)) and np.isclose(getattr(roundtrip,key),getattr(start,key),rtol=0,atol=1e-10)),key
    budget=plan['search']['evaluations'];pop=plan['search']['population'];state=OUT/'state.pkl'
    if resume and state.exists():
        with state.open('rb') as f:es,best,n=pickle.load(f)
        log=(OUT/'evals.jsonl').open('a')
    else:
        assert not (OUT/'evals.jsonl').exists(),'Use --resume for existing search'
        es=cma.CMAEvolutionStrategy(x0,plan['search']['sigma'],dict(bounds=[0,1],popsize=pop,seed=plan['search']['seed'],verbose=-9))
        log=(OUT/'evals.jsonl').open('w');best=score_job((1,x0,asdict(start)));n=1
        assert best['numerics_passed'],best
        log.write(json.dumps(best)+'\n');log.flush();write(OUT/'best.json',best);Params(**best['params']).to_json(OUT/'best_params.json')
        print('Baseline sole-target membership',best['score'],flush=True)
    with ProcessPoolExecutor(max_workers=plan['search']['workers'],mp_context=mp.get_context('spawn')) as pool:
        while n+pop<=budget and not es.stop():
            xs=es.ask();first=n+1;futures={pool.submit(score_job,(first+i,x,asdict(start))):i for i,x in enumerate(xs)};rows=[None]*pop
            for future in as_completed(futures):
                row=future.result();rows[futures[future]]=row;log.write(json.dumps(row)+'\n');log.flush()
                if row['numerics_passed'] and (row['score'],-row['eval'])>(best['score'],-best['eval']):
                    best=row;write(OUT/'best.json',best);Params(**best['params']).to_json(OUT/'best_params.json')
                print('eval',row['eval'],'score',round(row['score'],6),'best',round(best['score'],6),'seconds',round(row['seconds'],1),row.get('error',''),flush=True)
            n+=pop;es.tell(xs,[-r['score'] for r in rows])
            with state.open('wb') as f:pickle.dump((es,best,n),f)
    log.close();write(OUT/'search.json',dict(attempted=n,budget=budget,termination=dict(es.stop()) if es.stop() else {'budget_complete':True},best_eval=best['eval'],best_score=best['score']))
    return best


def compare(plan,base,best):
    (OUT/'members').mkdir(exist_ok=True);results={};draws={};arrays={};numerics={}
    for name,p in [('baseline',base),('candidate',Params(**best['params']))]:
        members=[];draws[name]=[];numerics[name]=[]
        for seed in [1,2,3]:
            p=p.replace(downsample=16,beyond_seed=seed)
            print('Final comparison',name,'ds16 layout',seed,flush=True)
            r=ClimateModel(p).run();assert r.numerics['all_checks_passed']
            members.append(r);draws[name].append(metrics(r));numerics[name].append(r.numerics)
            np.savez_compressed(OUT/'members'/f'{name}_{seed}.npz',T=r.T,P=r.P,days=r.days)
        r=ensemble_mean(members);ev=evaluate(r);st=monthly_stats(r.T,r.P,r.days,p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
        ix=climate_indices(st['Tm'],st['Pm'],st['summer']);g=r.grid;mask=g.inmap & g.land & (g.target==2)
        _,components=label(mask)
        results[name]=dict(**metrics(r),other_zone_diagnostics=dict(per_class=ev['per_class'],recall=ev['recall'],all_zone_accuracy=ev['accuracy']),
            target_components=int(components),target_latitude_range=[float(g.lat[mask].min()),float(g.lat[mask].max())],
            numerics_passed=bool(r.numerics['all_checks_passed']))
        for key,value in dict(Tm=st['Tm'],Pm=st['Pm'],MAT=ix['MAT'],MAP=ix['MAP'],aridity=ix['aridity'],
            Tcold=ix['Tcold'],Thot=ix['Thot'],koppen=classify(st['Tm'],st['Pm'],st['summer']),
            land=g.land,inmap=g.inmap,target=g.target,steppe_mask=mask,elev=g.elev,lat=g.lat).items():arrays[f'{name}__{key}']=value
    np.savez_compressed(OUT/'preview.npz',**arrays)
    write(OUT/'numerics.json',numerics);write(OUT/'comparison.json',dict(ensemble=results,members=draws,
        final_downsample=16,layouts=[1,2,3],selection_after_comparison=False,adopt=False,
        note='Other-zone diagnostics do not enter loss or selection. Single-layout ds64 fit; ds16 three-layout comparison is sensitivity, not native or independent Earth validation.'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--resume',action='store_true');ap.add_argument('--compare-only',action='store_true');a=ap.parse_args()
    plan=json.loads(PLAN.read_text());base,protocol=frozen_protocol(plan)
    if a.compare_only:best=json.loads((OUT/'best.json').read_text())
    else:best=search(plan,base,a.resume)
    free={n for n,*_ in SPACE}|{'downsample','beyond_seed'}
    for key,v in asdict(base).items():
        if key not in free:assert best['params'][key]==json.loads(json.dumps(v)),key
    compare(plan,base,best)
    for name,digest in {**protocol['sources_sha256'],**protocol['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    files=[p for p in OUT.iterdir() if p.is_file() and p.name not in ['state.pkl','results.json','review.json']]
    write(OUT/'results.json',dict(status='steppe_only_exploratory_world_fit_complete',protocol_sha256=sha(FOLDER/'protocol.json'),
        files_sha256={p.name:sha(p) for p in files},adopt=False,main_atlas_changed=False,
        sole_target='Existing painted northern cold_dry class2',new_validation_claim=False))


if __name__=='__main__':main()
