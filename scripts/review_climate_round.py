"""Compare a candidate with saved, published fields at the same resolution.

Layout checkpoints make interrupted native checks resumable. The combined
checkpoint uses the atlas builder's identity format, so a passed review can
be exported without rerunning the climate. No atlas is promoted by this tool.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import pickle
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from rotclimate.config import Params
from rotclimate import biome_targets as B
from scripts.whittaker_target_experiment import metrics


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def identity(params, seeds):
    return dict(params=json.loads(json.dumps(asdict(params))), seeds=seeds,
        sources={p.name:sha(p) for p in (ROOT/'rotclimate').glob('*.py')
                 if p.name not in {'atlas.py','render.py','biomes.py','climate_fields.py'}},
        map_inputs={p.name:sha(p) for p in (ROOT/'data/source').iterdir() if p.is_file()})


def measured(result):
    row = metrics(result)
    row['coverage'] = B.rendered_coverage(result)
    row['covered_score'] = B.covered_score(row['strict']['score'], row['coverage'])
    row['numerics'] = result.numerics
    return row


def baseline_seeds(packet, path):
    key = packet.get('identity')
    if isinstance(key, dict) and isinstance(key.get('seeds'), list):
        return key['seeds']
    # The physical-screen cache binds to its complete canonical protocol.
    protocol_path = path.parent.parent/'protocol.json'
    if isinstance(key, str) and protocol_path.exists():
        protocol = json.loads(protocol_path.read_text())
        if hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest() == key:
            return protocol['seeds']
    raise ValueError('Baseline checkpoint has no verifiable layout identities')


def assess(baseline, candidate, branch):
    """Existing class protections plus no new grey terrain for Whittaker."""
    failures = []
    objective = 'covered_score' if branch == 'whittaker' else 'zonefit'
    if candidate[objective] <= baseline[objective] + 1e-8:
        failures.append('Primary fit objective did not improve')
    if not candidate['numerics'].get('all_checks_passed'):
        failures.append('Observed numerical checks failed')
    for key, margin in [('zone_accuracy', .01)]:
        if candidate[key] < baseline[key]-margin-1e-12: failures.append(key+' regressed beyond its protection')
    for key, margin in [('cold_dry', .02), ('hot_dry', .03)]:
        if candidate['zone_recall'][key] < baseline['zone_recall'][key]-margin-1e-12:
            failures.append(key+' recall regressed beyond its protection')
    if candidate['mediterranean']['cs_share'] < baseline['mediterranean']['cs_share']-.02-1e-12:
        failures.append('Mediterranean Cs share regressed beyond its protection')
    if candidate['mediterranean']['dry_share'] > max(.05, baseline['mediterranean']['dry_share'])+1e-12:
        failures.append('Mediterranean dry share exceeded its protection')
    if branch == 'whittaker':
        maximum = min(B.coverage_policy()['publication_outside_limit'], baseline['coverage']['outside_share'])
        if candidate['coverage']['outside_share'] > maximum+1e-12:
            failures.append('Whittaker outside-diagram land increased or exceeded its publication limit')
        if candidate['strict']['score'] < B.coverage_policy()['publication_minimum_strict_score']:
            failures.append('Strict biome objective below its publication minimum')
        if candidate['strict']['macro_hard'] < baseline['strict']['macro_hard']-.01-1e-12:
            failures.append('Exact allowed-biome agreement regressed by more than one point')
    return dict(eligible=not failures, objective=objective,
                gain=candidate[objective]-baseline[objective], failures=failures)


def cached_run(params, seeds, folder):
    from rotclimate.model import ClimateModel, ensemble_mean
    runs = []
    for seed in seeds:
        q = params.replace(beyond_seed=seed)
        key = identity(q, [seed])
        path = folder/f'layout{seed}.pkl'
        if path.exists():
            with path.open('rb') as file: packet = pickle.load(file)  # self-generated local checkpoint
            if packet['identity'] != key: raise ValueError('Layout checkpoint inputs changed: '+str(path))
            result = packet['result']
            print(f'Loaded layout {seed}', flush=True)
        else:
            print(f'Simulating ds{q.downsample}, layout {seed}', flush=True)
            result = ClimateModel(q).run()
            if not result.numerics['all_checks_passed']: raise RuntimeError('Layout numerical checks failed')
            with path.with_suffix('.tmp').open('wb') as file: pickle.dump(dict(identity=key, result=result), file)
            path.with_suffix('.tmp').replace(path)
            print(f'Checked and saved layout {seed}', flush=True)
        runs.append(result)
    result = ensemble_mean(runs)
    path = folder/'ensemble.pkl'
    with path.with_suffix('.tmp').open('wb') as file:
        pickle.dump(dict(identity=identity(params, seeds), result=result), file)
    path.with_suffix('.tmp').replace(path)
    return result, path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--branch', choices=['free','earth','whittaker'], required=True)
    ap.add_argument('--candidate', type=Path, required=True)
    ap.add_argument('--baseline', type=Path, required=True, help='Trusted local checkpoint containing the published mean climate')
    ap.add_argument('--downsample', type=int, default=8)
    ap.add_argument('--seeds', type=int, nargs='+', default=[1,2,3])
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    params = Params.from_json(a.candidate).replace(downsample=a.downsample)
    a.out.mkdir(parents=True, exist_ok=True)
    folder = a.out/'checkpoints'; folder.mkdir(exist_ok=True)
    protocol = dict(branch=a.branch, candidate=identity(params, a.seeds),
        baseline_path=str(a.baseline), baseline_sha256=sha(a.baseline),
        review_source_sha256=sha(Path(__file__)),
        note='Baseline reuses its saved fields and original numerical certificates, rather than claiming a new simulation. Both climates are scored with the current unchanged classifier and source terrain.')
    protocol = json.loads(json.dumps(protocol))
    path = a.out/'protocol.json'
    if path.exists() and json.loads(path.read_text()) != protocol:
        raise ValueError('Review inputs changed; use a new output directory')
    write(path, protocol)
    with a.baseline.open('rb') as file: packet = pickle.load(file)
    baseline = packet['result']
    if baseline.params.downsample != a.downsample:
        raise ValueError('Baseline and candidate must use the same weather resolution')
    if not baseline.numerics or not baseline.numerics.get('all_checks_passed'):
        raise ValueError('Baseline has no successful observed numerical certificate')
    # The compared ensemble must use the same named layouts, even when world
    # geometry parameters themselves are being calibrated.
    members = baseline.numerics.get('members')
    if members is None or len(members) != len(a.seeds) or baseline_seeds(packet, a.baseline) != a.seeds:
        raise ValueError('Baseline layout identities differ from requested candidate layouts')
    baseline_row = measured(baseline)
    result, checkpoint = cached_run(params, a.seeds, folder)
    for key in ('T', 'Tsl', 'P', 'W', 'u', 'v', 'E', 'snow'):
        if not np.isfinite(getattr(result, key)).all(): raise ValueError('Nonfinite candidate field: '+key)
    if (result.P < 0).any() or (result.W < 0).any(): raise ValueError('Negative candidate water')
    candidate_row = measured(result)
    review = dict(branch=a.branch, downsample=a.downsample, seeds=a.seeds,
        baseline=baseline_row, candidate=candidate_row, selection=assess(baseline_row, candidate_row, a.branch),
        checkpoint=str(checkpoint), checkpoint_sha256=sha(checkpoint))
    write(a.out/'review.json', review)
    print(json.dumps(review['selection'], indent=2), flush=True)


if __name__ == '__main__': main()
