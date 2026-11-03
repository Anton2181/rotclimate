"""Resume the declared climate/atlas jobs and distinguish stale running markers.

Linux execution workspace only. Foreground supervisor: it cannot keep jobs
alive through a workspace shutdown. Re-run it after restart to use checkpoints.
"""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/continuation_20261103'
JOBS=[
    ('atlas','run_atlas_snapshot.py','calibration/atlas_release_r43_20261103/plan.json',
     'output/atlas_r43/snapshot_status.json','ready_for_publication',0,[]),
    ('publish','finish_atlas_snapshot.py','calibration/atlas_release_r43_20261103/publication.json',
     'output/atlas_r43/publication_status.json','finished_pushed',0,[]),
    ('storm61','expand_storm_exchange.py','calibration/storm_expansion_20261103/plan_v2.json',
     'output/storm_expansion_20261103b/status.json','finished_pushed',5,['--workers','1']),
    ('fitted','screen_fitted_flux.py','calibration/fitted_flux_20261103/plan.json',
     'output/fitted_flux_20261103/status.json','finished_pushed',10,[]),
    ('bounds','screen_parameter_bounds.py','calibration/parameter_bounds_20261103/plan.json',
     'output/parameter_bounds_20261103/status.json','finished_pushed',10,[]),
]


def process_start(stat):
    # The process name in parentheses may contain spaces or parentheses.
    return stat.rsplit(')',1)[1].split()[19]


def machine_key():
    text=Path('/proc/sys/kernel/random/boot_id').read_text()+process_start(Path('/proc/1/stat').read_text())
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def matches(argv,script,plan):
    if not argv or not Path(argv[0]).name.startswith('python'):return False
    if 'scripts/'+script not in argv:return False
    try:return argv[argv.index('--plan')+1]==plan and '--train-only' not in argv
    except (ValueError,IndexError):return False


def running(script,plan):
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            if (path/'cwd').resolve()!=ROOT:continue
            argv=(path/'cmdline').read_bytes().decode().strip('\0').split('\0')
            if matches(argv,script,plan):return int(path.name),process_start((path/'stat').read_text())
        except (OSError,UnicodeError,IndexError):pass
    return None


def marker(path):
    try:return json.loads((ROOT/path).read_text())
    except FileNotFoundError:return {}


def status_record():
    from datetime import datetime,timezone
    rows={}
    for name,script,plan,path,goal,nice,extra in JOBS:
        data=marker(path);live=running(script,plan)
        state=('complete' if data.get('stage')==goal else 'running' if live else
               'failed' if data.get('stage')=='failed' else 'interrupted' if data else 'not_started')
        rows[name]=dict(state=state,pid=None if not live else live[0],
            process_start=None if not live else live[1],last_stage=data.get('stage'),
            last_step=data.get('step',data.get('profile')),marker_updated_utc=data.get('updated_utc'),
            declaration=plan)
    return dict(updated_utc=datetime.now(timezone.utc).isoformat(),machine=machine_key(),jobs=rows,
        scope='Process presence is checked on this machine. Marker timestamps alone never establish that work is still running. Workspace shutdown stops jobs; this command resumes their existing checkpoints.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status',action='store_true',help='read actual live processes without launching work')
    parser.add_argument('--retry-failed',action='store_true',help='resume after the cause of a recorded failure has been repaired')
    args=parser.parse_args()
    if args.status:print(json.dumps(status_record(),indent=2));return
    OUT.mkdir(exist_ok=True);lock=(OUT/'.supervisor.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    children={};streams=[]
    for name,script,plan,path,goal,nice,extra in JOBS:
        data=marker(path)
        if data.get('stage')==goal or running(script,plan):continue
        if data.get('stage')=='failed' and not args.retry_failed:
            print(name+': previous failure needs investigation; independent jobs continue',flush=True);continue
        declared=subprocess.check_output(['git','show','HEAD:'+plan],cwd=ROOT)
        if declared!=(ROOT/plan).read_bytes():raise ValueError('Uncommitted declaration: '+plan)
        command=[str(ROOT/'.venv/bin/python'),'-u','-I','scripts/'+script,'--plan',plan,*extra]
        if nice:command=['nice','-n',str(nice),*command]
        stream=(OUT/(name+'.log')).open('a');streams.append(stream)
        children[name]=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
            env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
        print('Resuming '+name+' from its committed declaration/checkpoints',flush=True)
    previous=None
    while True:
        for child in children.values():child.poll()
        record=status_record();temporary=OUT/'status.tmp'
        temporary.write_text(json.dumps(record,indent=2)+'\n');temporary.replace(OUT/'status.json')
        concise={name:(row['state'],row['last_stage'],row['last_step']) for name,row in record['jobs'].items()}
        if concise!=previous:print(json.dumps(concise),flush=True);previous=concise
        if not any(row['state']=='running' for row in record['jobs'].values()):break
        time.sleep(15)
    for stream in streams:stream.close()
    if any(row['state']!='complete' for row in record['jobs'].values()):raise SystemExit(1)


if __name__=='__main__':main()
