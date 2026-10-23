"""Check a selected rainfall fit on paired new geography or finer grids.

Run benchmark_rainfall.py with fits named baseline and candidate first.
These tests accept lower mean rainfall loss and monthly MAE, with no failed
numerical checks. They do not select among multiple candidates.
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
import numpy as np
from rotclimate.config import Params
from scripts.rainfall_metrics import LOSS_SPEC, loss


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--benchmark', type=Path, required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--regions-file', type=Path, help='Required predeclared definitions for a new-geography check')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    protocol = json.loads((a.benchmark/'protocol.json').read_text())
    if set(protocol['fits']) != {'baseline', 'candidate'} or protocol['rainfall_loss'] != LOSS_SPEC:
        raise ValueError('Expected exactly one paired rainfall comparison')
    # JSON represents the terrain tuple as a list.
    if protocol['fits']['candidate'] != json.loads(json.dumps(asdict(Params.from_json(a.candidate)))):
        raise ValueError('This benchmark did not test the selected candidate')
    if a.regions_file:
        definitions = json.loads(a.regions_file.read_text())
        if protocol['region_specs'] != definitions or set(protocol['regions']) != set(definitions):
            raise ValueError('Geographic tests differ from the predeclared regions')
    identity = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    rows, failures = {}, []
    evidence = [a.benchmark/'protocol.json', a.candidate]
    for region in protocol['regions']:
        pair = {}
        for fit in ['baseline', 'candidate']:
            path = a.benchmark/'cases'/f'{fit}_{region}.json'
            evidence.append(path)
            row = json.loads(path.read_text())
            if row['identity'] != identity: raise ValueError('Benchmark evidence inputs differ')
            if row['fit'] != fit or row['region'] != region: raise ValueError('Benchmark case labels differ')
            if row['status'] != 'passed' or not row.get('numerics', {}).get('all_checks_passed'):
                failures.append(region+': failed '+fit)
            pair[fit] = row
        if any(row['status'] != 'passed' or not row.get('numerics', {}).get('all_checks_passed')
               for row in pair.values()): continue
        if pair['baseline']['rainfall']['scored_land_cells'] != pair['candidate']['rainfall']['scored_land_cells']:
            raise ValueError('Unpaired geography')
        for row in pair.values():
            if not np.isclose(row['rainfall']['loss'], loss(row['climate']), rtol=1e-6, atol=1e-8):
                raise ValueError('Rainfall loss and diagnostics disagree')
        rows[region] = {fit:row['rainfall'] for fit,row in pair.items()}
    complete = len(rows) == len(protocol['regions']) and not failures
    means = {}
    if complete:
        for fit in ['baseline', 'candidate']:
            means[fit] = {key:float(np.mean([pair[fit][key] for pair in rows.values()]))
                          for key in ['loss', 'monthly_mae_mm', 'annual_log_rmse']}
        for key in ['loss', 'monthly_mae_mm']:
            if means['candidate'][key] > means['baseline'][key]: failures.append(key+' increased')
    output = dict(passed=complete and not failures, failures=failures,
                  comparison='new_geography' if a.regions_file else 'resolution_transfer',
                  identity=identity, cell_km=protocol['cell_km'], regions=rows, means=means,
                  candidate_sha256=hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
                  evidence_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence},
                  note='One selected candidate; geographic checks become development data if reused for tuning.')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps(output, indent=2))


if __name__ == '__main__': main()
