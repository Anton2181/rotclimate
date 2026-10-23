"""Review a predeclared single-parameter r31 rainfall pilot; no atlas adoption."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash, identity, write_json


def assess(ref, current, rp, cp, plan):
    names = plan['pilot_regions']
    if not ref.get('complete') or not current.get('complete'):
        raise ValueError('Incomplete pilot evidence')
    if ref['identity'] != identity(rp) or current['identity'] != identity(cp):
        raise ValueError('Input manifest mismatch')
    if set(current['regions']) != set(names) or set(cp['regions']) != set(names) or not set(names) <= set(ref['regions']):
        raise ValueError('Unexpected pilot region set')
    if rp['sources'] != cp['sources'] or rp['cell_km'] != cp['cell_km']:
        raise ValueError('Unpaired scientific sources or resolution')
    changes = {key for key in rp['params'] if rp['params'][key] != cp['params'][key]}
    if changes != {plan['parameter']} or cp['params'][plan['parameter']] not in plan['candidates']:
        raise ValueError('Pilot changed parameters outside its predeclared hypothesis')
    if rp['params'][plan['parameter']] != plan['control']:
        raise ValueError('Incorrect reference convergence strength')
    regional = {}
    failures = []
    for name in names:
        b, c = ref['regions'][name], current['regions'][name]
        if rp['region_specs'][name] != cp['region_specs'][name] or b['case_identity'] != c['case_identity'] or b['cells'] != c['cells']:
            raise ValueError('Unpaired observed inputs: '+name)
        for row, run in [(b,ref), (c,current)]:
            if row['status'] != 'passed' or row['numerics'].get('all_checks_passed') is not True or row['identity'] != run['identity']:
                raise ValueError('Unverified regional evidence: '+name)
        regional[name] = dict(baseline_loss=b['rain']['loss'], candidate_loss=c['rain']['loss'],
            baseline_monthly_mae_mm=b['rain']['monthly_mae_mm'], candidate_monthly_mae_mm=c['rain']['monthly_mae_mm'])
        if c['rain']['monthly_mae_mm'] > b['rain']['monthly_mae_mm']+max(2., .1*b['rain']['monthly_mae_mm']):
            failures.append(name+': monthly rainfall MAE regressed beyond protection')
    means = {}
    for label, data in [('baseline',ref), ('candidate',current)]:
        rows = [data['regions'][n] for n in names]
        means[label] = dict(rainfall_loss=sum(r['rain']['loss'] for r in rows)/len(rows),
            monthly_rainfall_mae_mm=sum(r['rain']['monthly_mae_mm'] for r in rows)/len(rows),
            monthly_temperature_mae_C=sum(r['temperature']['monthly_mae_C'] for r in rows)/len(rows))
    b,c = means['baseline'],means['candidate']
    if c['rainfall_loss'] >= b['rainfall_loss']: failures.append('Mean rainfall loss did not improve')
    if c['monthly_rainfall_mae_mm'] >= b['monthly_rainfall_mae_mm']: failures.append('Monthly rainfall MAE did not improve')
    if c['monthly_temperature_mae_C'] > 1.01*b['monthly_temperature_mae_C']: failures.append('Temperature error increased by more than 1%')
    return dict(eligible_for_dev31=not failures, failures=failures, means=means, regions=regional,
                note='Six development-region screen; no validation or atlas promotion.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--reference', type=Path, required=True)
    ap.add_argument('--candidates', nargs='+', type=Path, required=True)
    ap.add_argument('--plan', type=Path, default=ROOT/'calibration/rainfall_r31_20261023/plan.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    ref = json.loads((a.reference/'summary.json').read_text()); rp = json.loads((a.reference/'protocol.json').read_text())
    reviews = {}; evidence = [a.plan, a.reference/'summary.json', a.reference/'protocol.json']
    for folder in a.candidates:
        summary = json.loads((folder/'summary.json').read_text()); protocol = json.loads((folder/'protocol.json').read_text())
        reviews[str(folder)] = assess(ref, summary, rp, protocol, plan)
        evidence += [folder/'summary.json',folder/'protocol.json']
    eligible = [name for name,result in reviews.items() if result['eligible_for_dev31']]
    selected = min(eligible, key=lambda name:reviews[name]['means']['candidate']['rainfall_loss']) if eligible else None
    result = dict(selected_for_dev31=selected, candidates=reviews, evidence_sha256={str(p):file_hash(p) for p in evidence})
    a.out.parent.mkdir(parents=True, exist_ok=True);write_json(a.out,result)
    print(json.dumps(result,indent=2))


if __name__ == '__main__': main()
