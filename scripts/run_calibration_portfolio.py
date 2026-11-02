"""Run and resume a frozen set of independent CMA searches, retaining all outcomes.

Example: python -I scripts/run_calibration_portfolio.py \
  --campaign calibration/r42_multistart_20261102/campaign.json \
  --out output/r42_multistart_20261102 --workers 1

Selection uses development results only. This script never runs sealed regions,
adopts physics, replaces an atlas or commits files.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'scripts'))
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash, freeze


def select_finalist(records):
    """Choose S, not group penalties or an individually favourable restart."""
    eligible = [r for r in records if not r.get('failed') and r.get('n', 0) > 0
                and r.get('S', float('inf')) <= .995
                and r.get('T_relative', float('inf')) <= .01
                and r.get('P_relative', float('inf')) <= .01]
    return min(eligible, key=lambda r: (r['S'], r['chain'], r['n'])) if eligible else None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--campaign', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--workers', type=int, default=1)
    a = ap.parse_args()
    if a.workers < 1:
        ap.error('workers must be positive')
    campaign = json.loads(a.campaign.read_text())
    plans = [(ROOT / path, json.loads((ROOT / path).read_text())) for path in campaign['plans']]
    if any(p.get('scoring_policy') != 'v3' or not p.get('require_reference_reproduction') for _, p in plans):
        ap.error('Portfolio requires v3 plans with initial reference reproduction')
    a.out.mkdir(parents=True, exist_ok=True)
    sources = [Path(__file__), ROOT / 'scripts/gate_calibrate.py', *(ROOT / 'rotclimate').glob('*.py')]
    freeze(a.out / 'campaign_identity.json', dict(campaign=campaign, plans=[p for _, p in plans],
           sources={str(p.relative_to(ROOT)): file_hash(p) for p in sources}))

    def status(stage, **fields):
        data = dict(stage=stage, updated_utc=datetime.now(timezone.utc).isoformat(), **fields)
        tmp = a.out / 'status.tmp'
        tmp.write_text(json.dumps(data, indent=2) + '\n')
        tmp.replace(a.out / 'status.json')
        print(json.dumps(data), flush=True)

    records = []
    try:
        for i, (path, plan) in enumerate(plans, 1):
            out = a.out / f'chain_{i}'
            history = out / 'evals.jsonl'
            rows = [json.loads(line) for line in history.read_text().splitlines()] if history.exists() else []
            while len(rows) < plan['evals']:
                status('running', chain=i, completed_in_chain=len(rows), budget=plan['evals'])
                command = [sys.executable, '-u', '-I', str(ROOT / 'scripts/gate_calibrate.py'),
                           '--plan', str(path), '--out', str(out), '--workers', str(a.workers), '--hours', '12']
                if (out / 'state.pkl').exists():
                    command.append('--resume')
                with (a.out / f'chain_{i}.log').open('a') as log:
                    subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
                updated = [json.loads(line) for line in history.read_text().splitlines()]
                if len(updated) <= len(rows):
                    raise RuntimeError('Search made no progress; see chain log')
                rows = updated
            records.extend(dict(r, chain=i) for r in rows)
        selected = select_finalist(records)
        result = dict(evaluations=len(records), failed=sum(bool(r.get('failed')) for r in records),
                      independent_starts=len(plans), finalist=selected,
                      limitation='Starting-point sensitivity within one parameter box, not proof of a global optimum.')
        if selected:
            plan = plans[selected['chain'] - 1][1]
            p = load_params(ROOT / plan['start']).replace(**{**plan.get('set', {}), **selected['knobs']})
            (a.out / 'finalist_params.json').write_text(json.dumps(asdict(p), indent=2) + '\n')
        (a.out / 'selection.json').write_text(json.dumps(result, indent=2) + '\n')
        status('awaiting_validation' if selected else 'completed_no_qualifying_candidate', **result)
    except Exception as exc:
        status('failed', error=str(exc))
        raise


if __name__ == '__main__':
    main()
