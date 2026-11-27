"""Plot reviewed local source changes; no model imports or integrations."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/padding_budget_capture_20261127'
LABELS = dict(evaporation='Surface evaporation', marine_exchange='Marine humidity exchange',
    column_drying='Total linear drying', convergence_import='Convergence import',
    advection='Advection', diffusion='Diffusion', storm_exchange='Storm exchange')


def main():
    review_path = OUT / 'review.json'
    review = json.loads(review_path.read_text())
    assert review['status'] == 'reviewed_exact_diagnostic_replays_not_climate_qualification'
    assert not (OUT / 'term_changes.png').exists(), 'Preserve completed figure'
    for name, expected in review['files_sha256'].items():
        assert hashlib.sha256((OUT / name).read_bytes()).hexdigest() == expected
    rows = review['endpoint_differences']
    assert [r['region'] for r in rows] == ['s_2n_43e', 'u_21n_21e', 'north_india']
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    csv_rows = []
    for ax, row, title in zip(axes, rows, ['Somalia', 'Sahara', 'North India'], strict=True):
        delta = row['annual_changes_mm']
        values = [delta[k] for k in LABELS]
        assert np.isfinite(values + [delta['rain'], delta['residual']]).all()
        y = np.arange(len(values))
        ax.barh(y, values, color=['#377d8d' if v >= 0 else '#b47552' for v in values])
        ax.scatter([delta['rain']], [len(values) + .3], marker='D', color='#222222', label='Rain change')
        ax.axvline(0, color='#777777', linewidth=.8)
        ax.set(yticks=[*y, len(values) + .3], yticklabels=[*LABELS.values(), 'Rain'],
               xlabel='Change (mm/model year)', title=title)
        ax.invert_yaxis()
        ax.grid(axis='x', alpha=.15)
        ax.set_axisbelow(True)
        ax.tick_params(axis='y', labelsize=8)
        ax.margins(x=.20)
        for yy, value in zip([*y, len(values) + .3], [*values, delta['rain']], strict=True):
            ax.annotate(f'{value:+.1f}', xy=(value, yy), xytext=(4 if value >= 0 else -4, 0),
                        textcoords='offset points', va='center', ha='left' if value >= 0 else 'right', fontsize=8)
        for name, value in delta.items():
            csv_rows.append(dict(region=row['region'], component=name, change_mm_year=value))
    fig.suptitle('Coupled local moisture changes: 4012 km minus 1100 km padding', fontsize=15)
    fig.text(.5, .035, 'Identical physical replay and scored locations. Positive bars add to the local equation; negative bars remove.\n'
             'Rain change = sum of seven source changes minus residual change. Components respond together; these are not isolated causal effects or a global water budget.',
             ha='center', fontsize=9)
    fig.subplots_adjust(left=.13, right=.97, top=.86, bottom=.18, wspace=.80)
    fig.savefig(OUT / 'term_changes.png', dpi=160)
    plt.close(fig)
    with (OUT / 'term_changes.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['region', 'component', 'change_mm_year'])
        writer.writeheader()
        writer.writerows(csv_rows)
    (OUT / 'figure_provenance.json').write_text(json.dumps(dict(
        review_sha256=hashlib.sha256(review_path.read_bytes()).hexdigest(),
        plotter_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        figure_sha256=hashlib.sha256((OUT / 'term_changes.png').read_bytes()).hexdigest(),
        table_sha256=hashlib.sha256((OUT / 'term_changes.csv').read_bytes()).hexdigest(),
        integrations=0, climate_adopted=False), indent=2) + '\n')


if __name__ == '__main__':
    main()
