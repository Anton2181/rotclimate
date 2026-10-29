"""Wait for the frozen batch, verify/publish results, then commit only its artifacts."""
from pathlib import Path
import argparse,json,os,subprocess,sys,time,traceback
from datetime import datetime,timezone
import fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from analyze_regional_rainfall import analyze

ALLOWED=('atlases/climate_accuracy/','output/regional_rainfall_benchmark_20261029/','output/regional_rainfall_results_final_20261029/')
EXACT={'scripts/organize_climate_accuracy.py','reports/REGIONAL_RAINFALL_RESULTS_20261029.md'}
SCRIPTS=['scripts/finalize_rainfall_benchmark.py','scripts/publish_regional_rainfall_results.py','scripts/analyze_regional_rainfall.py','scripts/organize_climate_accuracy.py','scripts/package_fit_atlases.py','scripts/check_atlas_checkout.py','scripts/check_portable_atlases.py','scripts/check_climate_accuracy_browser.py','scripts/serve_atlases.py']


def commit_artifacts(root,paths,message):
    root=root.resolve();names=[]
    for path in paths:
        path=path.resolve();name=str(path.relative_to(root))
        if not path.is_file() or (name not in EXACT and not any(name.startswith(prefix) for prefix in ALLOWED)):raise ValueError('Refusing a non-artifact commit path: '+name)
        names.append(name)
    if not names:raise ValueError('No declared artifacts to commit')
    subprocess.run(['git','add','-f','--',*names],cwd=root,check=True,capture_output=True)
    # --only prevents an unrelated staged user change from joining this commit.
    subprocess.run(['git','commit','--only','-m',message,'--',*names],cwd=root,check=True,capture_output=True)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()


def arm(path,source,out):
    path=path.resolve();source=source.resolve();out=out.resolve();assert not path.exists(),'Retain earlier automation declarations'
    protocol=ROOT/'calibration/regional_rainfall_benchmark_20261029/plan.json';assert protocol.read_bytes()==(source/'frozen_protocol.json').read_bytes()
    guards=[ROOT/'atlases/climate_accuracy/index.html',ROOT/'reports/REGIONAL_RAINFALL_RESULTS_20261029.md',ROOT/'scripts/organize_climate_accuracy.py',*sorted((ROOT/'atlases/climate_accuracy/data').glob('regional_rainfall_results*')),ROOT/'atlases/climate_accuracy/data/regional_rainfall_maps.png']
    plan=dict(purpose='Finish the authorized monthly rainfall batch automatically after all declared attempts, preserving fixed masks/objective and every result',source=str(source.relative_to(ROOT)),out=str(out.relative_to(ROOT)),benchmark_plan_sha256=file_hash(protocol),sources={name:file_hash(ROOT/name) for name in SCRIPTS},guarded_publication_inputs={str(p.relative_to(ROOT)):file_hash(p) for p in guards},branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),push_remote='origin',push_ref='refs/heads/claude/friendly-turing-43ygeu',timeout_s=28800,poll_s=15,commit_scope='Only explicit own atlas/report/result artifacts via git commit --only; never unrelated staged work',physics_adoption=False,recalibration=False)
    path.parent.mkdir(parents=True,exist_ok=True);write_json(path,plan);print(json.dumps(dict(armed_plan=str(path.relative_to(ROOT)),note='Commit this declaration before starting the detached finalizer'),indent=2))


