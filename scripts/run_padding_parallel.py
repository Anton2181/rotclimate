"""Execute only the prospective nine-case private scheduling amendment."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, freeze, write_json

PLAN = ROOT / 'calibration/padding_sensitivity_parallel_20261127/plan.json'
OUT = ROOT / 'output/padding_sensitivity_parallel_20261127'


def run_phase(label, arguments, expected, run=subprocess.run):
    write_json(OUT / 'driver_status.json', dict(stage=label, pid=os.getpid(), utc=datetime.now(timezone.utc).isoformat()))
    with (OUT / (label + '.log')).open('ab') as log:
        result = run(arguments, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode or not expected.exists():
        write_json(OUT / 'driver_failure.json', dict(stage=label, returncode=result.returncode,
            expected_output_present=expected.exists(), automatic_retry=False))
        return False
    return True


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / '.driver.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 10
    assert not (OUT / 'driver_failure.json').exists(), 'Preserve failure and record recovery review before restarting'
    sources = [Path(__file__), PLAN, ROOT / 'scripts/padding_sensitivity.py', ROOT / 'scripts/review_padding_sensitivity.py']
    freeze(OUT / 'driver_protocol.json', dict(sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        maximum_integrations=9, one_worker=True, model_overrides={}, auto_adoption=False))
    py = str(ROOT / '.venv/bin/python')
    if not (OUT / 'results.json').exists():
        if not run_phase('integrating', [py, '-u', '-I', str(ROOT / 'scripts/padding_sensitivity.py'),
                '--plan', str(PLAN), '--private-parallel', '--run'], OUT / 'results.json'):
            raise SystemExit('Padding command failed; no automatic retry')
    if not (OUT / 'review.json').exists():
        if not run_phase('reviewing', [py, '-u', '-I', str(ROOT / 'scripts/review_padding_sensitivity.py'),
                '--plan', str(PLAN)], OUT / 'review.json'):
            raise SystemExit('Review failed; no physical rerun or automatic retry')
    write_json(OUT / 'driver_status.json', dict(stage='ready_for_agent_figure_and_findings_review',
        pid=os.getpid(), utc=datetime.now(timezone.utc).isoformat(), climate_adopted=False, main_patch_applied=False))


if __name__ == '__main__':
    main()
