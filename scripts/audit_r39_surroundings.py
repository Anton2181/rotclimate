"""Prospective, fixed-candidate nine-layout audit with a paired uncertainty gate."""
from pathlib import Path
import importlib.metadata
import json
import pickle
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json
from check_r39_world import assert_world_only,world_failures,build_identity
from check_r39_world_transfer import measure
from check_r39_world_robust import result_from_member
from rotclimate.score import evaluate,objective


def paired_interval(differences):
    values=np.sort(np.asarray(differences,float))
    if values.shape!=(9,) or not np.isfinite(values).all():raise ValueError('Need nine finite paired differences')
    rng=np.random.default_rng(394901)
    means=values[rng.integers(0,len(values),size=(20000,len(values)))].mean(1)
    lower,upper=np.quantile(means,[.025,.975])
    return dict(mean=float(values.mean()),lower=float(lower),upper=float(upper),
                passed=bool(values.mean()>0 and lower>0),draws=20000,seed=394901)


def main():
    folder=ROOT/'calibration/map_world_r39_audit';plan_path=folder/'plan.json';plan=json.loads(plan_path.read_text())
    robust=ROOT/'output/r39_world_robust';prior=json.loads((robust/'review.json').read_text())
    if not prior['complete']:raise ValueError('Robust campaign is incomplete')
    if prior['eligible_for_publication']:
        print('Robust world already qualifies; skip the separate audit.',flush=True);return
    old=load_params(ROOT/'atlases/earth_fit/params.json').replace(downsample=16)
    candidate=load_params(ROOT/plan['fixed_candidate'])
    assert_world_only(candidate,load_params(ROOT/'calibration/map_world_r39/start.json'))
    native_review_path=ROOT/plan['native_review'];original=json.loads(native_review_path.read_text())
    native=original['native'][0]
    if original['eligible_for_publication'] or original['transfer']['passed'] or native['failures']:
        raise ValueError('Expected the original native-passing, transfer-rejected fixed candidate')
    checkpoint=ROOT/plan['native_checkpoint']
    with checkpoint.open('rb') as stream:cached=pickle.load(stream)
    if cached['identity']!=build_identity(candidate,[1,2,3]):raise ValueError('Changed original native input identity')
    ev=evaluate(cached['result'])
    if not cached['result'].numerics.get('all_checks_passed'):raise ValueError('Unverified native cache')
    if abs(objective(ev,'zonefit')-native['metrics']['zonefit'])>1e-12 or abs(ev['accuracy']-native['metrics']['accuracy'])>1e-12:
        raise ValueError('Original native metrics no longer reproduce')
    summary=json.loads((ROOT/'atlases/earth_fit/summary.json').read_text())
    reference=dict(zonefit=summary['zonefit'],accuracy=summary['strict_accuracy'],recall=summary['recall'],mediterranean=summary['mediterranean'])
    if world_failures(native['metrics'],reference,native=True):raise ValueError('Original native guards do not pass')
    paths=list((ROOT/'rotclimate').glob('*.py'))+list((ROOT/'data/source').glob('*'))+[
        Path(__file__),plan_path,ROOT/plan['fixed_candidate'],native_review_path,checkpoint,
        robust/'review.json',robust/'protocol.json',ROOT/'scripts/check_r39_world.py',
        ROOT/'scripts/check_r39_world_transfer.py',ROOT/'scripts/check_r39_world_robust.py',
        ROOT/'scripts/earth_benchmark.py',ROOT/'scripts/local_benchmark_protocol.py',
        ROOT/'atlases/earth_fit/params.json',ROOT/'atlases/earth_fit/summary.json']
    out=ROOT/'output/r39_world_audit';out.mkdir(exist_ok=True)
    run=freeze(out/'protocol.json',dict(plan=plan,
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','numba']},
        source_hashes={str(p.relative_to(ROOT)):file_hash(p) for p in paths if p.is_file()}))
    layouts=plan['layouts']
    print('Nine prospective reference layouts; fixed sample, no selection',flush=True)
    a=measure(old,layouts,'audit_reference',out,run)
    print('Nine prospective fixed-candidate layouts',flush=True)
    b=measure(candidate.replace(downsample=16),layouts,'audit_candidate',out,run)
    paired=[]
    for seed in layouts:
        scores={}
        for name,p in [('reference',old),('candidate',candidate.replace(downsample=16))]:
            result=result_from_member(out/'members'/f'audit_{name}_seed{seed}.pkl',p,seed)
            evaluation=evaluate(result)
            scores[name]=dict(zonefit=objective(evaluation,'zonefit'),accuracy=evaluation['accuracy'])
        paired.append(dict(seed=seed,**scores,difference=scores['candidate']['zonefit']-scores['reference']['zonefit']))
    interval=paired_interval([row['difference'] for row in paired]);failures=[]
    if b['zonefit']<a['zonefit']:failures.append('Prospective nine-layout mean-climate zonefit worsened')
    if b['accuracy']<a['accuracy']-.01:failures.append('Prospective strict agreement loss exceeds0.01')
    if not interval['passed']:failures.append('Paired bootstrap lower bound is not positive')
    transfer=dict(reference=a,candidate=b,paired=paired,bootstrap=interval,passed=not failures,
                  failures=failures,layouts=layouts,note='Separate prospective audit; preceding layouts17/23 failure remains rejected.')
    passed=not failures
    final=dict(complete=True,identity=run,native=[native],transfer=transfer,eligible_for_publication=passed,
        params=plan['fixed_candidate'] if passed else None,checkpoint=plan['native_checkpoint'] if passed else None,
        preceding_attempt='output/r39_world_balance/review.json',
        scope='Uncertainty over generated surroundings, not external validation of planetary physics')
    write_json(out/'review.json',final);write_json(out/'progress.json',final)
    print('Fixed-candidate audit complete; publication eligible:',passed,flush=True)
    print('Paired score interval:',interval,flush=True)


if __name__=='__main__':main()
