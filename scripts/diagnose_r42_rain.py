"""Observe existing r42 rainfall physics on the complete benchmark footprint.

No coefficients, forcing or integration code are changed. Each diagnostic
must reproduce its frozen ordinary benchmark errors and actual case identity.
The source terms describe the model's steady column equation; they are not
water-source tracers or a globally conservative atmospheric budget.
"""
from __future__ import annotations

import argparse
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
from rotclimate.koppen import monthly_stats, monthly_weights
from rotclimate.model import ClimateModel
from rotclimate.numerics import matrix_product

SOURCES = ('advection', 'diffusion', 'storm_exchange', 'evaporation',
           'column_drying', 'convergence_import')


def monthly(field, days, year_days):
    field = np.asarray(field)
    weights = monthly_weights(days, year_days)
    return matrix_product(weights, field.reshape(len(days), -1)).reshape((12,) + field.shape[1:])


def balance_check(budget, rain):
    """Monsoon drying is a subset of column drying, never a second sink."""
    total = sum(np.asarray(budget[k], float) for k in SOURCES)
    error = total - rain - budget['residual']
    scale = np.maximum(sum(np.abs(budget[k]) for k in SOURCES) + np.abs(rain)
                       + np.abs(budget['residual']), 1.0)
    # Budget arrays and saved rain are float32; allow their storage roundoff.
    allowance = 32 * np.finfo(np.float32).eps * scale
    if not np.isfinite(error).all() or (np.abs(error) > allowance).any():
        raise ValueError('Recorded moisture components do not reconstruct the recorded equation')
    return dict(max_reconstruction_error_mm_day=float(np.abs(error).max()),
                max_absolute_equation_residual_mm_day=float(np.max(budget['absolute_residual'])),
                mean_absolute_equation_residual_mm_day=float(np.mean(budget['absolute_residual'])))


