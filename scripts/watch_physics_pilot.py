"""Run a bounded fixed physics pilot with atomic status and source-change stops.

Default is read-only preflight. --run starts the declared job; no atlas export,
commit or push is performed here. The existing runner owns scientific gates.
"""
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def atomic(path,value):
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');temporary.replace(path)


def stop_child(child):
    if child.poll() is not None:return
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:return
    try:child.wait(timeout=20)
    except subprocess.TimeoutExpired:
        try:os.killpg(child.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        child.wait(timeout=10)


def run(plan_path,out,hours):
    plan=json.loads(plan_path.read_text())
    if (out/'protocol.json').exists() or (out/'status.json').exists():
        raise ValueError('Preserve prior jobs; choose a fresh output directory')
    out.mkdir(parents=True,exist_ok=True)
    # Protect startup too, before the scientific runner writes its full manifest.
    paths=[plan_path,ROOT/'scripts/check_vapor_flux.py',ROOT/'scripts/paired_physics_pilot.py',
           ROOT/'scripts/check_surface_momentum.py',ROOT/plan['physics'],*sorted((ROOT/'rotclimate').glob('*.py'))]
    expected={str(p.relative_to(ROOT)):sha(p) for p in paths}
    signatures={}
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    command=[sys.executable,'-u',str(ROOT/'scripts/check_vapor_flux.py'),'--plan',str(plan_path),'--out',str(out)]
    began=time.monotonic();state='running';reason=None;child=None
    try:
        with (out/'run.log').open('w') as log:
            environment=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
            child=subprocess.Popen(command,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            atomic(out/'monitor_pid.json',dict(monitor_pid=os.getpid(),runner_pid=child.pid,source_commit=source_commit))
            while True:
                manifest=out/'protocol.json'
                if manifest.exists():expected.update(json.loads(manifest.read_text())['sources'])
                changed=[]
                for name,digest in expected.items():
                    path=ROOT/name
                    try:stat=path.stat();signature=(stat.st_mtime_ns,stat.st_size)
                    except FileNotFoundError:changed.append(name);continue
                    if signatures.get(name)!=signature:
                        if sha(path)!=digest:changed.append(name)
                        signatures[name]=signature
                elapsed=time.monotonic()-began
                if changed:state='stopped_source_change';reason='Frozen inputs changed: '+', '.join(changed[:4]);stop_child(child)
                elif elapsed>hours*3600:state='stopped_budget';reason='Declared wall-clock budget exhausted';stop_child(child)
                code=child.poll()
                if code is not None and state=='running':state='complete' if code==0 else 'failed';reason=None if code==0 else 'Runner exit code '+str(code)
                rows=[]
                for profile in plan['profiles']:
                    for region in plan['regions']:
                        path=out/profile/f'{region}.json'
                        if path.exists():rows.append(json.loads(path.read_text()))
                review_path=out/'review.json';review=json.loads(review_path.read_text()) if review_path.exists() else None
                status=dict(state=state,reason=reason,updated_utc=datetime.now(timezone.utc).isoformat(),elapsed_seconds=round(elapsed,1),
                    budget_hours=hours,source_commit=source_commit,monitor_pid=os.getpid(),runner_pid=child.pid,
                    numerical_threads=dict(OPENBLAS_NUM_THREADS=1,OMP_NUM_THREADS=1),
                    completed_runs=len(rows),planned_runs=len(plan['profiles'])*len(plan['regions']),
                    passed_runs=sum(r['status']=='passed' for r in rows),failed_runs=sum(r['status']=='failed' for r in rows),
                    phase='full_earth_gates' if state=='running' and review is not None else 'fixed_regional_pilot',
                    screening_finalists=None if review is None else review['development_finalists'],atlas_climate_adoption=False)
                atomic(out/'status.json',status)
                if code is not None:break
                time.sleep(15)
    except BaseException as error:
        path=out/'status.json'
        previous=json.loads(path.read_text()) if path.exists() else {}
        previous.update(state='monitor_stopped',reason=repr(error),updated_utc=datetime.now(timezone.utc).isoformat())
        atomic(path,previous)
        raise
    finally:
        if child is not None:stop_child(child)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--hours',type=float,default=2);parser.add_argument('--run',action='store_true')
    args=parser.parse_args()
    if not 0<args.hours<=2:parser.error('Budget must be positive and at most the declared2hours')
    plan_path=args.plan.resolve();plan=json.loads(plan_path.read_text())
    if not args.run:
        print(json.dumps(dict(action='preflight_only',runs=len(plan['profiles'])*len(plan['regions']),hours=args.hours,
                              profiles=list(plan['profiles']),planet='fixed by joint.earth_profile'),indent=2));return
    def terminate(signum,frame):raise KeyboardInterrupt('Monitor termination requested')
    signal.signal(signal.SIGTERM,terminate)
    run(plan_path,args.out.resolve(),args.hours)


if __name__=='__main__':main()
