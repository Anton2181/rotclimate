"""Wait for the authorized r42 release, verify its artifacts, commit and push.

Arm and commit the plan before starting --run. Unrelated staged work is
excluded with git commit --only. Failed checks stop publication with receipts.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json

PREFIXES = ('atlases/earth_fit/', 'calibration/earth_correction_r42_20261101/',
            'output/earth_correction_r42_20261101/', 'output/atlas_r42/')
EXACT = {'atlases/index.html', 'atlases/pages.json', 'scripts/build_fit_hub.py', 'reports/R42_20261101.md'}
for fit in ('free_fit', 'whittaker_fit', 'earth_physics'):
    EXACT.update('atlases/' + fit + '/' + leaf for leaf in
                 ('index.html', 'climate-comparison.js', 'harvest.js', 'foraging.js', 'population.js'))


def allowed(name):
    parts = Path(name).parts
    if Path(name).is_absolute() or '..' in parts:
        return False
    return (name in EXACT or any(name.startswith(prefix) for prefix in PREFIXES)) and not (
        'previous_atlases' in parts or 'checkpoints' in parts or name.endswith(('.pkl', '.zip'))
        or 'interrupted' in name or name.endswith(('automation_status.json', '.retrain.lock')))


def stage_artifacts(root, names):
    names = sorted(set(names))
    if not names or any(not allowed(name) for name in names):
        raise ValueError('Refusing undeclared release artifacts')
    subprocess.run(['git', 'add', '-f', '-A', '--', *names], cwd=root, check=True, capture_output=True)
    return names


def commit_artifacts(root, names):
    names = stage_artifacts(root, names)
    subprocess.run(['git', 'commit', '--only', '-m', 'Publish verified r42 atlas with matched corrections and all map layers', '--', *names],
                   cwd=root, check=True, capture_output=True)
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def publication_paths():
    # HEAD still contains files already staged for deletion by the first QA
    # snapshot; keep them in the later --only commit's explicit path list.
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    tracked += subprocess.check_output(['git', 'ls-tree', '-r', '-z', '--name-only', 'HEAD'], cwd=ROOT).decode().split('\0')
    names = {name for name in tracked if name and allowed(name)}
    for prefix in PREFIXES:
        folder = ROOT / prefix
        for path in folder.rglob('*'):
            if not path.is_file():
                continue
            name = str(path.relative_to(ROOT))
            if allowed(name) and (prefix.startswith('atlases/') or path.suffix in {'.json', '.npz', '.png', '.log'}):
                names.add(name)
    return sorted(names)


def arm(path):
    if path.exists():
        raise ValueError('Retain existing declarations; use a new plan path')
    scripts = ['finalize_r42_atlas.py', 'build_atlas_variant.py', 'add_r40_atlas_diagnostics.py',
               'add_corrected_layers.py', 'add_corrected_climate.py', 'add_language_layers.py',
               'refresh_atlas_pages.py', 'retrain_earth_corrections.sh', 'correction_training_receipt.py',
               'train_earth_correction.py', 'train_rain_pattern.py', 'evaluate_earth_correction.py',
               'evaluate_rain_pattern.py', 'collect_earth_fields.py', 'package_fit_atlases.py',
               'check_atlas_checkout.py', 'check_portable_atlases.py', 'check_atlas_smoke.js', 'serve_atlases.py']
    files = [ROOT / 'scripts' / name for name in scripts]
    for folder in ('rotclimate', 'harvest', 'population', 'foraging', 'polity'):
        files.extend(sorted((ROOT / folder).glob('*.py')))
    files.extend(p for p in (ROOT / 'data/source').iterdir() if p.is_file())
    files.extend([ROOT / 'atlas/index.html', ROOT / 'output/atlas_r42/release.sh',
                  ROOT / 'calibration/local_accuracy_20261023/r42_params.json', ROOT / 'calibration/map_world_r42/params.json'])
    files.extend(sorted((ROOT / 'atlas').glob('*.js')))
    files.extend(p for p in (ROOT / 'atlases/climate_accuracy').rglob('*') if p.is_file())
    hub = (ROOT / 'scripts/build_fit_hub.py').read_text()
    hub = hub.replace('Earth r41 physics, the best on the 31-region Earth test',
                      'Earth r42 physics, the best on the Earth test (49 development regions and an unseen sealed set)')
    hub = hub.replace('reports/R41_20261101.md">Earth r41 calibration', 'reports/R42_20261101.md">Earth r42 calibration')
    guard = {str(p.relative_to(ROOT)): file_hash(p) for p in files}
    guard['scripts/build_fit_hub.py'] = hashlib.sha256(hub.encode()).hexdigest()
    untouched = {str(p.relative_to(ROOT)): file_hash(p) for fit in ('free_fit', 'whittaker_fit')
                 for p in sorted((ROOT / 'atlases' / fit / 'data').rglob('*')) if p.is_file()}
    plan = dict(declared=datetime.now(timezone.utc).isoformat(), profile='r42',
                branch=subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
                sources_after_release=guard, untouched_map_data=untouched,
                report_base=(ROOT / 'reports/R42_20261101.md').read_text(),
                checkpoint_sha256=file_hash(ROOT / 'output/r42_world/candidate_001.pkl'),
                remote='origin', push_ref='refs/heads/claude/ecstatic-wozniak-rtrwd2',
                scope='Adopted r42 release only; no experimental physics or fit candidate adoption.', timeout_s=21600)
    path.parent.mkdir(parents=True, exist_ok=True); write_json(path, plan)


def run(path):
    plan = json.loads(path.read_text())
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(path.relative_to(ROOT))], cwd=ROOT) != path.read_bytes():
        raise ValueError('Commit the publication plan first')
    out = ROOT / 'output/atlas_r42/final_qa'; out.mkdir(parents=True, exist_ok=True)
    lock = (out / '.publication.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX)
    status_path = out / 'automation_status.json'
    if status_path.exists() and json.loads(status_path.read_text()).get('stage') == 'finished_pushed':
        print(status_path.read_text()); return
    def status(stage, **extra):
        row = dict(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
        write_json(status_path, row); print(json.dumps(row), flush=True)
    def command(args, log):
        with (out / log).open('w') as stream:
            subprocess.run(args, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, check=True,
                           env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', GIT_TERMINAL_PROMPT='0'))
    try:
        status('waiting_for_staged_release'); deadline = time.monotonic() + plan['timeout_s']
        while 'RELEASE DONE' not in (ROOT / 'output/atlas_r42/resumed_20261102.log').read_text():
            if 'RELEASE FAILED' in (ROOT / 'output/atlas_r42/resumed_20261102.log').read_text():
                raise RuntimeError('Atlas release failed; its artifacts remain staged')
            if time.monotonic() > deadline:
                raise RuntimeError('Timed out waiting for release')
            time.sleep(15)
        status('checking_publication_inputs')
        branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip()
        if branch != plan['branch']:
            raise ValueError('Publication branch changed')
        for name, expected in {**plan['sources_after_release'], **plan['untouched_map_data']}.items():
            if file_hash(ROOT / name) != expected:
                raise ValueError('Publication input changed: ' + name)
        if file_hash(ROOT / 'output/r42_world/candidate_001.pkl') != plan['checkpoint_sha256']:
            raise ValueError('Raw climate checkpoint changed')
        from earth_benchmark import load_params
        from rotclimate.joint import SHARED_FIELDS
        raw = load_params(ROOT / 'calibration/local_accuracy_20261023/r42_params.json')
        world = load_params(ROOT / 'atlases/earth_fit/params.json')
        if any(getattr(raw, k) != getattr(world, k) for k in SHARED_FIELDS):
            raise ValueError('Atlas does not use the adopted r42 physics')
        atlas = ROOT / 'atlases/earth_fit'
        summary = json.loads((atlas / 'summary.json').read_text())
        meta = json.loads((atlas / 'data/atlas.json').read_text())
        if not summary['observed_numerics']['all_checks_passed'] or not meta.get('corrected_climate') or not meta.get('languages'):
            raise ValueError('Missing verified climate/corrected/language products')
        expected_languages = {'language_density', 'language_territories', 'language_edges',
                              'language_farming_arrival', 'language_families'}
        if not expected_languages <= {layer['id'] for layer in meta['layers']}:
            raise ValueError('Language layers were not fully restored')
        pages = json.loads((ROOT / 'atlases/pages.json').read_text())
        if 'r42' not in pages['earth_fit']['note']:
            raise ValueError('Atlas page still labels an older physics profile')
        cal = ROOT / 'calibration/earth_correction_r42_20261101'
        temp = json.loads((cal / 'temperature/protocol.json').read_text())['meta']
        rain = json.loads((cal / 'rain_pattern/protocol.json').read_text())['meta']
        for model in (temp, rain):
            if model['physics_params_sha256'] != file_hash(ROOT / 'calibration/local_accuracy_20261023/r42_params.json'):
                raise ValueError('Correction models were trained on different physics')
        for kind in ('temperature', 'rain_pattern'):
            for name, digest in json.loads((cal / kind / 'protocol.json').read_text())['files'].items():
                if file_hash(cal / kind / name) != digest:
                    raise ValueError('Correction model differs from its training receipt: ' + name)
        suffix = ('\n\n<!--r42-atlas-release-20261102-->\n## Atlas release completed\n\n'
                  f'The Earth atlas now uses r42 on the published world geometry, layouts 1–3. '
                  f'Raw strict zone agreement is {100 * summary["strict_accuracy"]:.2f}%. '
                  'Observed numerical checks pass. The corrected climate is the default, with raw output '
                  'available through its climate switch; food, population, foraging and political reach '
                  'were rebuilt, and language layers restored. Free-fit and Whittaker map data are unchanged.\n\n'
                  f'R42-trained corrections, with geographic clusters held out: temperature MAE '
                  f'{temp["raw_monthly_mae_C"]:.4f} → {temp["held_out_monthly_mae_C"]:.4f} C; rain loss '
                  f'{rain["raw_loss"]:.4f} → {rain["held_out_loss"]:.4f}. '
                  'These correction scores use dev31; they are separate from the raw 49-region adoption test.\n\n'
                  'Browser, Windows-checkout and portable-bundle receipts are retained in '
                  '`output/atlas_r42/final_qa`. The r41 atlas backup is kept outside publication.\n')
        report = ROOT / 'reports/R42_20261101.md'; expected_report = plan['report_base'] + suffix
        if report.read_text() not in (plan['report_base'], expected_report):
            raise ValueError('Release report changed outside the declared append')
        report.write_text(expected_report)
        status('browser_checks')
        server = subprocess.Popen([sys.executable, 'scripts/serve_atlases.py', '--no-browser', '--port', '8774'],
                                  cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            ready = time.monotonic() + 15
            while True:
                if server.poll() is not None:
                    raise RuntimeError('Final browser-check server exited')
                try:
                    with socket.create_connection(('127.0.0.1', 8774), timeout=1):
                        break
                except OSError:
                    if time.monotonic() > ready:
                        raise RuntimeError('Final browser-check server did not start')
                    time.sleep(.1)
            command(['node', 'scripts/check_atlas_smoke.js', *['http://127.0.0.1:8774/atlases/' + n + '/' for n in ('earth_fit', 'free_fit', 'whittaker_fit')]], 'browser_final.json')
        finally:
            server.terminate(); server.wait()
        status('checkout_and_portable_checks')
        stage_artifacts(ROOT, publication_paths())
        command([sys.executable, 'scripts/check_atlas_checkout.py', '--out', str(out / 'fresh_checkout.json')], 'fresh_checkout.log')
        bundle = out / 'rotclimate_r42_atlases.zip'
        command([sys.executable, 'scripts/package_fit_atlases.py', '--out', str(bundle)], 'package.log')
        command([sys.executable, 'scripts/check_portable_atlases.py', str(bundle), '--out', str(out / 'portable.json')], 'portable.log')
        write_json(out / 'publication.json', dict(status='verified', physics='r42', physics_adoption=False,
                   checkpoint_sha256=plan['checkpoint_sha256'], bundle_sha256=file_hash(bundle),
                   raw_strict_zone_accuracy=summary['strict_accuracy'], corrected_default=True,
                   unchanged_fits=['free_fit', 'whittaker_fit'], publication_plan_sha256=file_hash(path)))
        commit = commit_artifacts(ROOT, publication_paths())
        status('committed_pushing', commit=commit)
        for attempt in range(3):
            try:
                command(['git', 'push', plan['remote'], commit + ':' + plan['push_ref']], f'push_{attempt + 1}.log')
                break
            except subprocess.CalledProcessError:
                if attempt == 2:
                    raise
                time.sleep(5 * (attempt + 1))
        status('finished_pushed', commit=commit)
    except Exception as error:
        status('failed', error=repr(error)); raise


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--arm', type=Path); group.add_argument('--run', type=Path)
    args = ap.parse_args()
    arm(args.arm.resolve()) if args.arm else run(args.run.resolve())
