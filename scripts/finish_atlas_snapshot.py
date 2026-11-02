"""Verify, atomically promote and publish a completed pinned atlas build."""
from pathlib import Path
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json


def allowed(name, plan):
    parts = Path(name).parts
    if Path(name).is_absolute() or '..' in parts or any(x in parts for x in ['snapshot', 'previous_atlases', '.git']): return False
    if name.endswith(('.zip', '.pkl', '.tmp', '.lock', '_status.json')): return False
    exact = {'atlases/index.html', 'atlases/pages.json', 'atlases/release.json', plan['report']}
    for fit in ['free_fit', 'whittaker_fit', 'earth_physics']:
        exact.update('atlases/' + fit + '/' + n for n in ['index.html', 'harvest.js', 'population.js', 'foraging.js', 'climate-comparison.js'])
    return name in exact or any(name.startswith(p.rstrip('/') + '/') for p in
        ['atlases/earth_fit', plan['corrections'], plan['correction_output'], plan['output']])


def publication_paths(root, plan):
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
    tracked += subprocess.check_output(['git', 'ls-tree', '-r', '-z', '--name-only', 'HEAD'], cwd=root).decode().split('\0')
    names = {n for n in tracked if n and allowed(n, plan)}
    for base in ['atlases/earth_fit', plan['corrections'], plan['correction_output'], plan['output']]:
        for parent, dirs, files in os.walk(root / base):
            dirs[:] = [d for d in dirs if d not in {'snapshot', 'previous_atlases', '.git'}]
            for leaf in files:
                path = Path(parent) / leaf; name = str(path.relative_to(root))
                if allowed(name, plan) and (base.startswith(('atlases/', 'calibration/')) or path.suffix in {'.json', '.npz', '.png', '.log'}): names.add(name)
    return sorted(names)


