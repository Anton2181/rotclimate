"""Bounded physical screens to reduce grey land in the Whittaker atlas.

Runs seven predeclared humidity/lapse/orography profiles at ds32, then checks
the two best at ds16. Every profile classifies a three-layout mean climate,
including source-resolution terrain for its diagram coverage. No rainfall,
temperature or biome IDs are clipped into an envelope.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import pickle
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rotclimate.config import Params
from rotclimate import biome_targets as B

OUT=ROOT/'output/whittaker_coverage_20261022'
PROFILES={
 'baseline':{},
 'rh78_lapse45':dict(ocean_rh=.78,lapse_rate=4.5),
 'rh72_lapse45':dict(ocean_rh=.72,lapse_rate=4.5),
 'rh66_lapse45':dict(ocean_rh=.66,lapse_rate=4.5),
 'rh72_lapse4_orog175':dict(ocean_rh=.72,lapse_rate=4.,orographic=1.75),
 'rh66_lapse4_orog175':dict(ocean_rh=.66,lapse_rate=4.,orographic=1.75),
 'rh72_lapse5_orog175':dict(ocean_rh=.72,lapse_rate=5.,orographic=1.75),
}


def write(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)


def run_case(name,downsample,base,identity):
    from rotclimate.model import run_ensemble
    from rotclimate.score import evaluate,objective
    from rotclimate.calibrate import mediterranean_shares
    started=time.time();tag=f'ds{downsample}_{name}';path=OUT/'cases'/f'{tag}.json'
    p=base.replace(**PROFILES[name],downsample=downsample)
    if path.exists():
        old=json.loads(path.read_text())
        if old['identity']!=identity or old['params']!=json.loads(json.dumps(asdict(p))):
            raise ValueError('Case inputs changed: '+tag)
        return old
    row=dict(name=name,downsample=downsample,identity=identity,params=asdict(p))
    try:
        result=run_ensemble(p,[1,2,3],workers=1)
        if not result.numerics['all_checks_passed']:raise RuntimeError('Observed convergence checks failed')
        ev=evaluate(result);valid=result.grid.inmap & result.grid.land
        strict=B.evaluate(ev['indices'],result.grid.target,valid)
        cover=B.rendered_coverage(result)
        row.update(status='passed',strict=strict,coverage=cover,score=B.covered_score(strict['score'],cover),
                   zonefit=objective(ev,'zonefit'),exact_zone_agreement=ev['accuracy'],
                   mediterranean=mediterranean_shares(result,ev),observed_numerics=result.numerics)
        cache=OUT/'checkpoints'/f'{tag}.pkl';tmp=cache.with_suffix('.tmp')
        with tmp.open('wb') as file:pickle.dump(dict(params=asdict(p),identity=identity,result=result),file)
        tmp.replace(cache)
    except Exception as exc:
        row.update(status='failed',error=repr(exc))
    row['seconds']=round(time.time()-started,2);write(path,row);return row


def ranked(rows):
    return sorted((r for r in rows if r['status']=='passed'),key=lambda r:-r['score'])


def batch(names,ds,base,identity,workers):
    rows=[]
    with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn')) as pool:
        jobs={pool.submit(run_case,name,ds,base,identity):name for name in names}
        for job in as_completed(jobs):
            row=job.result();rows.append(row)
            print(json.dumps({k:row[k] for k in ['name','downsample','status','seconds']} | (
                dict(outside=row['coverage']['outside_share'],strict=row['strict']['score'],score=row['score'])
                if row['status']=='passed' else dict(error=row['error']))),flush=True)
    return sorted(rows,key=lambda r:r['name'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workers',type=int,default=2)
    args=ap.parse_args()
    if not 1<=args.workers<=2:ap.error('Use one or two workers')
    for folder in ['cases','checkpoints']: (OUT/folder).mkdir(parents=True,exist_ok=True)
    base=Params.from_json(ROOT/'atlases/whittaker_fit/params.json')
    sources=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),ROOT/'data/whittaker_coverage.json',ROOT/'data/biome_target_crosswalk.json']
    protocol=dict(base=asdict(base),profiles=PROFILES,seeds=[1,2,3],steps_per_year=base.steps_per_year,
        coarse_downsample=32,refinement_downsample=16,coverage_policy=B.coverage_policy(),
        sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        selection='Two highest coverage-aware scores at ds32, then highest ds16 score among publication-eligible profiles. No target envelopes or fields modified.')
    protocol=json.loads(json.dumps(protocol));path=OUT/'protocol.json'
    if path.exists() and json.loads(path.read_text())!=protocol:raise ValueError('Frozen screen inputs changed')
    write(path,protocol);identity=hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest()
    coarse=batch(list(PROFILES),32,base,identity,args.workers)
    candidates=[r['name'] for r in ranked(coarse) if r['name']!='baseline'][:2]
    if len(candidates)<2:raise RuntimeError('Not enough successful candidate profiles')
    fine=batch(candidates,16,base,identity,args.workers)
    policy=B.coverage_policy()
    eligible=[r for r in ranked(fine) if r['coverage']['outside_share']<=policy['publication_outside_limit']
              and r['strict']['score']>=policy['publication_minimum_strict_score']]
    review=dict(coarse=coarse,refinement=fine,selected=eligible[0]['name'] if eligible else None,
                note='Three-layout mean climate; source-terrain coverage; training layouts reused. Publication still needs native ds8 verification.')
    write(OUT/'review.json',review)
    if eligible:
        p=base.replace(**PROFILES[eligible[0]['name']],downsample=8)
        p.to_json(OUT/'selected_params.json')
        print('Selected '+eligible[0]['name']+' for native verification',flush=True)
    else:print('No profile met publication gates; retain the current atlas',flush=True)


if __name__=='__main__':main()
