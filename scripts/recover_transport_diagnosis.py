"""Finish the frozen six-case diagnosis after a tuple/list controller failure.

Original sources, declaration and failed controller evidence remain unchanged.
Two completed cases are verified and reused. One interrupted attempt is counted;
four missing cases are integrated once under the same physical parameters.
"""
from pathlib import Path
from multiprocessing import Pool
import argparse
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,freeze,identity,write_json
from transport_diagnosis_pilot import sources_for,verify_exact
from transport_diagnostic_recorder import run_one


def canonical_exact(row,plan,out):
    # Compare JSON records with JSON records. asdict retains parameter tuples
    # in memory; JSON serialization deliberately represents them as lists.
    return verify_exact(json.loads(json.dumps(row,allow_nan=False)),plan,out)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();path=a.plan.resolve();out=a.out.resolve();recovery=json.loads(path.read_text())
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous recovery evidence')
    if subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():
        raise ValueError('Commit literal recovery before remaining integrations')
    original_path=ROOT/recovery['original_plan'];plan=json.loads(original_path.read_text())
    sources=sources_for(plan,original_path)
    for name,sha in recovery['preserved_sources'].items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Changed original interrupted-run evidence: '+name)
    sources.update(recovery['preserved_sources'])
    for name in [str(path.relative_to(ROOT)),str(Path(__file__).relative_to(ROOT))]:sources[name]=file_hash(ROOT/name)
    out.mkdir(parents=True);token=freeze(out/'protocol.json',dict(plan=plan,recovery=recovery,sources=sources))
    records=[];origins={};proof=[];attempts=list(recovery['initial_attempts']);started=time.monotonic()
    for name,region in recovery['completed_cases']:
        directory=ROOT/recovery['original_output'];row=json.loads((directory/name/(region+'.json')).read_text())
        proof.append(canonical_exact(row,plan,directory));records.append(row);origins[name+'/'+region]=recovery['original_output']
    def check():
        for name,sha in sources.items():
            if file_hash(ROOT/name)!=sha:raise ValueError('Frozen recovery source changed: '+name)
    def save(complete=False,error=None):
        passed=sum(r['status']=='passed' for r in records);failed=sum(r['status']!='passed' for r in records)
        write_json(out/'review.json',dict(complete=complete,identity=token,records=records,origins=origins,exact_proof=proof,
            attempts=attempts,actual_integrations=len(attempts),strictly_passed=passed,
            failed_integrations=failed,interrupted_integrations=1,pending_integrations=len(attempts)-len(records)-1,
            cumulative_actual_integrations=plan['counter_before']['attempts']+len(attempts),
            cumulative_strict_passes=plan['counter_before']['passes']+passed,
            cumulative_failures=plan['counter_before']['failures']+failed+1,
            seconds=time.monotonic()-started,error=error,physics_or_atlas_adoption=False,
            scope='Original diagnostic outcomes unchanged; one interrupted controller attempt counted; only four missing cases newly integrated'))
    try:
        check();save()
        with Pool(2) as pool:
            for name,regions in recovery['remaining_profiles'].items():
                attempts.extend(dict(profile=name,region=r,state='submitted') for r in regions);save()
                for row in pool.imap(run_one,[(name,r,plan['profiles'][name],plan,token,str(out)) for r in regions]):
                    records.append(row);origins[name+'/'+row['region']]=str(out.relative_to(ROOT))
                    for attempt in attempts:
                        if attempt['profile']==name and attempt['region']==row['region'] and attempt['state']=='submitted':attempt['state']=row['status']
                    save()
                    proof.append(canonical_exact(row,plan,out));save();check()
        check();save(True)
    except BaseException as error:
        save(False,repr(error));raise


if __name__=='__main__':main()
