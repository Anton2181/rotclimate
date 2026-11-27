"""Create the fixed current-source97-region r58 reference; never fit or adopt."""
from dataclasses import asdict
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
PLAN=ROOT/'calibration/current_climate_reference_20261127/plan.json'
OUT=ROOT/'output/climate_reference_20261127'
MODEL=OUT/'model'


def check(plan):
    for section in ['model_sources_sha256','execution_sources_sha256','inputs_sha256']:
        for name,digest in plan[section].items():assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():
        f=MODEL/name
        assert not f.is_symlink() and f.stat().st_nlink==1 and file_hash(f)==digest,name
    for name,version in plan['libraries'].items():assert importlib.metadata.version(name)==version,name
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:assert os.environ.get(name)=='1',name
    assert os.getpriority(os.PRIO_PROCESS,0)>=10


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',action='store_true');args=ap.parse_args()
    plan=json.loads(PLAN.read_text())
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert len(plan['cases'])==plan['maximum_integrations']==97
    assert len({s['region'] for s in plan['cases']})==97
    OUT.mkdir(parents=True,exist_ok=True)
    lock=(OUT/'.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (OUT/'failure.json').exists(),'Preserve failed run, no automatic retry'
    if not args.run:
        assert not (OUT/'preparation.json').exists() and not list(OUT.glob('ref58/*/attempts/*.json'))
        for name,digest in plan['private_files_sha256'].items():
            origin=ROOT if name in plan['model_sources_sha256'] or name in plan['helper_sources_sha256'] else ROOT/plan['cache_origin']
            assert file_hash(origin/name)==digest
            target=MODEL/name
            if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(origin/name,target)
        (OUT/'.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')
    else:assert not (OUT/'results.json').exists(),'Preserve completed current reference'
    check(plan)
    assert not any(n=='rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0]=[str(MODEL/'scripts'),str(MODEL)]
    import benchmark_local as benchmark
    from rotclimate import earth
    from rotclimate.config import Params
    assert Path(benchmark.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    specs=json.loads((ROOT/plan['region_specs']).read_text());earth.REGIONS.update(specs)
    params=Params.from_json(ROOT/plan['params'])
    assert params.wind_source==params.sst_source=='model'
    assert params.t_require_convergence and params.moisture_require_convergence and params.solver_require_convergence
    assert params.moisture_residual_tol==.01
    if not args.run:
        for part in plan['parts']:
            old=json.loads((ROOT/part['historical_protocol']).read_text())
            assert old['params']==json.loads(json.dumps(asdict(params)))
        actual={}
        for spec in plan['cases']:
            case=earth.region_case(spec['region'],56.,1100.)
            actual[spec['region']]=case_hash(case)
            assert actual[spec['region']]==spec['case_identity'],spec['region']
            assert (MODEL/'data/cache/earth'/f"{spec['region']}_56km_1100pad.npz").exists()
        check(plan)
        freeze(OUT/'preparation.json',dict(plan_sha256=file_hash(PLAN),private_regular_files=len(plan['private_files_sha256']),actual_case_identities=actual,integrations=0))
        print('Prepared97 actual case identities; zero integrations',flush=True);return
    assert json.loads((OUT/'preparation.json').read_text())['plan_sha256']==file_hash(PLAN)
    freeze(OUT/'protocol.json',dict(plan_sha256=file_hash(PLAN),preparation_sha256=file_hash(OUT/'preparation.json'),execution_sources_sha256=plan['execution_sources_sha256']))
    protocols={}
    for part in plan['parts']:
        folder=OUT/'ref58'/('r58_'+part['name'])
        for name in ['cases','cells','attempts']:(folder/name).mkdir(parents=True,exist_ok=True)
        protocol=dict(params=asdict(params),regions=part['regions'],region_specs={n:specs[n] for n in part['regions']},cell_km=56.,pad_km=1100.,sources=plan['benchmark_protocol_sources_sha256'],note='Reused development regions; actual derived model inputs are hashed per case.')
        protocols[part['name']]=freeze(folder/'protocol.json',protocol)
    rows=[]
    for index,spec in enumerate(plan['cases']):
        check(plan)
        folder=OUT/'ref58'/('r58_'+spec['part'])
        record=folder/'cases'/(spec['region']+'.json');attempt=folder/'attempts'/(spec['region']+'.json')
        if record.exists():
            row=json.loads(record.read_text())
            assert row['status']=='passed' and row['numerics']['all_checks_passed']
            assert row['case_identity']==spec['case_identity'] and row['identity']==protocols[spec['part']]
            assert file_hash(folder/'cells'/(spec['region']+'.npz'))==row['cells_sha256']
            rows.append(dict(part=spec['part'],**row));continue
        assert not attempt.exists(),'Preserve interrupted integration; recovery must be recorded separately'
        assert file_hash(ROOT/spec['historical_cells'])==spec['historical_cells_sha256']
        write_json(OUT/'status.json',dict(stage='integrating',completed_cases=index,total_cases=97,region=spec['region']))
        freeze(attempt,dict(spec=spec,protocol_sha256=file_hash(folder/'protocol.json'),campaign_protocol_sha256=file_hash(OUT/'protocol.json')))
        row=benchmark.one((spec['region'],asdict(params),56.,str(folder),specs,protocols[spec['part']],1100.))
        if row['status']!='passed' or row['numerics']['all_checks_passed'] is not True:
            write_json(OUT/'failure.json',dict(region=spec['region'],record=row,automatic_retry=False));raise RuntimeError('Original numerical criteria failed; stop')
        assert row['case_identity']==spec['case_identity']
        rows.append(dict(part=spec['part'],**row))
        print(f"Current reference {index+1}/97: {spec['region']}",flush=True)
    for part in plan['parts']:
        folder=OUT/'ref58'/('r58_'+part['name']);records={r['region']:{k:v for k,v in r.items() if k!='part'} for r in rows if r['part']==part['name']}
        write_json(folder/'summary.json',dict(complete=True,identity=protocols[part['name']],fit=plan['params'],overrides={},cell_km=56.,pad_km=1100.,regions=records,groups={g:benchmark.group_means(records,n) for g,n in benchmark.GROUPS.items() if any(x in records for x in n)},all=benchmark.group_means(records,part['regions']),attribution=benchmark.attribution(folder,part['regions'])))
    check(plan)
    write_json(OUT/'results.json',dict(status='completed_current_source97_reference',protocol_sha256=file_hash(OUT/'protocol.json'),rows=rows,candidate_integrations=0,atlas_changed=False))
    subprocess.run([str(ROOT/'.venv/bin/python'),'-I',str(ROOT/'scripts/review_current_climate_reference.py')],cwd=ROOT,check=True)
    write_json(OUT/'status.json',dict(stage='ready_for_agent_review',completed_cases=97))


if __name__=='__main__':main()
