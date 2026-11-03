"""Prospective 61-region physics comparison on a pinned model snapshot.

Only the selected full-development finalist can reach fine grids and unopened f.
This experiment never adopts physics or changes normal atlas data.
"""
from pathlib import Path
import argparse
import fcntl
import importlib.metadata
import json
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, freeze, write_json
from validate_r42_multistart import paired_score
from run_r42_conservative_replay import numerical_drift
from run_atlas_snapshot import link_missing

PREFIX = 'output/storm_expansion_20261103b/'


def output_prefix(plan):
    prefix = plan.get('output', PREFIX).rstrip('/') + '/'
    path = Path(prefix)
    if path.is_absolute() or '..' in path.parts or len(path.parts) < 2 or path.parts[0] != 'output':
        raise ValueError('Study output must be an owned output subdirectory')
    return prefix


def prepare_model(plan):
    model = ROOT / plan['model_root']
    if not (model / '.git').exists():
        subprocess.run(['git', 'worktree', 'add', '--detach', '--no-checkout', str(model), plan['model_commit']], cwd=ROOT, check=True)
    if not (model / 'scripts/benchmark_local.py').exists():
        subprocess.run(['git', 'sparse-checkout', 'set', '--no-cone',
            '/scripts/', '/rotclimate/', '/data/', '/calibration/', '/ravages/', '/.gitignore', '/.gitattributes'], cwd=model, check=True)
        subprocess.run(['git', 'checkout', plan['model_commit']], cwd=model, check=True, capture_output=True)
    link_missing(ROOT / 'data', model / 'data')
    if not (model / '.venv').exists(): (model / '.venv').symlink_to(ROOT / '.venv', target_is_directory=True)
    return model


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=2); a = ap.parse_args()
    if a.workers < 1: ap.error('workers must be positive')
    plan = json.loads(a.plan.read_text()); prefix = output_prefix(plan)
    out = ROOT / prefix; out.mkdir(parents=True, exist_ok=True)
    lock = (out / '.study.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    marker = out / 'status.json'
    if marker.exists() and json.loads(marker.read_text()).get('stage') == 'finished_pushed': return
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(a.plan.resolve().relative_to(ROOT))], cwd=ROOT) != a.plan.read_bytes():
        raise ValueError('Commit the prospective study declaration first')
    freeze(out / 'plan.json', plan); model = prepare_model(plan)
    def status(stage, **fields):
        from datetime import datetime, timezone
        row = dict(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat(), **fields)
        write_json(marker, row); print(json.dumps(row), flush=True)
    def check():
        if subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() != plan['branch']:
            raise ValueError('Study publication branch changed')
        if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=model, text=True).strip() != plan['model_commit']:
            raise ValueError('Pinned model revision changed')
        for n, h in plan['model_sources'].items():
            if file_hash(model / n) != h: raise ValueError('Pinned model input changed: ' + n)
        for n, h in plan['sources'].items():
            if file_hash(ROOT / n) != h: raise ValueError('Frozen study input changed: ' + n)
        if any(importlib.metadata.version(n) != v for n, v in plan['libraries'].items()):
            raise ValueError('Scientific library versions changed')
    def bench(label, params, names, specs, cell_km=56., allow_failure=False):
        check(); folder = out / label; status('running', step=label)
        cmd = [str(ROOT / '.venv/bin/python'), '-u', '-I', 'scripts/benchmark_local.py',
               '--fit', str(ROOT / params), '--regions', *names, '--region-specs', str(ROOT / specs),
               '--cell-km', str(cell_km), '--workers', str(a.workers), '--out', str(folder)]
        with (out / (label + '.log')).open('a') as log:
            process = subprocess.run(cmd, cwd=model, stdout=log, stderr=subprocess.STDOUT,
                env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
        check(); summary = json.loads((folder / 'summary.json').read_text())
        if set(summary['regions']) != set(names): raise ValueError('Missing declared cases')
        if not summary.get('complete'):
            if allow_failure: return None
            raise ValueError('Reference or control failed: ' + label)
        if process.returncode: raise RuntimeError('Unexpected benchmark failure')
        for name, row in summary['regions'].items():
            if file_hash(folder / 'cells' / (name + '.npz')) != row['cells_sha256']: raise ValueError('Raw packet changed')
        return summary['regions']
    try:
        status('waiting_for_dependency'); deadline = time.monotonic() + 43200
        while True:
            after = ROOT / plan['after_status']
            current = json.loads(after.read_text()) if after.exists() else {'stage': 'not_started'}
            if current['stage'] == plan.get('after_stage', 'training_complete'): break
            if current['stage'] == 'failed' or time.monotonic() > deadline: raise RuntimeError('Study dependency failed or timed out')
            time.sleep(15)
        d = bench('reference_d_undamped', plan['raw_reference'], plan['retired_d'], plan['region_specs'])
        reference = bench('reference61', plan['reference'], plan['regions'], plan['region_specs'])
        locations = dict(plan['raw_locations'])
        locations.update({n: prefix + 'reference_d_undamped' for n in d})
        drift = numerical_drift({n: dict(reference=p) for n,p in locations.items()},
            {'regions': reference}, out / 'reference61', {'max_T_c': .01, 'max_P_mm_month': .05})
        write_json(out / 'numerical_control.json', drift)
        if not drift['passes']:
            result = dict(outcome='stopped_at_numerical_control', adoption=False, sealed_run=False)
        else:
            scores = {}; packets = {}
            for name, params in plan['candidates'].items():
                rows = bench(name + '_dev61', params, plan['regions'], plan['region_specs'], allow_failure=True)
                packets[name] = rows
                scores[name] = None if rows is None else paired_score(reference, rows, plan['regions'])
            eligible = [n for n, s in scores.items() if s is not None and s['S'] <= .995 and s['T'] <= .01 and s['P'] <= .01]
            chosen = min(eligible, key=lambda n: (scores[n]['S'], n)) if eligible else None
            result = dict(adoption=False, dev61=scores, selected=chosen, sealed_run=False,
                S49_reported={n: paired_score({k:reference[k] for k in plan['historical49']},
                               {k:rows[k] for k in plan['historical49']}, plan['historical49'])
                              for n, rows in packets.items() if rows is not None})
            write_json(out / 'development_selection.json', result)
            if chosen:
                # Every declared full-development family finishes before this freeze.
                freeze(out / 'finalist.json', dict(name=chosen, params_sha256=file_hash(ROOT / plan['candidates'][chosen]),
                    scores=scores, model_commit=plan['model_commit'], holdout=plan['holdout']))
                publish(out, plan, 'Freeze one physics finalist after all declared full development comparisons')
                names = plan['fine_regions']
                r = bench('reference_fine28', plan['reference'], names, plan['region_specs'], 28.)
                c = bench('candidate_fine28', plan['candidates'][chosen], names, plan['region_specs'], 28., allow_failure=True)
                fine = None if c is None else paired_score(r, c, names)
                result.update(fine28=fine, fine_pass=fine is not None and fine['S'] <= 1.01)
                if result['fine_pass']:
                    write_json(out / 'presealed.json', result)
                    publish(out, plan, 'Freeze storm-family finalist after full development and finer-grid qualification')
                    names = list(json.loads((ROOT / plan['holdout']).read_text()))
                    r = bench('reference_sealed_f', plan['reference'], names, plan['holdout'])
                    c = bench('candidate_sealed_f', plan['candidates'][chosen], names, plan['holdout'], allow_failure=True)
                    sealed = None if c is None else paired_score(r, c, names)
                    result.update(sealed_run=True, sealed_f=sealed, sealed_pass=sealed is not None and sealed['S'] <= 1.)
            result['outcome'] = 'qualified_for_review' if result.get('sealed_pass') else 'rejected'
        write_json(out / 'result.json', result)
        commit = publish(out, plan, 'Record complete 61-region ' + plan.get('study_name', 'storm-family comparison') + ' and all qualification outcomes')
        status('finished_pushed', commit=commit, result=result)
    except Exception as error:
        status('failed', error=repr(error)); raise


def publish(folder, plan, message):
    names = []
    for parent, dirs, files in os.walk(folder):
        dirs[:] = [n for n in dirs if n not in {'model', '.git'}]
        names.extend(str((Path(parent) / n).relative_to(ROOT)) for n in files
            if Path(n).suffix in {'.json', '.npz', '.log'} and n not in {'status.json', 'push.log'})
    names.sort()
    prefix = output_prefix(plan)
    if not names or any(not n.startswith(prefix) or 'model' in Path(n).parts for n in names): raise ValueError('Unrelated publication paths')
    subprocess.run(['git', 'add', '-f', '--', *names], cwd=ROOT, check=True, capture_output=True)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', *names], cwd=ROOT)
    if changed.returncode not in (0, 1): raise RuntimeError('Cannot inspect staged study files')
    if changed.returncode:
        subprocess.run(['git', 'commit', '--only', '-m', message, '--', *names], cwd=ROOT, check=True, capture_output=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with (folder / 'push.log').open('a') as log:
        subprocess.run(['git', 'push', '--atomic', plan['remote'], *[commit + ':' + r for r in plan['push_refs']]],
                       cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT)
    return commit


if __name__ == '__main__': main()
