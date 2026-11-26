"""Independently check saved-field marine paths and report their limits."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from local_benchmark_protocol import file_hash, write_json

OUT = ROOT / 'output/marine_gate_audit_20261126'
PARENT = ROOT / 'output/somalia_mechanism_20261126'
TRACE = ROOT / 'output/somalia_transport_trace_20261126'
CAPTURE = ROOT / 'output/somalia_marine_exchange_trace_20261126'
LABELS = ['quarter_cell', 'eighth_cell']
STATUSES = ['sea_reached', 'off_domain', 'calm', 'land_through_horizon']


def scalar_path(land, u, v, row, col, step, horizon):
    """Manual bilinear scalar reference; no production path/geometry helper."""
    ny, nx = land.shape
    r, c, distance = float(row), float(col), 0.

    def sample(field):
        y, x = min(max(r, 0.), ny - 1.), min(max(c, 0.), nx - 1.)
        y0, x0 = math.floor(y), math.floor(x)
        y1, x1 = min(y0 + 1, ny - 1), min(x0 + 1, nx - 1)
        dy, dx = y - y0, x - x0
        return ((1 - dy) * ((1 - dx) * field[y0, x0] + dx * field[y0, x1])
                + dy * ((1 - dx) * field[y1, x0] + dx * field[y1, x1]))

    for _ in range(math.ceil(horizon / step)):
        ue, vn = sample(u), sample(v)
        speed = math.hypot(ue, vn)
        if speed < 1e-6:
            return 'calm', distance, -1, -1
        ds = min(step, horizon - distance)
        r += vn / speed * ds / 56.
        c -= ue / speed * ds / 56.
        distance += ds
        if not (-.5 < r < ny - .5 and -.5 < c < nx - .5):
            return 'off_domain', distance, -1, -1
        ri, ci = math.floor(r + .5), math.floor(c + .5)
        if not land[ri, ci]:
            return 'sea_reached', distance, ri, ci
    return 'land_through_horizon', distance, -1, -1


def check_sources(result):
    for name, digest in result['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in result['files_sha256'].items():
        assert file_hash(OUT / name) == digest, name


def review():
    assert not (OUT / 'review.json').exists(), 'Preserve completed review'
    result = json.loads((OUT / 'results.json').read_text())
    check_sources(result)
    plan = json.loads((ROOT / 'calibration/marine_gate_audit_20261126/plan.json').read_text())
    with (OUT / 'cell_months.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    expected_keys = set()
    checked_paths = checked_scalars = 0
    summaries = []
    for case, summary in zip(plan['cases'], result['summaries'], strict=True):
        region, variant = case['region'], case['variant']
        assert (region, variant) == (summary['region'], summary['variant'])
        with np.load(PARENT / region / variant / 'fields.npz') as z:
            fields = dict(z)
        with np.load(TRACE / region / variant / 'trace.npz') as z:
            trace = dict(z)
        with np.load(CAPTURE / region / variant / 'capture.npz') as z:
            capture = dict(z)
        np.testing.assert_array_equal(trace['days'], capture['days'])
        starts = list(zip(*np.nonzero(fields['mask'])))
        index = {pair: k for k, pair in enumerate(starts)}
        sea = np.column_stack(np.nonzero(~fields['land']))
        assert len(sea) and summary['has_in_domain_sea']
        nt = len(trace['days'])
        weights = np.array([[max(0., min((m + 1) / 12, (k + 1) / nt)
                                       - max(m / 12, k / nt)) * 12
                             for k in range(nt)] for m in range(12)])
        selected = [r for r in rows if (r['region'], r['variant']) == (region, variant)]
        for m in range(1, 13):
            expected_keys.update((region, variant, m, int(r), int(c)) for r, c in starts)
        for row in selected:
            m, r, c = int(row['month']) - 1, int(row['row']), int(row['col'])
            k = index[r, c]
            ne, nn = float(row['inward_normal_east']), float(row['inward_normal_north'])
            distance = float(np.sqrt(((sea - [r, c]) ** 2).sum(axis=1)).min() * 56.)
            instant_gate = np.clip((trace['trace__moisture_u'][:, k] * ne
                                   + trace['trace__moisture_v'][:, k] * nn) / 3, 0, 1)
            values = {
                'sea_distance_km': distance,
                'local_gate_of_monthly_mean': np.clip((fields['u'][m, r, c] * ne
                                                       + fields['v'][m, r, c] * nn) / 3, 0, 1),
                'mean_instantaneous_production_gate': weights[m] @ instant_gate,
                'positive_marine_exchange_mm': weights[m] @ np.maximum(capture['marine'][:, k], 0) * 365 / 12,
                'negative_marine_exchange_mm': weights[m] @ np.minimum(capture['marine'][:, k], 0) * 365 / 12,
            }
            assert row['nearest_index_is_real_sea'] == 'True'
            for key, value in values.items():
                np.testing.assert_allclose(float(row[key]), value, atol=1e-9, rtol=1e-11)
                checked_scalars += 1
            for label, step in zip(LABELS, result['path_steps_km'], strict=True):
                status, length, sr, sc = scalar_path(fields['land'], fields['u'][m], fields['v'][m],
                                                     r, c, step, result['path_horizon_km'])
                assert status == row[label + '_status'], (region, variant, m, r, c, label)
                np.testing.assert_allclose(length, float(row[label + '_distance_km']), atol=1e-8, rtol=1e-11)
                assert (sr, sc) == (int(row[label + '_sea_row']), int(row[label + '_sea_col']))
                checked_paths += 1
        for key, sign in [('positive_marine_annual_mean_mm', 1), ('negative_marine_annual_mean_mm', -1)]:
            expected = float((np.maximum(capture['marine'], 0) if sign == 1
                              else np.minimum(capture['marine'], 0)).mean() * 365)
            np.testing.assert_allclose(summary[key], expected, atol=1e-9, rtol=1e-11)
        for label in LABELS:
            for status in STATUSES:
                group = [r for r in selected if r[label + '_status'] == status]
                reported = summary['paths_by_step'][label][status]
                assert reported['cell_months'] == len(group)
                assert reported['positive_local_gate_rows'] == sum(float(r['local_gate_of_monthly_mean']) > 0 for r in group)
        summaries.append(dict(region=region, variant=variant, scalar_paths_checked=len(selected) * 2,
                              cell_month_rows=len(selected)))
    actual = [(r['region'], r['variant'], int(r['month']), int(r['row']), int(r['col'])) for r in rows]
    assert len(actual) == len(set(actual)) and set(actual) == expected_keys
    figure(result, rows)
    check_sources(result)
    write_json(OUT / 'review.json', dict(status='passed_independent_saved_field_review',
        results_sha256=file_hash(OUT / 'results.json'), reviewer_sha256=file_hash(Path(__file__)),
        figure_sha256=file_hash(OUT / 'marine_access.png'), independent_scalar_paths=checked_paths,
        independent_cell_month_scalars=checked_scalars, complete_unique_cell_months=len(rows), cases=summaries))
    print(json.dumps(dict(paths=checked_paths, scalars=checked_scalars, cell_months=len(rows))))


def figure(result, rows):
    names = ['Somalia\nr58', 'Somalia\nturning', 'Sahara\nr58']
    colors = ['#377d8d', '#b3b3b3', '#bf996a', '#d1b152']
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.7))
    x = np.arange(3)
    for offset, label, alpha in [(-.18, LABELS[0], 1.), (.18, LABELS[1], .65)]:
        bottom = np.zeros(3)
        for status, color in zip(STATUSES, colors):
            height = np.array([s['paths_by_step'][label][status]['cell_months'] / s['cell_month_rows'] * 100
                               for s in result['summaries']])
            axes[0].bar(x + offset, height, .32, bottom=bottom, color=color, alpha=alpha,
                        label=status.replace('_', ' ') if offset < 0 else None)
            bottom += height
    axes[0].set(xticks=x, xticklabels=names, ylabel='Scored cell-months (%)', ylim=(0, 105),
                title='Monthly backward-flow access\nLeft: 14 km steps; right: 7 km')
    axes[0].legend(fontsize=8, loc='lower left')
    for summary, name, color in zip(result['summaries'], names, ['#377d8d', '#bd7750', '#647658']):
        group = [r for r in rows if (r['region'], r['variant']) == (summary['region'], summary['variant'])]
        axes[1].scatter([float(r['local_gate_of_monthly_mean']) for r in group],
                        [float(r['mean_instantaneous_production_gate']) for r in group],
                        s=10, alpha=.5, color=color, label=name.replace('\n', ' · '))
    axes[1].plot([0, 1], [0, 1], color='#555555', linewidth=.8)
    axes[1].set(xlim=(-.03, 1.03), ylim=(-.03, 1.03), xlabel='Gate applied to monthly mean wind',
                ylabel='Monthly mean of instantaneous gate', title='Temporal averaging changes the gate')
    axes[1].legend(fontsize=8)
    positive = [s['positive_marine_annual_mean_mm'] for s in result['summaries']]
    negative = [s['negative_marine_annual_mean_mm'] for s in result['summaries']]
    axes[2].bar(x, positive, .55, color='#377d8d', label='Positive instantaneous exchange')
    axes[2].bar(x, negative, .55, color='#bd7750', label='Negative instantaneous exchange')
    axes[2].axhline(0, color='#555555', linewidth=.8)
    axes[2].set(xticks=x, xticklabels=names, ylabel='Captured marine exchange (mm/year)',
                title='Actual source and sink cancel seasonally')
    axes[2].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis='y', alpha=.14)
        ax.set_axisbelow(True)
    fig.suptitle('Saved fields give little support for a false marine-access explanation in Somalia', fontsize=14)
    fig.text(.5, .04, 'Monthly frozen surface-flow proxy, finite 1,701 km horizon; domain exits remain unknown.\n'
             'All three domains contain real sea cells. No new climate runs, physical change, rainfall attribution or adoption.',
             ha='center', fontsize=9)
    fig.subplots_adjust(left=.06, right=.985, top=.81, bottom=.21, wspace=.36)
    fig.savefig(OUT / 'marine_access.png', dpi=160)
    plt.close(fig)


def seal():
    assert not (OUT / 'qualification.json').exists()
    result = json.loads((OUT / 'results.json').read_text())
    check_sources(result)
    review_record = json.loads((OUT / 'review.json').read_text())
    assert review_record['results_sha256'] == file_hash(OUT / 'results.json')
    assert review_record['reviewer_sha256'] == file_hash(Path(__file__))
    assert review_record['figure_sha256'] == file_hash(OUT / 'marine_access.png')
    report = ROOT / 'calibration/marine_gate_audit_20261126/findings.md'
    test = ROOT / 'tests/test_marine_access.py'
    write_json(OUT / 'qualification.json', dict(status='passed_saved_field_diagnostic_no_adoption',
        sources_sha256={**result['sources_sha256'], str(Path(__file__).relative_to(ROOT)):file_hash(Path(__file__)),
                        str(report.relative_to(ROOT)):file_hash(report), str(test.relative_to(ROOT)):file_hash(test)},
        files_sha256={n:file_hash(OUT / n) for n in ['preparation.json', 'cell_months.csv', 'results.json', 'review.json', 'marine_access.png']},
        independent_scalar_paths=review_record['independent_scalar_paths'],
        independent_cell_month_scalars=review_record['independent_cell_month_scalars'],
        figure_visually_inspected=True, synthetic_geometry_tests=8,
        climate_integrations=0, physical_source_files_changed=False, climate_adopted=False, atlas_changed=False))
    print('Qualified saved-field audit; no climate change or adoption.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    args = parser.parse_args()
    (seal if args.seal else review)()
