"""Write separated Earth/world inputs for a new constrained joint experiment.

This prepares reproducible inputs; it does not run or select a calibration.
Historical joint_calibrate.py retains its original behavior.
"""
from pathlib import Path
import argparse
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))

from earth_benchmark import load_params
from local_benchmark_protocol import file_hash, freeze, write_json
from rotclimate import joint


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--physics', required=True, type=Path)
    parser.add_argument('--world', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    physics, world = load_params(args.physics), load_params(args.world)
    description = joint.describe(physics, world)
    args.out.mkdir(parents=True, exist_ok=True)
    paths = [args.physics, args.world, Path(__file__), ROOT/'rotclimate/joint.py',
             ROOT/'rotclimate/config.py', ROOT/'scripts/earth_benchmark.py',
             ROOT/'scripts/local_benchmark_protocol.py']
    freeze(args.out/'protocol.json', dict(inputs=description,
        source_hashes={str(p.resolve()): file_hash(p) for p in paths}))
    write_json(args.out/'earth_profile.json', description['earth_profile'])
    write_json(args.out/'world_profile.json', description['world_profile'])
    print('Prepared Earth/world profiles; no calibration or adoption performed.')


if __name__ == '__main__':
    main()
