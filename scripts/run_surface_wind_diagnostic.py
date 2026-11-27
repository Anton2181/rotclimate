"""Six fixed controls/interventions on a private, unchanged physical model."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import argparse
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
from padding_budget_capture import exact, pending, equation_check
from surface_wind_forcing import at_day, project_monthly

PLAN = ROOT / 'calibration/surface_wind_diagnostic_20261127/plan.json'
OUT = ROOT / 'output/surface_wind_diagnostic_20261127'
MODEL = OUT / 'model'


def check(plan):
    for section in ['model_sources_sha256', 'execution_sources_sha256', 'inputs_sha256']:
        for name, digest in plan[section].items():
            assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['private_files_sha256'].items():
        f = MODEL / name
        assert not f.is_symlink() and f.stat().st_nlink == 1 and file_hash(f) == digest, name
    for name, version in plan['libraries'].items():
        assert importlib.metadata.version(name) == version, name
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        assert os.environ.get(name) == '1', name
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 10


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    plan = json.loads(PLAN.read_text())
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    assert len(plan['cases']) == plan['maximum_diagnostic_integrations'] == 6
    assert [s['arm'] for s in plan['cases']] == ['model'] * 3 + ['observed'] * 3
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (OUT / 'failure.json').exists(), 'Preserve failure; no automatic retries'
    if not args.run:
        assert not (OUT / 'preparation.json').exists()
        assert not list(OUT.glob('*/attempt.json'))
        for name, digest in plan['private_files_sha256'].items():
            origin = ROOT if name in plan['model_sources_sha256'] or name in plan['helper_sources_sha256'] else ROOT / plan['cache_origin']
            source, dest = origin / name, MODEL / name
            assert file_hash(source) == digest
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
        (OUT / '.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')
    else:
        assert not (OUT / 'results.json').exists(), 'Preserve completed study'
    check(plan)
    assert not any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0] = [str(MODEL), str(MODEL / 'scripts'), str(ROOT)]
    from rotclimate import earth
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    from rotclimate.koppen import monthly_stats
    from circulation_reference import projection_jacobian, geographic_wind
    from circulation_components import bilinear_monthly
    assert Path(earth.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    earth.REGIONS.update(json.loads((ROOT / plan['region_specs']).read_text()))
    base = Params.from_json(ROOT / plan['params'])
    if not args.run:
        with np.load(ROOT / plan['surface_reference']) as z:
            reference = dict(z)
        forcing_hashes = {}
        for spec in plan['cases'][:3]:
            case = earth.region_case(spec['region'], 56., 1100.)
            assert case_hash(case) == spec['case_identity']
            center = earth.REGIONS[spec['region']]
            assert center['lat0'] > 0
            geometry = projection_jacobian(case.grid.lat, case.lon, center['lat0'], center['lon0'])
            east, north = [bilinear_monthly(reference[k], case.grid.lat, case.lon) for k in ['u', 'v']]
            wind = project_monthly(east, north, geometry)
            restored = geographic_wind(wind[:, 0], wind[:, 1], geometry)
            np.testing.assert_allclose(restored, [east, north], atol=2e-12, rtol=1e-13)
            f = OUT / ('forcing_' + spec['region'] + '.npz')
            assert not f.exists()
            np.savez_compressed(f, wind=wind, east=east, north=north,
                latitude=case.grid.lat, longitude=case.lon, jacobian=np.stack(geometry))
            forcing_hashes[f.name] = file_hash(f)
        check(plan)
        freeze(OUT / 'preparation.json', dict(plan_sha256=file_hash(PLAN),
            private_declared_regular_files=len(plan['private_files_sha256']),
            model_source_changes=False, integrations=0, forcing_sha256=forcing_hashes))
        print('Prepared three projected surface-wind packets; zero integrations', flush=True)
        return
    preparation = json.loads((OUT / 'preparation.json').read_text())
    assert preparation['plan_sha256'] == file_hash(PLAN)
    for name, digest in preparation['forcing_sha256'].items():
        assert file_hash(OUT / name) == digest
    freeze(OUT / 'protocol.json', dict(plan_sha256=file_hash(PLAN),
        preparation_sha256=file_hash(OUT / 'preparation.json'), execution_sources_sha256=plan['execution_sources_sha256']))
    rows = []
    for spec in plan['cases']:
        check(plan)
        folder = OUT / spec['name']
        folder.mkdir(parents=True, exist_ok=True)
        if not pending(folder):
            rows.append(json.loads((folder / 'result.json').read_text()))
            continue
        with np.load(ROOT / spec['reference_capture']) as z:
            reference = dict(z)
        case = earth.region_case(spec['region'], 56., 1100.)
        assert case_hash(case) == spec['case_identity']
        p = earth.earth_params(base, case)
        assert not p.retrograde and p.north_bearing == 0 and p.wind_source == 'model' and p.sst_source == 'model'
        assert p.heat_land_friction == p.water_land_friction == 0
        if spec['arm'] == 'observed':
            p = replace(p, wind_source='observed')
            packet = OUT / ('forcing_' + spec['region'] + '.npz')
            assert file_hash(packet) == preparation['forcing_sha256'][packet.name]
            with np.load(packet) as z:
                exact(z['latitude'], case.grid.lat)
                exact(z['longitude'], case.lon)
                case.grid.obs_wind = z['wind'].copy()
            case.grid.obs_wind.flags.writeable = False
            forcing_bytes = case.grid.obs_wind.tobytes()
        freeze(folder / 'attempt.json', dict(spec=spec, params=asdict(p),
            protocol_sha256=file_hash(OUT / 'protocol.json')))
        row = dict(name=spec['name'], region=spec['region'], arm=spec['arm'], case_identity=spec['case_identity'])
        try:
            m = ClimateModel(p, grid=case.grid)
            ii, jj = reference['rows'], reference['cols']
            m.trace_cells = (ii, jj)
            def progress(completed, total):
                write_json(OUT / 'status.json', dict(stage='integrating', name=spec['name'],
                    completed_steps=completed, total_steps=total, utc=datetime.now(timezone.utc).isoformat()))
            result = m.run(diagnose_moisture=True, progress=progress)
            assert result.numerics['all_checks_passed']
            stats = monthly_stats(result.T, result.P, result.days, p.year_days,
                                  summer_solstice=p.winter_solstice_day + p.year_days / 2)
            fields = dict(T=stats['Tm'][:, ii, jj], P=np.maximum(stats['Pm'][:, ii, jj], 0))
            for key in ['E', 'W', 'u', 'v']:
                stats = monthly_stats(getattr(result, key), getattr(result, key), result.days, p.year_days)
                fields[key] = stats['Pm' if key == 'E' else 'Tm'][:, ii, jj]
            fields['days'] = result.days
            trace = sorted(m.trace, key=lambda r:r['day'])
            np.testing.assert_array_equal([r['day'] for r in trace], result.days)
            for key in ['gain', 'sinkd', 'W', 'P', 'u', 'v', 'moisture_u', 'moisture_v', 'T', 'E', 'SST']:
                fields['step_' + key] = np.stack([r[key] for r in trace])
            sl = case.grid.map_slice()
            budget = {k:v[:, ii - sl[0].start, jj - sl[1].start] for k, v in result.moisture_budget.items()}
            scaled = equation_check(budget, fields['step_P'].astype(np.float32).astype(float), p.moisture_residual_tol)
            fields.update({'budget__' + k:v for k, v in budget.items()})
            if spec['arm'] == 'model':
                for key, value in fields.items():
                    if key in reference:
                        exact(value, reference[key])
            else:
                assert case.grid.obs_wind.tobytes() == forcing_bytes
                expected = np.stack([at_day(case.grid.obs_wind, d)[:, ii, jj] for d in result.days])
                for axis, key in enumerate(['u', 'v']):
                    exact(fields['step_' + key], expected[:, axis])
                    exact(fields['step_moisture_' + key], expected[:, axis])
            assert case_hash(case) == spec['case_identity']
            fields.update({k:reference[k] for k in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P']})
            np.savez_compressed(folder / 'capture.npz', **fields)
            row.update(status='passed', baseline_byte_exact=spec['arm'] == 'model',
                actual_observed_wind_verified=spec['arm'] == 'observed',
                capture_sha256=file_hash(folder / 'capture.npz'), numerical_certificate=result.numerics,
                residual_tolerance=p.moisture_residual_tol, max_scaled_exported_residual=scaled)
        except Exception as error:
            row.update(status='failed', error=repr(error), automatic_retry=False)
            write_json(folder / 'result.json', row)
            write_json(OUT / 'failure.json', row)
            raise
        write_json(folder / 'result.json', row)
        rows.append(row)
        print(spec['name'], 'passed original numerical criteria and input checks', flush=True)
    check(plan)
    write_json(OUT / 'results.json', dict(status='completed_six_fixed_surface_wind_diagnostics', rows=rows,
        protocol_sha256=file_hash(OUT / 'protocol.json'), climate_adopted=False, atlas_changed=False))
    subprocess.run([str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/review_surface_wind_diagnostic.py')], cwd=ROOT, check=True)
    write_json(OUT / 'status.json', dict(stage='ready_for_agent_figure_and_findings_review', completed_cases=6))


if __name__ == '__main__':
    main()
