"""Prepare or execute six fixed private diagnostic replays; never tune physics."""
import argparse
from datetime import datetime, timezone
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json

PLAN = ROOT / 'calibration/padding_budget_capture_20261127/plan.json'
OUT = ROOT / 'output/padding_budget_capture_20261127'
MODEL = OUT / 'model'
COMPONENTS = ['evaporation', 'marine_exchange', 'column_drying', 'convergence_import',
              'advection', 'diffusion', 'storm_exchange']


def pending(folder):
    if (folder / 'result.json').exists():
        row = json.loads((folder / 'result.json').read_text())
        if row['status'] != 'passed':
            raise RuntimeError('Preserve failed replay; no automatic retry')
        assert file_hash(folder / 'capture.npz') == row['capture_sha256']
        return False
    if (folder / 'attempt.json').exists():
        raise RuntimeError('Interrupted replay requires recorded recovery, not retry')
    return True


def exact(actual, expected):
    assert actual.dtype == expected.dtype and actual.shape == expected.shape
    assert actual.tobytes() == expected.tobytes(), 'Physical reproduction changed'


def equation_check(budget, rain, tolerance):
    assert np.isfinite(rain).all() and (rain >= 0).all()
    assert all(np.isfinite(budget[k]).all() for k in COMPONENTS + ['residual'])
    net = sum(budget[k].astype(float) for k in COMPONENTS)
    source = sum(budget[k].astype(float) for k in COMPONENTS[:4])
    rounding = 8 * np.finfo(np.float32).eps * (sum(np.abs(budget[k].astype(float)) for k in COMPONENTS) + np.abs(rain))
    assert np.all(np.abs(net - rain - budget['residual']) <= rounding + 1e-12), 'Exported equation incomplete'
    scale = np.maximum(rain + np.abs(source), .1)
    assert np.all(np.abs(budget['residual']) <= tolerance * scale + rounding + 1e-12), 'Strict local equation residual failed'
    return float(np.max(np.abs(budget['residual']) / scale))


