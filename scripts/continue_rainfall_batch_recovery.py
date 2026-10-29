"""Second batch recovery, preserving the first recovery receipt and counts.

Reuses the verified first recovery controller. Only its recovery-receipt name
and cumulative process-segment counts change. Scientific case drivers and the
original benchmark controller remain frozen.
"""
from pathlib import Path
import argparse,inspect,json,sys,textwrap
import fcntl
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import continue_rainfall_benchmark as original


def run(plan,out):
    recovery=json.loads(plan.read_text())
    assert original.file_hash(out/'recovery_batch.json')==recovery['prior_recovery_receipt_sha256']
    source=textwrap.dedent(inspect.getsource(original.run))
    assert source.count("out/'recovery_batch.json'")==2
    source=source.replace("out/'recovery_batch.json'","out/'recovery_batch_2.json'")
    source=source.replace('interrupted_process_segments=2','interrupted_process_segments=4').replace('recovery_segments_planned=2','recovery_segments_planned=4').replace('interrupted_process_segments_retained=2','interrupted_process_segments_retained=4').replace('checkpoint_continuation_segments=2','checkpoint_continuation_segments=4')
    source=source.replace('Two infrastructure interruptions continued','Four infrastructure interruptions continued')
    namespace=dict(original.run.__globals__,__file__=__file__)
    exec(compile(source,'<second recovery receipt accounting>','exec'),namespace);namespace['run'](plan,out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recovery-plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with (a.out/'.recovery.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);run(a.recovery_plan,a.out)
