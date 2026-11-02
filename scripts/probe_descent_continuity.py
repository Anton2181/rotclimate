"""Run an isolated descent/ascent prototype beside unchanged r42 controls."""
from __future__ import annotations

import argparse
import difflib
import importlib.util
import json
import os
from pathlib import Path
import sys

os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import numpy as np

from benchmark_local import DEV12_SPECS, temperature_metrics
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash, file_hash, freeze, write_json
from rainfall_metrics import local_metrics
from rotclimate import earth
from rotclimate.koppen import monthly_stats
from rotclimate.model import ClimateModel

FIELDS = ('T', 'Tsl', 'P', 'W', 'u', 'v', 'E', 'snow')


def prototype(path):
    # The copy uses the canonical package's relative imports, without replacing
    # rotclimate.model or changing any production or running search instance.
    name = 'rotclimate._descent_continuity_probe'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.ClimateModel


def run_region(plan, name, Prototype, destination):
    folder = ROOT / plan['regions'][name]['reference']
    protocol = json.loads((folder / 'protocol.json').read_text())
    expected = json.loads((folder / 'summary.json').read_text())['regions'][name]
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    earth.REGIONS.update(protocol['region_specs'])
    base = load_params(ROOT / plan['params'])
    results, rows = {}, {}
    packet = {}
    for mode in ('reference', 'disabled', 'continuity'):
        case = earth.region_case(name, float(protocol['cell_km']))
        g = case.grid
        actual = case_hash(case, observed_sea=base.sst_source == 'observed')
        if actual != expected['case_identity']:
            raise ValueError('Input identity differs: ' + name)
        mask = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        if int(mask.sum()) != expected['cells']:
            raise ValueError('Scored footprint differs')
        p = earth.earth_params(base, case)
        model = (ClimateModel(p, grid=g) if mode == 'reference' else
                 Prototype(p, grid=g, branch_continuity_strength=plan['strength'] if mode == 'continuity' else 0))
        result = model.run(steps=p.steps_per_year)
        if not result.numerics['all_checks_passed'] or any(not np.isfinite(getattr(result, k)).all() for k in FIELDS):
            raise ValueError('Prototype numerical checks failed: ' + name + '/' + mode)
        if (result.P < 0).any():
            raise ValueError('Negative rain')
        results[mode] = result
        for field in FIELDS:
            packet[mode + '_' + field] = getattr(result, field)
        st = monthly_stats(result.T, result.P, result.days, p.year_days,
                           summer_solstice=p.winter_solstice_day + p.year_days / 2)
        t = temperature_metrics(st['Tm'][:, mask], case.obs_T[:, mask])['monthly_mae_C']
        rain = local_metrics(np.maximum(st['Pm'], 0), np.nan_to_num(case.obs_P), mask)
        if mode == 'reference' and not np.allclose(
            [t, rain['loss']], [expected['temperature']['monthly_mae_C'], expected['rain']['loss']], rtol=0, atol=1e-10):
            raise ValueError('Ordinary control does not reproduce reference')
        rows[mode] = dict(temperature_monthly_mae_c=t, rain=rain, numerics=result.numerics,
                          monthly_rain_mm=st['Pm'][:, mask].mean(1).tolist(),
                          monthly_temperature_c=st['Tm'][:, mask].mean(1).tolist())
        packet['days'], packet['mask'] = result.days, mask
        packet['obs_P'], packet['obs_T'] = case.obs_P, case.obs_T
        packet['lat'], packet['lon'] = g.lat, case.lon
    differences = {k: float(np.max(np.abs(getattr(results['disabled'], k) - getattr(results['reference'], k)))) for k in FIELDS}
    byte_equal = all(np.array_equal(getattr(results['disabled'], k), getattr(results['reference'], k)) for k in FIELDS)
    tmp = destination / (name + '.tmp')
    with tmp.open('wb') as stream:
        np.savez_compressed(stream, **packet)
    tmp.replace(destination / (name + '.npz'))
    row = dict(region=name, status='passed' if byte_equal else 'disabled_mismatch', case_identity=actual,
               disabled_fields_byte_equal=byte_equal, disabled_max_differences=differences,
               modes=rows, packet_sha256=file_hash(destination / (name + '.npz')))
    write_json(destination / (name + '.json'), row)
    if not byte_equal:
        raise ValueError('Disabled prototype changed fields: ' + name)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text()); a.out.mkdir(parents=True, exist_ok=True)
    if file_hash(ROOT / 'rotclimate/model.py') != plan['base_model_sha256']:
        raise ValueError('Production model differs from the frozen prototype basis')
    files = [Path(__file__), a.plan, ROOT / plan['params'], ROOT / plan['prototype'],
             ROOT / 'experiments/descent_continuity_20261102/closure.py',
             *sorted((ROOT / 'rotclimate').glob('*.py'))]
    for spec in plan['regions'].values():
        files.extend([ROOT / spec['reference'] / 'protocol.json', ROOT / spec['reference'] / 'summary.json'])
    run = freeze(a.out / 'protocol.json', dict(plan=plan, sources={str(f.resolve().relative_to(ROOT)): file_hash(f) for f in files}))
    diff = ''.join(difflib.unified_diff((ROOT / 'rotclimate/model.py').read_text().splitlines(True),
                   (ROOT / plan['prototype']).read_text().splitlines(True), fromfile='r42/model.py', tofile='probe/model.py'))
    (a.out / 'source_diff.patch').write_text(diff)
    Probe = prototype(ROOT / plan['prototype'])
    rows = {}
    for name in plan['regions']:
        path = a.out / (name + '.json')
        try:
            if path.exists():
                row = json.loads(path.read_text())
                if row.get('status') != 'passed' or file_hash(a.out / (name + '.npz')) != row['packet_sha256']:
                    raise ValueError('Previous probe is incomplete or changed: ' + name)
            else:
                row = run_region(plan, name, Probe, a.out)
        except Exception as error:
            write_json(a.out / (name + '_failure.json'), dict(status='failed', error=repr(error)))
            raise
        rows[name] = row
        write_json(a.out / 'summary.json', dict(identity=run, complete=len(rows) == len(plan['regions']),
                                               regions=rows, adoption=False))
        print(name, {m: dict(T=r['temperature_monthly_mae_c'], P=r['rain']['loss']) for m, r in row['modes'].items()}, flush=True)


if __name__ == '__main__':
    main()
