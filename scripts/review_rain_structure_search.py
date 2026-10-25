"""Review the completed frozen search, without running disqualified finalists."""
from dataclasses import asdict
from pathlib import Path
import argparse
import json
import math
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from earth_benchmark import load_params
from gate_calibrate import score
from guarded_gate_search import manifest
from local_benchmark_protocol import file_hash,freeze,write_json


def review_rows(rows,reference,groups,expected):
    if len(rows)!=expected:raise ValueError('The declared evaluation budget is not complete')
    if [r['n'] for r in rows]!=list(range(expected)):raise ValueError('Missing or duplicated evaluation indices')
    checks=[]
    ref_t=sum(v[0] for v in reference.values())/len(reference)
    ref_p=sum(v[1] for v in reference.values())/len(reference)
    for row in rows:
        errors=row['regions']
        if set(errors)!=set(reference):raise ValueError('Changed region set')
        failures=[]
        if any(v is None for v in errors.values()):
            failures=['Unverified regional solve']
        else:
            if any(len(v)!=2 or any(not math.isfinite(x) or x<0 for x in v) for v in errors.values()):
                raise ValueError('Invalid regional error')
            cost,actual=score(errors,reference,groups)
            for name in ['S','T','P','penalty']:
                if not math.isfinite(row[name]) or abs(actual[name]-row[name])>1e-12:
                    raise ValueError('Recorded score does not reproduce: '+name)
            if not math.isfinite(row['cost']) or abs(cost-row['cost'])>1e-12 or any(
                    not math.isfinite(row['groups'][k]) or abs(actual['groups'][k]-row['groups'][k])>1e-12 for k in groups):
                raise ValueError('Recorded cost or groups do not reproduce')
            if row['n']==0:
                if any(abs(errors[n][i]-reference[n][i])>1e-10 for n in reference for i in [0,1]):
                    raise ValueError('Initial control does not reproduce reference')
                failures.append('Initial reference control, not a new candidate')
            if actual['S']>.995:failures.append('S exceeds 0.995')
            failures += [g+': group worsened' for g,s in actual['groups'].items() if s>1.]
            if actual['T']>1.01*ref_t:failures.append('Temperature error exceeds 1% allowance')
            if actual['P']>1.01*ref_p:failures.append('Rain error exceeds 1% allowance')
        checks.append(dict(n=row['n'],eligible=not failures,failures=failures,S=row.get('S'),cost=row['cost']))
    eligible=sorted((r for r in checks if r['eligible']),key=lambda r:(r['S'],r['n']))[:3]
    return dict(complete=True,evaluations=len(rows),eligible_count=sum(r['eligible'] for r in checks),
                selected_indices=[r['n'] for r in eligible],checks=checks)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--search',required=True,type=Path)
    ap.add_argument('--input-reference',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
    a=ap.parse_args();plan=json.loads(a.plan.read_text())
    if json.loads((a.search/'plan.json').read_text())!=plan:raise ValueError('Search plan changed')
    raw=(a.search/'evals.jsonl').read_text()
    if not raw.endswith('\n'):raise ValueError('Incomplete last evaluation')
    rows=[json.loads(line) for line in raw.splitlines() if line.strip()]
    bounds={name:(low,high) for name,low,high in plan['knobs']}
    for row in rows:
        if set(row['knobs'])!=set(bounds):raise ValueError('Changed search variables')
        for name,value in row['knobs'].items():
            low,high=bounds[name]
            if not math.isfinite(value) or not low-1e-12<=value<=high+1e-12:
                raise ValueError('Out-of-bounds search variable: '+name)
    groups=json.loads((ROOT/'calibration/local_accuracy_20261023/policy_v2.json').read_text())['groups']
    summary=json.loads((a.input_reference/'summary.json').read_text())
    reference={n:(r['temperature']['monthly_mae_C'],r['rain']['loss']) for n,r in summary['regions'].items()}
    result=review_rows(rows,reference,groups,plan['evals'])
    # The exact same source/forcing/package guard is checked at campaign end.
    run=freeze(a.search/'input_manifest.json',manifest(a.plan,a.input_reference))
    a.out.mkdir(parents=True,exist_ok=True)
    base=load_params(ROOT/plan['start']).replace(**plan.get('set',{}))
    result.update(input_identity=run,source_sha256=file_hash(Path(__file__)),
        evidence_sha256={str(p):file_hash(p) for p in [a.plan,a.search/'evals.jsonl',a.search/'input_manifest.json']},
        note='Search-screen selection only. Eligible finalists still require the fresh 31-region gate, '
             'paired 28 km check and established six-region evaluation before adoption.')
    for index in result['selected_indices']:
        write_json(a.out/f'candidate_{index:03d}_params.json',asdict(base.replace(**rows[index]['knobs'])))
    if not result['selected_indices']:
        result['decision']='No eligible finalist; retain r38. Do not run finer-grid or validation selection on failing candidates.'
    else:result['decision']='Evaluate the selected finalists in the frozen order; no adoption from search scores alone.'
    write_json(a.out/'review.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='checks'},indent=2))


if __name__=='__main__':main()
