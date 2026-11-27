"""Four exact private diagnostic replays; observations never enter the solve."""
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
from padding_budget_capture import exact, pending

PLAN = ROOT / 'calibration/circulation_components_20261127/plan.json'
OUT = ROOT / 'output/circulation_components_20261127'
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
    assert len(plan['cases']) == plan['maximum_diagnostic_integrations'] == 4
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (OUT / 'failure.json').exists(), 'Preserve failure; no automatic retries'
    if not args.run:
        assert not list(OUT.glob('*/attempt.json'))
        for name, digest in plan['private_files_sha256'].items():
            origin = ROOT if name in plan['model_sources_sha256'] or name in plan['helper_sources_sha256'] else ROOT / plan['cache_origin']
            source, dest = origin / name, MODEL / name
            assert file_hash(source) == digest
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)
        (OUT / '.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')
        check(plan)
        freeze(OUT / 'preparation.json', dict(plan_sha256=file_hash(PLAN),
            private_declared_regular_files=len(plan['private_files_sha256']),
            model_source_changes=False, observational_forcing=False, integrations=0))
        print('Private component capture prepared; no climate integrations')
        return
    assert not (OUT / 'results.json').exists(), 'Preserve completed study'
    check(plan)
    assert json.loads((OUT / 'preparation.json').read_text())['plan_sha256'] == file_hash(PLAN)
    freeze(OUT / 'protocol.json', dict(plan_sha256=file_hash(PLAN),
        preparation_sha256=file_hash(OUT / 'preparation.json'), execution_sources_sha256=plan['execution_sources_sha256']))
    assert not any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0] = [str(MODEL), str(MODEL / 'scripts')]
    from rotclimate import earth, model as physical
    from rotclimate.config import Params
    from rotclimate.koppen import monthly_stats
    assert Path(earth.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    earth.REGIONS.update(json.loads((ROOT / plan['region_specs']).read_text()))
    base = Params.from_json(ROOT / plan['params'])
    rows = []
    for spec in plan['cases']:
        check(plan)
        folder = OUT / spec['name']
        folder.mkdir(parents=True, exist_ok=True)
        if not pending(folder):
            rows.append(json.loads((folder / 'result.json').read_text()))
            continue
        assert file_hash(ROOT / spec['reference_fields']) == spec['reference_fields_sha256']
        assert file_hash(ROOT / spec['reference_budget']) == spec['reference_budget_sha256']
        with np.load(ROOT / spec['reference_fields']) as z:
            reference = dict(z)
        case = earth.region_case(spec['region'], 56., spec['pad_km'])
        assert case_hash(case) == spec['case_identity']
        p = earth.earth_params(base, case)
        assert not p.retrograde and p.north_bearing == 0 and p.wind_source == 'model' and p.sst_source == 'model'
        for name in ['wind_cap', 'heat_land_friction', 'water_land_friction', 'zonal_land_friction', 'subtropical_high', 'monsoon_heating', 'moisture_thermal_height_km', 'monsoon_westerly_floor']:
            assert getattr(p, name) == 0, name
        assert p.moisture_pressure_drag_ratio == 1 and not p.moisture_mass_balance
        assert p.slp_large > 0 and p.monsoon_pressure_hpa > 0 and p.monsoon_westerly > 0
        freeze(folder / 'attempt.json', dict(spec=spec, protocol_sha256=file_hash(OUT / 'protocol.json')))
        row = dict(name=spec['name'], region=spec['region'], pad_km=spec['pad_km'])
        try:
            m = physical.ClimateModel(p, grid=case.grid)
            ii, jj = reference['rows'], reference['cols']
            m.trace_cells = (ii, jj)
            latest, captured = {}, []
            zonal, pressure = m.zonal_wind, m.pressure_wind
            def observe_zonal(s):
                before = getattr(m, 'last_pres', None)
                before = None if before is None else before.copy()
                result = zonal(s)
                field = lambda a:np.broadcast_to(a, case.grid.land.shape)[ii, jj].copy()
                latest['zonal'] = dict(previous_pressure=before, season=float(s),
                    zonal_u=field(result[0]), zonal_v=field(result[1]),
                    phi_i=field(result[2]), phi_h=field(result[3]),
                    phi_i_full=np.broadcast_to(result[2], case.grid.land.shape).copy(),
                    phi_h_full=np.broadcast_to(result[3], case.grid.land.shape).copy())
                return result
            def observe_pressure(anomaly):
                result = pressure(anomaly)
                latest['pressure'] = dict(current_pressure=m.last_pres.copy(),
                    pressure_u=result[0][ii, jj].copy(), pressure_v=result[1][ii, jj].copy())
                return result
            m.zonal_wind, m.pressure_wind = observe_zonal, observe_pressure
            def progress(completed, total):
                if len(m.trace) > len(captured):
                    assert len(m.trace) == len(captured) + 1
                    assert latest['zonal']['previous_pressure'] is not None
                    captured.append(dict(**latest['zonal'], **latest['pressure']))
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
            assert len(captured) == len(trace)
            for key in ['gain', 'sinkd', 'W', 'P']:
                fields['step_' + key] = np.stack([r[key] for r in trace])
            for key in list(fields):
                exact(fields[key], reference[key])
            fields.update({k:reference[k] for k in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P']})
            for key in ['u', 'v', 'moisture_u', 'moisture_v']:
                fields['step_' + key] = np.stack([r[key] for r in trace])
            sl = case.grid.map_slice()
            with np.load(ROOT / spec['reference_budget']) as old:
                for key, value in result.moisture_budget.items():
                    value = value[:, ii - sl[0].start, jj - sl[1].start]
                    exact(value, old['budget__' + key])
                    fields['budget__' + key] = value
            for key in captured[0]:
                fields['diag__' + key] = np.stack([r[key] for r in captured])
            fields.update(grid_lat=m.lat.copy(), grid_geo_lat=case.grid.lat.copy(), grid_lon=case.lon.copy(),
                grid_land=case.grid.land.copy(), grid_bl_drag=np.broadcast_to(m.bl_drag, case.grid.land.shape).copy(),
                grid_drag=np.broadcast_to(m.drag, case.grid.land.shape).copy())
            np.savez_compressed(folder / 'capture.npz', **fields)
            row.update(status='passed', physical_and_budget_fields_byte_exact=True,
                capture_sha256=file_hash(folder / 'capture.npz'), numerical_certificate=result.numerics,
                constants=dict(omega=physical.OMEGA, rho=physical.RHO_AIR, dx_m=case.grid.dx_m,
                    monsoon_westerly=p.monsoon_westerly, monsoon_pressure_hpa=p.monsoon_pressure_hpa,
                    hadley_edge=p.hadley_edge, hadley_shift=p.hadley_shift, hadley_scale=m.hadley_scale),
                earth_frame=dict(retrograde=p.retrograde, north_bearing=p.north_bearing))
        except Exception as error:
            row.update(status='failed', error=repr(error), automatic_retry=False)
            write_json(folder / 'result.json', row)
            write_json(OUT / 'failure.json', row)
            raise
        write_json(folder / 'result.json', row)
        rows.append(row)
        print(spec['name'], 'passed exact physical/budget capture', flush=True)
    check(plan)
    write_json(OUT / 'results.json', dict(status='completed_four_fixed_component_captures', rows=rows,
        protocol_sha256=file_hash(OUT / 'protocol.json'), climate_adopted=False, atlas_changed=False))
    subprocess.run([str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/review_circulation_components.py')], cwd=ROOT, check=True)
    write_json(OUT / 'status.json', dict(stage='ready_for_agent_figure_and_findings_review', completed_cases=4))


if __name__ == '__main__':
    main()
