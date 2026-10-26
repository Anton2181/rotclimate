"""Hard-constrained physical proposals from verified paired momentum responses."""
from pathlib import Path
from dataclasses import asdict
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from scipy.optimize import linprog
from earth_benchmark import load_params
from gate_local import measures,score,validate
from local_benchmark_protocol import file_hash,freeze,write_json


def solve_hull(objective,constraints,limits):
    objective=np.asarray(objective,float)
    a,b=np.asarray(constraints,float),np.asarray(limits,float)
    if (objective.ndim!=1 or not objective.size or a.shape!=(len(b),len(objective))
            or not all(np.isfinite(x).all() for x in [objective,a,b])):
        raise ValueError('Need finite matching objective and response constraints')
    result=linprog(objective,A_ub=a,b_ub=b,A_eq=np.ones((1,len(objective))),b_eq=[1],
                   bounds=(0,1),method='highs')
    if not result.success:
        if result.status!=2:
            raise ValueError('Proposal optimizer failed for a reason other than infeasibility: '+result.message)
        return dict(feasible=False,status=result.status,message=result.message)
    weights=np.asarray(result.x)
    if ((weights < -1e-9).any() or abs(weights.sum()-1)>1e-9 or (a@weights>b+1e-9).any()):
        raise ValueError('Optimizer returned an infeasible physical proposal')
    return dict(feasible=True,weights=weights.tolist(),predicted_S=float(objective@weights),
                maximum_constraint_excess=float(np.max(a@weights-b)),status=result.status,message=result.message)


def main():
    path=ROOT/'calibration/momentum_hull_20261026/plan.json'
    plan=json.loads(path.read_text())
    out=ROOT/'output/momentum_hull_20261026'
    out.mkdir(exist_ok=True)
    policy_path=ROOT/'calibration/local_accuracy_20261023/policy_v2.json'
    policy=json.loads(policy_path.read_text())
    names=[n for group in policy['groups'].values() for n in group]
    points=[]
    manifest={}
    reference=None
    base_protocol=None
    for parent_name in plan['parents']:
        parent=ROOT/parent_name
        parent_review=json.loads((parent/'review.json').read_text())
        outer=json.loads((parent/'protocol.json').read_text())
        if not parent_review['complete'] or parent_review['eligible_for_earth_adoption']:
            raise ValueError('Unexpected parent state')
        paths={'reference':parent/'reference',**{name:parent/'development'/name for name in outer['plan']['candidates']}}
        for name,folder in paths.items():
            summary=json.loads((folder/'summary.json').read_text())
            protocol=json.loads((folder/'protocol.json').read_text())
            validate(summary,protocol,set(names))
            if reference is None:
                reference=summary
                base_protocol=protocol
            for key in ['sources','region_specs','cell_km','pad_km']:
                if protocol[key]!=base_protocol[key]:
                    raise ValueError('Unpaired scientific benchmark inputs: '+key)
            for key,value in base_protocol['params'].items():
                if key not in plan['fields'] and protocol['params'][key]!=value:
                    raise ValueError('Parameter outside declared shared block: '+key)
            for region,row in summary['regions'].items():
                if row['case_identity']!=reference['regions'][region]['case_identity']:
                    raise ValueError('Unpaired actual geography')
                cells=folder/'cells'/f'{region}.npz'
                if file_hash(cells)!=row['cells_sha256']:
                    raise ValueError('Changed sampled climate evidence')
                manifest[str(cells.relative_to(ROOT))]=file_hash(cells)
            for p in [folder/'summary.json',folder/'protocol.json',parent/'review.json',parent/'protocol.json']:
                manifest[str(p.relative_to(ROOT))]=file_hash(p)
            if name=='reference' and points:
                for region in names:
                    if any(summary['regions'][region][key]!=reference['regions'][region][key]
                           for key in ['temperature','rain','case_identity']):
                        raise ValueError('Parent references differ')
                continue
            point=dict(name=parent.name+'/'+name,params=protocol['params'],summary=summary)
            points.append(point)
    sources=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),path,policy_path,
        ROOT/'scripts/gate_local.py',ROOT/'scripts/local_benchmark_protocol.py',ROOT/'scripts/earth_benchmark.py']
    # A response archive must match the CURRENT scientific model; added code
    # outside the old source list also invalidates the comparison.
    current={str(p.relative_to(ROOT)):file_hash(p) for p in (ROOT/'rotclimate').glob('*.py')}
    old={k:v for k,v in base_protocol['sources'].items() if k.startswith('rotclimate/')}
    if current!=old:
        raise ValueError('Scientific source epoch changed')
    manifest.update({str(p.relative_to(ROOT)):file_hash(p) for p in sources})
    identity=freeze(out/'protocol.json',dict(plan=plan,points=[dict(name=p['name'],params=p['params']) for p in points],
        evidence_sha256=manifest))
    baseline=measures(reference,names)
    values={}
    for point in points:
        s=point['summary']
        columns=dict(overall=score(measures(s,names),baseline),
            temperature=measures(s,names)['T_monthly_mae']/baseline['T_monthly_mae'],
            rain=measures(s,names)['P_loss']/baseline['P_loss'])
        columns.update({group:score(measures(s,members),measures(reference,members)) for group,members in policy['groups'].items()})
        for region in ['north_india','iran_plateau','iberia','japan','mexico','east_australia','pacific_nw']:
            b,c=reference['regions'][region],s['regions'][region]
            rain=c['rain']['loss']/b['rain']['loss']
            columns[region]=rain if region in ['north_india','iran_plateau'] else .5*(rain+c['temperature']['monthly_mae_C']/b['temperature']['monthly_mae_C'])
        for key,value in columns.items():
            values.setdefault(key,[]).append(value)
    bounds=dict(overall=.995,temperature=1.01,rain=1.01,**{key:1 for key in policy['groups']},
        north_india=.95,iran_plateau=1.02,**{key:1.02 for key in ['iberia','japan','mexico','east_australia','pacific_nw']})
    strict=solve_hull(values['overall'],[values[key] for key in bounds],list(bounds.values()))
    diagnostic=None
    if not strict['feasible']:
        remaining={key:value for key,value in bounds.items() if key!='overall'}
        diagnostic=solve_hull(values['overall'],[values[key] for key in remaining],list(remaining.values()))
    proposal=None
    if strict['feasible']:
        base=load_params(ROOT/plan['physics'])
        kwargs={key:sum(w*p['params'][key] for w,p in zip(strict['weights'],points)) for key in plan['fields']}
        proposal=out/'proposal_params.json'
        write_json(proposal,asdict(base.replace(**kwargs)))
    final=dict(complete=True,identity=identity,strict=strict,diagnostic_without_overall_threshold=diagnostic,
        point_names=[p['name'] for p in points],constraint_names=list(bounds),constraint_limits=bounds,
        responses=values,proposal=str(proposal.relative_to(ROOT)) if proposal else None,
        model_integrations=0,eligible_for_adoption=False,
        interpretation='A convex surrogate is only a proposal model. No mixed response is measured climate skill; '
                       'the diagnostic cannot select a candidate. This is not a bound on the nonlinear model or other physics.')
    write_json(out/'review.json',final)
    print(json.dumps(final,indent=2))


if __name__=='__main__':main()
