"""Check Gaussian support and stress cases with explicit kernel matrices."""
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

OUT = ROOT / 'output/convergence_boundary_audit_20261126'
PARENT = ROOT / 'output/somalia_mechanism_20261126'
MODES = ['reflect', 'nearest', 'constant']


def kernel_matrix(size, sigma, mode):
    """Explicit finite Gaussian, no SciPy filtering/boundary helper."""
    radius = math.floor(4 * sigma + .5)
    taps = list(range(-radius, radius + 1))
    weights = [math.exp(-.5 * (offset / sigma) ** 2) for offset in taps]
    normalization = sum(weights)
    matrix = np.zeros((size, size))
    for target in range(size):
        for offset, weight in zip(taps, weights):
            source = target + offset
            if mode == 'reflect':
                source %= 2 * size
                if source >= size:
                    source = 2 * size - 1 - source
            elif mode == 'nearest':
                source = min(max(source, 0), size - 1)
            elif mode == 'constant':
                if not 0 <= source < size:
                    continue
            else:
                raise ValueError(mode)
            matrix[target, source] += weight / normalization
    return matrix


def manual_divergence(u, v):
    east, north = np.empty_like(u, dtype=float), np.empty_like(v, dtype=float)
    east[:, 1:-1] = .5 * (u[:, 2:] - u[:, :-2])
    east[:, 0], east[:, -1] = u[:, 1] - u[:, 0], u[:, -1] - u[:, -2]
    north[1:-1] = .5 * (v[2:] - v[:-2])
    north[0], north[-1] = v[1] - v[0], v[-1] - v[-2]
    return (east - north) / 56000.


def check_sources(result):
    for name, digest in result['sources_sha256'].items():
        assert file_hash(ROOT / name) == digest, name
    for name, digest in result['files_sha256'].items():
        assert file_hash(OUT / name) == digest, name


def review():
    assert not (OUT / 'review.json').exists()
    result = json.loads((OUT / 'results.json').read_text())
    check_sources(result)
    with (OUT / 'cell_months.csv').open() as stream:
        rows = list(csv.DictReader(stream))
    expected_keys = set()
    checks = 0
    maximum_filter_difference = 0.
    for summary in result['summaries']:
        region, variant = summary['region'], summary['variant']
        with np.load(PARENT / region / variant / 'fields.npz') as packet:
            f = dict(packet)
        ny, nx = f['mask'].shape
        indices = list(zip(*np.nonzero(f['mask'])))
        matrices = {mode:(kernel_matrix(ny, result['sigma_cells'], mode),
                          kernel_matrix(nx, result['sigma_cells'], mode)) for mode in MODES}
        for mode in ['reflect', 'nearest']:
            for matrix in matrices[mode]:
                np.testing.assert_allclose(matrix.sum(axis=1), 1., atol=1e-14, rtol=0)
        mass = np.outer(matrices['constant'][0].sum(axis=1), matrices['constant'][1].sum(axis=1))
        selected = [r for r in rows if (r['region'], r['variant']) == (region, variant)]
        for m in range(12):
            divergence = manual_divergence(f['u'][m].astype(float), f['v'][m].astype(float))
            smoothed = {mode:my @ divergence @ mx.T for mode, (my, mx) in matrices.items()}
            for r, c in indices:
                expected_keys.add((region, variant, m + 1, int(r), int(c)))
            for row in [r for r in selected if int(r['month']) == m + 1]:
                r, c = int(row['row']), int(row['col'])
                for key, expected in [('nominal_in_domain_kernel_mass', mass[r, c]),
                                      ('nominal_exterior_kernel_mass', 1 - mass[r, c]),
                                      ('monthly_raw_divergence_per_s', divergence[r, c])]:
                    np.testing.assert_allclose(float(row[key]), expected, rtol=1e-12, atol=1e-15)
                    checks += 1
                for mode in MODES:
                    value = smoothed[mode][r, c]
                    actual = float(row[mode + '_smoothed_divergence_per_s'])
                    maximum_filter_difference = max(maximum_filter_difference, abs(actual - value))
                    np.testing.assert_allclose(actual, value, rtol=1e-11, atol=1e-19)
                    np.testing.assert_allclose(float(row[mode + '_positive_convergence_proxy_per_day']),
                                               min(max(-value, 0), 1e-5) * 86400, rtol=1e-11, atol=1e-13)
                    checks += 2
        exterior = 1 - mass[f['mask']]
        for name, expected in [('min', exterior.min()), ('mean', exterior.mean()), ('max', exterior.max())]:
            np.testing.assert_allclose(summary['nominal_exterior_kernel_mass'][name], expected, atol=1e-14)
        assert len(selected) == summary['cell_month_rows'] == len(indices) * 12
        reference = np.array([float(r['reflect_smoothed_divergence_per_s']) for r in selected])
        for mode in MODES:
            values = np.array([float(r[mode + '_smoothed_divergence_per_s']) for r in selected])
            record = summary['extensions'][mode]
            expected = dict(mean_signed_divergence_per_s=float(values.mean()),
                mean_positive_convergence_proxy_per_day=float(np.clip(-values, 0, 1e-5).mean() * 86400),
                mean_absolute_difference_from_reflect_per_s=float(np.abs(values - reference).mean()))
            for name, value in expected.items():
                np.testing.assert_allclose(record[name], value, atol=1e-19, rtol=1e-12)
            assert record['sign_disagreement_cell_months'] == np.count_nonzero(np.sign(values) != np.sign(reference))
    actual_keys = [(r['region'], r['variant'], int(r['month']), int(r['row']), int(r['col'])) for r in rows]
    assert len(actual_keys) == len(set(actual_keys)) and set(actual_keys) == expected_keys
    figure(result)
    check_sources(result)
    write_json(OUT / 'review.json', dict(status='passed_independent_explicit_kernel_review',
        results_sha256=file_hash(OUT / 'results.json'), reviewer_sha256=file_hash(Path(__file__)),
        figure_sha256=file_hash(OUT / 'boundary_support.png'), unique_cell_months=len(rows),
        independent_scalar_checks=checks, manual_separable_filter_cell_month_checks=len(rows) * 3,
        maximum_filter_difference_per_s=maximum_filter_difference, no_boundary_mode_selected=True))
    print(json.dumps(dict(rows=len(rows), checks=checks, maximum_filter_difference_per_s=maximum_filter_difference)))


