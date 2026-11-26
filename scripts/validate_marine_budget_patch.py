"""Bounded toy comparisons in unpatched/patched private physical modules."""
import argparse
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, freeze, write_json

PLAN = ROOT / 'calibration/marine_budget_export_patch_20261126/plan.json'
OUT = ROOT / 'output/marine_budget_export_patch_20261126'
NAMES = ['concentration', 'flux', 'reservoir']
PHYSICAL = ['T', 'Tsl', 'P', 'W', 'u', 'v', 'E']


def check_sources(plan, prep):
    assert prep['plan_sha256'] == file_hash(PLAN)
    assert prep['preparer_sha256'] == file_hash(ROOT / 'scripts/prepare_marine_budget_patch.py')
    assert prep['patch_sha256'] == file_hash(PLAN.parent / 'marine_budget.patch')
    for name, digest in prep['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
        assert file_hash(OUT / 'baseline' / name) == digest, name
        if name not in plan['base_model_sources_sha256']:
            assert file_hash(OUT / 'patched' / name) == digest, name
    for name, digest in prep['patched_sources_sha256'].items():
        assert file_hash(OUT / 'patched' / name) == digest, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version', choices=['baseline', 'patched'])
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    prep = json.loads((OUT / 'preparation.json').read_text())
    check_sources(plan, prep)
    freeze(OUT / 'validation_protocol.json', dict(plan_sha256=file_hash(PLAN),
        preparation_sha256=file_hash(OUT / 'preparation.json'), validator_sha256=file_hash(Path(__file__))))
    private = OUT / args.version
    assert not any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0] = [str(private), str(private / 'tests')]
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    assert Path(earth.__file__).resolve().is_relative_to(private.resolve())
    records = []
    for name in NAMES:
        overrides = dict(plan['toy_overrides'])
        if name == 'concentration':
            overrides.update(subsidence_drying=.1, flux_convergence=.3)
        else:
            overrides.update(moisture_transport_form='flux', flux_convergence=0., eddy_moisture_scheme='conservative')
            if name == 'reservoir':
                overrides.update(moisture_mass_balance=True, moisture_two_layer=True, moisture_mass_tracer=True,
                                 moisture_reservoirs=True, moisture_relaxation=.1, picard_iters=1024)
        diagnostics = [True] if args.version == 'baseline' else [True, False]
        for diagnose in diagnostics:
            label = name + ('_diagnosed' if diagnose else '_ordinary')
            folder = OUT / ('validation_' + args.version) / label
            folder.mkdir(parents=True, exist_ok=True)
            receipt = folder / 'result.json'
            if receipt.exists():
                record = json.loads(receipt.read_text())
                if record['status'] == 'passed':
                    assert record['fields_sha256'] == file_hash(folder / 'fields.npz')
                records.append(record)
                continue
            assert not (folder / 'attempt.json').exists(), 'Do not repeat interrupted toy integration'
            freeze(folder / 'attempt.json', dict(name=name, version=args.version, diagnose=diagnose,
                overrides=overrides, validator_sha256=file_hash(Path(__file__))))
            record = dict(name=name, version=args.version, diagnose=diagnose)
            try:
                case = _toy_case()
                p = earth.earth_params(strict_params().replace(**overrides), case)
                result = ClimateModel(p, grid=case.grid).run(diagnose_moisture=diagnose)
                numerical = result.numerics
                assert numerical['linear_unconverged'] == numerical['temperature_unconverged'] == numerical['moisture_unconverged'] == 0
                assert numerical['moisture_checked']
                arrays = {key:getattr(result, key) for key in PHYSICAL}
                if result.layer_water is not None:
                    arrays['layer_water'] = result.layer_water
                if diagnose:
                    arrays.update({'budget__' + key:value for key, value in result.moisture_budget.items()})
                record['numerics'] = numerical
                if args.version == 'patched':
                    baseline = OUT / 'validation_baseline' / (name + '_diagnosed') / 'fields.npz'
                    with np.load(baseline) as old:
                        for key in PHYSICAL + (['layer_water'] if 'layer_water' in arrays else []):
                            np.testing.assert_array_equal(arrays[key], old[key])
                    assert numerical['all_checks_passed'], numerical
                    if not diagnose:
                        with np.load(OUT / 'validation_patched' / (name + '_diagnosed') / 'fields.npz') as observed:
                            for key in PHYSICAL:
                                np.testing.assert_array_equal(arrays[key], observed[key])
                    else:
                        terms = result.moisture_budget
                        components = ['evaporation', 'marine_exchange', 'column_drying', 'convergence_import',
                                      'advection', 'diffusion', 'storm_exchange']
                        net = sum(terms[key].astype(float) for key in components)
                        rain = result.P[(slice(None),) + case.grid.map_slice()].astype(float)
                        rounding = 8 * np.finfo(np.float32).eps * (sum(np.abs(terms[key].astype(float)) for key in components) + np.abs(rain))
                        assert np.all(np.abs(net - rain - terms['residual']) <= rounding + 1e-12)
                        source = sum(terms[key].astype(float) for key in components[:4])
                        scale = np.maximum(rain + np.abs(source), .1)
                        assert np.all(np.abs(terms['residual']) <= p.moisture_residual_tol * scale + rounding + 1e-12)
                        if name == 'reservoir':
                            assert not terms['marine_exchange'].any(), 'Reservoir E already includes surface relaxation'
                        else:
                            assert np.max(np.abs(terms['marine_exchange'])) > .01, 'Exercise active land marine relaxation'
                        record['max_scaled_exported_residual'] = float(np.max(np.abs(terms['residual']) / scale))
                        record['marine_min_mm_day'] = float(terms['marine_exchange'].min())
                        record['marine_max_mm_day'] = float(terms['marine_exchange'].max())
                np.savez_compressed(folder / 'fields.npz', **arrays)
                record.update(status='passed', fields_sha256=file_hash(folder / 'fields.npz'))
            except Exception as error:
                record.update(status='failed', error=repr(error))
                write_json(receipt, record)
                raise
            write_json(receipt, record)
            records.append(record)
            print(args.version, label, 'checked', flush=True)
    check_sources(plan, prep)
    write_json(OUT / ('validation_' + args.version + '.json'), dict(status='passed_fixed_private_toy_checks',
        records=records, validator_sha256=file_hash(Path(__file__)), earth_region_integrations=0,
        physical_climate_improvement_claim=False, main_patch_applied=False))


if __name__ == '__main__':
    main()
