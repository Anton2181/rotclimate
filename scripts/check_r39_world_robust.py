"""Fit four fixed geometries across five development layouts, then validate once."""
from dataclasses import asdict
from pathlib import Path
import importlib.metadata
import json
import pickle
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json,identity
from check_r39_world import assert_world_only,world_failures
from check_r39_world_transfer import corrected,violation,measure
from rotclimate.model import ensemble_mean
from rotclimate.score import evaluate,objective
from rotclimate.calibrate import mediterranean_shares


def member_path(parent,name,seed):
    return parent/'members'/f'{name}_seed{seed}.pkl'


def result_from_member(path,p,seed):
    with Path(path).open('rb') as stream:cached=pickle.load(stream)
    result=cached['result']
    if identity(asdict(result.params))!=identity(asdict(p.replace(beyond_seed=seed))):
        raise ValueError('Cached member has different actual parameters: '+str(path))
    if not result.numerics.get('all_checks_passed'):raise ValueError('Unverified cached member')
    return result


def combine(paths,p,seeds):
    if len(paths)!=len(seeds) or len(set(seeds))!=len(seeds):raise ValueError('Need unique, paired training layouts')
    results=[result_from_member(path,p,seed) for path,seed in zip(paths,seeds)]
    result=ensemble_mean(results);ev=evaluate(result)
    return dict(zonefit=objective(ev,'zonefit'),accuracy=ev['accuracy'],recall=ev['recall'],
                mediterranean=mediterranean_shares(result,ev),numerics=result.numerics)


def training_failures(batches,combined,reference_batches,reference_combined,prediction,native_reference):
    failures=[]
    for name,metric in batches.items():
        if metric['zonefit']<reference_batches[name]['zonefit']:failures.append(name+': training batch zonefit worsened')
    if combined['zonefit']<reference_combined['zonefit']:failures.append('Five-layout training zonefit worsened')
    if violation(prediction,native_reference)>0:failures.append('Predicted native protections failed')
    return failures


