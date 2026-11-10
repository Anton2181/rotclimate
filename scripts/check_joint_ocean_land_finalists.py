"""Run predeclared marine diagnostics and development checks after joint refit.

No new independent pool is opened and no climate is adopted by this driver.
Run only after scripts/run_joint_ocean_land_refit.py has completed.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, freeze, write_json
from report_joint_ocean_land_refit import CAMPAIGN, SOURCE, eligible, summarize, plot
from gate_v3 import load, score
from rotclimate import joint
from rotclimate.config import Params

EXECUTION = ROOT / 'calibration/joint_ocean_land_20261110/followup_plan.json'


def command(args, log):
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
    with log.open('a') as stream:
        stream.write('\nCOMMAND: ' + json.dumps(args) + '\n'); stream.flush()
        code = subprocess.call([sys.executable, '-u', '-I', *args], cwd=ROOT,
                               env=env, stdout=stream, stderr=subprocess.STDOUT)
    if code:
        raise RuntimeError(f'Failed command ({code}); see {log}')


def benchmark(fit, folder, regions, *, cell_km=56, specs=None):
    args = ['scripts/benchmark_local.py', '--fit', str(fit), '--regions', *regions,
            '--workers', '3', '--cell-km', str(cell_km), '--out', str(folder)]
    if specs:
        args += ['--region-specs', str(specs)]
    command(args, folder.parent / (folder.name + '.log'))
    return load(folder)


def paired(reference, candidate):
    if set(reference) != set(candidate):
        raise ValueError('Mismatched regions')
    for name, row in reference.items():
        other = candidate[name]
        if row['case_identity'] != other['case_identity'] or row['cells'] != other['cells']:
            raise ValueError('Mismatched geography: ' + name)
    return score(reference, candidate, list(reference))


def verify_replay(rows, expected, label):
    import numpy as np
    for region, row in rows.items():
        actual = [row['temperature']['monthly_mae_C'], row['rain']['loss']]
        if not np.allclose(actual, expected[region], rtol=0, atol=1e-10):
            raise ValueError(f'{label} replay differs: {region}')


def verify_optimizer_checkpoint(folder, chain, *, evaluations=17, generations=2):
    """Check a trusted local pickle against its public, JSON-normalized history."""
    with (folder/'state.pkl').open('rb') as stream:
        es, pending, best, n, _rng = pickle.load(stream)
    if (n != evaluations or len(chain['records']) != evaluations or pending or es._told
            or es.countiter != generations):
        raise ValueError('Search did not finish the declared generations: ' + folder.name)
    # Pickle retains region-error tuples; JSONL serializes those as lists.
    normalized_best = json.loads(json.dumps(best, default=float))
    if normalized_best != chain['best']:
        raise ValueError('Search state disagrees with JSONL best: ' + folder.name)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=SOURCE / 'followup')
    args = ap.parse_args(); out = args.out
    search = summarize()
    if search['status'] != 'completed_development_search':
        raise SystemExit('Refusing to freeze unfinished searches')
    execution = json.loads(EXECUTION.read_text())
    campaign = json.loads(CAMPAIGN.read_text())
    out.mkdir(parents=True, exist_ok=True)
    command(['scripts/audit_joint_refit_sampling.py'], out/'sampling.log')
    sampling_path=SOURCE/'sampling_replay.json'
    sampling=json.loads(sampling_path.read_text())
    if (sampling['status']!='passed' or sampling['search_status']!='completed_development_search'
            or any(r['proposals_verified']!=16 or r['complete_generations']!=2
                   for r in sampling['starts'].values())):
        raise ValueError('Incomplete seeded proposal replay')
    inputs = [Path(__file__), EXECUTION, CAMPAIGN, ROOT/'scripts/report_joint_ocean_land_refit.py',
              ROOT/'scripts/audit_joint_refit_sampling.py',sampling_path,
              ROOT/'scripts/audit_air_sea_exchange.py', ROOT/'scripts/gate_v3.py',
              ROOT/'scripts/benchmark_local.py', ROOT/'scripts/rainfall_metrics.py',
              ROOT/'scripts/earth_benchmark.py', ROOT/'scripts/local_benchmark_protocol.py',
              *sorted((ROOT/'rotclimate').glob('*.py'))]
    for name in campaign['starts']:
        inputs.extend([SOURCE/name/'evals.jsonl', SOURCE/name/'best_params.json',
                       SOURCE/name/'search_identity.json'])
        verify_optimizer_checkpoint(SOURCE/name, search['starts'][name])
    inputs.extend(ROOT/p for p in execution['spec_files'].values())
    identity = freeze(out/'identity.json', dict(execution=execution,
        sources={str(p.relative_to(ROOT)): file_hash(p) for p in inputs}))
    write_json(SOURCE/'progress.json', search); plot(search, SOURCE/'joint_refit_progress.png')
    configs = {'r44': 'calibration/joint_ocean_land_20261110/reference_params.json'}
    qualifiers = []
    for name, chain in search['starts'].items():
        best = chain['best']
        if 'S' not in best:
            raise ValueError('No numerically valid best profile: ' + name)
        plan = json.loads((ROOT/campaign['starts'][name]).read_text())
        params = joint.earth_profile(Params.from_json(ROOT/plan['start'])).replace(**best['knobs'])
        actual = Params.from_json(SOURCE/name/'best_params.json')
        if asdict(params) != asdict(actual):
            raise ValueError('Saved best parameters disagree with trajectory: ' + name)
        path = out/(name+'_best_params.json')
        freeze(path, asdict(params))
        configs[name] = str(path.relative_to(ROOT))
        if eligible(best):
            qualifiers.append(name)
    write_json(out/'status.json', dict(status='marine_diagnostics', identity=identity,
        qualifiers=qualifiers, adopted='r44', independent_validation=False))
    marine = dict(id='P8d cost-best marine diagnosis', regions=execution['marine_regions'],
        cell_km=56, configs=configs,
        params_sha256={name:file_hash(ROOT/path) for name,path in configs.items()},
        scope='All three declared cost-best profiles, including failed development screens; known/spent coasts only.')
    freeze(out/'marine_plan_identity.json', marine)
    marine_path=out/'marine_plan.json'
    if marine_path.exists() and json.loads(marine_path.read_text()) != marine:
        raise ValueError('Changed marine plan')
    write_json(marine_path, marine)
    command(['scripts/audit_air_sea_exchange.py', '--plan', str(marine_path),
             '--workers', '3', '--out', str(out/'marine')], out/'marine.log')
    checks = {}
    if qualifiers:
        parts = [('dev31', ['dev31'], None)]
        for part in ('retired_a', 'retired_b', 'retired_c'):
            spec = ROOT / execution['spec_files'][part]
            parts.append((part, list(json.loads(spec.read_text())), spec))
        reference_fit = ROOT/configs['r44']
        reference = {}
        for part, names, spec in parts:
            reference.update(benchmark(reference_fit, out/('reference_'+part), names, specs=spec))
        control = search['starts']['r44_start']['records'][0]['regions']
        verify_replay(reference, control, 'r44')
        ref_fine = benchmark(reference_fit, out/'reference_fine28', execution['fine_regions'], cell_km=28)
        h_spec = ROOT/execution['spec_files']['spent_h']
        h_names = list(json.loads(h_spec.read_text()))
        ref_h = benchmark(reference_fit, out/'reference_spent_h', h_names, specs=h_spec)
        for name in qualifiers:
            write_json(out/'status.json', dict(status='development_replay', identity=identity,
                finalist=name, qualifiers=qualifiers, adopted='r44', independent_validation=False))
            fit = ROOT/configs[name]; candidate = {}
            for part, names, spec in parts:
                candidate.update(benchmark(fit, out/(name+'_'+part), names, specs=spec))
            verify_replay(candidate, search['starts'][name]['best']['regions'], name)
            dev = paired(reference, candidate)
            fine = paired(ref_fine, benchmark(fit, out/(name+'_fine28'), execution['fine_regions'], cell_km=28))
            stress = paired(ref_h, benchmark(fit, out/(name+'_spent_h'), h_names, specs=h_spec))
            checks[name] = dict(dev49=dev, fine28=fine, spent_h=stress,
                dev_pass=dev['S']<=.995 and dev['T']<=.01 and dev['P']<=.01,
                fine_pass=fine['S']<=1.01, spent_h_not_worse=stress['S']<=1.,
                independently_validated=False, adopted=False)
            write_json(out/'checks.json', checks)
    write_json(out/'summary.json', dict(status='completed_development_followup', identity=identity,
        cost_best_profiles=configs, qualifiers=qualifiers, checks=checks,
        marine_summary=str((out/'marine/summary.json').relative_to(ROOT)),
        adopted='r44', independent_validation=False,
        limitation='h is spent and used as stress only. No new independent pool and no automatic adoption.'))
    write_json(out/'status.json', dict(status='completed', identity=identity,
        qualifiers=qualifiers, adopted='r44', independent_validation=False))
    print('Completed finalist diagnostics and checks:', qualifiers, flush=True)


if __name__ == '__main__':
    main()
