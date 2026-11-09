"""Fail before a v2.2 build if correction artifacts or resume identities are stale."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_correction(folder, physics_path):
    """Match both the published training protocol and the actual model metadata."""
    import numpy as np
    protocol = json.loads((folder / 'protocol.json').read_text())
    physics_hash = sha(physics_path)
    if protocol['meta']['physics_params_sha256'] != physics_hash:
        raise ValueError('Correction protocol belongs to different physics: ' + str(folder))
    for name, digest in protocol['files'].items():
        path = folder / name
        if not path.is_file() or sha(path) != digest:
            raise ValueError('Missing or changed correction artifact: ' + str(path))
    with np.load(folder / 'correction.npz', allow_pickle=False) as archive:
        meta = json.loads(str(archive['meta']))
    if meta['physics_params_sha256'] != physics_hash:
        raise ValueError('Correction model belongs to different physics: ' + str(folder))
    return sha(folder / 'correction.npz')


def check(root, out, *, record=False):
    from rotclimate.config import Params
    from rotclimate import joint
    from correction_training_receipt import inputs, matches
    physics_path = root / 'calibration/local_accuracy_20261023/r44_params.json'
    world_path = root / 'calibration/map_world_r44_terrain22/params.json'
    cal = root / 'calibration/earth_correction_r44_20261107'
    evals = root / 'output/earth_correction_r44_20261107'
    terrain = root / json.loads(world_path.read_text())['terrain_file']
    required = [physics_path, world_path, terrain, root / 'data/delta_fan_model.json',
        root / 'reports/LAKES_DELTAS_20261108.md', evals / 'training_receipt.json']
    for component in ['temperature', 'rain_pattern']:
        required += [cal / component / name for name in ['correction.npz', 'protocol.json', 'evaluation.json']]
    missing = [str(p.relative_to(root)) for p in required if not p.is_file()]
    if missing:
        raise ValueError('Required release inputs are missing; reconstruct r44 corrections before building: ' + ', '.join(missing))
    physics, world = Params.from_json(physics_path), Params.from_json(world_path)
    joint.validate_partition(); joint.require_strict(world)
    different = sorted(k for k in joint.SHARED_FIELDS if getattr(physics, k) != getattr(world, k))
    if different:
        raise ValueError('World parameters differ from adopted r44 shared physics: ' + str(different))
    for component in ['temperature', 'rain_pattern']:
        verify_correction(cal / component, physics_path)
    receipt = json.loads((evals / 'training_receipt.json').read_text())
    if not matches(receipt, inputs(physics_path.relative_to(root), 'r44'), root):
        raise ValueError('Correction reconstruction receipt is incomplete or stale')
    # This identity covers both physical inputs and export/add-on code. An old
    # stages_done file cannot silently skip work after any of them changes.
    sources = [*required, *sorted((root / 'scripts').glob('*.py')),
        root / 'scripts/release_v22_deltas.sh', *sorted((root / 'data').glob('*.json'))]
    for package in ['rotclimate', 'harvest', 'polity', 'atlas']:
        sources += sorted(p for p in (root / package).rglob('*') if p.is_file() and p.suffix in {'.py', '.js', '.html'})
    identity = {str(p.relative_to(root)): sha(p) for p in sorted(set(sources))}
    manifest = out / 'release_inputs.json'; stages = out / 'stages_done'
    if stages.exists() and stages.read_text().strip():
        if not manifest.exists() or json.loads(manifest.read_text()) != identity:
            raise ValueError('Existing release stages have different/unrecorded inputs; use a new release output directory')
    if record:
        out.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(identity, indent=2) + '\n')
    return dict(status='passed', input_files=len(identity), corrections_verified=True,
        missing_checkpoint_can_be_regenerated=not (root / 'output/r44_lakes_world/candidate_001.pkl').is_file(),
        resume_identity_recorded=record)


def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('--out', type=Path, default=ROOT / 'output/atlas_v22')
    ap.add_argument('--record', action='store_true'); args = ap.parse_args()
    try:
        result = check(ROOT, args.out, record=args.record)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        ap.exit(1, str(exc) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
