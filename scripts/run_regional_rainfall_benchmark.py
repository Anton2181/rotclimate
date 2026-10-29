"""Run frozen r39 reproductions and explicit wet/dry calendar-month trials."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json


def run(path,out):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    prior_path=ROOT/plan['prior_cap_receipt'];prior=json.loads(prior_path.read_text())
    assert prior['literal_plan_sha256']==file_hash(ROOT/plan['prior_cap_plan'])
    before=plan['prototype_counters_before_cap'];prior_counts=dict(starts=before['starts']+prior['actual_earth_initialized_integrations_started'],completions=before['completions']+prior['integrations_completed'],retained_noncompletions=before['retained_noncompletions']+prior['actual_earth_initialized_integrations_started']-prior['integrations_completed'])
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal rainfall benchmark before outcomes')
    if out.exists() and any(out.iterdir()):raise ValueError('Retain previous rainfall benchmark attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_protocol.json',plan);write_json(out/'prior_cap_receipt.json',prior);records=[]
    def worker(spec):
        folder=out/spec['name'];log=(out/(spec['name']+'.log')).open('w');start=time.monotonic()
        script='scripts/r39_rainfall_control.py' if spec['kind']=='legacy' else 'scripts/rainfall_month_pilot.py'
        env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        try:
            process=subprocess.run([sys.executable,script,'--plan',spec['plan'],'--out',str(folder)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
            receipt=folder/'verification.json';record=dict(**spec,returncode=process.returncode,wall_seconds=time.monotonic()-start,receipt_exists=receipt.exists())
            if receipt.exists():record.update(receipt_sha256=file_hash(receipt),run=json.loads(receipt.read_text()))
            elif (folder/'progress.json').exists():record['unfinished_progress']=json.loads((folder/'progress.json').read_text())
            return record
        finally:log.close()
    # Separate processes isolate reference data from prototype model namespaces.
    # Every case in each declared stage runs; failed references do not cause
    # silently skipped prototype cases or a substituted baseline.
    for stage in ['legacy','prototype']:
        specs=[c for c in plan['cases'] if c['kind']==stage]
        with ThreadPoolExecutor(max_workers=plan['workers']) as pool:
            pending={pool.submit(worker,s):s for s in specs}
            for future in as_completed(pending):
                record=future.result();records.append(record);write_json(out/'progress.json',dict(stage=stage,finished_cases=records,planned_cases=plan['cases']))
                print(json.dumps({k:v for k,v in record.items() if k!='run'}),flush=True)
    legacy_attempts=legacy_passes=prototype_starts=prototype_completions=0
    for record in records:
        r=record.get('run',{});progress=record.get('unfinished_progress',{})
        if record['kind']=='legacy':legacy_attempts+=r.get('legacy_benchmark_attempts_added',progress.get('actual_legacy_integrations_started',0));legacy_passes+=r.get('legacy_strict_passes_added',0)
        else:prototype_starts+=r.get('actual_earth_initialized_integrations_started',progress.get('started',0));prototype_completions+=r.get('integrations_completed',0)
    write_json(out/'verification.json',dict(status='regional_rainfall_attempts_finished',literal_plan_sha256=file_hash(path),prior_cap_receipt_sha256=file_hash(prior_path),prior_prototype_counts=prior_counts,legacy_attempts_added=legacy_attempts,legacy_strict_passes_added=legacy_passes,prototype_starts_added=prototype_starts,prototype_completions_added=prototype_completions,prototype_starts=prior_counts['starts']+prototype_starts,prototype_completions=prior_counts['completions']+prototype_completions,prototype_retained_noncompletions=prior_counts['retained_noncompletions']+prototype_starts-prototype_completions,legacy_attempts=plan['legacy_counters_before']['attempts']+legacy_attempts,legacy_strict_passes=plan['legacy_counters_before']['strict_passes']+legacy_passes,results=records,physical_adoption=False,recalibration=False,scope='Every fixed legacy and prototype attempt retained. No score-based early stopping, substitutions or best-initialization selection. Monthly scores are produced separately from complete saved fields under the frozen masks/calendar.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan,a.out)
