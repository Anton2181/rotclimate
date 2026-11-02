"""Separate vapor transport, storm mixing and accounted condensation on r42.

Queued behind the complete original screen. Existing opt-in physics only;
no tuning, sealed data, adoption or normal atlas changes.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, freeze, write_json
from validate_r42_multistart import paired_score

PREFIX = 'output/r42_storm_factorial_20261102/'


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=1); a = ap.parse_args()
    if a.workers < 1: ap.error('workers must be positive')
    plan = json.loads(a.plan.read_text()); out = ROOT / PREFIX; out.mkdir(parents=True, exist_ok=True)
    lock = (out / '.study.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if (out / 'status.json').exists() and json.loads((out / 'status.json').read_text()).get('stage') == 'finished_pushed': return
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(a.plan.resolve().relative_to(ROOT))], cwd=ROOT) != a.plan.read_bytes():
        raise ValueError('Commit the prospective declaration before starting')
    freeze(out / 'plan.json', plan)

    def status(stage, **fields):
        row = dict(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat(), **fields)
        write_json(out / 'status.json', row); print(json.dumps(row), flush=True)

    def check():
        for name, digest in plan['sources'].items():
            if file_hash(ROOT / name) != digest: raise ValueError('Frozen input changed: ' + name)
        if subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() != plan['branch']:
            raise ValueError('Study branch changed')

    try:
        status('waiting_for_original_screen'); deadline = time.monotonic() + plan['timeout_s']
        while True:
            marker = ROOT / plan['after_status']
            current = json.loads(marker.read_text()) if marker.exists() else {}
            if current.get('stage') == 'finished_pushed': break
            if current.get('stage') == 'failed' or time.monotonic() > deadline:
                raise RuntimeError('Original screen failed or timed out; factorial remains unstarted')
            time.sleep(15)
        check()
        ref = json.loads((ROOT / plan['reference'] / 'summary.json').read_text())
        if not ref.get('complete'): raise ValueError('Incomplete reference')
        rows = {}
        for name, params in plan['profiles'].items():
            check(); folder = out / name; status('running_profile', profile=name)
            command = [sys.executable, '-u', '-I', 'scripts/benchmark_local.py', '--fit', params,
                       '--regions', *plan['regions'], '--region-specs', plan['region_specs'],
                       '--workers', str(a.workers), '--out', str(folder)]
            with (out / (name + '.log')).open('a') as log:
                process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
            check()
            summary = json.loads((folder / 'summary.json').read_text())
            if set(summary['regions']) != set(plan['regions']): raise ValueError('Missing declared cases')
            if not summary.get('complete'):
                rows[name] = dict(status='failed', score=None, failures=summary.get('failures')); continue
            if process.returncode: raise RuntimeError('Unexpected benchmark process failure')
            for region, row in summary['regions'].items():
                if file_hash(folder / 'cells' / (region + '.npz')) != row['cells_sha256']:
                    raise ValueError('Raw result changed: ' + region)
            rows[name] = dict(status='complete', score=paired_score(ref['regions'], summary['regions'], plan['regions']))
        write_json(out / 'results.json', dict(adoption=False, sealed_run=False, profiles=rows,
            note='Eight reused development regions. Isolates existing mechanisms; incomplete profiles are unscored. Full49/fine/unseen checks required for adoption.'))
        names = sorted(str(p.relative_to(ROOT)) for p in out.rglob('*') if p.is_file()
                       and p.suffix in {'.json', '.npz', '.log'} and p.name not in {'status.json', 'push.log'})
        if not all(n.startswith(PREFIX) for n in names): raise ValueError('Unrelated publication path')
        subprocess.run(['git', 'add', '-f', '--', *names], cwd=ROOT, check=True, capture_output=True)
        changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', *names], cwd=ROOT)
        if changed.returncode not in (0, 1): raise RuntimeError('Cannot inspect result staging')
        if changed.returncode:
            subprocess.run(['git', 'commit', '--only', '-m', 'Record isolated r42 vapor and storm-closure factorial', '--', *names],
                           cwd=ROOT, check=True, capture_output=True)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        status('committed_pushing', commit=commit)
        with (out / 'push.log').open('a') as log:
            subprocess.run(['git', 'push', '--atomic', plan['remote'],
                            *[commit + ':' + ref for ref in plan['push_refs']]], cwd=ROOT, check=True,
                           stdout=log, stderr=subprocess.STDOUT)
        status('finished_pushed', commit=commit)
    except Exception as error:
        status('failed', error=repr(error)); raise


if __name__ == '__main__': main()
