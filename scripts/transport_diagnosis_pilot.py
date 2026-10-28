"""Exactly six archive-matched diagnostic reruns, no calibration or adoption."""
from pathlib import Path
from multiprocessing import Pool
import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,freeze,identity,write_json
from transport_diagnostic_recorder import run_one


def sources_for(plan,path):
    parent=json.loads((ROOT/plan['parent_protocol']).read_text())
    epoch=plan['source_epoch']
    if set(epoch['files'])!={'rotclimate/reservoir_moisture.py'}:
        raise ValueError('Only the one-file read-only observer transition is allowed')
    for name,hashes in epoch['files'].items():
        for side in ('before','after'):
            data=subprocess.check_output(['git','show',epoch[side+'_commit']+':'+name],cwd=ROOT)
            if hashlib.sha256(data).hexdigest()!=hashes[side+'_sha256']:
                raise ValueError('Changed Git source transition: '+name)
        if parent['sources'][name]!=hashes['before_sha256']:
            raise ValueError('Wrong parent instrumentation source')
    sources={name:epoch['files'].get(name,{}).get('after_sha256',sha) for name,sha in parent['sources'].items()}
    sources[plan['parent_protocol']]=file_hash(ROOT/plan['parent_protocol'])
    for name in plan['diagnostic_sources']:
        sources[name]=file_hash(ROOT/name)
    sources[str(path.relative_to(ROOT))]=file_hash(path)
    for name,record in json.loads((ROOT/plan['reference_sources']).read_text()).items():
        sources[name]=record['sha256']
    for profile,archive in plan['profile_control_archives'].items():
        for region in plan['regions']:
            for suffix in ('.json','.npz'):
                source=archive+'/'+region+suffix;sources[source]=file_hash(ROOT/source)
            if region in plan['extra_circulation_regions']:
                source=archive+'/'+region+'_extra.npz';sources[source]=file_hash(ROOT/source)
    for name,sha in sources.items():
        if file_hash(ROOT/name)!=sha:raise ValueError('Undeclared source/input change: '+name)
    return sources


def verify_exact(row,plan,out):
    import numpy as np
    if row['status']!='passed' or row.get('physical_control_exact') is not True:
        raise ValueError('Diagnostic integration failed or climate changed')
    original=ROOT/plan['profile_control_archives'][row['name']]/(row['region']+'.npz')
    original_row=json.loads(original.with_suffix('.json').read_text())
    if row['params']!=original_row['params'] or row['case_identity']!=original_row['case_identity']:
        raise ValueError('Changed actual diagnostic parameters/case')
    actual=out/row['name']/(row['region']+'.npz')
    if file_hash(actual)!=row['arrays_sha256']:raise ValueError('Changed diagnostic climate archive')
    with np.load(original) as old,np.load(actual) as new:
        if set(old.files)!=set(new.files):raise ValueError('Changed climate field set')
        for key in old.files:
            if not np.array_equal(old[key],new[key],equal_nan=True):raise ValueError('Climate changed: '+key)
        count=len(old.files)
    native=out/row['name']/(row['region']+'_transport.npz')
    if file_hash(native)!=row['transport_arrays_sha256']:raise ValueError('Changed diagnostic sidecar')
    return dict(profile=row['name'],region=row['region'],exact_original_arrays=count,
        solved_steps=row['transport']['solved_steps'],strict_pass=row['numerics']['all_checks_passed'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();path=args.plan.resolve();out=args.out.resolve();plan=json.loads(path.read_text())
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous diagnostic attempts; use a fresh directory')
    declaration=str(path.relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+declaration],cwd=ROOT)!=path.read_bytes():
        raise ValueError('Commit the literal six-run declaration before integrations')
    if plan['regions']!=['north_india','mexico','pacific_nw'] or list(plan['profiles'])!=['global04','global06'] or plan['maximum_integrations']!=6:
        raise ValueError('Expected declared three-region/two-profile diagnosis')
    sources=sources_for(plan,path)
    out.mkdir(parents=True);token=freeze(out/'protocol.json',dict(plan=plan,sources=sources,
        packages={k:importlib.metadata.version(k) for k in ('numpy','scipy','numba')}))
    records=[];attempts=[];started=time.monotonic();proof=[]
    def check():
        for name,sha in sources.items():
            if file_hash(ROOT/name)!=sha:raise ValueError('Frozen diagnostic source changed: '+name)
    def save(complete=False,error=None):
        passed=sum(r['status']=='passed' for r in records)
        write_json(out/'review.json',dict(complete=complete,identity=token,actual_integrations=len(attempts),
            strictly_passed=passed,failed_integrations=sum(r['status']!='passed' for r in records),
            pending_integrations=len(attempts)-len(records),attempts=attempts,records=records,exact_proof=proof,
            cumulative_actual_integrations=plan['counter_before']['attempts']+len(attempts),
            cumulative_strict_passes=plan['counter_before']['passes']+passed,
            cumulative_failures=plan['counter_before']['failures']+sum(r['status']!='passed' for r in records),
            seconds=time.monotonic()-started,error=error,physics_or_atlas_adoption=False))
    try:
        with Pool(2) as pool:
            for name in plan['profiles']:
                check()
                # Persist the actual submitted attempts before waiting; failures
                # and interrupted jobs cannot disappear from the run count.
                attempts.extend(dict(profile=name,region=r) for r in plan['regions']);save()
                for row in pool.imap(run_one,[(name,r,plan['profiles'][name],plan,token,str(out)) for r in plan['regions']]):
                    records.append(row);save()
                    proof.append(verify_exact(row,plan,out));save();check()
        check();save(True)
    except BaseException as error:
        save(False,repr(error));raise


if __name__=='__main__':main()
