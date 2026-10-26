"""Bounded multi-resolution world selection, with persistent layout results."""
from dataclasses import asdict
from pathlib import Path
from multiprocessing import Pool
import json
import pickle
import sys
import importlib.metadata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json,identity
from check_r39_world import assert_world_only,build_identity,world_failures
from rotclimate.config import Params
from rotclimate.model import ClimateModel,ensemble_mean
from rotclimate.score import evaluate,objective
from rotclimate.calibrate import mediterranean_shares


def corrected(metric,coarse_anchor,native_anchor):
    fraction=lambda value:float(np.clip(value,0.,1.))
    return dict(zonefit=metric['zonefit']+native_anchor['zonefit']-coarse_anchor['zonefit'],
        accuracy=fraction(metric['accuracy']+native_anchor['accuracy']-coarse_anchor['accuracy']),
        recall={k:fraction(metric['recall'][k]+native_anchor['recall'][k]-coarse_anchor['recall'][k]) for k in native_anchor['recall']},
        mediterranean={k:fraction(metric['mediterranean'][k]+native_anchor['mediterranean'][k]-coarse_anchor['mediterranean'][k]) for k in native_anchor['mediterranean']})


def violation(metric,ref):
    return (max(0.,ref['zonefit']+.001-metric['zonefit'])+max(0.,ref['accuracy']-metric['accuracy'])+
        sum(max(0.,v-.02-metric['recall'][k]) for k,v in ref['recall'].items())+
        max(0.,metric['mediterranean']['dry_share']-ref['mediterranean']['dry_share']-.005)+
        max(0.,ref['mediterranean']['cs_share']-.02-metric['mediterranean']['cs_share']))


def metric_from_row(row):
    return dict(zonefit=row['score'],accuracy=row['accuracy'],recall=row['recall'],mediterranean=row['mediterranean'])


def member(job):
    params,seed,path,run=job;p=Params(**params).replace(beyond_seed=seed);path=Path(path)
    expected=build_identity(p,[seed])
    failure=path.with_suffix('.failed.json')
    if failure.exists():raise ValueError('Saved layout failure needs diagnosis: '+str(failure))
    if path.exists():
        with path.open('rb') as stream:saved=pickle.load(stream)
        if saved['identity']!=expected or saved['run']!=run:raise ValueError('Changed saved member inputs')
        result=saved['result']
    else:
        try:
            result=ClimateModel(p).run()
            if result.numerics.get('all_checks_passed') is not True:raise ValueError('Member numerical checks failed')
        except Exception as error:
            write_json(failure,dict(identity=expected,run=run,error=repr(error)))
            raise
        with path.with_suffix('.tmp').open('wb') as stream:pickle.dump(dict(identity=expected,run=run,result=result),stream)
        path.with_suffix('.tmp').replace(path)
    if not result.numerics.get('all_checks_passed'):raise ValueError('Unverified saved member')
    print(path.stem+': verified',flush=True)
    return result


def measure(p,seeds,tag,out,run):
    folder=out/'members';folder.mkdir(exist_ok=True)
    checkpoint=out/(tag+'.pkl');expected=build_identity(p,seeds)
    if checkpoint.exists():
        with checkpoint.open('rb') as stream:saved=pickle.load(stream)
        if saved['identity']!=expected or saved['run']!=run:raise ValueError('Changed saved ensemble inputs')
        result=saved['result']
    else:
        jobs=[(asdict(p),int(s),str(folder/f'{tag}_seed{s}.pkl'),run) for s in seeds]
        with Pool(2) as pool:results=pool.map(member,jobs)
        result=ensemble_mean(results)
        with checkpoint.with_suffix('.tmp').open('wb') as stream:pickle.dump(dict(identity=expected,run=run,result=result),stream)
        checkpoint.with_suffix('.tmp').replace(checkpoint)
    if not result.numerics.get('all_checks_passed'):raise ValueError('Unverified ensemble')
    ev=evaluate(result)
    return dict(zonefit=objective(ev,'zonefit'),accuracy=ev['accuracy'],recall=ev['recall'],
                mediterranean=mediterranean_shares(result,ev),numerics=result.numerics)


