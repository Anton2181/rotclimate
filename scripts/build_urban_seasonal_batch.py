"""Two-worker orchestration of unchanged declared run_case, preserving completed cases."""
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[key]='1'
import ast
from concurrent.futures import ProcessPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import build_urban_seasonal as B
OUT=B.OUT;BASE=B.BASE


def load_case(args):
    mode,model,reading,hours=args;key=f'{mode}_{model}_{reading}_h{hours}'
    dest=OUT/'cases'/key;c=json.loads((dest/'results.json').read_text())
    assert B.sha(dest/'fields.npz')==c['fields_sha256']
    with np.load(dest/'fields.npz') as z:a={k:z[k] for k in z.files}
    compact={k:a[k] for k in ['request','target','civilian','staff','active','allocator_total','food_ceiling','arrivals','initial_supported','initial_food_ceiling','initial_town_unmet']}
    compact['town_unmet']=a['town__unmet'];compact['town_stock']=a['town__stock_path']
    sites=json.loads((BASE/f'{model}/placed_{mode}_sites.json').read_text())['sites'];rows=[]
    for i,s in enumerate(sites):
        rows.append(dict(case=key,id=s['id'],name=s['name'],row=s['row'],column=s['column'],requested=float(a['request'][i]),
            supported=float(a['target'][i]),support_fraction=float(a['target'][i]/a['request'][i]) if a['request'][i]>0 else 0.,
            civilian=float(a['civilian'][i]),staff=float(a['staff'][i]),active=bool(a['active'][i]),
            conditional_initial_supported=float(a['initial_supported'][i]),seasonal_unmet_person_years=float(a['town__unmet'][i]/B.KCAL),qualified=c['qualified']))
    return c,compact,rows


def job(args):
    try:return B.run_case(*args,OUT)
    except BaseException:
        import traceback
        traceback.print_exc()
        raise


def main():
    plans=[B.PLAN,*[B.PLAN.parent/n for n in ['seasonal_inventory_kernel_a1.json','seasonal_solver_a2.json','seasonal_certificate_a3.json']]]
    for p in plans:assert subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)==p.read_bytes()
    prep=json.loads((OUT/'preparation.json').read_text());kernel=json.loads((OUT/'kernel_review.json').read_text())
    assert prep['status']=='passed_exact_people_and_seasonal_network_controls'
    assert kernel['status']=='passed' and kernel['module_sha256']==B.sha(ROOT/'polity/seasonal_settlement_network.py')
    for name,digest in {**prep['sources_sha256'],**prep['protected_sha256']}.items():assert B.sha(ROOT/name)==digest,name
    for m,s in prep['networks'].items():assert B.sha(OUT/f'prepared/network_{m}.npz')==s['sha256']
    for k,s in prep['provenance'].items():assert B.sha(OUT/f'prepared/people_{k}.npz')==s['matrix_sha256']
    snapshot=OUT/'reference_pilot/serial_producer_snapshot.txt'
    if snapshot.exists() and not (B.PLAN.parent/'seasonal_certificate_a3.json').exists():
        def function(p):return ast.dump(next(n for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='run_case'))
        assert function(snapshot)==function(Path(B.__file__))
    sources={**prep['sources_sha256'],**{str(p.relative_to(ROOT)):B.sha(p) for p in [*plans,Path(__file__),Path(B.__file__),
        ROOT/'polity/seasonal_settlement_network.py',OUT/'preparation.json',OUT/'kernel_review.json']}}
    items=[(mode,model,reading,hours) for mode in ['raw','corrected'] for model in ['control','candidate'] for reading in ['central','low'] for hours in [600,300]]
    completed={};missing=[]
    for args in items:
        key=f'{args[0]}_{args[1]}_{args[2]}_h{args[3]}'
        if (OUT/'cases'/key/'results.json').exists():completed[args]=load_case(args)
        else:missing.append(args)
    with ProcessPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(job,args):args for args in missing}
        for future in as_completed(futures):completed[futures[future]]=future.result()
    cases=[];compact={};towns=[]
    for args in items:
        c,a,t=completed[args];cases.append(c);towns+=t;compact.update({c['key']+'__'+k:v for k,v in a.items()})
    B.table(OUT/'towns.csv',towns);np.savez_compressed(OUT/'town_model.npz',**compact)
    B.table(OUT/'summary.csv',[{k:v for k,v in c.items() if k not in ['audit','history']} for c in cases])
    files=['towns.csv','town_model.npz','summary.csv']+[f'cases/{c["key"]}/results.json' for c in cases]
    for name,digest in prep['protected_sha256'].items():assert B.sha(ROOT/name)==digest,name
    B.write(OUT/'results.json',dict(status='seasonal_network_candidate_development_comparison',sources_sha256=sources,
        protected_sha256=prep['protected_sha256'],files_sha256={n:B.sha(OUT/n) for n in files},cases=cases,
        all_cases_completed=True,all_cases_qualified=all(c['qualified'] for c in cases),
        all_world_rural_food_supported=all(c['audit']['all_world_rural_food_supported'] for c in cases),
        orchestration='Two independent case workers; completed cases retained; unchanged run_case and scientific choices.',
        main_atlas_published=False,adopt=False,new_validation_claim=False))


if __name__=='__main__':main()
