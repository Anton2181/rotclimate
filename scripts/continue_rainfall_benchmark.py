"""Continue an interrupted frozen rainfall batch without rerunning finished cases."""
from pathlib import Path
import argparse,inspect,json,os,subprocess,sys,textwrap
import fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import run_regional_rainfall_benchmark as batch
from local_benchmark_protocol import file_hash,write_json


def run(recovery_path,out):
    recovery_path=recovery_path.resolve();out=out.resolve();recovery=json.loads(recovery_path.read_text())
    assert subprocess.check_output(['git','show','HEAD:'+str(recovery_path.relative_to(ROOT))],cwd=ROOT)==recovery_path.read_bytes(),'Commit recovery declaration first'
    for name,digest in recovery['sources'].items():assert file_hash(ROOT/name)==digest,name
    path=ROOT/recovery['original_plan'];assert file_hash(path)==recovery['original_plan_sha256']
    prior=json.loads((out/'progress.json').read_text());assert not (out/'verification.json').exists()
    done={r['name'] for r in prior['finished_cases']}
    for r in prior['finished_cases']:
        assert file_hash(out/r['name']/'verification.json')==r['receipt_sha256']
    for replay_path in recovery['qualification_replays']:
        receipt=json.loads((ROOT/replay_path/'verification.json').read_text())
        assert all(receipt['next_day_exact_reproduction'].values())
        meta=json.loads((ROOT/replay_path/'recovery.json').read_text())
        assert meta['recovery_driver_sha256']==file_hash(ROOT/'scripts/resume_rainfall_month.py')
    for name,files in recovery['interrupted_cases'].items():
        assert name not in done
        for relative,digest in files.items():assert file_hash(out/name/relative)==digest
    source=textwrap.dedent(inspect.getsource(batch.run))
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,old
        source=source.replace(old,new)
    replace("    if out.exists() and any(out.iterdir()):raise ValueError('Retain previous rainfall benchmark attempts')\n",'')
    replace('records=[]','records=list(prior_records)')
    replace("specs=[c for c in plan['cases'] if c['kind']==stage]","specs=[c for c in plan['cases'] if c['kind']==stage and c['name'] not in already_done]")
    replace("        script='scripts/r39_rainfall_control.py' if spec['kind']=='legacy' else 'scripts/rainfall_month_pilot.py'", "        resume=spec['name'] in interrupted\n        script='scripts/resume_rainfall_month.py' if resume else ('scripts/r39_rainfall_control.py' if spec['kind']=='legacy' else 'scripts/rainfall_month_pilot.py')")
    replace("'--out',str(folder)","'--source' if resume else '--out',str(folder)")
    replace(".open('w');start=time.monotonic()", ".open('a');start=time.monotonic()")
    namespace=dict(batch.run.__globals__,prior_records=prior['finished_cases'],already_done=done,interrupted=set(recovery['interrupted_cases']))
    write_json(out/'recovery_batch.json',dict(recovery_plan_sha256=file_hash(recovery_path),controller_sha256=file_hash(Path(__file__)),interrupted_process_segments=2,recovery_segments_planned=2,extra_earth_initializations_by_recovery=0,scope='Two infrastructure interruptions continued from retained daily checkpoints. Qualification replay segments are separate diagnostics. Original initializations count once; interrupted segments are not discarded and are not new model starts. All queued literal cases still run.'))
    exec(compile(source,'<frozen batch with checkpoint recovery>','exec'),namespace);namespace['run'](path,out)
    receipt_path=out/'verification.json';receipt=json.loads(receipt_path.read_text());receipt.update(recovery_batch_sha256=file_hash(out/'recovery_batch.json'),interrupted_process_segments_retained=2,checkpoint_continuation_segments=2,qualification_replay_segments=recovery['actual_replay_segments_retained'])
    write_json(receipt_path,receipt)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recovery-plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with (a.out/'.recovery.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(a.recovery_plan,a.out)