def run(path):
    path=path.resolve();plan=json.loads(path.read_text());out=ROOT/plan['out'];source=ROOT/plan['source'];out.mkdir(parents=True,exist_ok=True)
    assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Commit automation declaration first'
    def status(stage,**extra):
        row=dict(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat(),automation_plan_sha256=file_hash(path),**extra);write_json(out/'automation_status.json',row);print(json.dumps(row),flush=True)
    def command(arguments,log_name):
        with (out/log_name).open('w') as log:subprocess.run(arguments,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',GIT_TERMINAL_PROMPT='0'))
    prior_status=out/'automation_status.json'
    if prior_status.exists() and json.loads(prior_status.read_text()).get('stage')=='finished_pushed':
        print(prior_status.read_text());return
    status('waiting_for_all_declared_attempts');deadline=time.monotonic()+plan['timeout_s'];last_finished=None
    while not (source/'verification.json').exists():
        if time.monotonic()>deadline:status('timed_out_waiting_for_original_batch');return
        progress=source/'progress.json'
        if progress.exists():
            finished=len(json.loads(progress.read_text()).get('finished_cases',[]))
            if finished!=last_finished:status('waiting_for_all_declared_attempts',finished_cases=finished);last_finished=finished
        time.sleep(plan['poll_s'])
    status('batch_finished_validating_sources')
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    protocol=ROOT/'calibration/regional_rainfall_benchmark_20261029/plan.json';assert file_hash(protocol)==plan['benchmark_plan_sha256'];batch=json.loads((source/'verification.json').read_text());assert len(batch['results'])==10,'Every original attempt must be finalized'
    analyze(source,out/'analysis')
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    changed=[name for name,digest in plan['guarded_publication_inputs'].items() if file_hash(ROOT/name)!=digest]
    if branch!=plan['branch'] or changed:status('scored_publication_guard_changed',branch=branch,changed_paths=changed);return
    status('publishing_complete_or_retained_failed_cases')
    command([sys.executable,'scripts/publish_regional_rainfall_results.py','--source',str(source),'--out',str(out)],'publish.log')
    # Make the now-final rainfall comparison the opening study in the launcher.
    organizer=ROOT/'scripts/organize_climate_accuracy.py';text=organizer.read_text();entry=next(line for line in text.splitlines(keepends=True) if line.lstrip().startswith("('regional-rainfall-results',"));text=text.replace(entry,'',1).replace('STUDIES=[\n','STUDIES=[\n'+entry,1);organizer.write_text(text)
    command([sys.executable,'scripts/organize_climate_accuracy.py','--report',str(out/'organization.json')],'organization.log')
    # Stage only the served artifacts for the Windows checkout check. --only
    # below still excludes any unrelated user changes already in the index.
    served=[ROOT/'atlases/climate_accuracy/index.html',ROOT/'reports/REGIONAL_RAINFALL_RESULTS_20261029.md',organizer,*sorted((ROOT/'atlases/climate_accuracy/data').glob('regional_rainfall_results*')),ROOT/'atlases/climate_accuracy/data/regional_rainfall_maps.png']
    subprocess.run(['git','add','--',*[str(p.relative_to(ROOT)) for p in served]],cwd=ROOT,check=True,capture_output=True)
    status('verifying_portable_and_browser_outputs')
    command([sys.executable,'scripts/check_atlas_checkout.py','--out',str(out/'checkout.json')],'checkout.log')
    command([sys.executable,'scripts/package_fit_atlases.py','--out',str(out/'portable.zip')],'package.log')
    command([sys.executable,'scripts/check_portable_atlases.py',str(out/'portable.zip'),'--out',str(out/'portable.json')],'portable.log')
    import socket
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    server_log=(out/'server.log').open('w');server=subprocess.Popen([sys.executable,'scripts/serve_atlases.py','--no-browser','--port',str(port)],cwd=ROOT,stdout=server_log,stderr=subprocess.STDOUT)
    try:
        time.sleep(1);command([sys.executable,'scripts/check_climate_accuracy_browser.py','--base',f'http://127.0.0.1:{port}','--out',str(out/'browser')],'browser.log')
    finally:server.terminate();server.wait();server_log.close()
    # Independently compare the current published files with the packaged bytes.
    import zipfile
    with zipfile.ZipFile(out/'portable.zip') as z:
        for p in served:
            if p!=organizer:assert p.read_bytes()==z.read(str(p.relative_to(ROOT))),str(p)
    status('qa_passed_committing_own_artifacts')
    raw=[p for p in source.rglob('*') if p.is_file() and p.suffix in {'.json','.npz'}]
    generated=[p for p in out.rglob('*') if p.is_file() and p.name!='automation_status.json' and p.suffix in {'.json','.npz','.png'} and not (p.suffix=='.png' and 'browser' in p.parts)]
    commit=commit_artifacts(ROOT,list(dict.fromkeys(served+raw+generated)),'Publish completed regional rainfall benchmark and every retained outcome')
    status('committed_pushing',commit=commit)
    try:command(['git','-c','http.version=HTTP/1.1','push',plan['push_remote'],'HEAD:'+plan['push_ref']],'push.log')
    except subprocess.CalledProcessError:status('committed_push_failed',commit=commit);return
    status('finished_pushed',commit=commit,primary=json.loads((out/'analysis/analysis.json').read_text())['primary'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--arm',action='store_true');parser.add_argument('--source',type=Path);parser.add_argument('--out',type=Path);a=parser.parse_args()
    if a.arm:
        assert a.source and a.out;arm(a.plan,a.source,a.out)
    else:
        plan=json.loads(a.plan.read_text());folder=ROOT/plan['out'];folder.mkdir(parents=True,exist_ok=True)
        with (folder/'.automation.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:run(a.plan)
            except Exception as error:
                write_json(folder/'automation_status.json',dict(stage='failed_retained',error=repr(error),traceback=traceback.format_exc()));raise