def diagnose(plan, name, destination):
    declaration = plan['regions'][name]
    reference = ROOT / declaration['reference']
    protocol = json.loads((reference / 'protocol.json').read_text())
    expected = json.loads((reference / 'summary.json').read_text())['regions'][name]
    if expected.get('status') != 'passed' or not expected['numerics']['all_checks_passed']:
        raise ValueError('Unverified benchmark reference')
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    earth.REGIONS.update(protocol['region_specs'])
    case = earth.region_case(name, float(protocol['cell_km']))
    base = load_params(ROOT / plan['params'])
    actual_case = case_hash(case, observed_sea=base.sst_source == 'observed')
    if actual_case != expected['case_identity']:
        raise ValueError('Diagnostic footprint/forcing differs from reference: ' + name)
    p = earth.earth_params(base, case)
    g = case.grid
    mask = g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
    if int(mask.sum()) != expected['cells']:
        raise ValueError('Scoring mask differs from reference')
    ii, jj = np.nonzero(mask)
    model = ClimateModel(p, grid=g)
    model.trace_cells = (ii, jj)
    result = model.run(steps=p.steps_per_year, diagnose_moisture=True)
    if not result.numerics['all_checks_passed']:
        raise ValueError('Diagnostic numerical checks failed')
    st = monthly_stats(result.T, result.P, result.days, p.year_days,
                       summer_solstice=p.winter_solstice_day + p.year_days / 2)
    metrics = (temperature_metrics(st['Tm'][:, mask], case.obs_T[:, mask])['monthly_mae_C'],
               local_metrics(np.maximum(st['Pm'], 0), np.nan_to_num(case.obs_P), mask)['loss'])
    target = (expected['temperature']['monthly_mae_C'], expected['rain']['loss'])
    if not np.allclose(metrics, target, rtol=0, atol=1e-10):
        raise ValueError('Diagnostics changed the ordinary benchmark: ' + name)
    trace_days = np.array([r['day'] for r in model.trace])
    if not np.array_equal(trace_days, result.days):
        raise ValueError('Trace does not cover exactly the recorded model year')
    sl = g.map_slice()
    inside = np.zeros(mask.shape, bool); inside[sl] = True
    if (mask & ~inside).any():
        raise ValueError('Cropped budget omits scored cells')
    cropped = mask[sl]
    budget = {k: a[:, cropped] for k, a in result.moisture_budget.items()}
    rain = result.P[:, mask]
    closure = balance_check(budget, rain)
    traces = {key: np.stack([row[key] for row in model.trace]) for key in
              ('W', 'Ws', 'P', 'E', 'T', 'background', 'storm', 'conv', 'orog',
               'damp', 'A', 'gain', 'sinkd', 'conv_rate', 'chi')}
    traces['rh'] = traces['W'] / np.maximum(traces['Ws'], 1e-6)
    packet = dict(days=result.days, i=ii, j=jj, lat=g.lat[mask], lon=case.lon[mask],
                  T=result.T[:, mask], P=rain, obs_T=case.obs_T[:, mask], obs_P=case.obs_P[:, mask],
                  **{'budget_' + k: v for k, v in budget.items()},
                  **{'trace_' + k: v for k, v in traces.items()})
    tmp = destination / (name + '.tmp')
    with tmp.open('wb') as stream:
        np.savez_compressed(stream, **packet)
    tmp.replace(destination / (name + '.npz'))
    month = {k: monthly(v, result.days, p.year_days).mean(1).tolist() for k, v in budget.items()}
    month['rain'] = monthly(rain, result.days, p.year_days).mean(1).tolist()
    month['observed_rain'] = (case.obs_P[:, mask].mean(1) * 12 / p.year_days).tolist()
    report = dict(status='passed', region=name, cells=int(mask.sum()), case_identity=actual_case,
                  errors=dict(temperature_monthly_mae_c=metrics[0], rain_loss=metrics[1]),
                  reproduces_ordinary_benchmark=True, numerics=result.numerics, closure=closure,
                  monthly_mm_day=month,
                  trace_monthly={k: monthly(v, result.days, p.year_days).mean(1).tolist() for k, v in traces.items()},
                  annual_mm={k: float(np.mean(v) * p.year_days) for k, v in month.items()},
                  packet_sha256=file_hash(destination / (name + '.npz')),
                  notes=['Monsoon drying is included in column drying; do not sum it twice.',
                         'Trace ascent components are inputs to a nonlinear rain closure, not additive rainfall shares.',
                         'Equal-region/cell benchmark footprint; no area or population reweighting.',
                         'Steady concentration-transport equation diagnostics, not global mass conservation or source tracing.'])
    write_json(destination / (name + '.json'), report)
    return report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    a.out.mkdir(parents=True, exist_ok=True)
    files = [Path(__file__), a.plan, ROOT / plan['params'], ROOT / 'scripts/benchmark_local.py',
             ROOT / 'scripts/local_benchmark_protocol.py', ROOT / 'scripts/rainfall_metrics.py',
             *sorted((ROOT / 'rotclimate').glob('*.py'))]
    for spec in plan['regions'].values():
        files.extend([ROOT / spec['reference'] / 'summary.json', ROOT / spec['reference'] / 'protocol.json'])
    run = freeze(a.out / 'protocol.json', dict(plan=plan, sources={str(f.resolve().relative_to(ROOT)): file_hash(f) for f in files}))
    rows = {}
    for name in plan['regions']:
        existing = a.out / (name + '.json')
        if existing.exists():
            row = json.loads(existing.read_text())
            if row.get('status') != 'passed' or file_hash(a.out / (name + '.npz')) != row['packet_sha256']:
                raise ValueError('Existing diagnostic is incomplete or changed: ' + name)
        else:
            try:
                row = diagnose(plan, name, a.out)
            except Exception as error:
                write_json(existing, dict(status='failed', region=name, error=repr(error)))
                raise
        rows[name] = row
        write_json(a.out / 'summary.json', dict(identity=run, complete=len(rows) == len(plan['regions']), regions=rows))
        print(name, row['annual_mm'], flush=True)


if __name__ == '__main__':
    main()
