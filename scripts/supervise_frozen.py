"""Run the fixed vapor pilot with a deadline and immutable scientific sources.

The child alone creates its scientific protocol. This supervisor records its
own startup identity, checks every protocol source initially and on completion,
and detects intervening edits using file identity and nanosecond stat changes.
Use a fresh output directory; redirect supervisor stdout outside that directory.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import signal
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT/'scripts/check_vapor_flux.py'
THREADS = {'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'}


class MonitorStop(RuntimeError):
    """An immutable input, deadline or completion condition failed."""


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def stat_identity(path):
    s = path.stat()
    return s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns


def stable_hash(path):
    """Hash one file, rejecting a concurrent mutation rather than caching it."""
    before = stat_identity(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    after = stat_identity(path)
    if before != after:
        raise MonitorStop('Source changed while hashing: '+str(path))
    return digest.hexdigest(), after


class SourceGuard:
    """Initial/final full SHA verification with stat-checked intermediate polls."""

    def __init__(self):
        self.expected = {}
        self.checked = {}

    def bind(self, path, sha):
        # Keep the original path so retargeting a source symlink changes the
        # identity we stat, rather than silently monitoring its old target.
        path = Path(os.path.abspath(path))
        if (not isinstance(sha, str) or len(sha) != 64
                or any(c not in '0123456789abcdef' for c in sha)):
            raise MonitorStop('Invalid source SHA-256: '+str(path))
        if path in self.expected and self.expected[path] != sha:
            raise MonitorStop('Conflicting source identity: '+str(path))
        self.expected[path] = sha

    def verify(self, *, full=False):
        for path, expected in self.expected.items():
            try:
                current = stat_identity(path)
                if full or self.checked.get(path) != current:
                    actual, current = stable_hash(path)
                    if actual != expected:
                        raise MonitorStop('Frozen source changed: '+str(path))
                    self.checked[path] = current
            except OSError as error:
                raise MonitorStop('Frozen source unavailable: '+str(path)) from error


def bind_protocol(path, guard):
    """Read the child's complete atomic protocol once; bind it and its sources."""
    try:
        before = stat_identity(path)
        raw = path.read_bytes()
        if stat_identity(path) != before:
            raise MonitorStop('Scientific protocol changed while being read')
        protocol = json.loads(raw)
    except (OSError, ValueError) as error:
        raise MonitorStop('Cannot read scientific protocol: '+str(path)) from error
    sources = protocol.get('sources') if isinstance(protocol, dict) else None
    if not isinstance(sources, dict) or not sources:
        raise MonitorStop('Scientific protocol has no source bindings')
    for name, sha in sources.items():
        if not isinstance(name, str) or Path(name).is_absolute():
            raise MonitorStop('Scientific source must be relative to the repository')
        source = Path(os.path.abspath(ROOT/name))
        if not source.resolve().is_relative_to(ROOT):
            raise MonitorStop('Scientific source escapes the repository: '+name)
        guard.bind(source, sha)
    protocol_sha = hashlib.sha256(raw).hexdigest()
    guard.bind(path, protocol_sha)
    guard.verify(full=True)
    return protocol, protocol_sha


def stop_group(child):
    """Stop the runner and its pool workers, preserving all existing artifacts."""
    if child is None:
        return
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        child.wait(timeout=5.)
    except subprocess.TimeoutExpired:
        pass
    # The parent may exit before pool workers; signal the whole group again.
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()


def progress_counts(out):
    """Operational counts only; never rewrite the runner's scientific records."""
    path = out/'progress.json'
    if not path.exists():
        return {}
    try:
        progress = json.loads(path.read_text())
        rows = progress.get('records', [])
        return dict(completed_runs=len(rows),
            passed_runs=sum(r.get('status') == 'passed' for r in rows),
            failed_runs=sum(r.get('status') == 'failed' for r in rows))
    except (OSError, ValueError, TypeError):
        return {}


def check_completion(out, protocol):
    """The dedicated runner must finish its full review, not merely exit zero."""
    try:
        review = json.loads((out/'review.json').read_text())
        progress = json.loads((out/'progress.json').read_text())
    except (OSError, ValueError) as error:
        raise MonitorStop('Missing completed scientific review/progress') from error
    run_id = hashlib.sha256(json.dumps(protocol, sort_keys=True,
        allow_nan=False).encode()).hexdigest()
    if (review.get('complete') is not True or review.get('identity') != run_id
            or review.get('all_per_step_checks_passed') is not True
            or review.get('physics_or_atlas_adoption') is not False
            or progress.get('complete') is not True):
        raise MonitorStop('Child did not certify a complete scientific comparison')


