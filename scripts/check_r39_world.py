"""Native-resolution and additional-layout checks before r39 atlas publication."""
from dataclasses import asdict
from pathlib import Path
import json
import pickle
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json,identity
from rotclimate.config import Params
from rotclimate.model import run_ensemble
from rotclimate.score import evaluate,objective
from rotclimate.calibrate import mediterranean_shares
from rotclimate.calibrate import WORLD_GENES


def assert_world_only(candidate,start):
    locked=['tilt','retrograde','planet_radius','year_days','eccentricity','perihelion_after_solstice',
            'solar_flux','greenhouse_wm2','map_width_mi','map_height_mi']
    for key in locked:
        if not np.isclose(getattr(candidate,key),getattr(start,key),rtol=0,atol=1e-10):
            raise ValueError('Locked planet changed: '+key)
    allowed={k for k in WORLD_GENES if not k.startswith('tier')}|{'tier_tops','downsample'}
    for key,value in asdict(candidate).items():
        if key not in allowed and value!=getattr(start,key):raise ValueError('Shared physics changed: '+key)


def world_failures(candidate,reference,*,native):
    failures=[]
    if native:
        if candidate['zonefit']<reference['zonefit']+.001:failures.append('Native zonefit improvement below 0.001')
        if candidate['accuracy']<reference['accuracy']:failures.append('Native strict accuracy worsened')
        recall_allowance=.02;dry_allowance=.005;cs_allowance=.02
    else:
        if candidate['accuracy']<reference['accuracy']-.01:failures.append('Coarse strict accuracy lost more than 0.01')
        recall_allowance=.03;dry_allowance=.01;cs_allowance=.03
    for zone,value in reference['recall'].items():
        if candidate['recall'][zone]<value-recall_allowance:failures.append(zone+': recall exceeded loss allowance')
    if candidate['mediterranean']['dry_share']>reference['mediterranean']['dry_share']+dry_allowance:
        failures.append('Mediterranean dry share exceeded allowance')
    if candidate['mediterranean']['cs_share']<reference['mediterranean']['cs_share']-cs_allowance:
        failures.append('Mediterranean Cs share exceeded loss allowance')
    return failures


def build_identity(p,seeds):
    return dict(params=json.loads(json.dumps(asdict(p))),seeds=seeds,
        sources={f.name:file_hash(f) for f in (ROOT/'rotclimate').glob('*.py')
                 if f.name not in {'atlas.py','render.py','biomes.py','climate_fields.py'}},
        map_inputs={f.name:file_hash(f) for f in (ROOT/'data/source').iterdir() if f.is_file()})


def measured(p,seeds,checkpoint,run_id):
    expected=build_identity(p,seeds)
    if checkpoint.exists():
        with checkpoint.open('rb') as stream:saved=pickle.load(stream)
        if saved['identity']!=expected or saved['run']!=run_id:raise ValueError('Changed saved world inputs')
        result=saved['result']
    else:
        result=run_ensemble(p,seeds,workers=2)
        if result.numerics.get('all_checks_passed') is not True:raise ValueError('World numerical checks failed')
        with checkpoint.with_suffix('.tmp').open('wb') as stream:
            pickle.dump(dict(identity=expected,run=run_id,result=result),stream)
        checkpoint.with_suffix('.tmp').replace(checkpoint)
    if result.numerics.get('all_checks_passed') is not True:raise ValueError('Unverified cached world')
    ev=evaluate(result)
    return dict(zonefit=objective(ev,'zonefit'),accuracy=ev['accuracy'],recall=ev['recall'],
                mediterranean=mediterranean_shares(result,ev),numerics=result.numerics)