def stage(root, names):
    indexed = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0'))
    present = [n for n in names if (root / n).exists() or n in indexed]
    if present: subprocess.run(['git', 'add', '-f', '-A', '--', *present], cwd=root, check=True, capture_output=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--plan', type=Path, required=True)
    a = ap.parse_args(); publication = json.loads(a.plan.read_text()); plan = json.loads((ROOT / publication['build_plan']).read_text())
    out = ROOT / plan['output']; out.mkdir(parents=True, exist_ok=True)
    lock = (out / '.publication.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status_path = out / 'publication_status.json'
    if status_path.exists() and json.loads(status_path.read_text()).get('stage') == 'finished_pushed': return
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(a.plan.resolve().relative_to(ROOT))], cwd=ROOT) != a.plan.read_bytes():
        raise ValueError('Commit the publication declaration first')
    def status(label, **extra):
        from datetime import datetime, timezone
        row = dict(stage=label, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
        write_json(status_path, row); print(json.dumps(row), flush=True)
    def command(args, log):
        with (out / log).open('w') as stream:
            subprocess.run(args, cwd=ROOT, check=True, stdout=stream, stderr=subprocess.STDOUT,
                env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
    try:
        status('waiting_for_snapshot'); deadline = time.monotonic() + 43200
        while True:
            marker = out / 'snapshot_status.json'
            current = json.loads(marker.read_text()) if marker.exists() else {}
            if current.get('stage') == 'ready_for_publication': break
            if current.get('stage') == 'failed' or time.monotonic() > deadline:
                raise RuntimeError('Snapshot failed or timed out; live atlas was not promoted')
            time.sleep(15)
        if subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() != publication['branch']:
            raise ValueError('Publication branch changed')
        snapshot = Path(current['snapshot']); live = ROOT / 'atlases/earth_fit'
        backup = out / 'previous_atlases' / ('earth_fit_' + plan['previous'])
        staged = snapshot / 'atlases' / plan['stage_name']
        if not backup.exists():
            if file_hash(live / 'params.json') != publication['previous_params_sha256']:
                raise ValueError('Live atlas changed; refusing to replace an unexpected release')
            if not staged.exists(): raise ValueError('Staged atlas missing')
            backup.parent.mkdir(parents=True, exist_ok=True)
            # Stage verification below runs before either live directory move.
            atlas = staged
        else:
            atlas = live if live.exists() else staged
        status('verifying_staged_release')
        if json.loads((atlas / 'params.json').read_text()) != json.loads((ROOT / plan['world_params']).read_text()):
            raise ValueError('Atlas geometry/shared settings differ from adopted world parameters')
        meta = json.loads((atlas / 'data/atlas.json').read_text())
        summary = json.loads((atlas / 'summary.json').read_text())
        languages = {'language_density', 'language_territories', 'language_edges', 'language_farming_arrival', 'language_families'}
        if (meta.get('physics_profile') != plan['profile'] or not meta.get('corrected_climate')
                or not summary['observed_numerics']['all_checks_passed'] or not languages <= {x['id'] for x in meta['layers']}):
            raise ValueError('Incomplete or incorrectly labelled climate/language release')
        raw_hash = file_hash(ROOT / plan['params'])
        for kind in ['temperature', 'rain_pattern']:
            folder = snapshot / plan['corrections'] / kind; protocol = json.loads((folder / 'protocol.json').read_text())
            if protocol['meta']['physics_params_sha256'] != raw_hash: raise ValueError('Corrections trained on different physics')
            if any(file_hash(folder / n) != h for n, h in protocol['files'].items()): raise ValueError('Correction model changed')
        shutil.copytree(snapshot / plan['corrections'], ROOT / plan['corrections'], dirs_exist_ok=True)
        shutil.copytree(snapshot / plan['correction_output'], ROOT / plan['correction_output'], dirs_exist_ok=True)
        diagnostic = snapshot / plan['output'] / 'diagnostics'
        if diagnostic.exists(): shutil.copytree(diagnostic, out / 'diagnostics', dirs_exist_ok=True)
        checkpoint = ROOT / plan['checkpoint']; checkpoint.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot / plan['checkpoint'], checkpoint)
        if atlas == staged:
            if live.exists():
                if backup.exists(): raise ValueError('Unexpected live atlas and backup during promotion')
                live.rename(backup)
            try: staged.rename(live)
            except Exception:
                if not live.exists() and backup.exists(): backup.rename(live)
                raise
        pages_path = ROOT / 'atlases/pages.json'; pages = json.loads(pages_path.read_text())
        pages['earth_fit']['note'] = (f'Earth {plan["profile"]} physics, adopted after paired development, finer-grid and unseen validation, '
            'on the published world geometry. Climate averages surroundings layouts 1–3 with verified numerical checks. '
            'The map opens on Earth-trained corrected climate; raw climate remains available. Food, population and foraging are c.200 AD scenarios.')
        pages_path.write_text(json.dumps(pages, indent=1, ensure_ascii=False) + '\n')
        command([sys.executable, '-I', 'scripts/refresh_atlas_pages.py'], 'pages.log')
        command([sys.executable, '-I', 'scripts/build_fit_hub.py'], 'hub.log')
        if json.loads((ROOT / 'atlases/release.json').read_text())['earth_physics'] != plan['profile']:
            raise ValueError('Hub/launcher release label is stale')
        report = ROOT / plan['report']; marker = '<!--atlas-publication-complete-->'
        if marker not in report.read_text():
            report.write_text(report.read_text() + f'\n\n{marker}\nThe verified {plan["profile"]} atlas release is complete. '
                f'Raw strict target-zone agreement: {100 * summary["strict_accuracy"]:.2f}%. '
                'Matched corrections and all food/population/foraging/trade/language exports are included. '
                'Publication checks and source snapshot identity are retained under ' + plan['output'] + '.\n')
        status('browser_checks')
        server = subprocess.Popen([sys.executable, 'scripts/serve_atlases.py', '--no-browser'], cwd=ROOT,
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        try:
            url = None
            for line in server.stdout:
                if line.startswith('Open '): url = line.strip()[5:]; break
            if not url: raise RuntimeError('Launcher did not open a fresh local address')
            parts = urlsplit(url); base = parts.scheme + '://' + parts.netloc
            command(['node', 'scripts/check_atlas_smoke.js', *[base + '/atlases/' + n + '/' for n in ['earth_fit', 'free_fit', 'whittaker_fit']]], 'browser.json')
        finally:
            server.terminate(); server.wait()
        # Independent research may advance during the snapshot build. Publish a
        # committed, coherent research page rather than accidentally staging it.
        status('waiting_for_committed_research')
        while subprocess.run(['git', 'diff', '--quiet', 'HEAD', '--', 'atlases/climate_accuracy'], cwd=ROOT).returncode:
            if time.monotonic() > deadline: raise RuntimeError('Research page remained uncommitted')
            time.sleep(15)
        status('checkout_and_portable_checks')
        stage(ROOT, publication_paths(ROOT, plan))
        command([sys.executable, 'scripts/check_atlas_checkout.py', '--out', str(out / 'checkout.json')], 'checkout.log')
        bundle = out / 'atlases.zip'
        command([sys.executable, 'scripts/package_fit_atlases.py', '--out', str(bundle)], 'package.log')
        command([sys.executable, 'scripts/check_portable_atlases.py', str(bundle), '--out', str(out / 'portable.json')], 'portable.log')
        indexed = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0'))
        with zipfile.ZipFile(bundle) as z:
            required = set(json.loads(z.read('manifest.json'))['sha256'])
        if not required <= indexed: raise ValueError('Portable assets are not all in the Git publication snapshot: ' + str(sorted(required - indexed)))
        write_json(out / 'publication.json', dict(status='verified', profile=plan['profile'],
            snapshot=json.loads((out / 'snapshot.json').read_text()), bundle_sha256=file_hash(bundle),
            raw_strict_zone_accuracy=summary['strict_accuracy']))
        names = publication_paths(ROOT, plan); stage(ROOT, names)
        subprocess.run(['git', 'commit', '--only', '-m', 'Publish complete verified ' + plan['profile'] + ' atlas from pinned source snapshot', '--', *names],
                       cwd=ROOT, check=True, capture_output=True)
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        status('committed_pushing', commit=commit)
        command(['git', 'push', '--atomic', publication['remote'], *[commit + ':' + ref for ref in publication['push_refs']]], 'push.log')
        status('finished_pushed', commit=commit)
    except Exception as error:
        status('failed', error=repr(error)); raise


if __name__ == '__main__': main()
