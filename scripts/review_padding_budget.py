"""Independently review six fixed diagnostic captures without model imports."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json

OUT = ROOT / 'output/padding_budget_capture_20261127'
PLAN = ROOT / 'calibration/padding_budget_capture_20261127/plan.json'
TERMS = ['evaporation', 'marine_exchange', 'column_drying', 'convergence_import',
         'advection', 'diffusion', 'storm_exchange']


def main():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    plan = json.loads(PLAN.read_text())
    protocol = json.loads((OUT / 'protocol.json').read_text())
    result = json.loads((OUT / 'results.json').read_text())
    assert file_hash(PLAN) == protocol['plan_sha256']
    assert file_hash(OUT / 'protocol.json') == result['protocol_sha256']
    for name, digest in protocol['execution_sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['inputs_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in {**plan['model_sources_sha256'], **plan['cache_seed_sha256'], **plan['helper_sources_sha256']}.items():
        assert file_hash(OUT / 'model' / name) == digest, name
    assert len(result['rows']) == len(plan['cases']) == 6
    assert [(r['region'], r['pad_km']) for r in result['rows']] == [(r['region'], r['pad_km']) for r in plan['cases']]
    statistics, files = [], {}
    for row, spec in zip(result['rows'], plan['cases'], strict=True):
        folder = OUT / row['region'] / f"pad_{row['pad_km']:g}"
        assert row == json.loads((folder / 'result.json').read_text())
        assert row['status'] == 'passed' and row['physical_fields_byte_exact']
        assert row['numerical_certificate']['all_checks_passed']
        assert row['residual_tolerance'] == .01
        assert file_hash(folder / 'capture.npz') == row['capture_sha256']
        attempt = json.loads((folder / 'attempt.json').read_text())
        assert attempt == dict(**spec, protocol_sha256=file_hash(OUT / 'protocol.json'))
        reference = ROOT / plan['reference_study'] / row['region'] / folder.name / 'fields.npz'
        assert file_hash(reference) == spec['fields_sha256']
        with np.load(reference) as old, np.load(folder / 'capture.npz') as z:
            for name in ['T', 'P', 'E', 'W', 'u', 'v', 'days', 'step_gain', 'step_sinkd', 'step_W', 'step_P']:
                assert z[name].shape == old[name].shape and z[name].dtype == old[name].dtype
                assert z[name].tobytes() == old[name].tobytes(), name
            terms = [z['budget__' + name].astype(float) for name in TERMS]
            rain = z['step_P'].astype(np.float32).astype(float)
            residual = z['budget__residual'].astype(float)
            assert all(t.shape == rain.shape and np.isfinite(t).all() for t in terms + [residual])
            assert (rain >= 0).all() and np.isfinite(rain).all()
            nt = len(z['days'])
            np.testing.assert_allclose(z['days'], (np.arange(nt) + .5) * 365 / nt, atol=1e-10, rtol=0)
            reconstructed = np.zeros_like(rain)
            absolute = np.abs(rain)
            for term in terms:
                reconstructed += term
                absolute += np.abs(term)
            rounding = 8 * np.finfo(np.float32).eps * absolute
            assert np.all(np.abs(reconstructed - rain - residual) <= rounding + 1e-12)
            net_source = terms[0] + terms[1] + terms[2] + terms[3]
            scale = np.maximum(rain + np.abs(net_source), .1)
            assert np.all(np.abs(residual) <= .01 * scale + rounding + 1e-12)
            annual = {name:float(term.mean() * 365) for name, term in zip(TERMS, terms, strict=True)}
            annual.update(rain=float(rain.mean() * 365), residual=float(residual.mean() * 365))
            for name, expected in [('convergence_import', z['step_gain'] * z['step_W']),
                                   ('column_drying', -z['step_sinkd'] * z['step_W'])]:
                got = z['budget__' + name].astype(float)
                assert np.all(np.abs(got - expected) <= 2 * np.finfo(np.float32).eps * np.maximum(np.abs(expected), 1.))
            statistics.append(dict(region=row['region'], pad_km=row['pad_km'], annual_mm=annual,
                mean_absolute_residual_mm_day=float(np.abs(residual).mean()),
                rms_residual_mm_day=float(np.sqrt(np.mean(residual ** 2))),
                max_absolute_residual_mm_day=float(np.abs(residual).max()),
                max_scaled_residual=float(np.max(np.abs(residual) / scale))))
        for name in ['attempt.json', 'result.json', 'capture.npz']:
            f = folder / name
            files[str(f.relative_to(OUT))] = file_hash(f)
    differences = []
    for region in dict.fromkeys(s['region'] for s in plan['cases']):
        base, other = [r for r in statistics if r['region'] == region]
        assert [base['pad_km'], other['pad_km']] == [1100., 4012.]
        differences.append(dict(region=region, from_pad_km=1100., to_pad_km=4012.,
            annual_changes_mm={k:other['annual_mm'][k] - v for k, v in base['annual_mm'].items()}))
    write_json(OUT / 'review.json', dict(status='reviewed_exact_diagnostic_replays_not_climate_qualification',
        protocol_sha256=file_hash(OUT / 'protocol.json'), results_sha256=file_hash(OUT / 'results.json'),
        files_sha256=files, statistics=statistics, endpoint_differences=differences,
        interpretation='Signed local concentration equation terms, not conservative planetary closure, boundary flux or tagged moisture attribution.',
        climate_adopted=False, atlas_changed=False))
    print('Independently reviewed six byte-exact physical replays and complete exported local equations.')


if __name__ == '__main__':
    main()