def main():
    folder=ROOT/'calibration/map_world_r39';plan=json.loads((folder/'plan.json').read_text())
    if not (folder/'best_result.json').exists():raise SystemExit('World calibration must finish before finalist selection')
    rows=[json.loads(line) for line in (folder/'world/evals.jsonl').read_text().splitlines() if line.strip()]
    if len(rows)>plan['evaluations']:raise ValueError('World search exceeded frozen budget')
    old=json.loads((folder/'coarse_old_control.json').read_text())
    old_metrics=dict(zonefit=old['score'],accuracy=old['accuracy'],recall=old['recall'],mediterranean=old['mediterranean'])
    eligible=[];seen=set();screen=[]
    for row in sorted(rows,key=lambda r:(-r['score'],r['eval'])):
        if row.get('error') or row.get('raced') or not row.get('observed_numerics',{}).get('all_checks_passed'):continue
        key=identity(row['params'])
        if key in seen:continue
        seen.add(key)
        metric=dict(zonefit=row['score'],accuracy=row['accuracy'],recall=row['recall'],mediterranean=row['mediterranean'])
        failures=world_failures(metric,old_metrics,native=False)
        screen.append(dict(eval=row['eval'],score=row['score'],failures=failures))
        if not failures:eligible.append(row)
    eligible=eligible[:2]
    out=ROOT/'output/r39_world_publication';out.mkdir(exist_ok=True)
    sources=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),folder/'plan.json',folder/'protocol.json',
        folder/'world/evals.jsonl',folder/'world/calibration_config.json',ROOT/'atlases/earth_fit/params.json',ROOT/'atlases/earth_fit/summary.json']
    run=freeze(out/'protocol.json',dict(plan=plan,coarse_screen=screen,finalists=[r['eval'] for r in eligible],
        sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources}))
    write_json(out/'coarse_selection.json',dict(screen=screen,selected=[r['eval'] for r in eligible]))
    published=json.loads((ROOT/'atlases/earth_fit/summary.json').read_text())
    reference=dict(zonefit=published['zonefit'],accuracy=published['strict_accuracy'],recall=published['recall'],mediterranean=published['mediterranean'])
    native=[];selected=None;params_folder=folder/'finalists';params_folder.mkdir(exist_ok=True)
    start=load_params(folder/'start.json')
    for row in eligible:
        tag=f'candidate_{row["eval"]:03d}';p=Params(**row['params']).replace(downsample=8)
        assert_world_only(p,start)
        parameter_file=params_folder/(tag+'.json');p.to_json(parameter_file)
        print(tag+': evaluating native layouts 1–3',flush=True)
        try:
            metric=measured(p,plan['layouts'],out/(tag+'.pkl'),run)
            failures=world_failures(metric,reference,native=True)
            native.append(dict(name=tag,metrics=metric,failures=failures,params=str(parameter_file.relative_to(ROOT))))
        except Exception as error:
            native.append(dict(name=tag,failures=[repr(error)]));failures=[repr(error)]
        write_json(out/'progress.json',dict(complete=False,native=native))
        print(tag+': '+('native passed' if not failures else 'native failed: '+str(failures)),flush=True)
        if not failures:selected=(tag,p,parameter_file);break
    transfer=None
    if selected:
        tag,p,parameter_file=selected;seeds=[17,23]
        try:
            a=measured(load_params(ROOT/'atlases/earth_fit/params.json').replace(downsample=16),seeds,out/'transfer_reference.pkl',run)
            b=measured(p.replace(downsample=16),seeds,out/'transfer_candidate.pkl',run)
            failures=[]
            if b['zonefit']<a['zonefit']:failures.append('Additional-layout zonefit worsened')
            if b['accuracy']<a['accuracy']-.01:failures.append('Additional-layout strict accuracy lost more than 0.01')
            transfer=dict(reference=a,candidate=b,failures=failures,passed=not failures)
        except Exception as error:
            transfer=dict(failures=[repr(error)],passed=False)
    passed=bool(selected and transfer['passed'])
    review=dict(complete=True,identity=run,native=native,transfer=transfer,eligible_for_publication=passed,
        params=str(selected[2].relative_to(ROOT)) if passed else None,
        checkpoint=str((out/(selected[0]+'.pkl')).relative_to(ROOT)) if passed else None,
        decision='Build staging atlas from verified native checkpoint.' if passed else 'Keep current canonical r38 atlas; no world qualifies.')
    write_json(out/'review.json',review);write_json(out/'progress.json',review)
    print(json.dumps(review,indent=2),flush=True)


if __name__=='__main__':main()
