"""Common-unit panels for the declared maximum matched annual contrasts."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/annual_assumption_impact_20261117'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    assert not (OUT / 'presentation.json').exists()
    review = json.loads((OUT / 'review.json').read_text())
    assert review['status'].startswith('passed_exhaustive')
    assert review['results_sha256'] == sha(OUT / 'results.json')
    with (OUT / 'rankings.csv').open() as f:
        rows = list(csv.DictReader(f))
    factors = ['density', 'extraction', 'hours_worker_year']
    labels = ['Urban density', 'Marketed share', 'Listed field hours']
    colours = ['#426d94', '#b57927', '#458169']
    panels = [('residents', 1e6, 'Town residents\n(million)'),
              ('coverage_percentage_points', 1, 'Grain coverage\n(percentage points)'),
              ('rural_shortfall_person_years', 1e3, 'Rural grain shortfall\n(thousand ration-years)')]
    fig, axes = plt.subplots(2, 3, figsize=(13.5, 7.5))
    fig.subplots_adjust(left=.14, right=.98, top=.79, bottom=.20, wspace=.35, hspace=.65)
    plotted = []
    for j, (metric, scale, title) in enumerate(panels):
        maximum = max(float(r['max_absolute_delta']) / scale for r in rows if r['model'] == 'candidate' and r['outcome'] == metric)
        for i, climate in enumerate(['raw', 'corrected']):
            ax = axes[i, j]
            values = []
            for factor in factors:
                row = next(r for r in rows if (r['model'], r['climate'], r['outcome'], r['factor']) == ('candidate', climate, metric, factor))
                value = float(row['max_absolute_delta'])
                plotted.append(dict(climate=climate, outcome=metric, factor=factor, absolute_delta=value, display_scale=scale))
                values.append(value / scale)
            ax.barh(range(3), values, color=colours, height=.58)
            for k, value in enumerate(values):
                ax.text(value + maximum * .025, k, f'{value:.2f}', va='center', fontsize=10)
            ax.set_yticks(range(3), labels if j == 0 else ['', '', ''])
            ax.invert_yaxis(); ax.set_xlim(0, maximum * 1.23)
            ax.spines[['top', 'right']].set_visible(False)
            ax.grid(axis='x', alpha=.18); ax.set_axisbelow(True)
            ax.set_title(f'{climate.capitalize()} · {title}', fontsize=11, pad=12)
    fig.suptitle('Annual atlas assumptions: largest matched change in existing cases', fontsize=17, x=.53, y=.97)
    fig.text(.14, .885, 'Candidate cohort · fixed climate within each pair · one input changed at a time', fontsize=12)
    fig.text(.14, .065,
             'Absolute scenario differences, not measured uncertainty. Each panel has its own units; raw/corrected scales match.\n'
             'Density: flat 100 vs sliding 100–500 people/ha. Marketed share: 10–33.719%. Field allowance: 300–600 h/worker.\n'
             'Hours contrasts exist only at 33.719% marketed share. Annual grain support is not a complete diet or seasonal guarantee.',
             fontsize=10, linespacing=1.6)
    fig.savefig(OUT / 'assumption_impacts.png', dpi=160, facecolor='white')
    plt.close(fig)
    (OUT / 'presentation.json').write_text(json.dumps(dict(results_sha256=sha(OUT / 'results.json'),
        review_sha256=sha(OUT / 'review.json'), renderer_sha256=sha(Path(__file__)),
        figure_sha256=sha(OUT / 'assumption_impacts.png'), plotted_values=plotted), indent=2) + '\n')
    print('Rendered 18 already reviewed contrast maxima')


if __name__ == '__main__':
    main()
