"""Two exact default-off controls, then one fixed 97-region solar-bound candidate."""
from dataclasses import asdict
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
sys.path[:0] = [str(ROOT/'scripts'), str(ROOT)]
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from experiments.wet_energy_budget import patched_model
PLAN = ROOT/'calibration/wet_energy_budget_20261127/plan.json'
OUT = ROOT/'output/wet_energy_budget_20261127'
MODEL = OUT/'model'


def check(plan):
    for section in ['model_sources_sha256', 'execution_sources_sha256', 'inputs_sha256']:
        for name, digest in plan[section].items():
            assert file_hash(ROOT/name) == digest, name
    for name, digest in plan['private_files_sha256'].items():
        f = MODEL/name
        assert not f.is_symlink() and f.stat().st_nlink == 1 and file_hash(f) == digest, name
    for name, version in plan['libraries'].items():
        assert importlib.metadata.version(name) == version, name
    for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']:
        assert os.environ.get(name) == '1', name
    assert os.getpriority(os.PRIO_PROCESS, 0) >= 10


def exact_controls(folder, spec):
    with np.load(folder/'cells'/(spec['region']+'.npz')) as new, np.load(ROOT/spec['control_cells']) as old:
        assert set(new) == set(old)
        for key in old:
            assert new[key].dtype == old[key].dtype and new[key].shape == old[key].shape
            assert new[key].tobytes() == old[key].tobytes(), (spec['region'], key)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', action='store_true')
    args = ap.parse_args()
    plan = json.loads(PLAN.read_text())
    assert subprocess.check_output(['git', 'show', 'HEAD:'+str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    assert len(plan['cases']) == 97 and plan['maximum_integrations'] == 99
    OUT.mkdir(parents=True, exist_ok=True)
    lock = (OUT/'.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not (OUT/'failure.json').exists(), 'Preserve failure; no automatic retry'
    if not args.run:
        assert not (OUT/'preparation.json').exists() and not list(OUT.glob('*/attempts/*.json'))
        for name, digest in plan['private_files_sha256'].items():
            target = MODEL/name
            assert not target.exists(), 'Do not patch a previously prepared private tree'
            target.parent.mkdir(parents=True, exist_ok=True)
            if name == 'rotclimate/model.py':
                target.write_text(patched_model((ROOT/name).read_text()))
            elif name == 'rotclimate/wet_energy.py':
                shutil.copyfile(ROOT/'experiments/wet_energy_budget.py', target)
            else:
                origin = ROOT if name in plan['model_sources_sha256'] or name in plan['helper_sources_sha256'] else ROOT/plan['cache_origin']
                shutil.copyfile(origin/name, target)
            assert file_hash(target) == digest
        (OUT/'.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')
    else:
        assert not (OUT/'results.json').exists(), 'Completed studies are immutable'
    check(plan)
    assert not any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0] = [str(MODEL/'scripts'), str(MODEL)]
    import benchmark_local as benchmark
    from rotclimate import earth, model as physical
    from rotclimate.config import Params
    assert Path(physical.__file__).resolve().is_relative_to(MODEL.resolve())
    assert Path(benchmark.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    specs = json.loads((ROOT/plan['region_specs']).read_text())
    earth.REGIONS.update(specs)
    params = Params.from_json(ROOT/plan['params'])
    assert params.wind_source == params.sst_source == 'model'
    assert params.soil_wet_cooling and params.soil_bucket_mm > 0 and params.wet_cooling > 0 and params.wet_sun > 0
    assert params.land_coupling_insolation > 0
    assert params.t_require_convergence and params.moisture_require_convergence and params.solver_require_convergence
    assert params.moisture_residual_tol == .01
    for part in plan['parts']:
        old = json.loads((ROOT/part['control_protocol']).read_text())
        assert old['params'] == json.loads(json.dumps(asdict(params)))
    if not args.run:
        actual = {}
        for spec in plan['cases']:
            actual[spec['region']] = case_hash(earth.region_case(spec['region'], 56., 1100.))
            assert actual[spec['region']] == spec['case_identity']
        check(plan)
        freeze(OUT/'preparation.json', dict(plan_sha256=file_hash(PLAN),
            private_regular_files=len(plan['private_files_sha256']), actual_case_identities=actual, integrations=0))
        print('Prepared 97 actual input identities; zero integrations', flush=True)
        return
    assert json.loads((OUT/'preparation.json').read_text())['plan_sha256'] == file_hash(PLAN)
    freeze(OUT/'protocol.json', dict(plan_sha256=file_hash(PLAN), preparation_sha256=file_hash(OUT/'preparation.json'),
        execution_sources_sha256=plan['execution_sources_sha256'], intervention=plan['intervention']))
    jobs = [('default_off', next(s for s in plan['cases'] if s['region'] == n)) for n in plan['default_off_controls']]
    jobs += [('candidate', s) for s in plan['cases']]
    protocols = {}
    for arm in ['default_off', 'candidate']:
        for part in plan['parts']:
            names = [n for n in part['regions'] if arm == 'candidate' or n in plan['default_off_controls']]
            if not names:
                continue
            folder = OUT/(arm+'_'+part['name'])
            for name in ['cases', 'cells', 'attempts']:
                (folder/name).mkdir(parents=True, exist_ok=True)
            protocols[arm, part['name']] = freeze(folder/'protocol.json', dict(params=asdict(params),
                regions=names, region_specs={n:specs[n] for n in names}, cell_km=56., pad_km=1100.,
                sources=plan['benchmark_protocol_sources_sha256'], physical_operator_override=dict(
                    WET_ENERGY_BUDGET=(arm == 'candidate'), hypothesis=plan['intervention']),
                note='Private source solar-bound experiment. Parameters unchanged; two default-off controls must be byte exact.'))
    rows = []
    for index, (arm, spec) in enumerate(jobs):
        check(plan)
        name = spec['region']
        folder = OUT/(arm+'_'+spec['part'])
        record, attempt = folder/'cases'/(name+'.json'), folder/'attempts'/(name+'.json')
        identity = protocols[arm, spec['part']]
        if record.exists():
            row = json.loads(record.read_text())
            assert row['status'] == 'passed' and row['numerics']['all_checks_passed']
            assert row['case_identity'] == spec['case_identity'] and row['identity'] == identity
            assert file_hash(folder/'cells'/(name+'.npz')) == row['cells_sha256']
            if arm == 'default_off':
                exact_controls(folder, spec)
            else:
                assert file_hash(folder/'cells'/(name+'_energy.npz')) == row['energy_capture_sha256']
            rows.append(dict(arm=arm, part=spec['part'], **row))
            continue
        assert not attempt.exists(), 'Preserve interrupted integration; recovery needs a separate recorded decision'
        write_json(OUT/'status.json', dict(stage='integrating', completed=index, total=99, arm=arm, region=name))
        freeze(attempt, dict(spec=spec, arm=arm, protocol_sha256=file_hash(folder/'protocol.json'),
                            campaign_protocol_sha256=file_hash(OUT/'protocol.json')))
        physical.WET_ENERGY_BUDGET = arm == 'candidate'
        original_run, original_budget = physical.ClimateModel.run, physical.solar_wetness_budget
        with np.load(ROOT/spec['control_cells']) as z:
            coordinates = {k:z[k] for k in ['i', 'j', 'lat', 'lon']}
        ii, jj = coordinates['i'], coordinates['j']
        captures, current, previous = [], {}, {}
        bound_max = [0.]
        def observed_budget(*a, **kw):
            b = original_budget(*a, **kw)
            assert all(np.isfinite(v).all() for v in b.values())
            assert (b['scale'] >= 0).all() and (b['scale'] <= 1).all()
            assert (b['applied'] <= b['bound'] + 1e-10).all()
            bound_max[0] = max(bound_max[0], float(np.maximum(b['applied']-b['bound'], 0).max()))
            current.clear()
            current.update({k:v[ii,jj].copy() for k,v in b.items()})
            return b
        def recorded_run(self, *a, **kw):
            assert self.tap is None
            def tap(stage, day, values):
                if stage == 'subsidence':
                    previous['before'] = values[ii,jj].copy()
                elif stage == 'wet_cooling':
                    expected = previous['before'] - current['delta_wet'] * current['scale']
                    np.testing.assert_allclose(values[ii,jj], expected, rtol=0., atol=1e-12)
                    previous['after_wet'] = values[ii,jj].copy()
                elif stage == 'wet_sun':
                    ds = current['delta_sun']
                    expected = previous['after_wet'] - np.where(ds > 0, ds*current['scale'], ds)
                    np.testing.assert_allclose(values[ii,jj], expected, rtol=0., atol=1e-12)
                    captures.append(dict(day=np.asarray(day), before=previous['before'],
                        after_wet=previous['after_wet'], after_sun=values[ii,jj].copy(), **current))
            self.tap = tap
            try:
                result = original_run(self, *a, **kw)
            finally:
                self.tap = None
            if result.numerics['all_checks_passed']:
                np.savez_compressed(folder/'cells'/(name+'_energy.npz'), **coordinates,
                    scored_days=result.days, scored_steps=np.asarray(len(result.days)),
                    **{k:np.stack([c[k] for c in captures]) for k in captures[0]},
                    full_grid_bound_excess_max_W_m2=np.asarray(bound_max[0]))
            return result
        if arm == 'candidate':
            physical.solar_wetness_budget = observed_budget
            physical.ClimateModel.run = recorded_run
        try:
            row = benchmark.one((name, asdict(params), 56., str(folder), specs, identity, 1100.))
        except BaseException as error:
            write_json(OUT/'failure.json', dict(region=name, arm=arm, exception=repr(error), automatic_retry=False))
            raise
        finally:
            physical.ClimateModel.run, physical.solar_wetness_budget = original_run, original_budget
            physical.WET_ENERGY_BUDGET = False
        if row['status'] != 'passed' or row['numerics']['all_checks_passed'] is not True:
            write_json(OUT/'failure.json', dict(region=name, arm=arm, record=row, automatic_retry=False))
            raise RuntimeError('Original numerical criteria failed; stop')
        assert row['case_identity'] == spec['case_identity']
        if arm == 'default_off':
            exact_controls(folder, spec)
        else:
            row['energy_capture_sha256'] = file_hash(folder/'cells'/(name+'_energy.npz'))
            write_json(record, row)
        rows.append(dict(arm=arm, part=spec['part'], **row))
        print(f"Solar-bound {index+1}/99: {arm} {name}", flush=True)
    for (arm, part), identity in protocols.items():
        folder = OUT/(arm+'_'+part)
        records = {r['region']:{k:v for k,v in r.items() if k not in ['arm','part']} for r in rows if r['arm']==arm and r['part']==part}
        names = list(records)
        write_json(folder/'summary.json', dict(complete=True, identity=identity, fit=plan['params'], overrides={},
            cell_km=56., pad_km=1100., regions=records, all=benchmark.group_means(records,names)))
    check(plan)
    write_json(OUT/'results.json', dict(status='completed_fixed_solar_bound_candidate', rows=rows,
        protocol_sha256=file_hash(OUT/'protocol.json'), integrations=99, atlas_changed=False))
    subprocess.run([str(ROOT/'.venv/bin/python'), '-I', str(ROOT/'scripts/review_wet_energy_budget.py')], cwd=ROOT, check=True)
    write_json(OUT/'status.json', dict(stage='ready_for_agent_review', completed=99))


if __name__ == '__main__':
    main()