def run(plan_path, out, *, max_seconds=7200., poll_seconds=3.):
    """Launch only check_vapor_flux.py under an immutable input monitor."""
    plan_path, out = Path(plan_path).resolve(), Path(out).resolve()
    if (not math.isfinite(max_seconds) or not 0 < max_seconds <= 7200
            or not math.isfinite(poll_seconds) or not 2 <= poll_seconds <= 5):
        raise ValueError('Need 0 < max-seconds <= 7200 and 2 <= poll-seconds <= 5')
    if not plan_path.is_file() or not RUNNER.is_file():
        raise ValueError('Plan and dedicated runner must exist')
    if out.exists() and any(out.iterdir()):
        raise ValueError('Preserve the nonempty output directory; choose a fresh one')
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'],
        cwd=ROOT, text=True).strip()
    startup = {}
    guard = SourceGuard()
    for path in (Path(__file__).resolve(), RUNNER, plan_path):
        sha, _ = stable_hash(path)
        startup[str(path)] = sha
        guard.bind(path, sha)
    plan = json.loads(plan_path.read_text())
    planned_runs = len(plan['profiles'])*len(plan['regions'])
    out.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-u', '-I', str(RUNNER), '--plan', str(plan_path), '--out', str(out)]
    environment = dict(os.environ, **THREADS)
    started = time.monotonic()
    child = None
    protocol = None
    protocol_sha = None

    def status(state, result, reason=None):
        write_json(out/'status.json', dict(state=state, status=result, reason=reason,
            updated_utc=utc_now(), elapsed_seconds=round(time.monotonic()-started, 1),
            max_seconds=max_seconds, source_commit=source_commit,
            monitor_pid=os.getpid(), runner_pid=child.pid if child else None,
            numerical_threads={k:int(v) for k,v in THREADS.items()},
            planned_runs=planned_runs, protocol_sha256=protocol_sha,
            bound_source_files=len(guard.expected), **progress_counts(out)))

    def interrupted(signum, frame):
        raise MonitorStop('Supervisor interrupted by signal '+str(signum))

    previous_handlers = {s:signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        with (out/'run.log').open('x') as log:
            child = subprocess.Popen(command, cwd=ROOT, env=environment,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            manifest = dict(created_utc=utc_now(), source_commit=source_commit,
                monitor_pid=os.getpid(), runner_pid=child.pid, command=command,
                plan=str(plan_path), out=str(out), max_seconds=max_seconds,
                poll_seconds=poll_seconds, startup_sources_sha256=startup,
                numerical_threads={k:int(v) for k,v in THREADS.items()})
            write_json(out/'monitor_manifest.json', manifest)
            # The manifest itself is immutable, including both process IDs.
            guard.bind(out/'monitor_manifest.json', stable_hash(out/'monitor_manifest.json')[0])
            while True:
                if time.monotonic()-started >= max_seconds:
                    raise MonitorStop('Wall-clock deadline exceeded')
                protocol_path = out/'protocol.json'
                if protocol is None and protocol_path.exists():
                    protocol, protocol_sha = bind_protocol(protocol_path, guard)
                guard.verify()
                code = child.poll()
                if code is not None:
                    if code != 0:
                        raise MonitorStop('Scientific runner exited with code '+str(code))
                    if protocol is None:
                        raise MonitorStop('Scientific runner completed without a protocol')
                    guard.verify(full=True)
                    if time.monotonic()-started >= max_seconds:
                        raise MonitorStop('Wall-clock deadline exceeded during final source verification')
                    check_completion(out, protocol)
                    status('complete', 'passed')
                    print('Frozen comparison completed and all sources verified.', flush=True)
                    return 0
                status('running', 'running')
                time.sleep(min(poll_seconds, max(0., max_seconds-(time.monotonic()-started))))
    except BaseException as error:
        stop_group(child)
        reason = str(error) or type(error).__name__
        write_json(out/'monitor_failure.json', dict(status='failed', reason=reason,
            error_type=type(error).__name__, updated_utc=utc_now(),
            source_commit=source_commit, monitor_pid=os.getpid(),
            runner_pid=child.pid if child else None, protocol_sha256=protocol_sha))
        status('failed', 'failed', reason)
        print('Frozen comparison stopped: '+reason, file=sys.stderr, flush=True)
        return 1
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--max-seconds', type=float, default=7200.)
    parser.add_argument('--poll-seconds', type=float, default=3.)
    args = parser.parse_args()
    try:
        return run(args.plan, args.out, max_seconds=args.max_seconds, poll_seconds=args.poll_seconds)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    raise SystemExit(main())
