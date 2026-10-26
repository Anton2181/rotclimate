"""Test a bounded geometry path between rejected native r39 world endpoints."""
from pathlib import Path
import importlib.metadata
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json
from check_r39_world import assert_world_only,world_failures
from check_r39_world_transfer import corrected,violation,measure
from rotclimate.calibrate import WORLD_GENES


def blend_world(a,b,fraction):
    if not 0<=fraction<=1:raise ValueError('Interpolation outside endpoints')
    assert_world_only(b,a)
    fields={key:(1-fraction)*getattr(a,key)+fraction*getattr(b,key)
            for key in WORLD_GENES if not key.startswith('tier') and key not in {'tilt','retrograde'}}
    fields['tier_tops']=tuple(round((1-fraction)*x+fraction*y) for x,y in zip(a.tier_tops,b.tier_tops))
    result=a.replace(**fields);assert_world_only(result,a)
    return result


def blend_metrics(a,b,fraction):
    return {key:blend_metrics(value,b[key],fraction) if isinstance(value,dict)
            else (1-fraction)*value+fraction*b[key]
            for key,value in a.items() if key!='numerics'}


def main():
    folder=ROOT/'calibration/map_world_r39_balance';plan_path=folder/'plan.json'
    plan=json.loads(plan_path.read_text());parent=ROOT/plan['parent']
    review=json.loads((parent/'review.json').read_text())
    if not review.get('complete'):raise ValueError('Parent verification is unfinished')
    if review['eligible_for_publication']:
        print('Parent already qualified; skip interpolation and publish that world.',flush=True);return
    endpoints=plan['endpoints'];native={r['name']:r for r in review['native']}
    records=[native[f'native_{i:03d}'] for i in endpoints]
    if len(native)!=2 or not all(r['failures'] and r['metrics']['numerics']['all_checks_passed'] for r in records):
        raise ValueError('Expected exactly two rejected, numerically converged endpoints')
    params=[load_params(ROOT/r['params']) for r in records]
    start=load_params(ROOT/'calibration/map_world_r39/start.json')
    for p in params:assert_world_only(p,start)
    # The parent is immutable evidence, even though the normal atlas may later be promoted.
    parent_protocol=json.loads((parent/'protocol.json').read_text())
    for name,expected in parent_protocol['source_hashes'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Parent scientific input changed: '+name)
    summary=json.loads((ROOT/'atlases/earth_fit/summary.json').read_text())
    reference=dict(zonefit=summary['zonefit'],accuracy=summary['strict_accuracy'],
                   recall=summary['recall'],mediterranean=summary['mediterranean'])
    out=ROOT/'output/r39_world_balance';out.mkdir(exist_ok=True)
    sources=list((ROOT/'rotclimate').glob('*.py'))+list((ROOT/'data/source').glob('*'))+[
        Path(__file__),ROOT/'scripts/check_r39_world.py',ROOT/'scripts/check_r39_world_transfer.py',
        plan_path,parent/'review.json',parent/'protocol.json',ROOT/'atlases/earth_fit/params.json',
        ROOT/'atlases/earth_fit/summary.json',ROOT/'calibration/map_world_r39/start.json']
    sources += [ROOT/r['params'] for r in records]
    run=freeze(out/'protocol.json',dict(plan=plan,
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy']},
        source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in sources if p.is_file()}))
    screen=[];proposals=folder/'proposals';proposals.mkdir(exist_ok=True)
    for index,fraction in enumerate(plan['fractions_toward_65'],1):
        tag=f'balance_{index:03d}';p=blend_world(*params,fraction).replace(downsample=16)
        file=proposals/(tag+'.json');p.replace(downsample=8).to_json(file)
        print(tag+': intermediate-resolution layouts 1–3',flush=True)
        try:
            metrics=measure(p,plan['layouts'],tag+'_screen',out,run)
            anchor16=blend_metrics(*(review['intermediate'][str(i)]['metrics'] for i in endpoints),fraction)
            anchor8=blend_metrics(*(r['metrics'] for r in records),fraction)
            prediction=corrected(metrics,anchor16,anchor8)
            row=dict(name=tag,params=str(file.relative_to(ROOT)),fraction=fraction,metrics=metrics,
                     prediction=prediction,violation=violation(prediction,reference),status='passed')
        except Exception as error:row=dict(name=tag,status='failed',error=repr(error))
        screen.append(row);write_json(out/'progress.json',dict(complete=False,screen=screen))
    ranked=sorted((r for r in screen if r['status']=='passed'),key=lambda r:(r['violation'],-r['prediction']['zonefit'],r['name']))
    write_json(out/'selection.json',dict(selected=ranked[0]['name'] if ranked else None,
        ranking=[dict(name=r['name'],violation=r['violation'],prediction=r['prediction']) for r in ranked]))
    native_results=[];transfer=None;selected=None
    if ranked:
        row=ranked[0];p=load_params(ROOT/row['params']);tag=row['name']+'_native'
        print(tag+': actual native-resolution verification',flush=True)
        try:
            metrics=measure(p,plan['layouts'],tag,out,run);failures=world_failures(metrics,reference,native=True)
            native_results.append(dict(name=tag,params=row['params'],metrics=metrics,failures=failures))
            if not failures:selected=(tag,p,row['params'])
        except Exception as error:native_results.append(dict(name=tag,failures=[repr(error)]))
        write_json(out/'progress.json',dict(complete=False,screen=screen,native=native_results))
    if selected:
        try:
            old=measure(load_params(ROOT/'atlases/earth_fit/params.json').replace(downsample=16),plan['transfer_layouts'],'transfer_reference',out,run)
            new=measure(selected[1].replace(downsample=16),plan['transfer_layouts'],'transfer_candidate',out,run)
            failures=[]
            if new['zonefit']<old['zonefit']:failures.append('Additional-layout zonefit worsened')
            if new['accuracy']<old['accuracy']-.01:failures.append('Additional-layout strict accuracy loss exceeds 0.01')
            transfer=dict(reference=old,candidate=new,passed=not failures,failures=failures)
        except Exception as error:transfer=dict(passed=False,failures=[repr(error)])
    passed=bool(selected and transfer['passed'])
    final=dict(complete=True,identity=run,screen=screen,native=native_results,transfer=transfer,
               eligible_for_publication=passed,params=selected[2] if passed else None,
               checkpoint=str((out/(selected[0]+'.pkl')).relative_to(ROOT)) if passed else None)
    write_json(out/'review.json',final);write_json(out/'progress.json',final)
    print('Geometry balance complete; publication eligible:',passed,flush=True)


if __name__=='__main__':main()
