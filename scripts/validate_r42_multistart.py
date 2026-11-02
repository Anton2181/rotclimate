"""Finish the declared three-start search with paired, staged validation.

No parameter selection from sealed results, model adoption, or atlas changes.
The one finalist is committed before fresh runs; sealed e is opened only after
49-region reproduction and the paired 28 km check pass.
"""
from pathlib import Path
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import fcntl
import json
import math
import os
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, freeze, write_json
from run_calibration_portfolio import select_finalist

PREFIX = 'output/r42_multistart_validation_20261102/'


def paired_score(reference, candidate, names):
    if set(reference) != set(names) or set(candidate) != set(names) or len(set(names)) != len(names):
        raise ValueError('Paired validation needs every declared region exactly once')
    values = []
    for name in names:
        r, c = reference[name], candidate[name]
        for row in (r, c):
            if row.get('status') != 'passed' or row.get('numerics', {}).get('all_checks_passed') is not True:
                raise ValueError('Unverified regional result: ' + name)
        if r['case_identity'] != c['case_identity'] or r['cells'] != c['cells']:
            raise ValueError('Paired geography or observations differ: ' + name)
        row = [x[k][m] for x in (r, c) for k, m in [('temperature', 'monthly_mae_C'), ('rain', 'loss')]]
        if not all(math.isfinite(x) and x >= 0 for x in row):
            raise ValueError('Invalid climate errors: ' + name)
        values.append(row)
    tr, pr, tc, pc = [sum(row[i] for row in values) / len(values) for i in range(4)]
    if tr <= 0 or pr <= 0:
        raise ValueError('Reference mean errors must be positive')
    return dict(S=.5 * tc / tr + .5 * pc / pr, T=tc / tr - 1, P=pc / pr - 1, n=len(names))


def reproduce(rows, expected):
    if set(rows) != set(expected):
        raise ValueError('Reproduction needs the complete selected footprint')
    for name, row in rows.items():
        actual = (row['temperature']['monthly_mae_C'], row['rain']['loss'])
        if any(not math.isfinite(x) or abs(x - y) > 1e-10 for x, y in zip(actual, expected[name])):
            raise ValueError('Search result does not reproduce: ' + name)


def records_for_selection(root, campaign):
    records = []
    for chain, plan_path in enumerate(campaign['plans'], 1):
        plan = json.loads((root / plan_path).read_text())
        path = root / campaign['output'] / f'chain_{chain}/evals.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if [r['n'] for r in rows] != list(range(plan['evals'])):
            raise ValueError('All declared starts must finish before selection')
        records.extend(dict(row, chain=chain) for row in rows)
    return records