def check(plan, protocol):
    assert file_hash(PLAN) == protocol['plan_sha256']
    for name, digest in protocol['execution_sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['inputs_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['unchanged_main_model_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in {**plan['model_sources_sha256'], **plan['cache_seed_sha256'], **plan['helper_sources_sha256']}.items():
        f = MODEL / name
        assert not f.is_symlink() and f.stat().st_nlink == 1 and file_hash(f) == digest, name
    for name, version in plan['libraries'].items():
        assert importlib.metadata.version(name) == version
    for key in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        assert os.environ.get(key) == '1', key
    assert os.getpriority(os.PRIO_PROCESS, 0) >= plan['policy']['minimum_nice']


def prepare(plan):
    origins = [(plan['model_sources_sha256'], ROOT / plan['patched_source_origin']),
               (plan['cache_seed_sha256'], ROOT / plan['reference_study'] / 'model'),
               (plan['helper_sources_sha256'], ROOT / plan['reference_study'] / 'model')]
    for mapping, origin in origins:
        for name, digest in mapping.items():
            source, target = origin / name, MODEL / name
            assert file_hash(source) == digest
            assert not source.is_symlink() and source.stat().st_nlink == 1
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            assert not target.is_symlink() and target.stat().st_nlink == 1 and file_hash(target) == digest
    (OUT / '.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    assert len(plan['cases']) == plan['maximum_additional_diagnostic_integrations'] == 6
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes(), 'Commit prospective plan before preparation/execution'
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    protocol = dict(plan_sha256=file_hash(PLAN), execution_sources_sha256={
        str(f.relative_to(ROOT)):file_hash(f) for f in [Path(__file__), ROOT / 'scripts/review_padding_budget.py', ROOT / 'scripts/local_benchmark_protocol.py']})
    freeze(OUT / 'protocol.json', protocol)
    prepare(plan)
    check(plan, protocol)
    freeze(OUT / 'preparation.json', dict(protocol_sha256=file_hash(OUT / 'protocol.json'),
        private_regular_files=sum(1 for f in MODEL.rglob('*') if f.is_file()),
        diagnostic_source_changes=['rotclimate/model.py', 'rotclimate/transport.py'],
        diagnostic_patch_only=True, main_source_unchanged=True))
    if not args.run:
        print('Private six-replay packet prepared; no integrations')
        return
    assert not (OUT / 'results.json').exists(), 'Preserve completed experiment'
    assert not any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0] = [str(MODEL), str(MODEL / 'scripts')]
    from rotclimate import earth
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    from rotclimate.koppen import monthly_stats
    assert Path(earth.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    for name in ['calibration/local_accuracy_20261023/regions_dev12.json', 'calibration/sealed_20261123S18/regions.json', 'calibration/sealed_20261124U18/regions.json']:
        earth.REGIONS.update(json.loads((ROOT / name).read_text()))
    params = Params.from_json(ROOT / 'calibration/local_accuracy_20261023/r58_params.json')
    rows = []
    for spec in plan['cases']:
        check(plan, protocol)
        folder = OUT / spec['region'] / f"pad_{spec['pad_km']:g}"
        folder.mkdir(parents=True, exist_ok=True)
        if not pending(folder):
            rows.append(json.loads((folder / 'result.json').read_text()))
            continue
        old = ROOT / plan['reference_study'] / spec['region'] / folder.name
        assert file_hash(old / 'fields.npz') == spec['fields_sha256']
        assert file_hash(old / 'footprint.npz') == spec['footprint_sha256']
        with np.load(old / 'fields.npz') as z:
            reference = dict(z)
        case = earth.region_case(spec['region'], plan['cell_km'], spec['pad_km'])
        assert case_hash(case) == spec['case_identity']
        freeze(folder / 'attempt.json', dict(**spec, protocol_sha256=file_hash(OUT / 'protocol.json')))
        row = dict(region=spec['region'], pad_km=spec['pad_km'], case_identity=spec['case_identity'])
        try:
            model = ClimateModel(earth.earth_params(params, case), grid=case.grid)
            ii, jj = reference['rows'], reference['cols']
            model.trace_cells = (ii, jj)
            def progress(completed, total):
                write_json(OUT / 'status.json', dict(stage='integrating', region=spec['region'], pad_km=spec['pad_km'], completed_steps=completed, total_steps=total, utc=datetime.now(timezone.utc).isoformat()))
            result = model.run(diagnose_moisture=True, progress=progress)
            assert result.numerics['all_checks_passed']
            p = result.params
            m = monthly_stats(result.T, result.P, result.days, p.year_days,
                              summer_solstice=p.winter_solstice_day + p.year_days / 2)
            fields = dict(T=m['Tm'][:, ii, jj], P=np.maximum(m['Pm'][:, ii, jj], 0))
            for name in ['E', 'W', 'u', 'v']:
                m = monthly_stats(getattr(result, name), getattr(result, name), result.days, p.year_days)
                fields[name] = m['Pm' if name == 'E' else 'Tm'][:, ii, jj]
            fields['days'] = result.days
            trace = sorted(model.trace, key=lambda r:r['day'])
            np.testing.assert_array_equal([r['day'] for r in trace], result.days)
            for name in ['gain', 'sinkd', 'W', 'P']:
                fields['step_' + name] = np.stack([r[name] for r in trace])
            for name, actual in fields.items():
                exact(actual, reference[name])
            sl = case.grid.map_slice()
            rr, cc = ii - sl[0].start, jj - sl[1].start
            budget = {k:v[:, rr, cc] for k, v in result.moisture_budget.items()}
            rain = fields['step_P'].astype(np.float32).astype(float)
            scaled = equation_check(budget, rain, p.moisture_residual_tol)
            fields.update({'budget__' + k:v for k, v in budget.items()})
            np.savez_compressed(folder / 'capture.npz', **fields)
            row.update(status='passed', capture_sha256=file_hash(folder / 'capture.npz'),
                physical_fields_byte_exact=True, numerical_certificate=result.numerics,
                max_scaled_exported_residual=scaled, residual_tolerance=p.moisture_residual_tol)
        except Exception as error:
            row.update(status='failed', error=repr(error), automatic_retry=False)
            write_json(folder / 'result.json', row)
            raise
        write_json(folder / 'result.json', row)
        rows.append(row)
        print(spec['region'], spec['pad_km'], 'passed exact physical replay and equation checks', flush=True)
    check(plan, protocol)
    write_json(OUT / 'results.json', dict(status='completed_six_fixed_diagnostic_replays', rows=rows,
        protocol_sha256=file_hash(OUT / 'protocol.json'), climate_adopted=False, atlas_changed=False))
    subprocess.run([str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/review_padding_budget.py')], cwd=ROOT, check=True)
    write_json(OUT / 'status.json', dict(stage='ready_for_agent_findings_review', completed_cases=len(rows)))


if __name__ == '__main__':
    main()
