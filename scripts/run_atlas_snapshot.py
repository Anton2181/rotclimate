"""Build an adopted atlas from a pinned sparse worktree, leaving live maps alone.

Versioned source/data inputs come from the recorded Git revision. Missing large
observational cache files are linked, with raw archive hashes checked against
the adopted validation protocol. Separate early correction training can run
with --train-only; the existing receipt/lock serializes its writers.
"""
from pathlib import Path
import argparse
import fcntl
import importlib.metadata
import json
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json


def link_missing(source, destination):
    """Keep checked-out versioned files; share only missing cache files."""
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        target = destination / path.name
        if path.is_dir():
            link_missing(path, target)
        elif not target.exists():
            target.symlink_to(path.resolve())


def prepare(plan, plan_path, out):
    lock = (out / '.setup.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX)
    snapshot = out / 'snapshot'; manifest = out / 'snapshot.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        if saved['plan_sha256'] != file_hash(plan_path):
            raise ValueError('Snapshot declaration changed')
        revision = saved['source_commit']
    else:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        if subprocess.check_output(['git', 'show', revision + ':' + str(plan_path.resolve().relative_to(ROOT))], cwd=ROOT) != plan_path.read_bytes():
            raise ValueError('Commit the snapshot declaration first')
    if not (snapshot / '.git').exists():
        subprocess.run(['git', 'worktree', 'add', '--detach', '--no-checkout', str(snapshot), revision], cwd=ROOT, check=True)
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=snapshot, text=True).strip()
    if actual != revision: raise ValueError('Snapshot revision changed')
    if not (snapshot / 'scripts/build_atlas_variant.py').exists():
        patterns = ['/' + name + '/' for name in ['scripts', 'rotclimate', 'harvest', 'population', 'foraging', 'polity', 'atlas', 'data', 'calibration', 'ravages']]
        patterns += ['/atlases/pages.json', '/output/language_areas_20261101/layer2c/summary.json', '/.gitignore', '/.gitattributes']
        subprocess.run(['git', 'sparse-checkout', 'set', '--no-cone', *patterns], cwd=snapshot, check=True)
        subprocess.run(['git', 'checkout', revision], cwd=snapshot, check=True, capture_output=True)
    if not (snapshot / 'ravages/data.json').exists():
        subprocess.run(['git', 'sparse-checkout', 'add', '/ravages/'], cwd=snapshot, check=True)
    link_missing(ROOT / 'data', snapshot / 'data')
    if not (snapshot / '.venv').exists(): (snapshot / '.venv').symlink_to(ROOT / '.venv', target_is_directory=True)
    protocol = json.loads((ROOT / plan['validation_protocol']).read_text())
    required = {name: digest for name, digest in protocol['sources'].items()
                if name.startswith('rotclimate/') or name.endswith('.zip')}
    libraries = {name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'scikit-learn', 'Pillow']}
    if manifest.exists() and saved.get('libraries', libraries) != libraries:
        raise ValueError('Snapshot scientific library versions changed')
    for name, digest in required.items():
        if file_hash(snapshot / name) != digest: raise ValueError('Snapshot differs from validated physics/input: ' + name)
    record = saved if manifest.exists() else {}
    record.update(profile=plan['profile'], source_commit=revision, plan_sha256=file_hash(plan_path),
                  validated_sources=required, libraries=libraries, snapshot=str(snapshot))
    write_json(manifest, record)
    return snapshot


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--train-only', action='store_true'); a = ap.parse_args()
    plan = json.loads(a.plan.read_text()); out = ROOT / plan['output']; out.mkdir(parents=True, exist_ok=True)
    snapshot = prepare(plan, a.plan, out); py = str(ROOT / '.venv/bin/python')
    status_path = out / ('training_status.json' if a.train_only else 'snapshot_status.json')
    lock = (out / ('.training-driver.lock' if a.train_only else '.build-driver.lock')).open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    stages_file = out / ('training_completed.json' if a.train_only else 'stages_completed.json')
    done = json.loads(stages_file.read_text()) if stages_file.exists() else []
    def status(stage, **fields):
        from datetime import datetime, timezone
        row = dict(stage=stage, profile=plan['profile'], updated_utc=datetime.now(timezone.utc).isoformat(), **fields)
        write_json(status_path, row); print(json.dumps(row), flush=True)
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', PY=py,
               TAG=plan['profile'], PARAMS=plan['params'], OUT=plan['correction_output'], CAL=plan['corrections'])
    train = ('correction_training', ['bash', 'scripts/retrain_earth_corrections.sh'])
    atlas = 'atlases/' + plan['stage_name']; checkpoint = plan['checkpoint']
    stages = [train] if a.train_only else [
        ('world', [py, '-u', '-I', 'scripts/build_atlas_variant.py', '--params', plan['world_params'],
            '--name', plan['stage_name'], '--title', 'Rotclimate Earth-Fit Atlas',
            '--eyebrow', 'Climate, farming and settlement · three layouts · c.200 AD',
            '--note', f'Earth {plan["profile"]} physics on the published world geometry; layouts 1–3 and verified numerical checks.',
            '--downsample', '8', '--image-scale', '2', '--seeds', '1,2,3', '--workers', '1',
            '--fit-objective', 'zonefit', '--require-verified', '--checkpoint', checkpoint]),
        ('diagnostics', [py, '-I', 'scripts/add_r40_atlas_diagnostics.py', atlas, '--out', plan['output'] + '/diagnostics', '--release', plan['profile']]),
        train,
        ('corrected_layers', [py, '-I', 'scripts/add_corrected_layers.py', atlas, '--checkpoint', checkpoint,
            '--corrections', plan['corrections'], '--evals', plan['correction_output']]),
        ('corrected_climate', [py, '-I', 'scripts/add_corrected_climate.py', atlas, '--checkpoint', checkpoint,
            '--corrections', plan['corrections'], '--gif']),
        ('languages', [py, '-I', 'scripts/add_language_layers.py', atlas]),
        ('release_identity', [py, '-I', 'scripts/tag_atlas_physics.py', atlas, '--params', plan['params'],
                              '--profile', plan['profile'], '--report', plan['report']])]
    try:
        manifest = json.loads((out / 'snapshot.json').read_text())
        for name, command in stages:
            if name in done: continue
            for path, digest in manifest['validated_sources'].items():
                if file_hash(snapshot / path) != digest: raise ValueError('Validated snapshot input changed: ' + path)
            status('running', step=name, snapshot=str(snapshot))
            with (out / (name + '.log')).open('a') as log:
                subprocess.run(command, cwd=snapshot, env=env, check=True, stdout=log, stderr=subprocess.STDOUT)
            for path, digest in manifest['validated_sources'].items():
                if file_hash(snapshot / path) != digest: raise ValueError('Snapshot input changed during stage: ' + path)
            done.append(name); write_json(stages_file, done)
        status('training_complete' if a.train_only else 'ready_for_publication', snapshot=str(snapshot))
    except Exception as error:
        status('failed', error=repr(error)); raise


if __name__ == '__main__': main()
