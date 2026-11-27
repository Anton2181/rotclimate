"""Run a fixed isolated r58 study under its prospectively declared schedule."""
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json

PLAN = ROOT / 'calibration/padding_sensitivity_20261126/plan.json'
OUT = ROOT / 'output/padding_sensitivity_20261126'
MODEL = OUT / 'model'
W18C = ROOT / 'output/ppe_20261127/W18c/campaign_status.json'


def scored(case):
    return case.grid.inmap & case.grid.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)


def footprint(case):
    mask = scored(case)
    ii, jj = np.nonzero(mask)
    g = case.grid
    return dict(rows=ii, cols=jj, lat=g.lat[mask], lon=case.lon[mask], land=g.land[mask],
                land_frac=g.land_frac[mask], elev=g.elev[mask], elev_max=g.elev_max[mask],
                obs_T=case.obs_T[:, mask], obs_P=case.obs_P[:, mask])


def check_footprint(base, case, offset):
    """Compare actual translated cells, never interpolate or intersect masks."""
    actual = footprint(case)
    np.testing.assert_array_equal(actual['rows'], base['rows'] + offset)
    np.testing.assert_array_equal(actual['cols'], base['cols'] + offset)
    for name in ['land', 'land_frac', 'elev', 'elev_max', 'obs_T', 'obs_P']:
        np.testing.assert_array_equal(actual[name], base[name], err_msg=name)
    for name in ['lat', 'lon']:
        np.testing.assert_allclose(actual[name], base[name], rtol=0, atol=1e-10, err_msg=name)
    return actual


def require_closed_campaign(state, running):
    terminal = state.get('stage', '').startswith('closed_') or state.get('stage') == 'all_gates_passed_ready_for_review'
    if not terminal or running:
        raise RuntimeError('W18c still active or nonterminal; preparation only, no padding integrations permitted')