def main():
    folder=ROOT/'calibration/map_world_r39_transfer';plan_path=folder/'plan.json';plan=json.loads(plan_path.read_text())
    parent=ROOT/plan['parent_search'];old_review_path=ROOT/plan['native_anchor'];old_review=json.loads(old_review_path.read_text())
    if old_review['eligible_for_publication'] or len(old_review['native'])!=1:raise ValueError('Unexpected parent result')
    anchor_eval=int(old_review['native'][0]['name'].removeprefix('candidate_'));native_anchor=old_review['native'][0]['metrics']
    rows=[json.loads(line) for line in (parent/'world/evals.jsonl').read_text().splitlines() if line.strip()]
    anchor=next(r for r in rows if r['eval']==anchor_eval);initial=next(r for r in rows if r.get('stage')=='initial')
    parent_protocol=json.loads((ROOT/'output/r39_world_publication/protocol.json').read_text())
    for name,expected in parent_protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Parent scientific input changed: '+name)
    pub=json.loads((ROOT/'atlases/earth_fit/summary.json').read_text())
    reference=dict(zonefit=pub['zonefit'],accuracy=pub['strict_accuracy'],recall=pub['recall'],mediterranean=pub['mediterranean'])
    ranked=[];seen={identity(anchor['params'])}
    for row in rows:
        if row.get('error') or row.get('raced') or not row.get('observed_numerics',{}).get('all_checks_passed'):continue
        key=identity(row['params'])
        if key in seen:continue
        seen.add(key);prediction=corrected(metric_from_row(row),metric_from_row(anchor),native_anchor)
        ranked.append((violation(prediction,reference),-prediction['zonefit'],row['eval'],row,prediction))
    ranked.sort(key=lambda r:r[:3]);chosen=[r[3] for r in ranked[:5]]
    for row in [initial,anchor]:
        if not any(identity(row['params'])==identity(r['params']) for r in chosen):chosen.append(row)
    out=ROOT/'output/r39_world_transfer';out.mkdir(exist_ok=True)
    sources=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),ROOT/'scripts/check_r39_world.py',plan_path,
        old_review_path,parent/'world/evals.jsonl',parent/'start.json',ROOT/'atlases/earth_fit/params.json',ROOT/'atlases/earth_fit/summary.json']
    run=freeze(out/'protocol.json',dict(plan=plan,intermediate_candidates=[r['eval'] for r in chosen],
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy']},
        source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources}))
    write_json(out/'selection.json',dict(anchor=anchor_eval,selected=[r['eval'] for r in chosen],
        predictions=[dict(eval=r[2],violation=r[0],metrics=r[4]) for r in ranked]))
    start=load_params(parent/'start.json');records={}
    for row in chosen:
        tag=f'screen_{row["eval"]:03d}';p=Params(**row['params']).replace(downsample=16);assert_world_only(p,start)
        print(tag+': intermediate-resolution layouts 1–3',flush=True)
        try:records[str(row['eval'])]=dict(status='passed',metrics=measure(p,plan['layouts'],tag,out,run))
        except Exception as error:records[str(row['eval'])]=dict(status='failed',error=repr(error))
        write_json(out/'progress.json',dict(complete=False,intermediate=records))
    anchor_record=records[str(anchor_eval)]
    if anchor_record['status']!='passed':raise RuntimeError('Intermediate anchor failed; no native selection')
    rankings=[]
    for row in chosen:
        record=records[str(row['eval'])]
        if row['eval']==anchor_eval or record['status']!='passed':continue
        prediction=corrected(record['metrics'],anchor_record['metrics'],native_anchor)
        rankings.append((violation(prediction,reference),-prediction['zonefit'],row['eval'],row,prediction))
    rankings.sort(key=lambda r:r[:3]);write_json(out/'native_selection.json',dict(selected=[r[2] for r in rankings[:2]],
        predictions=[dict(eval=r[2],violation=r[0],metrics=r[4]) for r in rankings]))
    native=[];selected=None;finalists=folder/'finalists';finalists.mkdir(exist_ok=True)
    for _,_,index,row,prediction in rankings[:2]:
        tag=f'native_{index:03d}';p=Params(**row['params']).replace(downsample=8);assert_world_only(p,start)
        file=finalists/(tag+'.json');p.to_json(file)
        print(tag+': actual native-resolution verification',flush=True)
        try:
            metrics=measure(p,plan['layouts'],tag,out,run);failures=world_failures(metrics,reference,native=True)
            native.append(dict(name=tag,metrics=metrics,failures=failures,params=str(file.relative_to(ROOT))))
        except Exception as error:native.append(dict(name=tag,failures=[repr(error)]));failures=[repr(error)]
        write_json(out/'progress.json',dict(complete=False,intermediate=records,native=native))
        if not failures:selected=(tag,p,file);break
    transfer=None
    if selected:
        try:
            a=measure(load_params(ROOT/'atlases/earth_fit/params.json').replace(downsample=16),[17,23],'transfer_reference',out,run)
            b=measure(selected[1].replace(downsample=16),[17,23],'transfer_candidate',out,run)
            failures=[]
            if b['zonefit']<a['zonefit']:failures.append('Additional-layout zonefit worsened')
            if b['accuracy']<a['accuracy']-.01:failures.append('Additional-layout strict accuracy loss exceeds 0.01')
            transfer=dict(reference=a,candidate=b,passed=not failures,failures=failures)
        except Exception as error:transfer=dict(passed=False,failures=[repr(error)])
    passed=bool(selected and transfer['passed'])
    review=dict(complete=True,identity=run,intermediate=records,native=native,transfer=transfer,eligible_for_publication=passed,
        params=str(selected[2].relative_to(ROOT)) if passed else None,
        checkpoint=str((out/(selected[0]+'.pkl')).relative_to(ROOT)) if passed else None)
    write_json(out/'review.json',review);write_json(out/'progress.json',review)
    print('Supplemental world verification complete; publication eligible:',passed,flush=True)


if __name__=='__main__':main()
