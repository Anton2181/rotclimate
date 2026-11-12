"""Show held-province density errors without turning extrapolations into censuses."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha


def main():
    out = ROOT / 'output/settlement_housing_diagnostic_20261112'
    result = json.loads((out / 'results.json').read_text())
    review = json.loads((out / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(out / 'results.json')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 6.5))
    paper = '#f5f3ed'; fig.patch.set_facecolor(paper)
    for a in (ax, bx):
        a.set_facecolor(paper)
    area = result['cohorts'][0]['models'][1]
    sources = {r['city_key']: r for r in result['source_rows']}
    x = np.exp([r['observed_log_property_density'] for r in area['predictions']])
    y = np.exp([r['predicted_log_property_density'] for r in area['predictions']])
    coverage = [sources[r['city_key']]['sample_fraction'] * 100 for r in area['predictions']]
    points = ax.scatter(x, y, c=coverage, norm=LogNorm(vmin=.025, vmax=100), cmap='viridis',
                        s=45, edgecolors='white', linewidths=.5, zorder=3)
    ax.plot([7, 110], [7, 110], color='#8a928d', linestyle='--', linewidth=1)
    ax.set(xscale='log', yscale='log', xlim=(7, 110), ylim=(7, 110),
           xlabel='Encountered properties / investigated hectare',
           ylabel='Held-province prediction (properties / hectare)',
           title='Area model: all 50 city observations')
    ax.grid(alpha=.15, which='both')
    fig.colorbar(points, ax=ax, shrink=.7, pad=.02, label='Investigated fraction (%)')
    models = ['Constant density', 'Area', 'Area + coverage']
    colors = ['#899087', '#467c88', '#ad643b']
    for i, cohort in enumerate(result['cohorts'][:2]):
        for j, model in enumerate(cohort['models']):
            value = model['metrics']['mean_absolute_log_error']
            pos = i + (j - 1) * .23
            bx.bar(pos, value, width=.21, color=colors[j], label=models[j] if i == 0 else None)
            bx.text(pos, value + .009, f'{value:.3f}', ha='center', fontsize=9)
    bx.set(xticks=[0, 1], xticklabels=['All 50 cities\n23 held provinces', 'Coverage ≥1%: 26 cities\n16 held provinces'],
           ylim=(0, .69), ylabel='Mean absolute log density error (lower is better)',
           title='All coefficients fitted without the test province')
    bx.legend(frameon=False, loc='upper right', fontsize=9)
    bx.grid(axis='y', alpha=.15); bx.set_axisbelow(True)
    fig.text(.56, .17, 'Coverage ≥10%: 11 cities; unscored by frozen minimum.\nDifferent cohorts have different targets.',
             fontsize=9, color='#445451')
    fig.suptitle('Housing density: modest average gain, unresolved measurement', x=.055, ha='left', y=.97, fontsize=16)
    fig.text(.055, .065,
             'Area lowers average error but slightly worsens median error on all 50 cities. No AD150 size labels qualify.\n'
             'Selected mixed-period development archive; province blocking does not certify transfer or sampling.\n'
             'Source: Ortman & Hanson (2023), Table 2 · doi:10.1017/S0068113X23000375 · CC BY 4.0',
             fontsize=9, color='#445451')
    fig.subplots_adjust(left=.07, right=.98, top=.83, bottom=.29, wspace=.42)
    path = ROOT / 'reports/figures/settlement_housing_diagnostic_20261112.png'
    fig.savefig(path, dpi=160, facecolor=paper); plt.close(fig)
    print(path)


if __name__ == '__main__':
    main()