def publish(root, folder, message, plan):
    if str(folder.resolve().relative_to(root.resolve())) + '/' != PREFIX:
        raise ValueError('Refusing unrelated publication folder')
    names = sorted(str(p.relative_to(root)) for p in folder.rglob('*') if p.is_file()
                   and p.suffix in {'.json', '.npz', '.log'} and p.name not in {'status.json', 'push.log'})
    if not names or any(not n.startswith(PREFIX) for n in names):
        raise ValueError('Refusing unrelated publication paths')
    subprocess.run(['git', 'add', '-f', '--', *names], cwd=root, check=True, capture_output=True)
    changed = subprocess.run(['git', 'diff', '--cached', '--quiet', '--', *names], cwd=root)
    if changed.returncode not in (0, 1):
        raise RuntimeError('Cannot inspect staged validation artifacts')
    if changed.returncode:
        subprocess.run(['git', 'commit', '--only', '-m', message, '--', *names], cwd=root, check=True, capture_output=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    with (folder / 'push.log').open('a') as log:
        subprocess.run(['git', 'push', plan['remote'], commit + ':' + plan['push_ref']], cwd=root,
                       check=True, stdout=log, stderr=subprocess.STDOUT)
    return commit


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=2)
    a = ap.parse_args()
    if a.workers < 1:
        ap.error('workers must be positive')
    plan = json.loads(a.plan.read_text()); out = ROOT / plan['output']; out.mkdir(parents=True, exist_ok=True)
    lock = (out / '.validation.lock').open('a'); fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    status_path = out / 'status.json'
    if status_path.exists() and json.loads(status_path.read_text()).get('stage') == 'finished_pushed':
        return
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(a.plan.resolve().relative_to(ROOT))], cwd=ROOT) != a.plan.read_bytes():
        raise ValueError('Commit the validation declaration first')

    def status(stage, **extra):
        row = dict(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat(), **extra)
        write_json(status_path, row); print(json.dumps(row), flush=True)

    def check_sources():
        if subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip() != plan['branch']:
            raise ValueError('Validation branch changed')
        for name, digest in plan['sources'].items():
            if file_hash(ROOT / name) != digest:
                raise ValueError('Frozen validation source changed: ' + name)

    def bench(label, params, names, specs, resolution):
        check_sources(); folder = out / label
        status('validating', run=label)
        command = [sys.executable, '-u', '-I', 'scripts/benchmark_local.py', '--fit', str(params),
                   '--regions', *names, '--region-specs', str(specs), '--cell-km', str(resolution),
                   '--workers', str(a.workers), '--out', str(folder)]
        with (out / (label + '.log')).open('a') as log:
            subprocess.run(command, cwd=ROOT, check=True, stdout=log, stderr=subprocess.STDOUT,
                           env=dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1'))
        check_sources()
        summary = json.loads((folder / 'summary.json').read_text())
        if summary.get('complete') is not True:
            raise ValueError('Incomplete validation: ' + label)
        for name, row in summary['regions'].items():
            if file_hash(folder / 'cells' / (name + '.npz')) != row['cells_sha256']:
                raise ValueError('Regional packet differs from its receipt: ' + name)
        return summary['regions']

    try:
        freeze(out / 'plan.json', plan); check_sources()
        status('waiting_for_all_three_starts'); deadline = time.monotonic() + plan['timeout_s']
        campaign = json.loads((ROOT / plan['campaign']).read_text()); campaign['output'] = plan['search_output']
        while True:
            marker = ROOT / campaign['output'] / 'status.json'
            current = json.loads(marker.read_text())
            if current['stage'] in ('awaiting_validation', 'completed_no_qualifying_candidate'):
                break
            if current['stage'] == 'failed' or time.monotonic() > deadline:
                raise RuntimeError('Search failed or timed out; unseen validation stays unstarted')
            time.sleep(15)
        check_sources(); records = records_for_selection(ROOT, campaign)
        selected = select_finalist(records)
        saved = json.loads((ROOT / campaign['output'] / 'selection.json').read_text())
        if selected != saved['finalist']:
            raise ValueError('Selection differs from the prospectively declared rule')
        freeze(out / 'search_records.json', dict(records=records))
        if not selected:
            write_json(out / 'result.json', dict(outcome='no_qualifying_development_candidate', adoption=False, sealed_run=False))
        else:
            from earth_benchmark import load_params
            start = json.loads((ROOT / campaign['plans'][selected['chain'] - 1]).read_text())
            params = load_params(ROOT / start['start']).replace(**{**start.get('set', {}), **selected['knobs']})
            candidate = out / 'candidate_params.json'; reference = out / 'reference_params.json'
            freeze(candidate, asdict(params)); freeze(reference, asdict(load_params(ROOT / plan['reference_params'])))
            histories = [ROOT / campaign['output'] / f'chain_{i}/evals.jsonl' for i in range(1, 4)]
            freeze(out / 'finalist.json', dict(selected=selected, evaluations=len(records), sources=plan['sources'],
                histories_sha256={str(p.relative_to(ROOT)): file_hash(p) for p in histories}, adoption=False))
            # The finalist and complete search history are fixed before any fresh scoring.
            publish(ROOT, out, 'Freeze one finalist from all three r42 calibration starts', plan)
            names = list(selected['regions']); specs = ROOT / plan['development_specs']
            r = bench('r42_dev49', reference, names, specs, 56.0)
            c = bench('candidate_dev49', candidate, names, specs, 56.0)
            control = next(x for x in records if x['chain'] == 1 and x['n'] == 0)
            reproduce(r, control['regions']); reproduce(c, selected['regions'])
            for name, expected in plan['reference_case_identities'].items():
                if r[name]['case_identity'] != expected:
                    raise ValueError('Reference forcing footprint changed: ' + name)
            dev = paired_score(r, c, names)
            dev_pass = dev['S'] <= .995 and dev['T'] <= .01 and dev['P'] <= .01
            result = dict(adoption=False, dev49=dev, dev_pass=dev_pass, sealed_run=False)
            if dev_pass:
                names = plan['fine_regions']
                fr = bench('r42_fine28', reference, names, specs, 28.0)
                fc = bench('candidate_fine28', candidate, names, specs, 28.0)
                fine = paired_score(fr, fc, names); result.update(fine28=fine, fine_pass=fine['S'] <= 1.01)
                if result['fine_pass']:
                    # Commit the qualification receipt before opening the untouched boxes.
                    write_json(out / 'presealed.json', dict(**result, candidate_sha256=file_hash(candidate),
                               sealed_spec_sha256=file_hash(ROOT / plan['sealed_specs'])))
                    publish(ROOT, out, 'Freeze paired development and fine-grid qualification before sealed e', plan)
                    specs = ROOT / plan['sealed_specs']; names = list(json.loads(specs.read_text()))
                    sr = bench('r42_sealed_e', reference, names, specs, 56.0)
                    sc = bench('candidate_sealed_e', candidate, names, specs, 56.0)
                    sealed = paired_score(sr, sc, names)
                    result.update(sealed_run=True, sealed_e=sealed, sealed_pass=sealed['S'] <= 1.)
            result['outcome'] = 'qualified_for_review' if result.get('sealed_pass') else 'rejected'
            result['note'] = 'No physics adoption or atlas changes. Report all regional results and group tradeoffs.'
            write_json(out / 'result.json', result)
        commit = publish(ROOT, out, 'Record paired r42 multistart validation and every scored outcome', plan)
        status('finished_pushed', commit=commit, result=json.loads((out / 'result.json').read_text()))
    except Exception as error:
        status('failed', error=repr(error)); raise


if __name__ == '__main__':
    main()