def figure(result):
    summaries = result['summaries']
    fig, axes = plt.subplots(1, 3, figsize=(16, 6.5))
    names = ['Somalia\nr58', 'Somalia\nturning', 'Sahara\nr58']
    x = np.arange(3)
    exterior = np.array([r['nominal_exterior_kernel_mass']['mean'] for r in summaries])
    axes[0].bar(x, (1 - exterior) * 100, .55, color='#377d8d', label='Nominal in-domain kernel mass')
    axes[0].bar(x, exterior * 100, .55, bottom=(1 - exterior) * 100, color='#b5a071', label='Exterior continuation')
    axes[0].set(xticks=x, xticklabels=names, ylim=(0, 105), ylabel='Nominal kernel weight (%)',
                title='Most nominal support extends beyond grid')
    axes[0].legend(fontsize=8, loc='lower left')
    for offset, mode, label, color in [(-.24, 'reflect', 'Reflect (production)', '#377d8d'),
                                      (0, 'nearest', 'Nearest edge value', '#b47552'),
                                      (.24, 'constant', 'Zero exterior divergence', '#647658')]:
        axes[1].bar(x + offset, [r['extensions'][mode]['mean_positive_convergence_proxy_per_day'] for r in summaries],
                    .22, color=color, label=label)
        axes[2].bar(x + offset, [r['extensions'][mode]['sign_disagreement_cell_months'] / r['cell_month_rows'] * 100
                                 for r in summaries], .22, color=color)
    axes[1].set(xticks=x, xticklabels=names, ylabel='Clipped monthly convergence proxy (1/day)',
                title='Same monthly winds, different extensions')
    axes[1].legend(fontsize=8)
    axes[2].set(xticks=x, xticklabels=names, ylabel='Cell-months with differing sign (%)',
                title='Signed divergence can change sign')
    for ax in axes:
        ax.grid(axis='y', alpha=.14)
        ax.set_axisbelow(True)
    fig.suptitle('The 2,000 km convergence filter is sensitive to regional continuation', fontsize=15)
    fig.text(.5, .04, '45 × 45 cells at 56 km; Gaussian σ = 2,000 km, nominal four-sigma support ≈ 8,000 km.\n'
             'Frozen monthly fields only: alternative extensions are stress assumptions, not known outside winds, actual gain or predicted rainfall.',
             ha='center', fontsize=9)
    fig.subplots_adjust(left=.065, right=.98, top=.83, bottom=.21, wspace=.34)
    fig.savefig(OUT / 'boundary_support.png', dpi=160)
    plt.close(fig)


def seal():
    assert not (OUT / 'qualification.json').exists()
    result = json.loads((OUT / 'results.json').read_text())
    check_sources(result)
    record = json.loads((OUT / 'review.json').read_text())
    assert record['results_sha256'] == file_hash(OUT / 'results.json')
    assert record['reviewer_sha256'] == file_hash(Path(__file__))
    assert record['figure_sha256'] == file_hash(OUT / 'boundary_support.png')
    report = ROOT / 'calibration/convergence_boundary_audit_20261126/findings.md'
    write_json(OUT / 'qualification.json', dict(status='passed_boundary_diagnostic_no_physical_adoption',
        sources_sha256={**result['sources_sha256'], str(Path(__file__).relative_to(ROOT)):file_hash(Path(__file__)),
                        str(report.relative_to(ROOT)):file_hash(report)},
        files_sha256={name:file_hash(OUT / name) for name in ['preparation.json', 'cell_months.csv', 'results.json', 'review.json', 'boundary_support.png']},
        independent_scalar_checks=record['independent_scalar_checks'],
        manual_separable_filter_cell_month_checks=record['manual_separable_filter_cell_month_checks'],
        figure_visually_inspected=True, no_boundary_mode_selected=True, climate_integrations=0,
        physical_source_files_changed=False, climate_adopted=False, atlas_changed=False))
    print('Qualified boundary diagnostic; no extension selected or climate changed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seal', action='store_true')
    args = parser.parse_args()
    (seal if args.seal else review)()
