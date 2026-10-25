"""Freeze actual Earth inputs and source identities before starting/resuming a search.

Use --snapshot-only to record/check the identity of an already running search
whose initial r38 control has been independently reproduced. This wrapper
does not change the search plan, objective, budget or selection rules.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash, file_hash, freeze, identity
from rotclimate import earth


def manifest(plan_path, reference_path):
    plan=json.loads(plan_path.read_text())
    summary=json.loads((reference_path/'summary.json').read_text())
    protocol=json.loads((reference_path/'protocol.json').read_text())
    if not summary.get('complete') or summary['identity']!=identity(protocol):
        raise ValueError('A complete manifested input reference is required')
    params=json.loads(json.dumps(asdict(load_params(ROOT/plan['start']).replace(**plan.get('set',{})))))
    if params!=protocol['params']:
        raise ValueError('Input reference must use the exact search starting parameters')
    historical=json.loads((ROOT/plan['reference']/'summary.json').read_text())
    if set(summary['regions'])!=set(historical['regions']):
        raise ValueError('Search and recovered references use different regions')
    for name, expected in protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:
            raise ValueError('Reference scientific input has changed: '+name)
    earth.REGIONS.update(protocol['region_specs'])
    cases={}
    for name,row in summary['regions'].items():
        if row.get('status')!='passed' or row['numerics'].get('all_checks_passed') is not True:
            raise ValueError('Unverified input reference: '+name)
        original=historical['regions'][name]
        for part,key in [('temperature','monthly_mae_C'),('rain','loss')]:
            if abs(row[part][key]-original[part][key])>1e-10:
                raise ValueError('Recovered reference no longer reproduces the planned objective: '+name)
        actual=case_hash(earth.region_case(name,protocol['cell_km']),observed_sea=params['sst_source']=='observed')
        if actual!=row['case_identity']:
            raise ValueError('Actual regional forcing has changed: '+name)
        cases[name]=actual
    files=[plan_path,reference_path/'protocol.json',reference_path/'summary.json',
           ROOT/plan['reference']/'summary.json',ROOT/'scripts/gate_calibrate.py',Path(__file__)]
    return dict(sources=protocol['sources'],cases=cases,
                evidence_sha256={str(p.resolve().relative_to(ROOT)):file_hash(p) for p in files},
                packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','cma']})


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--input-reference',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--hours',type=float,default=1.85);ap.add_argument('--resume',action='store_true')
    ap.add_argument('--snapshot-only',action='store_true')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    run=freeze(a.out/'input_manifest.json',manifest(a.plan,a.input_reference))
    print('Verified search inputs:',run,flush=True)
    if not a.snapshot_only:
        command=[sys.executable,'-u','-I',str(ROOT/'scripts/gate_calibrate.py'),'--plan',str(a.plan),
                 '--out',str(a.out),'--workers',str(a.workers),'--hours',str(a.hours)]
        if a.resume:command.append('--resume')
        subprocess.run(command,cwd=ROOT,check=True)


if __name__=='__main__':main()
