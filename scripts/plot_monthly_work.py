"""Show fixed-plan refusals and the monthly collector-hour bottleneck."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from settlement_locations_earth import sha


def main():
    out = ROOT / 'output/settlement_monthly_work_20261112'
    result = json.loads((out / 'results.json').read_text()); review = json.loads((out / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(out / 'results.json')
    fields = dict(np.load(out / 'fields.npz'))
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(14, 6.4)); paper = '#f5f3ed'; fig.patch.set_facecolor(paper)
    for a in (ax, bx):
        a.set_facecolor(paper)
    cases = [f'{m}_h{h}_f0.075' for m in ('raw', 'corrected') for h in (600, 300)]
    rows = {(r['parent'], r['load_kcal'], r['availability']): r for r in result['rows']}
    yy = np.arange(4)
    for j, (load, color) in enumerate([(60000., '#ad643b'), (120000., '#467c88')]):
        values = [rows[(c, load, 'all_open')]['qualified_active_sites'] for c in cases]
        pos = yy + (j - .5) * .3
        ax.barh(pos, values, height=.28, color=color, label=f'{int(load):,} kcal / collector trip')
        for y, v in zip(pos, values):
            ax.text(v + 8, y, str(v), va='center', fontsize=9)
    original = [rows[(c, 120000., 'all_open')]['original_active_sites'] for c in cases]
    ax.scatter(original, yy, color='#45544e', marker='|', s=250, label='Original food-supported staff sites')
    ax.set_yticks(yy, ['Raw · 600 farm hours', 'Raw · 300 farm hours', 'Corrected · 600 farm hours', 'Corrected · 300 farm hours'])
    ax.invert_yaxis(); ax.set_xlim(0, 1000); ax.set_xlabel('Staffed sites passing every monthly collection bound')
    ax.set_title('Fixed grain shipments; all collection months open', loc='left', fontsize=12)
    ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True); ax.legend(loc='lower left', bbox_to_anchor=(0, -.35), frameon=False, fontsize=9)
    for load, color in [(60000, '#ad643b'), (120000, '#467c88')]:
        key = f'corrected_h600_f0.075_load{load}_all_open'
        required = fields[key + '__required_collection_hours'].sum(axis=1) / 1e6
        bx.plot(np.arange(1, 13), required, marker='o', ms=4, color=color, label=f'Required at {load:,} kcal / trip')
    gross = fields['corrected_h600_f0.075_load120000_all_open__gross_hours'].sum(axis=1) / 1e6
    bx.plot(np.arange(1, 13), gross, color='#45544e', linestyle='--', label='All supported staff hours')
    bx.set(xlim=(.7, 12.3), xticks=np.arange(1, 13), xlabel='Calendar bin (1–12)', ylabel='Collector hours / million',
           title='Corrected · 600 farm hours: aggregate diagnostic')
    bx.grid(alpha=.15); bx.legend(frameon=False, fontsize=9, loc='upper right')
    fig.suptitle('Food support alone does not fund grain collection and other duties', x=.045, y=.98, ha='left', fontsize=16)
    fig.text(.045, .075,
        'All 16 cases retained. Closing bins 7–9 refuses every fixed case. Seven walking hours/day; supplied loads and 600 staff hours/year.\n'
        'Aggregate hours cannot be pooled across sites or months. Fixed shipments may include surplus destination food.\n'
        'Scenario refusals do not establish zero residents or authority. No food reallocation, new reach map or default adoption.',
        fontsize=9, color='#445451')
    fig.subplots_adjust(left=.15, right=.98, top=.82, bottom=.33, wspace=.35)
    path = ROOT / 'reports/figures/settlement_monthly_work_20261112.png'; fig.savefig(path, dpi=160, facecolor=paper); plt.close(fig)
    print(path)


if __name__ == '__main__':
    main()
