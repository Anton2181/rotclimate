"""Verify completion before reusing a separately started correction training job."""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json

PARTS = ('dev31', 'fine28', 'fine14', 'sealed')
SCRIPTS = ('retrain_earth_corrections.sh', 'benchmark_local.py', 'earth_benchmark.py',
           'local_benchmark_protocol.py', 'rainfall_metrics.py', 'collect_earth_fields.py',
           'train_earth_correction.py', 'evaluate_earth_correction.py', 'train_rain_pattern.py',
           'evaluate_rain_pattern.py', 'correction_training_receipt.py')


def relative_name(path, root):
    # Keep the in-snapshot alias of a deliberately linked observational file;
    # its bytes, not its external resolved location, identify the input.
    return str(Path(os.path.abspath(path)).relative_to(Path(os.path.abspath(root))))


def record(inputs, files, root):
    return dict(status='complete', inputs=inputs,
                artifacts={relative_name(p, root): file_hash(p) for p in files})


def matches(receipt, inputs, root):
    if receipt.get('status') != 'complete' or receipt.get('inputs') != inputs or not receipt.get('artifacts'):
        return False
    return all((root / name).is_file() and file_hash(root / name) == digest
               for name, digest in receipt['artifacts'].items())


def inputs(params, tag):
    files = [params, *(ROOT / 'scripts' / name for name in SCRIPTS),
             *sorted((ROOT / 'rotclimate').glob('*.py')),
             *(ROOT / 'data/cache/worldclim' / f'wc2.1_5m_{name}.zip' for name in ('tavg', 'prec', 'elev', 'vapr')),
             ROOT / 'scripts/train_earth_correction.py',
             ROOT / 'calibration/climate_physics_20261023/rainfall_validation_regions.json',
             ROOT / 'calibration/local_accuracy_20261023/regions_dev12.json',
             *sorted((ROOT / 'data/cache/earth').glob('*.npz'))]
    return dict(tag=tag, files={relative_name(p, ROOT): file_hash(p) for p in files},
                packages={name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'scikit-learn')})


def artifacts(out, cal, tag):
    files = []
    for name in ('temperature', 'rain_pattern'):
        for leaf in ('correction.npz', 'protocol.json', 'evaluation.json'):
            files.append(cal / name / leaf)
        trained = json.loads((cal / name / 'protocol.json').read_text())['files']
        if not any(p.startswith('folds/') for p in trained):
            raise ValueError('Missing held-out correction models')
        for relative, digest in trained.items():
            model = cal / name / relative
            if not model.is_file() or file_hash(model) != digest:
                raise ValueError('Missing or changed trained correction model: ' + str(model))
            files.append(model)
    for part in PARTS:
        folder = out / f'{tag}_{part}'
        summary = json.loads((folder / 'summary.json').read_text())
        if summary.get('complete') is not True or any(r.get('status') != 'passed' or not r.get('numerics', {}).get('all_checks_passed') for r in summary['regions'].values()):
            raise ValueError('Incomplete correction benchmark: ' + part)
        files.extend([folder / 'summary.json', folder / 'protocol.json', out / f'eval_{part}.json', out / f'eval_rain_{part}.json'])
        for name, row in summary['regions'].items():
            cells = folder / 'cells' / (name + '.npz')
            if file_hash(cells) != row['cells_sha256']:
                raise ValueError('Changed benchmark packet: ' + name)
            files.extend([cells, folder / 'cases' / (name + '.json'), out / f'fields_{part}' / (name + '.npz')])
    if not all(p.is_file() for p in files):
        raise ValueError('Incomplete correction artifacts')
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=['check', 'write'])
    ap.add_argument('--params', required=True, type=Path)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--cal', required=True, type=Path)
    a = ap.parse_args(); path = a.out / 'training_receipt.json'
    if a.mode == 'check' and not path.exists():
        raise SystemExit(1)
    identity = inputs(a.params, a.tag)
    if a.mode == 'check':
        raise SystemExit(0 if matches(json.loads(path.read_text()), identity, ROOT) else 1)
    write_json(path, record(identity, artifacts(a.out, a.cal, a.tag), ROOT))


if __name__ == '__main__':
    main()
