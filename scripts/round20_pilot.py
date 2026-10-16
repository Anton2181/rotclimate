"""User-run pilot: test classification-aware calibration under strict numerics.

--plan prints every command without writing files or running a simulation.
Search budgets include the starting candidate; results never replace the atlas.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.config import Params


def baseline(spin):
    p = Params.from_json(ROOT / f'calibration/r19p_{spin}/best_params.json')
    return p.replace(downsample=8, steps_per_year=25, picard_iters=2, t_iters=48,
                     solver_rtol=1e-6, solver_max_iter=2000,
                     solver_require_convergence=True, transport_scheme='upwind')


def commands(out, evals, workers, worlds):
    searches = []
    for spin, fixed in [('earthlike', 0.25), ('retrograde', 0.75)]:
        searches.append([sys.executable, '-m', 'rotclimate.calibrate',
            '--start', str(out / f'{spin}_baseline.json'), '--out', str(out / spin),
            '--physics', 'v9', '--objective', 'zonefit', '--seeds', '1,2,3', '--race', '0',
            '--evals', str(evals), '--popsize', '16', '--workers', str(workers),
            '--seed', '20', '--sigma', '0.04', '--downsample', '8', '--steps', '25',
            '--fix', json.dumps({'retrograde': fixed}),
            '--bounds', json.dumps({'sst_offset': [-2, 2], 'land_offset': [-2, 2]})])
    rematch = [sys.executable, str(ROOT / 'scripts/spin_rematch.py'),
        str(out / 'retrograde'), str(out / 'earthlike'), '--k', '1',
        '--worlds', str(worlds), '--first-seed', '201', '--workers', str(workers),
        '--objective', 'zonefit', '--baseline-params', str(out / 'retrograde_baseline.json'),
        str(out / 'earthlike_baseline.json'), '--out', str(out / 'rematch.json')]
    return searches + [rematch]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=Path('calibration/r20_pilot'))
    ap.add_argument('--evals', type=int, default=65)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--worlds', type=int, default=12)
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--compare-only', action='store_true', help='compare the saved best fits without restarting searches')
    a = ap.parse_args()
    if a.evals < 17 or (a.evals - 1) % 16 or a.workers < 1 or a.worlds < 2:
        ap.error('evals must be 1 + a positive multiple of 16; workers >= 1; worlds >= 2')
    out = a.out if a.out.is_absolute() else ROOT / a.out
    starts = {spin: baseline(spin) for spin in ['earthlike', 'retrograde']}
    cmds = commands(out, a.evals, a.workers, a.worlds)
    if a.compare_only:
        for name in ['earthlike/evals.jsonl', 'retrograde/evals.jsonl',
                     'earthlike_baseline.json', 'retrograde_baseline.json']:
            if not (out / name).exists():
                ap.error(f'Missing saved comparison input: {out / name}')
        cmds = cmds[-1:]
        print(f'Comparison only: {a.worlds} test worlds starting at 201.', flush=True)
    else:
        print(f'{a.evals} candidates per spin on worlds 1–3; {a.worlds} test worlds starting at 201.', flush=True)
    print('Held-out comparisons include each unchanged starting world. This is a pilot, not a final spin verdict.', flush=True)
    for cmd in cmds:
        print(shlex.join(cmd), flush=True)
    if a.plan:
        return
    if a.compare_only:
        subprocess.run(cmds[0], cwd=ROOT, check=True)
        return
    if out.exists():
        ap.error(f'{out} already exists; choose a new --out to avoid mixing runs')
    out.mkdir(parents=True)
    for spin, p in starts.items():
        p.to_json(out / f'{spin}_baseline.json')
    (out / 'experiment.json').write_text(json.dumps(dict(
        objective='zonefit', evals=a.evals, search_seeds=[1, 2, 3],
        heldout_seeds=list(range(201, 201 + a.worlds)),
        baseline_params={spin: asdict(p) for spin, p in starts.items()},
        commands=cmds), indent=2) + '\n')
    for stage, cmd in zip(('Earth-like calibration', 'Reversed-spin calibration', 'Held-out comparison'), cmds):
        print(f"Starting {stage}...", flush=True)
        subprocess.run(cmd, cwd=ROOT, check=True)
        print(f"Completed {stage}.", flush=True)


if __name__ == '__main__':
    main()
