"""Scalar review and scientific presentation of existing import traces."""
import argparse
import csv
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json

OUT = ROOT / 'output/convergence_import_audit_20261126'
TRACE = ROOT / 'output/somalia_transport_trace_20261126'
FIELDS = ['import_mm_day', 'drying_mm_day', 'advection_positive_mm_day', 'advection_negative_mm_day',
          'overlapping_import_drying_mm_day', 'rain_mm_day', 'column_water_mm', 'gain_per_day', 'sink_per_day']


def check_sources(result):
    for name, digest in result['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in result['files_sha256'].items():
        assert file_hash(OUT / name) == digest, name


def review():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    result = json.loads((OUT / 'results.json').read_text())
    check_sources(result)
    plan = json.loads((ROOT / 'calibration/convergence_import_audit_20261126/plan.json').read_text())
    with (OUT / 'steps.csv').open() as stream:
        steps = list(csv.DictReader(stream))
    with (OUT / 'months.csv').open() as stream:
        months = list(csv.DictReader(stream))
    assert len(result['summaries']) == len(plan['cases']) == 3
    expected_keys = set()
    scalar_checks = monthly_checks = 0
    for case, summary in zip(plan['cases'], result['summaries'], strict=True):
        region, variant = case['region'], case['variant']
        with np.load(TRACE / region / variant / 'trace.npz') as packet:
            t = dict(packet)
        nt, nc = t['trace__W'].shape
        by_step = [r for r in steps if (r['region'], r['variant']) == (region, variant)]
        by_month = [r for r in months if (r['region'], r['variant']) == (region, variant)]
        cell_index = {(int(r), int(c)):i for i, (r, c) in enumerate(zip(t['rows'], t['cols']))}
        expected_keys.update((region, variant, k, r, c) for k in range(nt) for r, c in cell_index)
        assert len(by_step) == nt * nc and len(by_month) == 12
        assert sorted(int(r['month']) for r in by_month) == list(range(1, 13))
        annual_sums = {key:0. for key in FIELDS}
        for row in by_step:
            k = int(row['step'])
            i = cell_index[int(row['row']), int(row['col'])]
            assert float(row['day']) == t['days'][k]
            w, g, s = [float(t['trace__' + key][k, i]) for key in ['W', 'gain', 'sinkd']]
            a = float(t['budget__advection'][k, i])
            expected = [g * w, -s * w, max(a, 0), min(a, 0), min(g * w, s * w),
                        float(t['trace__P'][k, i]), w, g, s]
            for key, value in zip(FIELDS, expected, strict=True):
                np.testing.assert_allclose(float(row[key]), value, rtol=1e-12, atol=1e-11)
                annual_sums[key] += value
                scalar_checks += 1
        for key, total in annual_sums.items():
            if key.endswith('_mm_day'):
                np.testing.assert_allclose(summary['annual_mm'][key[:-7]], total / (nt * nc) * 365, rtol=1e-11, atol=1e-9)
        for month in by_month:
            m = int(month['month']) - 1
            weighted = {key:0. for key in FIELDS}
            positive = simultaneous = 0.
            for row in by_step:
                k = int(row['step'])
                overlap = max(0., min((m + 1) * 365 / 12, (k + 1) * 365 / nt)
                              - max(m * 365 / 12, k * 365 / nt))
                weight = overlap / (365 / 12) / nc
                for key in FIELDS:
                    weighted[key] += float(row[key]) * weight
                active = float(row['gain_per_day']) > 0
                positive += active * weight
                simultaneous += (active and float(row['advection_positive_mm_day']) > 0) * weight
            for key, value in weighted.items():
                output_key = key.replace('_mm_day', '_mm_month')
                expected = value * 365 / 12 if key.endswith('_mm_day') else value
                np.testing.assert_allclose(float(month[output_key]), expected, rtol=1e-11, atol=1e-9)
                monthly_checks += 1
            for key, expected in [('import_positive_fraction', positive),
                                  ('simultaneous_import_positive_advection_fraction', simultaneous)]:
                np.testing.assert_allclose(float(month[key]), expected, rtol=1e-11, atol=1e-10)
                monthly_checks += 1
    actual_keys = [(r['region'], r['variant'], int(r['step']), int(r['row']), int(r['col'])) for r in steps]
    assert len(actual_keys) == len(set(actual_keys)) and set(actual_keys) == expected_keys
    assert len(months) == 36
    # Verify historical summaries by direct projection, keeping each epoch separate.
    for name, record in result['historical_separate_epochs'].items():
        if name == 'fitted_flux_20261103':
            assert record == json.loads((ROOT / f'output/{name}/result.json').read_text())
        else:
            original = json.loads((ROOT / f'output/{name}/review.json').read_text())
            for key, value in record.items():
                if key != 'profiles':
                    assert original[key] == value
            for profile, fields in record['profiles'].items():
                for key, value in fields.items():
                    assert original['screen'][profile][key] == value
    figure(months, plan['cases'])
    check_sources(result)
    write_json(OUT / 'review.json', dict(status='passed_independent_saved_trace_review',
        results_sha256=file_hash(OUT / 'results.json'), reviewer_sha256=file_hash(Path(__file__)),
        unique_cell_steps=len(steps), complete_case_months=len(months), independent_step_scalar_checks=scalar_checks,
        independent_monthly_scalar_checks=monthly_checks, historical_records_checked=4,
        figure_sha256=file_hash(OUT / 'seasonal_terms.png')))
    print(json.dumps(dict(cell_steps=len(steps), step_checks=scalar_checks, monthly_checks=monthly_checks)))


def figure(months, cases):
    fig, axes = plt.subplots(2, 3, figsize=(16, 8))
    names = ['Somalia · r58', 'Somalia · minimum turning', 'Sahara · r58']
    for col, (case, name) in enumerate(zip(cases, names, strict=True)):
        data = sorted([r for r in months if (r['region'], r['variant']) == (case['region'], case['variant'])],
                      key=lambda r:int(r['month']))
        x = np.arange(1, 13)
        lines = [([float(r['import_mm_month']) for r in data], 'Convergence import', '#317a8c', '-'),
                 ([float(r['advection_positive_mm_month']) + float(r['advection_negative_mm_month']) for r in data],
                  'Net concentration advection', '#647658', '-'),
                 ([float(r['drying_mm_month']) for r in data], 'Column drying', '#b47552', '-'),
                 ([-float(r['rain_mm_month']) for r in data], 'Rain sink', '#555555', '--')]
        for y, label, color, style in lines:
            axes[0, col].plot(x, y, color=color, linestyle=style, linewidth=1.7, label=label)
        axes[0, col].axhline(0, color='#777777', linewidth=.6)
        axes[0, col].set(title=name, ylabel='Selected signed terms (mm/model month)')
        axes[1, col].plot(x, [float(r['gain_per_day']) for r in data], color='#317a8c', label='Import gain')
        axes[1, col].plot(x, [float(r['sink_per_day']) for r in data], color='#b47552', label='Drying sink')
        axes[1, col].set(xlabel='Production month', ylabel='Coefficient (1/day)', ylim=(0, None))
        for ax in axes[:, col]:
            ax.set_xticks([1, 3, 5, 7, 9, 11])
            ax.grid(alpha=.15)
    axes[0, 0].legend(fontsize=8, loc='lower left')
    axes[1, 0].legend(fontsize=8)
    fig.suptitle('Convergence import is active throughout Somalia’s baseline year', fontsize=15)
    fig.text(.5, .035, 'Existing instantaneous traces integrated into model months; independent vertical drying can coexist with import.\n'
             'Selected local concentration-form terms, not a complete conservative budget or causal rainfall attribution. No new climate integration.',
             ha='center', fontsize=9)
    fig.subplots_adjust(left=.065, right=.98, top=.90, bottom=.15, hspace=.29, wspace=.30)
    fig.savefig(OUT / 'seasonal_terms.png', dpi=160)
    plt.close(fig)


def seal():
    assert not (OUT / 'qualification.json').exists()
    result = json.loads((OUT / 'results.json').read_text())
    check_sources(result)
    record = json.loads((OUT / 'review.json').read_text())
    assert record['results_sha256'] == file_hash(OUT / 'results.json')
    assert record['reviewer_sha256'] == file_hash(Path(__file__))
    assert record['figure_sha256'] == file_hash(OUT / 'seasonal_terms.png')
    report = ROOT / 'calibration/convergence_import_audit_20261126/findings.md'
    write_json(OUT / 'qualification.json', dict(status='passed_exploratory_diagnostic_no_adoption',
        sources_sha256={**result['sources_sha256'], str(Path(__file__).relative_to(ROOT)):file_hash(Path(__file__)),
                        str(report.relative_to(ROOT)):file_hash(report)},
        files_sha256={name:file_hash(OUT / name) for name in ['preparation.json', 'steps.csv', 'months.csv', 'results.json', 'review.json', 'seasonal_terms.png']},
        exact_float32_reconstruction_scalars=result['exact_float32_reconstruction_scalars'],
        independent_step_scalar_checks=record['independent_step_scalar_checks'],
        independent_monthly_scalar_checks=record['independent_monthly_scalar_checks'],
        historical_separate_epochs=True, figure_visually_inspected=True,
        climate_integrations=0, physical_source_files_changed=False, climate_adopted=False, atlas_changed=False))
    print('Qualified convergence-import diagnostic; no physical change or adoption.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    args = parser.parse_args()
    (seal if args.seal else review)()
