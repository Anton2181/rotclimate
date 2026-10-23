"""Apply the predeclared rainfall selection policy to a completed Earth search.

The eleven comparison regions are previously used development data. A pass
here still requires the separate new-geography comparison and native atlas
verification before a published climate can change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts.rainfall_metrics import LOSS_SPEC, loss


def average(rows, field, key):
    return float(np.mean([r[field][key] for r in rows]))


def summaries(rows):
    wet = sum(r['rainfall']['wet_scored_cells'] for r in rows)
    return dict(
        loss=average(rows, 'rainfall', 'loss'),
        monthly_mae_mm=average(rows, 'rainfall', 'monthly_mae_mm'),
        annual_mae_mm=average(rows, 'rainfall', 'annual_mae_mm'),
        annual_log_rmse=average(rows, 'rainfall', 'annual_log_rmse'),
        seasonality_total_variation=average(rows, 'rainfall', 'seasonality_total_variation'),
        annual_rank_corr=float(np.mean([r['climate']['rain']['annual_rank_corr'] for r in rows])),
        temperature_rmse_C=float(np.mean([r['climate']['temperature']['rmse_C'] for r in rows])),
        pooled_wet_cells=wet,
        pooled_annual_within_25pct=sum(r['rainfall']['annual_within_25pct'] * r['rainfall']['wet_scored_cells']
                                      for r in rows)/wet,
        pooled_annual_within_50pct=sum(r['rainfall']['annual_within_50pct'] * r['rainfall']['wet_scored_cells']
                                      for r in rows)/wet,
    )


def assess(baseline, candidate, training, policy):
    if set(baseline) != set(candidate): raise ValueError('Unpaired regions')
    if not set(training) <= set(baseline): raise ValueError('Missing training region')
    protections = policy['selection']
    failures = []
    for name in baseline:
        b, c = baseline[name], candidate[name]
        for row in [b, c]:
            if row.get('status') != 'passed' or not row['numerics'].get('all_checks_passed'):
                failures.append(name+': failed numerical or execution checks')
            if not np.isclose(row['rainfall']['loss'], loss(row['climate']), rtol=1e-6, atol=1e-8):
                raise ValueError('Rainfall diagnostics disagree with optimizer loss: '+name)
        if b['rainfall']['scored_land_cells'] != c['rainfall']['scored_land_cells'] or \
                b['rainfall']['wet_scored_cells'] != c['rainfall']['wet_scored_cells']:
            raise ValueError('Scored geography changed: '+name)
        br, cr = b['rainfall'], c['rainfall']
        if cr['annual_log_rmse'] > br['annual_log_rmse'] + protections['maximum_region_annual_log_rmse_increase']:
            failures.append(name+': annual amount errors regressed beyond protection')
        mm, fraction = protections['maximum_region_monthly_mae_increase_mm_or_fraction']
        if cr['monthly_mae_mm'] > br['monthly_mae_mm'] + max(mm, br['monthly_mae_mm'] * fraction):
            failures.append(name+': monthly rainfall errors regressed beyond protection')
    b, c = summaries(list(baseline.values())), summaries(list(candidate.values()))
    if c['loss'] > b['loss'] * (1-protections['all_19_rainfall_loss_minimum_relative_gain']):
        failures.append('All-region rainfall loss did not improve by the minimum 1%')
    train_b = summaries([baseline[r] for r in training]); train_c = summaries([candidate[r] for r in training])
    if train_c['loss'] >= train_b['loss']: failures.append('Training rainfall loss did not improve')
    if c['monthly_mae_mm'] >= b['monthly_mae_mm']: failures.append('Mean monthly MAE did not improve')
    if c['annual_log_rmse'] > b['annual_log_rmse']: failures.append('Mean annual log RMSE increased')
    for key, limit in [('temperature_rmse_C', 'maximum_mean_temperature_rmse_increase_C'),
                       ('seasonality_total_variation', 'maximum_mean_seasonality_total_variation_increase')]:
        if c[key] > b[key] + protections[limit]: failures.append(key+' regressed beyond protection')
    for key, limit in [('annual_rank_corr', 'maximum_mean_annual_rank_correlation_loss'),
                       ('pooled_annual_within_25pct', 'maximum_pooled_annual_within_25pct_share_loss')]:
        if c[key] < b[key] - protections[limit]: failures.append(key+' regressed beyond protection')
    return dict(eligible_for_new_geographic_validation=not failures, failures=failures,
                baseline=b, candidate=c, training_baseline=train_b, training_candidate=train_c,
                relative_rainfall_loss_gain=1-c['loss']/b['loss'],
                note='Reused development regions; no atlas promotion or independent accuracy claim.')


def load_candidate(directory):
    config = json.loads((directory/'calibration_config.json').read_text())
    if config['objective'] != 'rainfall' or config['rainfall_loss'] != LOSS_SPEC:
        raise ValueError('Search used a different objective')
    params = json.loads((directory/'best_params.json').read_text())
    journal = [json.loads(line) for line in (directory/'evals.jsonl').read_text().splitlines()]
    best = min((r for r in journal if not r.get('error')), key=lambda r:r['cost'])
    if best['params'] != params: raise ValueError('Saved best parameters differ from journal')
    if not np.isclose(best['cost'], np.mean([loss(m) for m in best['regions'].values()])):
        raise ValueError('Selected optimizer cost does not match rainfall metrics')
    held = json.loads((directory/'holdout_evaluations.json').read_text()) if config['final_comparison'] else {}
    rows = {}
    for region in config['regions'] + config['final_comparison']:
        row = best if region in config['regions'] else held[region]
        if row.get('error') or row['params'] != params:
            raise ValueError('Final comparison failed or used different physics: '+region)
        rows[region] = dict(region=region, status='passed', climate=row['regions'][region],
                            rainfall=row['rainfall_details'][region], stations=row['stations'][region],
                            numerics=row['observed_numerics'][region])
    return config, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--search', type=Path, required=True)
    ap.add_argument('--baseline', type=Path, required=True)
    ap.add_argument('--policy', type=Path, default=ROOT/'calibration/climate_physics_20261023/rainfall_policy.json')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    config, candidate = load_candidate(a.search)
    policy = json.loads(a.policy.read_text())
    if config['regions'] != policy['training'] or config['final_comparison'] != policy['reused_comparison']:
        raise ValueError('Search regions do not match the predeclared policy')
    protocol = json.loads((a.baseline/'protocol.json').read_text())
    if protocol['fits']['baseline'] != config['params'] or protocol['cell_km'] != config['cell_km'] or \
            protocol['pad_km'] != config['pad_km']:
        raise ValueError('Baseline and search start or geography differ')
    # Drivers can differ; all shared scientific modules and observed inputs
    # must match byte-for-byte. Their historical hashes remain authoritative.
    for name in set(protocol['sources']) & set(config['sources']):
        if protocol['sources'][name] != config['sources'][name]:
            raise ValueError('Baseline scientific inputs differ: '+name)
    baseline = {r:json.loads((a.baseline/'cases'/f'baseline_{r}.json').read_text()) for r in candidate}
    decision = assess(baseline, candidate, policy['training'], policy)
    evidence = [a.policy, a.search/'calibration_config.json', a.search/'evals.jsonl',
                a.baseline/'protocol.json', a.baseline/'summary.json']
    if config['final_comparison']: evidence.append(a.search/'holdout_evaluations.json')
    output = dict(policy=policy, selection=decision, baseline=baseline, candidate=candidate,
                  evidence_sha256={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in evidence})
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(output, indent=2, allow_nan=False)+'\n')
    print(json.dumps(decision, indent=2))


if __name__ == '__main__': main()
