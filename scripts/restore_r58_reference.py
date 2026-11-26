"""Replay the adopted r58 development reference and compare archived scores."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json


def main():
    plan_path = ROOT / 'calibration/ppe_20261123/plan_W18c.json'
    plan = json.loads(plan_path.read_text())
    reference = ROOT / plan['reference']; reference.mkdir(parents=True, exist_ok=True)
    params = ROOT / 'calibration/local_accuracy_20261023/r58_params.json'
    adoption = json.loads((params.parent / 'r58_adoption.json').read_text())
    assert file_hash(params) == adoption['params_sha256']
    restoration = ROOT / 'output/climate_runtime_20261126/restoration.json'
    receipt = json.loads(restoration.read_text())
    for path, digest in receipt['cache_sha256'].items():
        assert file_hash(ROOT / path) == digest, path
    parts = {'dev31':None, 'retired_a':'calibration/sealed_20261031/regions.json',
             'retired_b':'calibration/sealed_20261031b/regions.json',
             'retired_c':'calibration/sealed_20261101c/regions.json', **plan['extra_parts']}
    for part, spec in parts.items():
        out = reference / f'r58_{part}'
        command = [sys.executable, '-I', str(ROOT / 'scripts/benchmark_local.py'), '--fit', str(params),
                   '--workers', '3', '--out', str(out), '--regions']
        command += ['dev31'] if spec is None else list(json.loads((ROOT / spec).read_text()))
        if spec: command += ['--region-specs', str(ROOT / spec)]
        print('Replaying r58', part, flush=True)
        subprocess.run(command, cwd=ROOT, check=True)
    archived = ROOT / 'calibration/ppe_20261123/W18_records/results.jsonl'
    record = next(json.loads(line) for line in archived.read_text().splitlines() if json.loads(line).get('ok'))
    expected = record['regions']; actual = {}; errors = []
    for part in parts:
        summary = json.loads((reference / f'r58_{part}/summary.json').read_text())
        assert summary['complete']
        for name, row in summary['regions'].items():
            assert row['numerics']['all_checks_passed']
            actual[name] = [row['temperature']['monthly_mae_C'], row['rain']['loss']]
    assert set(actual) == set(expected) and len(actual) == 97
    for name, values in actual.items():
        delta = [abs(a-b) for a,b in zip(values, expected[name][2:])]
        errors.append(dict(region=name, temperature_abs_delta=delta[0], rain_loss_abs_delta=delta[1]))
    passed = all(r['temperature_abs_delta']<=1e-7 and r['rain_loss_abs_delta']<=1e-8 for r in errors)
    sources = [Path(__file__), plan_path, params, archived, restoration, ROOT/'scripts/local_benchmark_protocol.py']
    write_json(reference/'restoration_review.json',dict(
        status='passed_archived_r58_scores_replayed' if passed else 'failed_archived_r58_score_comparison',
        passed=passed, regions=97, compared_scalar_scores=194,
        max_temperature_abs_delta=max(r['temperature_abs_delta'] for r in errors),
        max_rain_loss_abs_delta=max(r['rain_loss_abs_delta'] for r in errors), comparisons=errors,
        sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        atlas_changed=False, new_calibration=False))
    assert passed, 'Restored reference differs; diagnose before any candidate search'
    print('All194 adopted r58 scalar scores replay within declared precision.', flush=True)


if __name__ == '__main__':main()