def require_private_parallel(plan, state, running):
    """A scheduling amendment only: one private, low-priority, unstarted study."""
    if plan.get('private_parallel_execution') is not True:
        raise ValueError('Private parallel execution requires a prospective amended plan')
    parent = ROOT / plan['supersedes_unrun_output']
    if not (parent / 'superseded_before_run.json').exists() or list(parent.glob('*/pad_*/attempt.json')):
        raise ValueError('The original study must be retired with zero integration attempts')
    if os.getpriority(os.PRIO_PROCESS, 0) < 10:
        raise ValueError('Private parallel execution requires nice priority at least10')
    if any(os.environ.get(name) != '1' for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS']):
        raise ValueError('Private parallel execution requires one BLAS/OpenMP thread')
    terminal = state.get('stage', '').startswith('closed_') or state.get('stage') == 'all_gates_passed_ready_for_review'
    if running or not terminal:
        # The independent private study must not change the ongoing campaign.
        for name, digest in plan['model_sources_sha256'].items():
            assert file_hash(ROOT / name) == digest, name


def supervisor_running():
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            arguments = (entry / 'cmdline').read_bytes().split(b'\0')
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
        if any(arg.endswith(b'/run_w18c_campaign.py') or arg == b'run_w18c_campaign.py' for arg in arguments):
            return True
    return False


def copy_checked(source, destination, digest):
    """Use private regular files, so a future derived write cannot touch main."""
    if destination.is_symlink():
        raise ValueError('Private inputs must not be symlinks: ' + str(destination))
    if destination.exists():
        assert file_hash(destination) == digest, str(destination)
        return
    assert file_hash(source) == digest, str(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.copying')
    shutil.copyfile(source, temporary)
    assert file_hash(temporary) == digest
    temporary.replace(destination)


def validate_private(plan, protocol):
    for name, digest in {**plan['model_sources_sha256'], **plan['cache_seed_sha256']}.items():
        path = MODEL / name
        assert not path.is_symlink() and file_hash(path) == digest, name
    for name, digest in protocol['helper_sources_sha256'].items():
        path = MODEL / name
        assert not path.is_symlink() and file_hash(path) == digest, name
    for name, digest in plan['inputs_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, version in protocol['libraries'].items():
        assert importlib.metadata.version(name) == version, name
    assert protocol['runner_sha256'] == file_hash(Path(__file__))


def private_modules(plan):
    if any(n == 'rotclimate' or n.startswith('rotclimate.') for n in sys.modules):
        raise RuntimeError('Physical module already imported; start a fresh isolated process')
    sys.path[:0] = [str(MODEL), str(MODEL / 'scripts')]
    from rotclimate import earth
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    from rotclimate.koppen import monthly_stats
    assert Path(earth.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    for name in ['calibration/local_accuracy_20261023/regions_dev12.json',
                 'calibration/sealed_20261123S18/regions.json', 'calibration/sealed_20261124U18/regions.json']:
        earth.REGIONS.update(json.loads((ROOT / name).read_text()))
    params = Params.from_json(ROOT / 'calibration/local_accuracy_20261023/r58_params.json')
    return earth, params, ClimateModel, monthly_stats


def reference(region):
    if region == 'north_india':
        folder = ROOT / 'output/ppe_20261126/ref58/r58_dev31'
        record = json.loads((folder / 'cases/north_india.json').read_text())
        with np.load(folder / 'cells/north_india.npz') as packet:
            fields = dict(packet)
        return record['case_identity'], dict(T=fields['Ts'], P=fields['Ps'], obs_T=fields['To'], obs_P=fields['Po'])
    folder = ROOT / 'output/somalia_mechanism_20261126' / region / 'control'
    record = json.loads((folder / 'result.json').read_text())
    with np.load(folder / 'fields.npz') as packet:
        mask = packet['mask']
        fields = {name:packet[name][:, mask] for name in ['T', 'P', 'E', 'W', 'u', 'v', 'obs_T', 'obs_P']}
    return record['case_identity'], fields


def prepare(plan, protocol, earth):
    records = []
    for region in plan['regions']:
        base = None
        for pad, offset in zip(plan['pads_km'], plan['pad_cell_offsets'], strict=True):
            case = earth.region_case(region, plan['cell_km'], pad)
            if base is None:
                base = footprint(case)
                expected_identity, expected = reference(region)
                assert case_hash(case) == expected_identity, region
                np.testing.assert_array_equal(base['obs_T'], expected['obs_T'])
                np.testing.assert_array_equal(base['obs_P'], expected['obs_P'])
            fields = check_footprint(base, case, offset)
            folder = OUT / region / f'pad_{pad:g}'
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / 'footprint.npz'
            if not path.exists():
                with path.with_suffix('.tmp').open('wb') as stream:
                    np.savez_compressed(stream, **fields)
                path.with_suffix('.tmp').replace(path)
            else:
                with np.load(path) as old:
                    for name, value in fields.items():
                        np.testing.assert_array_equal(old[name], value)
            record = dict(region=region, pad_km=pad, offset_cells=offset,
                          case_identity=case_hash(case), scored_cells=len(fields['rows']),
                          grid_shape=[case.grid.ny, case.grid.nx], footprint_sha256=file_hash(path))
            freeze(folder / 'prepared.json', record)
            records.append(record)
            print('prepared', region, pad, record['grid_shape'], record['scored_cells'], flush=True)
    validate_private(plan, protocol)
    freeze(OUT / 'preparation.json', dict(status='prepared_no_climate_integrations',
        plan_sha256=file_hash(PLAN), protocol_sha256=file_hash(OUT / 'protocol.json'), cases=records,
        climate_integrations=0, shared_cache_writes=False))
    return records


def integrate(plan, protocol, earth, params, ClimateModel, monthly_stats, records, execution_gate=require_closed_campaign):
    execution_gate(json.loads(W18C.read_text()), supervisor_running())
    from rainfall_metrics import local_metrics
    results = []
    for pad in plan['pads_km']:
        if pad != plan['pads_km'][0] and not all(r['status'] == 'passed' for r in results[:3]):
            raise RuntimeError('Control failures prohibit expanded-domain integrations')
        for region in plan['regions']:
            validate_private(plan, protocol)
            execution_gate(json.loads(W18C.read_text()), supervisor_running())
            folder = OUT / region / f'pad_{pad:g}'
            receipt = folder / 'result.json'
            if receipt.exists():
                row = json.loads(receipt.read_text())
                if row['status'] == 'passed':
                    assert row['fields_sha256'] == file_hash(folder / 'fields.npz')
                results.append(row)
                continue
            if (folder / 'attempt.json').exists():
                raise RuntimeError('Interrupted integration requires recorded recovery review, not automatic repetition: ' + str(folder))
            case = earth.region_case(region, plan['cell_km'], pad)
            prepared = next(r for r in records if r['region'] == region and r['pad_km'] == pad)
            assert case_hash(case) == prepared['case_identity']
            assert file_hash(folder / 'footprint.npz') == prepared['footprint_sha256']
            with np.load(folder / 'footprint.npz') as packet:
                fixed = dict(packet)
            ii, jj = fixed['rows'], fixed['cols']
            row = dict(region=region, pad_km=pad, case_identity=prepared['case_identity'])
            freeze(folder / 'attempt.json', dict(**row, protocol_sha256=file_hash(OUT / 'protocol.json')))
            result = None
            try:
                model = ClimateModel(earth.earth_params(params, case), grid=case.grid)
                model.trace_cells = (ii, jj)
                result = model.run()
                assert result.numerics['all_checks_passed']
                p = result.params
                monthly = monthly_stats(result.T, result.P, result.days, p.year_days,
                                        summer_solstice=p.winter_solstice_day + p.year_days / 2)
                fields = dict(T=monthly['Tm'][:, ii, jj], P=np.maximum(monthly['Pm'][:, ii, jj], 0))
                for name in ['E', 'W', 'u', 'v']:
                    a = getattr(result, name)
                    stats = monthly_stats(a, a, result.days, p.year_days)
                    fields[name] = stats['Pm' if name == 'E' else 'Tm'][:, ii, jj]
                assert all(np.isfinite(value).all() for value in fields.values()) and (fields['P'] >= 0).all()
                if pad == plan['pads_km'][0]:
                    _, expected = reference(region)
                    for name in fields.keys() & expected.keys():
                        np.testing.assert_array_equal(fields[name].astype(np.float32), expected[name].astype(np.float32))
                trace = sorted(model.trace, key=lambda r:r['day'])
                np.testing.assert_array_equal([r['day'] for r in trace], result.days)
                fields.update(obs_T=fixed['obs_T'], obs_P=fixed['obs_P'], lat=fixed['lat'], lon=fixed['lon'],
                              rows=ii, cols=jj, days=result.days)
                for name in ['gain', 'sinkd', 'W', 'P']:
                    fields['step_' + name] = np.stack([r[name] for r in trace])
                with (folder / 'fields.tmp').open('wb') as stream:
                    np.savez_compressed(stream, **fields)
                (folder / 'fields.tmp').replace(folder / 'fields.npz')
                row.update(status='passed', fields_sha256=file_hash(folder / 'fields.npz'), numerics=result.numerics,
                    temperature_mae_C=float(np.abs(fields['T'] - fixed['obs_T']).mean()),
                    rain=local_metrics(fields['P'], fixed['obs_P'], np.ones(len(ii), bool)),
                    annual_import_mm=float((fields['step_gain'] * fields['step_W']).mean() * 365),
                    annual_drying_mm=float(-(fields['step_sinkd'] * fields['step_W']).mean() * 365),
                    exact_control_reproduction=(pad == plan['pads_km'][0]))
            except Exception as error:
                row.update(status='failed', error=repr(error), numerics=getattr(result, 'numerics', None))
            write_json(receipt, row)
            results.append(row)
            print('integrated', region, pad, row['status'], flush=True)
        if pad == plan['pads_km'][0] and any(r['status'] != 'passed' for r in results):
            write_json(OUT / 'results.json', dict(status='closed_control_failed', rows=results, climate_adopted=False))
            return
    validate_private(plan, protocol)
    write_json(OUT / 'results.json', dict(status='completed_fixed_padding_diagnostic', rows=results,
        climate_adopted=False, atlas_changed=False, all_numerical_checks_passed=all(r['status'] == 'passed' for r in results)))


def main():
    global PLAN, OUT, MODEL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true', help='After W18c closes, use the fixed nine-attempt integration budget')
    parser.add_argument('--plan', type=Path, default=PLAN)
    parser.add_argument('--private-parallel', action='store_true', help='Use only a separately declared prospective private scheduling amendment')
    args = parser.parse_args()
    PLAN = args.plan.resolve()
    plan = json.loads(PLAN.read_text())
    OUT = ROOT / plan['out']; MODEL = OUT / 'model'
    gate = (lambda state, running:require_private_parallel(plan, state, running)) if args.private_parallel else require_closed_campaign
    if args.run:
        if (OUT / 'superseded_before_run.json').exists():
            raise SystemExit('This unrun study was superseded; use its explicitly declared replacement plan')
        gate(json.loads(W18C.read_text()), supervisor_running())
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    assert plan['maximum_integrations'] == len(plan['regions']) * len(plan['pads_km']) == 9
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / '.gitignore').write_text('model/\n.lock\n')
    lock = (OUT / '.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    helpers = {name:file_hash(ROOT / name) for name in ['scripts/local_benchmark_protocol.py', 'scripts/rainfall_metrics.py']}
    protocol = dict(plan_sha256=file_hash(PLAN), runner_sha256=file_hash(Path(__file__)), helper_sources_sha256=helpers,
                    libraries={name:importlib.metadata.version(name) for name in ['numpy', 'scipy', 'numba', 'Pillow']})
    freeze(OUT / 'protocol.json', protocol)
    for name, digest in {**plan['model_sources_sha256'], **plan['cache_seed_sha256'], **helpers}.items():
        origin = plan.get('cache_seed_origins', {}).get(name, name)
        copy_checked(ROOT / origin, MODEL / name, digest)
    validate_private(plan, protocol)
    earth, params, ClimateModel, monthly_stats = private_modules(plan)
    try:
        records = prepare(plan, protocol, earth)
    except Exception as error:
        write_json(OUT / 'preparation_failure.json', dict(error=repr(error), climate_integrations=0))
        raise
    if args.run:
        integrate(plan, protocol, earth, params, ClimateModel, monthly_stats, records, execution_gate=gate)
    else:
        print('Prepared only. Waiting for terminal W18c and supervisor exit; climate integrations=0.', flush=True)


if __name__ == '__main__':
    main()
