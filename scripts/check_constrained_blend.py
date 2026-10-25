"""Constrained response-guided proposals, verified by the full physical model."""
from dataclasses import asdict
from pathlib import Path
import json
import subprocess
import sys
import importlib.metadata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from scipy.optimize import linprog
from earth_benchmark import load_params
from gate_local import evaluate,measures,score
from local_benchmark_protocol import file_hash,freeze,write_json


def proposals(rows,knobs,targets,fractions):
    ref=rows[0];groups=list(ref['groups']);objective=np.array([r['S'] for r in rows])
    a=np.array([[r['groups'][g] for r in rows] for g in groups]+
               [[r['T']/ref['T'] for r in rows],[r['P']/ref['P'] for r in rows]])
    points=[];screens=[]
    for target in targets:
        solved=linprog(objective,A_ub=a,b_ub=[target]*len(groups)+[1.01,1.01],
            A_eq=np.ones((1,len(rows))),b_eq=[1.],bounds=(0.,1.),method='highs')
        screens.append(dict(group_target=target,feasible=bool(solved.success),message=solved.message))
        if not solved.success:continue
        if not np.isclose(solved.x.sum(),1.,atol=1e-9) or (a@solved.x>np.array([target]*len(groups)+[1.01,1.01])+1e-8).any():
            raise ValueError('Optimizer returned an infeasible proposal')
        weighted={name:float(sum(w*r['knobs'][name] for w,r in zip(solved.x,rows))) for name,_,_ in knobs}
        for fraction in fractions:
            values={name:ref['knobs'][name]+fraction*(weighted[name]-ref['knobs'][name]) for name,_,_ in knobs}
            if any(not low-1e-12<=values[name]<=high+1e-12 for name,low,high in knobs):raise ValueError('Proposal exceeds original bounds')
            points.append(dict(name=f'g{target:g}_a{fraction:g}',knobs=values,
                predicted_S=1+fraction*(float(solved.fun)-1),group_target=target,fraction=fraction,
                support=[dict(n=r['n'],weight=float(w)) for w,r in zip(solved.x,rows) if w>1e-10]))
    return dict(proposals=points,linear_screens=screens,note='Predictions only; no interpolated loss is an observed climate result.')


def benchmark(params,out,regions,km=56,specs=None):
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
    command=[sys.executable,'-u','-I',str(ROOT/'scripts/benchmark_local.py'),'--fit',str(params),
             '--regions',*regions,'--workers','2','--cell-km',str(km),'--out',str(out)]
    if specs:command+=['--region-specs',str(specs)]
    with out.with_suffix('.log').open('a') as stream:
        result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:return None
    return json.loads((out/'summary.json').read_text())


def paired_score(ref_folder,candidate_folder,names):
    r=json.loads((ref_folder/'summary.json').read_text());c=json.loads((candidate_folder/'summary.json').read_text())
    rp=json.loads((ref_folder/'protocol.json').read_text());cp=json.loads((candidate_folder/'protocol.json').read_text())
    if not r.get('complete') or not c.get('complete') or rp['sources']!=cp['sources'] or rp['region_specs']!=cp['region_specs']:
        raise ValueError('Incomplete or scientifically unpaired benchmarks')
    for name in names:
        if r['regions'][name]['case_identity']!=c['regions'][name]['case_identity'] or any(
                x['numerics'].get('all_checks_passed') is not True for x in [r['regions'][name],c['regions'][name]]):
            raise ValueError('Unpaired or unverified regional climate')
    return score(measures(c,names),measures(r,names))


