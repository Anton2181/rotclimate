"""Observe existing instantaneous import/drying terms without climate runs."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, freeze, write_json
from rotclimate.koppen import monthly_weights

PLAN = ROOT / 'calibration/convergence_import_audit_20261126/plan.json'
OUT = ROOT / 'output/convergence_import_audit_20261126'
TRACE = ROOT / 'output/somalia_transport_trace_20261126'
PARENT = ROOT / 'output/somalia_mechanism_20261126'
QUALIFIED = ROOT / 'output/somalia_marine_exchange_trace_20261126/qualification.json'
HISTORIES = ['vapor_flux_20261026', 'flux_column_wind_20261026', 'column_mass_20261026']


def write_table(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    assert not (OUT / 'results.json').exists(), 'Preserve completed exploratory audit'
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    plan = json.loads(PLAN.read_text())
    qualification = json.loads(QUALIFIED.read_text())
    for name, digest in qualification['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in qualification['files_sha256'].items():
        assert file_hash(QUALIFIED.parent / name) == digest, name
    paths = [PLAN, Path(__file__), QUALIFIED, ROOT / 'rotclimate/model.py', ROOT / 'rotclimate/moisture.py',
             ROOT / 'rotclimate/transport.py', ROOT / 'rotclimate/koppen.py', ROOT / 'scripts/local_benchmark_protocol.py']
    paths += [ROOT / f'output/{name}/review.json' for name in HISTORIES]
    paths += [ROOT / f'calibration/{name}/plan.json' for name in HISTORIES]
    paths += [ROOT / 'output/fitted_flux_20261103/result.json', ROOT / 'calibration/fitted_flux_20261103/plan.json']
    for case in plan['cases']:
        r, v = case['region'], case['variant']
        paths += [TRACE / r / v / 'trace.npz', PARENT / r / v / 'fields.npz']
    sources = {str(path.relative_to(ROOT)):file_hash(path) for path in paths}
    OUT.mkdir(parents=True, exist_ok=True)
    freeze(OUT / 'preparation.json', dict(plan=plan, sources_sha256=sources))
    steps, months, summaries = [], [], []
    checks = 0
    for case in plan['cases']:
        r, v = case['region'], case['variant']
        with np.load(TRACE / r / v / 'trace.npz') as packet:
            t = dict(packet)
        with np.load(PARENT / r / v / 'fields.npz') as packet:
            f = dict(packet)
        ii, jj = np.nonzero(f['mask'])
        np.testing.assert_array_equal(ii, t['rows'])
        np.testing.assert_array_equal(jj, t['cols'])
        water, gain, sink = [t['trace__' + name] for name in ['W', 'gain', 'sinkd']]
        assert np.isfinite(water).all() and (water >= 0).all() and (gain >= 0).all() and (sink >= 0).all()
        imported, drying = gain * water, -sink * water
        for calculated, key in [(imported, 'convergence_import'), (drying, 'column_drying')]:
            np.testing.assert_array_equal(calculated.astype(np.float32), t['budget__' + key])
            checks += calculated.size
        adv = t['budget__advection'].astype(float)
        arrays = dict(import_mm_day=imported, drying_mm_day=drying,
            advection_positive_mm_day=np.maximum(adv, 0), advection_negative_mm_day=np.minimum(adv, 0),
            overlapping_import_drying_mm_day=np.minimum(imported, -drying),
            rain_mm_day=t['trace__P'], column_water_mm=water, gain_per_day=gain, sink_per_day=sink)
        for k, day in enumerate(t['days']):
            for n, (row, col) in enumerate(zip(ii, jj)):
                steps.append(dict(region=r, variant=v, step=k, day=float(day), row=int(row), col=int(col),
                                  **{key:float(values[k, n]) for key, values in arrays.items()}))
        weights = monthly_weights(t['days'], 365.)
        for m in range(12):
            record = dict(region=r, variant=v, month=m + 1)
            for key, values in arrays.items():
                value = float((weights[m] @ values).mean())
                record[key.replace('_mm_day', '_mm_month')] = value * 365 / 12 if key.endswith('_mm_day') else value
            record['import_positive_fraction'] = float((weights[m] @ (gain > 0)).mean())
            record['simultaneous_import_positive_advection_fraction'] = float((weights[m] @ ((gain > 0) & (adv > 0))).mean())
            months.append(record)
        summaries.append(dict(region=r, variant=v, steps=len(t['days']), cells=len(ii),
            annual_mm={key.replace('_mm_day', ''):float(values.mean() * 365)
                       for key, values in arrays.items() if key.endswith('_mm_day')},
            gain_per_day=dict(min=float(gain.min()), mean=float(gain.mean()), max=float(gain.max())),
            sink_per_day=dict(min=float(sink.min()), mean=float(sink.mean()), max=float(sink.max())),
            import_positive_fraction=float((gain > 0).mean()),
            simultaneous_import_positive_advection_fraction=float(((gain > 0) & (adv > 0)).mean()),
            simultaneous_import_drying_fraction=float(((gain > 0) & (sink > 0)).mean()),
            column_water_mean_mm=float(water.mean())))
    historical = {}
    for name in HISTORIES:
        record = json.loads((ROOT / f'output/{name}/review.json').read_text())
        historical[name] = dict(complete=record['complete'], all_per_step_checks_passed=record['all_per_step_checks_passed'],
            development_finalists=record['development_finalists'], physics_or_atlas_adoption=record['physics_or_atlas_adoption'],
            profiles={key:{field:value[field] for field in ['eligible_profile', 'qualifies', 'failures', 'S', 'temperature_ratio', 'rain_ratio'] if field in value}
                      for key, value in record['screen'].items()})
    historical['fitted_flux_20261103'] = json.loads((ROOT / 'output/fitted_flux_20261103/result.json').read_text())
    write_table(OUT / 'steps.csv', steps)
    write_table(OUT / 'months.csv', months)
    for name, digest in sources.items():
        assert file_hash(ROOT / name) == digest, name
    write_json(OUT / 'results.json', dict(status='completed_exploratory_saved_trace_audit', sources_sha256=sources,
        files_sha256={name:file_hash(OUT / name) for name in ['steps.csv', 'months.csv']},
        summaries=summaries, historical_separate_epochs=historical,
        exact_float32_reconstruction_scalars=checks, climate_integrations=0, climate_adopted=False,
        interpretation='Algebraic source accounting and co-occurrence only; no causal rainfall shares, double-counting proof, new physical setting or pooled historical scores.'))
    print(json.dumps(summaries, indent=1))


if __name__ == '__main__':
    main()
