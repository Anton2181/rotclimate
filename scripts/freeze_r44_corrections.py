"""Freeze verified reconstructed models and release scores, without raw cache dependencies."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    from correction_training_receipt import inputs, matches, PARTS
    from check_v22_release_inputs import verify_correction
    cal = ROOT / 'calibration/earth_correction_r44_20261107'
    out = ROOT / 'output/earth_correction_r44_20261107'
    physics = Path('calibration/local_accuracy_20261023/r44_params.json')
    full = out / 'training_receipt.json'
    receipt = json.loads(full.read_text())
    if not matches(receipt, inputs(physics, 'r44'), ROOT):
        raise ValueError('Full reconstruction receipt is incomplete or stale')
    plan = cal / 'reconstruction_plan.json'; declared = json.loads(plan.read_text())
    for name, digest in declared['inputs_sha256'].items():
        if sha(ROOT / name) != digest: raise ValueError('Reconstruction recipe changed: ' + name)
    protocols = {name: json.loads((cal/name/'protocol.json').read_text()) for name in ['temperature','rain_pattern']}
    hashes = {name: verify_correction(cal/name, ROOT/physics) for name in protocols}
    files = [full, plan]
    for name, protocol in protocols.items():
        files += [cal/name/path for path in protocol['files']]
        files += [cal/name/path for path in ['protocol.json','evaluation.json']]
    for part in PARTS:
        files += [out/f'eval_{part}.json', out/f'eval_rain_{part}.json',
            out/f'r44_{part}'/'summary.json', out/f'r44_{part}'/'protocol.json']
    scores = dict(temperature_cluster_cv_mae_C=protocols['temperature']['meta']['held_out_monthly_mae_C'],
        rain_cluster_cv_loss=protocols['rain_pattern']['meta']['held_out_loss'])
    reference = declared['expected_reference']
    consistency = dict(temperature_matches_published_rounding=round(scores['temperature_cluster_cv_mae_C'],3)==reference['temperature_cluster_cv_mae_C'],
        rain_matches_published_rounding=round(scores['rain_cluster_cv_loss'],4)==reference['rain_cluster_cv_loss'])
    if not all(consistency.values()):
        raise ValueError('Reconstruction differs from the published rounded reference; investigate before release: ' + str(scores))
    portable = dict(version=1,status='complete',date='2026-11-09',reconstruction=True,
        full_training_receipt_verified=True,full_training_receipt_sha256=sha(full),
        physics_params_sha256=sha(ROOT/physics),recipe_sha256=sha(plan),
        artifacts={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))},
        scope='Models, folds and scores needed for release; raw training cases/WorldClim caches remain audit inputs, not atlas build prerequisites.',
        interpretation='Existing fixed training recipe replayed on spent development/evaluation pools. Recovered artifacts have new identities; no new unseen-accuracy claim.',
        scores=scores,reference_consistency=consistency)
    (cal/'release_receipt.json').write_text(json.dumps(portable,indent=2)+'\n')
    status=dict(status='reconstruction_complete',date='2026-11-09',**scores,reference_consistency=consistency,
        recovered_sha256=hashes,lost_original_sha256=declared['lost_original_sha256'],
        byte_identical_to_lost_original={n:hashes[n]==declared['lost_original_sha256'][n] for n in hashes},
        release_receipt_sha256=sha(cal/'release_receipt.json'),interpretation=portable['interpretation'])
    (cal/'reconstruction_status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps(status,indent=2))


if __name__ == '__main__': main()
