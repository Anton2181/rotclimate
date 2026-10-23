"""Bounded calibration against the actual three-layout atlas climate.

Free and Whittaker vary only eight storm/moisture coefficients; Earth varies
world parameters with its Earth-tested physics fixed. This is development on
the existing painted targets, with no claim of independent validation.
Publication requires a separate paired fine/native comparison.
"""
import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate import calibrate as C
from rotclimate.config import Params

SPECS = dict(free=dict(space='storm-water', objective='zonefit'),
             earth=dict(space='world', objective='zonefit'),
             whittaker=dict(space='storm-water', objective='whittaker-covered'))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--branch', choices=list(SPECS), required=True)
    ap.add_argument('--evals', type=int, default=17)
    ap.add_argument('--workers', type=int, default=1)
    ap.add_argument('--downsample', type=int, default=32)
    ap.add_argument('--sigma', type=float, default=.025)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    spec = SPECS[a.branch]
    base = Params.from_json(ROOT/'atlases'/f'{a.branch}_fit'/'params.json').replace(downsample=a.downsample)
    C._set_space(C.SPACE_WORLD if a.branch == 'earth' else C.SPACE_STORM_WATER)
    decoded = C.decode(C.encode(base), base)
    changed = {k for k, v in asdict(base).items() if asdict(decoded)[k] != v
               and not (isinstance(v, float) and math.isclose(asdict(decoded)[k], v, rel_tol=1e-13, abs_tol=1e-13))}
    if changed: raise ValueError('Search bounds would alter the supplied baseline: '+str(changed))
    a.out.mkdir(parents=True, exist_ok=True)
    start = a.out/'start_params.json'
    if start.exists() and asdict(Params.from_json(start)) != asdict(base):
        raise ValueError('Baseline changed; use a new output directory')
    base.to_json(start)
    command = [str(ROOT/'.venv/bin/python'), '-u', '-I', str(ROOT/'scripts/calibrate_cli.py'),
        '--start', str(start), '--physics', spec['space'], '--objective', spec['objective'],
        '--ensemble-objective', 'climate', '--race', '0', '--saved-numerics',
        '--seeds', '1,2,3', '--evals', str(a.evals), '--popsize', '8',
        '--sigma', str(a.sigma), '--seed', '231023', '--workers', str(a.workers), '--out', str(a.out)]
    if a.branch == 'earth': command += ['--fix', '{"retrograde":0.75}']
    if (a.out/'state.pkl').exists(): command += ['--resume']
    subprocess.run(command, cwd=ROOT, check=True)
    rows = [json.loads(line) for line in (a.out/'evals.jsonl').read_text().splitlines()]
    valid = [r for r in rows if not r.get('error') and not r.get('raced')]
    best = max(valid, key=lambda r:r['score'])
    summary = dict(branch=a.branch, objective=spec['objective'], aggregation='climate',
        initial=rows[0]['score'], best=best['score'], gain=best['score']-rows[0]['score'],
        candidates=len(rows), failures=sum(bool(r.get('error')) for r in rows),
        best_evaluation=best['eval'], downsample=a.downsample, layouts=[1,2,3],
        note='Calibration comparison only; fine/native publication checks still required.')
    (a.out/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__': main()