def main():
    plan_path=ROOT/'calibration/constrained_blend_20261025/plan.json';plan=json.loads(plan_path.read_text())
    out=ROOT/'output/constrained_blend_20261025';out.mkdir(exist_ok=True)
    archive=ROOT/plan['archive'];old_review=json.loads((ROOT/plan['archive_review']).read_text())
    if not old_review['complete'] or old_review['eligible_count']!=0:raise ValueError('Unexpected parent campaign')
    if file_hash(archive)!=old_review['evidence_sha256'][plan['archive']]:raise ValueError('Archived evaluations changed')
    rows=[json.loads(line) for line in archive.read_text().splitlines() if line.strip()]
    if len(rows)!=120 or any('S' not in row for row in rows):raise ValueError('Unexpected archive budget/failures')
    original=json.loads((ROOT/plan['original_plan']).read_text());base=load_params(ROOT/plan['reference'])
    generated=proposals(rows,original['knobs'],plan['group_targets'],plan['fractions_from_reference'])
    paths=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),plan_path,archive,ROOT/plan['reference'],
        ROOT/'scripts/gate_local.py',ROOT/'calibration/local_accuracy_20261023/policy_v2.json']
    identity=freeze(out/'proposal_protocol.json',dict(plan=plan,generated=generated,
        sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths},
        packages={p:importlib.metadata.version(p) for p in ['numpy','scipy']}))
    param_folder=ROOT/'calibration/constrained_blend_20261025/proposals';param_folder.mkdir(exist_ok=True)
    for point in generated['proposals']:write_json(param_folder/(point['name']+'.json'),asdict(base.replace(**point['knobs'])))
    write_json(out/'proposals.json',generated)
    reference=out/'reference';r=benchmark(ROOT/plan['reference'],reference,['dev31'])
    if r is None:raise RuntimeError('Fresh reference failed')
    for name,errors in rows[0]['regions'].items():
        actual=r['regions'][name]
        if abs(actual['temperature']['monthly_mae_C']-errors[0])>1e-10 or abs(actual['rain']['loss']-errors[1])>1e-10:
            raise ValueError('Fresh r38 control changed: '+name)
    rp=json.loads((reference/'protocol.json').read_text())
    policy=json.loads((ROOT/'calibration/local_accuracy_20261023/policy_v2.json').read_text())
    reviews={};eligible=[]
    for point in generated['proposals']:
        name=point['name'];folder=out/'development'/name
        c=benchmark(param_folder/(name+'.json'),folder,['dev31'])
        if c is None:reviews[name]=dict(passes_development_gate=False,failures=['Numerical benchmark failure'])
        else:
            cp=json.loads((folder/'protocol.json').read_text());reviews[name]=evaluate(r,c,rp,cp,policy)
            if reviews[name]['passes_development_gate']:eligible.append(name)
        print(name+': '+json.dumps(reviews[name]),flush=True)
        write_json(out/'progress.json',dict(complete=False,identity=identity,development=reviews))
    eligible=sorted(eligible,key=lambda name:reviews[name]['score'])[:3]
    fine_names=['california','western_europe','japan','new_zealand'];fine_reviews={};selected=None
    if eligible:
        if benchmark(ROOT/plan['reference'],out/'fine_reference',fine_names,28) is None:raise RuntimeError('Fine reference failed')
        for name in eligible:
            folder=out/'fine'/name;c=benchmark(param_folder/(name+'.json'),folder,fine_names,28)
            s=paired_score(out/'fine_reference',folder,fine_names) if c else None
            fine_reviews[name]=dict(S=s,passed=s is not None and s<=1.01)
            if fine_reviews[name]['passed']:selected=name;break
    validation=None
    if selected:
        specs=ROOT/'calibration/local_accuracy_20261023/regions_sealed6.json';names=list(json.loads(specs.read_text()))
        a=benchmark(ROOT/plan['reference'],out/'validation_reference',names,specs=specs)
        b=benchmark(param_folder/(selected+'.json'),out/'validation_candidate',names,specs=specs)
        s=paired_score(out/'validation_reference',out/'validation_candidate',names) if a and b else None
        validation=dict(S=s,passed=s is not None and s<=1.01)
    passed=bool(selected and validation['passed'])
    review=dict(complete=True,identity=identity,development=reviews,fine=fine_reviews,selected=selected,
        validation=validation,eligible_for_adoption=passed,
        decision='Qualified physics candidate; world refits and atlas publication remain.' if passed else 'Retain r38; no qualified candidate.')
    write_json(out/'review.json',review);write_json(out/'progress.json',review)
    print(json.dumps(review,indent=2),flush=True)


if __name__=='__main__':main()
