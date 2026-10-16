"""User-run fresh-surroundings check of the two verified Mediterranean finalists.

Default is a read-only plan: two candidates on two previously unused seeds.
--run executes four sequential simulations, resumes exact matching results,
and never searches parameters or overwrites the atlas.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from rotclimate.config import Params
from scripts.diagnose_moisture import case_summary
from scripts.mediterranean_pilot import matching_params


def model_code_id():
    h=hashlib.sha256()
    for name in ('config','model','temperature','moisture','solver','ebm','astronomy','geography','koppen','score','numerics','transport'):
        h.update(name.encode())
        h.update((ROOT/'rotclimate'/f'{name}.py').read_bytes())
    return h.hexdigest()


def finalists():
    return {name: Params.from_json(ROOT/'calibration'/f'round20_retrograde_{name}_verified.json').replace(
                t_adaptive_retries=2,t_require_convergence=True)
            for name in ('strong_seasonal','focused_seasonal')}


def jobs_for(profiles,seeds):
    return [(name,seed,p.replace(beyond_seed=seed))
            for seed in seeds for name,p in profiles.items()]


def comparison(rows,expected):
    cases={}
    for name in dict.fromkeys(n for n,_,_ in expected):
        group=[r for (n,_),r in rows.items() if n==name]
        if not group:
            continue
        def stats(values):
            return dict(mean=sum(values)/len(values),min=min(values),max=max(values))
        cases[name]=dict(worlds=len(group),
            accuracy=stats([r['accuracy'] for r in group]),
            mediterranean={k:stats([r['mediterranean'][k] for r in group]) for k in ('dry_share','cs_share')},
            zone_recall={k:stats([r['zone_recall'][k] for r in group]) for k in group[0]['zone_recall']})
    paired=[]
    for seed in dict.fromkeys(s for _,s,_ in expected):
        a,b=rows.get(('strong_seasonal',seed)),rows.get(('focused_seasonal',seed))
        if a is None or b is None:
            continue
        paired.append(dict(seed=seed,
            focused_minus_strong_accuracy=b['accuracy']-a['accuracy'],
            focused_minus_strong_med_dry=b['mediterranean']['dry_share']-a['mediterranean']['dry_share'],
            focused_minus_strong_cold_dry=b['zone_recall']['cold_dry']-a['zone_recall']['cold_dry']))
    return dict(expected=len(expected),completed=len(rows),cases=cases,paired=paired,
                note='Small paired screening, not a statistical verdict. These worlds vary procedural surroundings; the painted map and terrain stay fixed. No fit is automatically selected.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true')
    ap.add_argument('--seeds',default='301,302')
    ap.add_argument('--cases',default='strong_seasonal,focused_seasonal')
    ap.add_argument('--out',type=Path,default=ROOT/'output/mediterranean_validation')
    a=ap.parse_args()
    try:
        seeds=[int(v) for v in a.seeds.split(',')]
    except ValueError:
        ap.error('--seeds must be comma-separated integers')
    if not seeds or len(seeds)!=len(set(seeds)):
        ap.error('Choose distinct seeds')
    profiles=finalists()
    names=a.cases.split(',')
    if len(names)!=len(set(names)) or any(n not in profiles for n in names):
        ap.error('Choose distinct cases from strong_seasonal,focused_seasonal')
    profiles={name:profiles[name] for name in names}
    for p in profiles.values():
        if not p.moisture_require_convergence or not p.solver_require_convergence:
            ap.error('Finalists must retain strict moisture and linear convergence')
    jobs=jobs_for(profiles,seeds)
    for name,seed,_ in jobs:
        print(f'{name}, world {seed}; temperature retries <= {profiles[name].t_adaptive_retries}',flush=True)
    print(f'{len(jobs)} sequential simulations; no search or atlas update. '
          'Past runs took 8–11 minutes; difficult steps and retries may add time.',flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.')
        return
    from scripts.diagnose_numerics import diagnose
    a.out.mkdir(parents=True,exist_ok=True)
    code_id=model_code_id()
    rows={}
    for name,seed,p in jobs:
        path=a.out/f'{name}_seed{seed}.json'
        fields=a.out/f'{name}_seed{seed}_fields.npz'
        d=json.loads(path.read_text()) if path.exists() else None
        reusable=(d is not None and fields.exists() and d.get('validation_code_id')==code_id
                  and matching_params(d['params'],p))
        if not reusable:
            start=time.monotonic()
            def progress(done,total):
                if done==1 or done%5==0 or done==total:
                    print(f'{name}, world {seed}: {done}/{total} seasonal steps; '
                          f'{(time.monotonic()-start)/60:.1f} min',flush=True)
            try:
                d=diagnose(p,snapshot=fields,progress=progress)
            except RuntimeError as error:
                (a.out/f'{name}_seed{seed}_failure.json').write_text(json.dumps(
                    dict(params=asdict(p),error=str(error),details=getattr(error,'details',None),
                         validation_code_id=code_id),indent=2)+'\n')
                raise
            d['validation_code_id']=code_id
            path.write_text(json.dumps(d,indent=2)+'\n')
        row=case_summary(d)
        if not row['convergence']['usable_for_comparison']:
            raise SystemExit(f'{name}, world {seed}: a convergence check failed; result saved, stopping.')
        rows[name,seed]=row
        (a.out/'comparison.json').write_text(json.dumps(comparison(rows,jobs),indent=2)+'\n')
        print(f"[{len(rows)}/{len(jobs)}] {name}, world {seed}: correct {row['accuracy']:.1%}, "
              f"Mediterranean dry {row['mediterranean']['dry_share']:.1%}, "
              f"cold-dry correct {row['zone_recall']['cold_dry']:.1%}",flush=True)


if __name__=='__main__':
    main()
