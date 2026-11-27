"""Six fixed private legacy/cap comparisons; no fitting, adoption or retries."""
from datetime import datetime, timezone
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from padding_budget_capture import equation_check, exact, pending
from review_padding_sensitivity import summarize_state

PLAN = ROOT / 'calibration/marine_target_cap_20261127/plan.json'
OUT = ROOT / 'output/marine_target_cap_20261127'
MODEL = OUT / 'model'


def check(plan, protocol):
    assert file_hash(PLAN) == protocol['plan_sha256']
    for section in ['main_model_sources_sha256', 'inputs_sha256', 'execution_sources_sha256']:
        for name, digest in plan[section].items():
            assert file_hash(ROOT / name) == digest, name
    for name, digest in plan['private_files_sha256'].items():
        path = MODEL / name
        assert not path.is_symlink() and path.stat().st_nlink == 1 and file_hash(path) == digest, name
    assert file_hash(OUT / 'preparation.json') == protocol['preparation_sha256']
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
    assert len(plan['cases']) == plan['maximum_integrations'] == 6
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (OUT / 'failure.json').exists(), 'Preserve closed scientific failure'
    prep = json.loads((OUT / 'preparation.json').read_text())
    assert prep['plan_sha256'] == file_hash(PLAN)
    assert prep['preparer_sha256'] == file_hash(ROOT / 'scripts/prepare_marine_target_cap.py')
    protocol = dict(plan_sha256=file_hash(PLAN), preparation_sha256=file_hash(OUT / 'preparation.json'),
                    execution_sources_sha256=plan['execution_sources_sha256'])
    freeze(OUT / 'protocol.json', protocol)
    check(plan, protocol)
    if not args.run:
        print('Private cap packet ready; no integrations')
        return
    assert not (OUT / 'results.json').exists(), 'Preserve completed study'
    assert not any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0] = [str(MODEL), str(MODEL / 'scripts')]
    from rotclimate import earth, marine_inflow
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    from rotclimate.koppen import monthly_stats
    assert Path(earth.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    for name in plan['region_specs']:
        earth.REGIONS.update(json.loads((ROOT / name).read_text()))
    base = Params.from_json(ROOT / plan['params'])
    assert base.ocean_sink == 1. and not base.inflow_source_cap
    rows = []
    for spec in plan['cases']:
        check(plan, protocol)
        folder = OUT / spec['name']
        folder.mkdir(parents=True, exist_ok=True)
        if not pending(folder):
            rows.append(json.loads((folder / 'result.json').read_text()))
            continue
        if spec['arm'] == 'cap':
            assert len(rows) >= 3 and all(r['status'] == 'passed' and r['legacy_control_exact'] for r in rows[:3])
        assert file_hash(ROOT / spec['reference_fields']) == spec['reference_fields_sha256']
        assert file_hash(ROOT / spec['reference_budget']) == spec['reference_budget_sha256']
        with np.load(ROOT / spec['reference_fields']) as z:
            reference = dict(z)
        case = earth.region_case(spec['region'], plan['cell_km'], plan['pad_km'])
        assert case_hash(case) == spec['case_identity']
        freeze(folder / 'attempt.json', dict(spec=spec, protocol_sha256=file_hash(OUT / 'protocol.json')))
        row = dict(name=spec['name'], region=spec['region'], arm=spec['arm'])
        original = marine_inflow.capped_marine_target
        try:
            params = earth.earth_params(base.replace(**plan['arms'][spec['arm']]), case)
            model = ClimateModel(params, grid=case.grid)
            ii, jj = reference['rows'], reference['cols']
            model.trace_cells = (ii, jj)
            target_trace = []
            def observe(target, saturation, ocean, nearest, rh, rate):
                bounded, returned_rate = original(target, saturation, ocean, nearest, rh, rate)
                assert ocean.any(), 'All three declared cases must contain real sea'
                target_trace.append(dict(legacy=rh * saturation[ii, jj], source=target[nearest][ii, jj].copy(),
                    bounded=bounded[ii, jj].copy(), rate=returned_rate[ii, jj].copy() * 86400))
                return bounded, returned_rate
            marine_inflow.capped_marine_target = observe
            def progress(completed, total):
                write_json(OUT / 'status.json', dict(stage='integrating', name=spec['name'],
                    completed_steps=completed, total_steps=total, utc=datetime.now(timezone.utc).isoformat()))
            result = model.run(diagnose_moisture=True, progress=progress)
            assert result.numerics['all_checks_passed']
            p = result.params
            stats = monthly_stats(result.T, result.P, result.days, p.year_days,
                                  summer_solstice=p.winter_solstice_day + p.year_days / 2)
            fields = dict(T=stats['Tm'][:, ii, jj], P=np.maximum(stats['Pm'][:, ii, jj], 0))
            for key in ['E', 'W', 'u', 'v']:
                stats = monthly_stats(getattr(result, key), getattr(result, key), result.days, p.year_days)
                fields[key] = stats['Pm' if key == 'E' else 'Tm'][:, ii, jj]
            fields.update({k:reference[k] for k in ['rows', 'cols', 'lat', 'lon', 'obs_T', 'obs_P']})
            fields['days'] = result.days
            trace = sorted(model.trace, key=lambda r:r['day'])
            np.testing.assert_array_equal([r['day'] for r in trace], result.days)
            for key in ['gain', 'sinkd', 'W', 'P', 'Ws']:
                fields['step_' + key] = np.stack([r[key] for r in trace])
            sl = case.grid.map_slice()
            budget = {k:v[:, ii - sl[0].start, jj - sl[1].start] for k, v in result.moisture_budget.items()}
            scaled = equation_check(budget, fields['step_P'].astype(np.float32).astype(float), p.moisture_residual_tol)
            if spec['arm'] == 'legacy':
                assert not target_trace
                for key in ['T', 'P', 'E', 'W', 'u', 'v', 'days', 'step_gain', 'step_sinkd', 'step_W', 'step_P']:
                    exact(fields[key], reference[key])
                with np.load(ROOT / spec['reference_budget']) as old:
                    for key, value in budget.items():
                        exact(value, old['budget__' + key])
            else:
                assert len(target_trace) >= len(trace)
                for key in ['legacy', 'source', 'bounded', 'rate']:
                    fields['target__' + key] = np.stack([r[key] for r in target_trace[-len(trace):]])
                np.testing.assert_array_equal(fields['target__bounded'], np.minimum(fields['target__legacy'], fields['target__source']))
                expected = fields['target__rate'] * (fields['target__bounded'] - fields['step_W'])
                assert np.all(np.abs(expected - budget['marine_exchange']) <=
                    4 * np.finfo(np.float32).eps * np.maximum(np.abs(expected), 1.))
            fields.update({'budget__' + k:v for k, v in budget.items()})
            summary = summarize_state(fields)
            np.savez_compressed(folder / 'fields.npz', **fields)
            row.update(status='passed', legacy_control_exact=spec['arm'] == 'legacy',
                fields_sha256=file_hash(folder / 'fields.npz'), metrics=summary,
                numerical_certificate=result.numerics, max_scaled_residual=scaled,
                residual_tolerance=p.moisture_residual_tol)
        except Exception as error:
            row.update(status='failed', error=repr(error), automatic_retry=False)
            write_json(folder / 'result.json', row)
            write_json(OUT / 'failure.json', row)
            write_json(OUT / 'status.json', dict(stage='closed_failed_case_no_retry', name=spec['name']))
            raise
        finally:
            marine_inflow.capped_marine_target = original
        write_json(folder / 'result.json', row)
        rows.append(row)
        print(spec['name'], 'passed', row['metrics'], flush=True)
    check(plan, protocol)
    write_json(OUT / 'results.json', dict(status='completed_fixed_six_case_cap_diagnostic', rows=rows,
        protocol_sha256=file_hash(OUT / 'protocol.json'), climate_adopted=False, atlas_changed=False))
    subprocess.run([str(ROOT / '.venv/bin/python'), '-I', str(ROOT / 'scripts/review_marine_target_cap.py')], cwd=ROOT, check=True)
    write_json(OUT / 'status.json', dict(stage='ready_for_agent_figure_and_findings_review', completed_cases=6))


if __name__ == '__main__':
    main()
