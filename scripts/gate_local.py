"""Apply the frozen local-accuracy rules to verified, paired Earth benchmarks.

    python -I scripts/gate_local.py REFERENCE CANDIDATE [CANDIDATE ...] --out review.json

The CLI infers policy v1 (19 regions) or v2 (31); --policy selects explicitly.
Old summaries without input manifests must be regenerated before adoption.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from local_benchmark_protocol import identity, file_hash, write_json


def score(s, ref):
    return 0.5*s['T_monthly_mae']/ref['T_monthly_mae'] + 0.5*s['P_loss']/ref['P_loss']


def measures(summary, names):
    rows = [summary['regions'][name] for name in names]
    return dict(T_monthly_mae=sum(r['temperature']['monthly_mae_C'] for r in rows)/len(rows),
                P_loss=sum(r['rain']['loss'] for r in rows)/len(rows))


def validate(summary, protocol, expected):
    if summary.get('complete') is not True or summary.get('identity') != identity(protocol):
        raise ValueError('Incomplete benchmark or mismatched input manifest')
    if set(summary['regions']) != expected or set(protocol['regions']) != expected or len(protocol['regions']) != len(expected):
        raise ValueError('Benchmark does not contain the exact policy regions')
    if summary['cell_km'] != 56 or protocol['cell_km'] != 56:
        raise ValueError('The development gate requires 56 km benchmarks')
    for name, row in summary['regions'].items():
        if row.get('status') != 'passed' or row.get('numerics', {}).get('all_checks_passed') is not True:
            raise ValueError('Unverified numerical result: '+name)
        if row.get('identity') != summary['identity'] or row.get('region') != name:
            raise ValueError('Regional result belongs to another run: '+name)
        if not row.get('case_identity') or row['cells'] < 1:
            raise ValueError('Missing geographic identity: '+name)
        for value in [row['temperature']['monthly_mae_C'], row['rain']['loss']]:
            if not math.isfinite(value) or value < 0: raise ValueError('Invalid local error: '+name)


def evaluate(ref, candidate, ref_protocol, candidate_protocol, policy):
    groups = policy['groups']
    names = [name for members in groups.values() for name in members]
    if len(names) != len(set(names)): raise ValueError('Policy groups overlap')
    expected = set(names)
    validate(ref, ref_protocol, expected); validate(candidate, candidate_protocol, expected)
    if ref_protocol['sources'] != candidate_protocol['sources']:
        raise ValueError('Scientific sources or observations changed between paired runs')
    if ref_protocol['region_specs'] != candidate_protocol['region_specs']:
        raise ValueError('Region definitions changed between paired runs')
    for key in ['steps_per_year','solver_rtol','moisture_residual_tol',
                't_require_convergence','moisture_require_convergence','solver_require_convergence']:
        if ref_protocol['params'][key] != candidate_protocol['params'][key]:
            raise ValueError('Numerical criteria differ: '+key)
    for name in names:
        b, c = ref['regions'][name], candidate['regions'][name]
        if b['case_identity'] != c['case_identity'] or b['cells'] != c['cells']:
            raise ValueError('Paired geography or observations differ: '+name)
    baseline = measures(ref, names); current = measures(candidate, names)
    if any(v <= 0 for v in baseline.values()): raise ValueError('Reference error must be positive')
    ratios = {key:current[key]/baseline[key]-1 for key in baseline}
    group_scores = {g:score(measures(candidate,members), measures(ref,members)) for g,members in groups.items()}
    overall = score(current, baseline)
    failures = []
    if overall > .995: failures.append('Overall score did not improve by at least 0.5%')
    failures += [g+': group score worsened' for g,s in group_scores.items() if s > 1]
    failures += [key+': error increased by more than 1%' for key,delta in ratios.items() if delta > .01]
    return dict(passes_development_gate=not failures, failures=failures, score=overall,
                group_scores=group_scores, relative_changes=ratios, baseline=baseline, candidate=current,
                note='Development gate only; finer-resolution, validation and atlas publication checks remain.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('reference', type=Path); ap.add_argument('candidates', nargs='+', type=Path)
    ap.add_argument('--policy', type=Path)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    ref = json.loads((a.reference/'summary.json').read_text())
    policy_path = a.policy or ROOT/'calibration/local_accuracy_20261023'/('policy_v2.json' if len(ref['regions']) == 31 else 'policy.json')
    policy = json.loads(policy_path.read_text())
    reference_protocol = json.loads((a.reference/'protocol.json').read_text())
    reviews = {}
    for folder in a.candidates:
        candidate = json.loads((folder/'summary.json').read_text())
        candidate_protocol = json.loads((folder/'protocol.json').read_text())
        result = evaluate(ref, candidate, reference_protocol, candidate_protocol, policy)
        result['evidence_sha256'] = {str(p):file_hash(p) for p in [policy_path, a.reference/'summary.json',
            a.reference/'protocol.json', folder/'summary.json', folder/'protocol.json']}
        reviews[str(folder)] = result
        print(f"{folder.name}: S {result['score']:.4f}; "+('passes development gate' if result['passes_development_gate'] else 'fails'))
        print(json.dumps(result, indent=2))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        write_json(a.out, dict(reference=str(a.reference), policy=str(policy_path), candidates=reviews))


if __name__ == '__main__': main()
