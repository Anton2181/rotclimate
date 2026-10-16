"""Retry the overnight world's failed temperature solve with more iterations.

Default is a read-only plan. --run performs one world-402 simulation with two
warm-up years. Only the temperature iteration allowance changes; physics,
damping stages and convergence tolerances are preserved. No atlas update.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import overnight_mediterranean as night


def retry_plan(source):
    source = Path(source).resolve()
    experiment = json.loads((source / 'experiment.json').read_text())
    summary = json.loads((source / 'summary.json').read_text())
    if summary['stage'] != 'complete':
        raise ValueError('Wait for the overnight batch to finish before this diagnostic.')
    previous = summary['runs']['fresh_anchor_s402']
    if previous['status'] != 'failed' or not previous['error'].startswith('Temperature/wind failed'):
        raise ValueError('This diagnostic requires the saved world-402 temperature failure.')
    before = night.Params(**experiment['anchor']).replace(beyond_seed=402)
    warmup = 2 * before.steps_per_year
    original = night.job('fresh_anchor_s402', before, warmup, source, experiment['source_id'])
    if original['input_id'] != previous['input_id']:
        raise ValueError('Failed case does not match the saved anchor, source and two-year warm-up.')
    if not (before.t_require_convergence and before.solver_require_convergence
            and before.moisture_require_convergence and before.moisture_residual_tol > 0):
        raise ValueError('The input must retain all strict convergence checks.')
    after = before.replace(t_iters=2 * before.t_iters)
    return dict(source=str(source), source_id=experiment['source_id'],
                diagnostic_id=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                previous_failure=previous, params=asdict(after), warmup_steps=warmup,
                parameter_changes={'t_iters': [before.t_iters, after.t_iters]},
                note='One bounded numerical retry. All physics, damping and tolerances unchanged; no atlas update.')


def run_retry(plan, out):
    out = Path(out).resolve()
    source = Path(plan['source'])
    if out == source or source in out.parents:
        raise ValueError('Use a separate output directory to preserve the overnight results.')
    if night.source_id() != plan['source_id']:
        raise ValueError('Model or input sources changed; this retry no longer matches the overnight experiment.')
    manifest = out / 'experiment.json'
    if manifest.exists() and json.loads(manifest.read_text()) != plan:
        raise ValueError('Output contains a different diagnostic. Choose a new --out directory.')
    j = night.job('anchor_s402_more_iterations', night.Params(**plan['params']),
                  plan['warmup_steps'], out, plan['source_id'], transport=True)
    # Include this wrapper as well as the original model/runner in cache identity.
    j['input_id'] = hashlib.sha256((j['input_id'] + plan['diagnostic_id']).encode()).hexdigest()
    (out / 'cases').mkdir(parents=True, exist_ok=True)
    night.atomic_json(manifest, plan)
    night.atomic_json(out / 'retry_params.json', plan['params'])
    answer = night.cached(j)
    if answer is None:
        answer = night.worker(j)
    else:
        print('Reusing the matching saved numerical retry.', flush=True)
    report = dict(status=answer['status'], parameter_changes=plan['parameter_changes'],
                  previous_failure=plan['previous_failure']['error'], retry=answer,
                  note=plan['note'])
    night.atomic_json(out / 'comparison.json', report)
    p = night.Params(**plan['params'])
    before, after = plan['parameter_changes']['t_iters']
    caps = lambda initial: '/'.join(str(initial * 2**i) for i in range(p.t_adaptive_retries + 1))
    lines = ['# World 402 numerical retry', '', plan['note'], '',
             f'Temperature iteration caps: {caps(before)} → {caps(after)}.',
             '', 'Status: ' + answer['status'] + '.']
    if answer['status'] == 'ok':
        row = answer['row']
        lines += ['', f"Overall strict agreement: {row['accuracy']:.2%}.",
                  f"Mediterranean dry area: {row['mediterranean']['dry_share']:.2%}.",
                  f"Cold-dry agreement: {row['zone_recall']['cold_dry']:.2%}.",
                  '', 'These are absolute results. The original world-402 failure has no valid climate score.',
                  'The published atlas and original incomplete-validation record are unchanged.']
    else:
        lines += ['', answer['error'], '', 'No usable climate score; inspect the saved convergence history.']
    (out / 'summary.md').write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[2:]), flush=True)
    print(f'Read {out / "summary.md"}', flush=True)
    return answer


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=ROOT / 'output/overnight_mediterranean')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/overnight_validation_retry')
    ap.add_argument('--run', action='store_true')
    a = ap.parse_args(argv)
    plan = retry_plan(a.source)
    p = night.Params(**plan['params'])
    caps = [p.t_iters * 2**i for i in range(p.t_adaptive_retries + 1)]
    print(f'World 402, unchanged anchor physics; {p.downsample=}, {p.steps_per_year} dates/year, '
          f'{plan["warmup_steps"]} warm-up steps.', flush=True)
    print(f'Temperature stage caps: {caps}; at most {sum(caps)} iterations per seasonal date. '
          'Full-update tolerance remains 0.05 C; linear and moisture checks remain strict.', flush=True)
    print(f'One simulation ({plan["warmup_steps"] + p.steps_per_year} seasonal steps). '
          'No parameter search or atlas build. Difficult steps may still fail at the bounded cap.', flush=True)
    if not a.run:
        print('Plan only. Add --run to execute.', flush=True)
        return 0
    answer = run_retry(plan, a.out)
    return 0 if answer['status'] == 'ok' else 1


if __name__ == '__main__':
    raise SystemExit(main())