def main():
    folder=ROOT/'calibration/map_world_r39_robust';plan_path=folder/'plan.json'
    plan=json.loads(plan_path.read_text());parent=ROOT/plan['parent']
    review=json.loads((parent/'review.json').read_text())
    if not review['complete'] or review['eligible_for_publication'] or not review['transfer'] or review['transfer']['passed']:
        raise ValueError('Expected the completed, rejected balance transfer attempt')
    parent_protocol=json.loads((parent/'protocol.json').read_text())
    for name,expected in parent_protocol['source_hashes'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Parent scientific input changed: '+name)
    p1,p2=[load_params(ROOT/f'calibration/map_world_r39_balance/proposals/balance_{i:03d}.json').replace(downsample=16) for i in [1,2]]
    proposals={'balance_001':p1,'balance_002':p2,
               'turn_minus1':p1.replace(north_bearing=p1.north_bearing-1),
               'turn_plus1':p1.replace(north_bearing=p1.north_bearing+1)}
    start=load_params(ROOT/'calibration/map_world_r39/start.json')
    for p in proposals.values():assert_world_only(p,start)
    old=load_params(ROOT/'atlases/earth_fit/params.json').replace(downsample=16)
    first,extra=plan['training_batches'];seeds=plan['training_layouts']
    if seeds!=first+extra or set(seeds)&set(plan['validation_layouts']):raise ValueError('Training/validation layouts overlap')
    reference_paths=[ROOT/f'output/earthlike_geography_20261025/checkpoints/control_{s}.pkl' for s in first]
    reference_paths += [member_path(parent,'transfer_reference',s) for s in extra]
    reused=list(reference_paths)
    for name in ['balance_001','balance_002']:reused += [member_path(parent,name+'_screen',s) for s in first]
    sources=list((ROOT/'rotclimate').glob('*.py'))+list((ROOT/'data/source').glob('*'))+[
        Path(__file__),ROOT/'scripts/check_r39_world.py',ROOT/'scripts/check_r39_world_transfer.py',
        ROOT/'scripts/earth_benchmark.py',ROOT/'scripts/local_benchmark_protocol.py',plan_path,
        parent/'review.json',parent/'protocol.json',ROOT/'output/earthlike_geography_20261025/protocol.json',
        ROOT/'atlases/earth_fit/params.json',ROOT/'atlases/earth_fit/summary.json',
        ROOT/'calibration/map_world_r39/start.json']
    sources += [ROOT/f'calibration/map_world_r39_balance/proposals/balance_{i:03d}.json' for i in [1,2]]
    out=ROOT/'output/r39_world_robust';out.mkdir(exist_ok=True)
    run=freeze(out/'protocol.json',dict(plan=plan,proposals={n:asdict(p) for n,p in proposals.items()},
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','numba']},
        source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources if p.is_file()},
        reused_member_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in reused}))
    reference_batches={'initial':combine(reference_paths[:3],old,first),'extra':review['transfer']['reference']}
    reference_combined=combine(reference_paths,old,seeds)
    if abs(reference_batches['initial']['zonefit']-json.loads((ROOT/'output/earthlike_geography_20261025/control.json').read_text())['zonefit'])>1e-12:
        raise ValueError('Archived initial control does not reproduce')
    summary=json.loads((ROOT/'atlases/earth_fit/summary.json').read_text())
    native_reference=dict(zonefit=summary['zonefit'],accuracy=summary['strict_accuracy'],recall=summary['recall'],mediterranean=summary['mediterranean'])
    write_json(out/'training_reference.json',dict(batches=reference_batches,combined=reference_combined,native=native_reference))
    anchor16=next(r['metrics'] for r in review['screen'] if r['name']=='balance_003')
    anchor8=review['native'][0]['metrics'];screen=[];param_folder=folder/'proposals';param_folder.mkdir(exist_ok=True)
    for name,p in proposals.items():
        print(name+': five-layout development screen',flush=True)
        param_path=param_folder/(name+'.json');p.replace(downsample=8).to_json(param_path)
        try:
            if name in ['balance_001','balance_002']:
                initial=next(r['metrics'] for r in review['screen'] if r['name']==name)
                initial_paths=[member_path(parent,name+'_screen',s) for s in first]
            else:
                initial=measure(p,first,name+'_initial',out,run)
                initial_paths=[member_path(out,name+'_initial',s) for s in first]
            more=measure(p,extra,name+'_extra',out,run)
            paths=initial_paths+[member_path(out,name+'_extra',s) for s in extra]
            combined=combine(paths,p,seeds);batches=dict(initial=initial,extra=more)
            prediction=corrected(initial,anchor16,anchor8)
            failures=training_failures(batches,combined,reference_batches,reference_combined,prediction,native_reference)
            row=dict(name=name,params=str(param_path.relative_to(ROOT)),batches=batches,combined=combined,
                     prediction=prediction,failures=failures,status='passed')
        except Exception as error:row=dict(name=name,status='failed',failures=[repr(error)])
        screen.append(row);write_json(out/'progress.json',dict(complete=False,screen=screen))
    ranked=sorted((r for r in screen if r['status']=='passed' and not r['failures']),key=lambda r:(-r['combined']['zonefit'],r['name']))
    write_json(out/'selection.json',dict(selected=ranked[0]['name'] if ranked else None,
        ranking=[dict(name=r['name'],zonefit=r['combined']['zonefit']) for r in ranked]))
    native=[];selected=None;transfer=None
    if ranked:
        row=ranked[0];p=load_params(ROOT/row['params']);tag=row['name']+'_native'
        print(tag+': actual native-resolution verification',flush=True)
        try:
            metrics=measure(p,first,tag,out,run);failures=world_failures(metrics,native_reference,native=True)
            native.append(dict(name=tag,params=row['params'],metrics=metrics,failures=failures))
            if not failures:selected=(tag,p,row['params'])
        except Exception as error:native.append(dict(name=tag,failures=[repr(error)]))
        write_json(out/'progress.json',dict(complete=False,screen=screen,native=native))
    if selected:
        print('Prospective five-layout validation; no further candidate selection',flush=True)
        try:
            a=measure(old,plan['validation_layouts'],'validation_reference',out,run)
            b=measure(selected[1].replace(downsample=16),plan['validation_layouts'],'validation_candidate',out,run)
            failures=[]
            if b['zonefit']<a['zonefit']:failures.append('Prospective-layout zonefit worsened')
            if b['accuracy']<a['accuracy']-.01:failures.append('Prospective-layout strict accuracy loss exceeds0.01')
            transfer=dict(reference=a,candidate=b,passed=not failures,failures=failures,layouts=plan['validation_layouts'])
        except Exception as error:transfer=dict(passed=False,failures=[repr(error)])
    passed=bool(selected and transfer['passed'])
    final=dict(complete=True,identity=run,screen=screen,native=native,transfer=transfer,
        eligible_for_publication=passed,params=selected[2] if passed else None,
        checkpoint=str((out/(selected[0]+'.pkl')).relative_to(ROOT)) if passed else None)
    write_json(out/'review.json',final);write_json(out/'progress.json',final)
    print('Robust world verification complete; publication eligible:',passed,flush=True)


if __name__=='__main__':main()
