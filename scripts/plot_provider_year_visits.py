"""Show point-task preservation from coherent complete provider-year calendars."""
import gzip
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_locations_earth import sha
from publish_network_duty_visits import point_image

OUT = ROOT / 'output/network_visit_year_complete_20261112'
PARENT = ROOT / 'output/network_duty_visits_20261112'
DATA = ROOT / 'atlases/earth_fit/data'


def plot():
    result = json.loads((OUT / 'results.json').read_text()); checked = json.loads((OUT / 'export_review.json').read_text())
    assert checked['status'] == 'passed' and checked['results_sha256'] == sha(OUT / 'results.json')
    fields = dict(np.load(OUT / 'fields.npz')); original = dict(np.load(PARENT / 'fields.npz'))
    meta = json.loads((DATA / 'atlas.json').read_text()); manifest = json.loads((DATA / 'network_visit_year_complete.json').read_text()); figures = []
    for mode in ('raw', 'corrected'):
        x = dict(np.load(ROOT / f'output/settlement_feedback_20261112/{mode}_inputs.npz')); paths = dict(np.load(PARENT / f'{mode}_paths.npz'))
        model = json.loads(gzip.decompress((DATA / manifest['packets'][mode]['payload']).read_bytes()))
        fig, axes = plt.subplots(2, 3, figsize=(15, 6.9), layout='constrained')
        for i, crew in enumerate((1, 4)):
            key = f'{mode}_h600_crew{crew}'; row = next(r for r in result['rows'] if r['key'] == key)
            for j, (visits, title) in enumerate([
                (original[key + '__served'], 'Original aggregate-hour-funded tasks'),
                (fields[key + '__baseline_served'], 'Collection-first twelve-bin gate'),
                (fields[key + '__served'], 'One coherent provider-year calendar')]):
                axes[i, j].imshow(point_image(x, paths, visits, model['actors'], meta))
                axes[i, j].set_title(f'{title}\nCrew {crew} · {int(visits.sum()):,} point visits', fontsize=10)
                axes[i, j].set_xticks([]); axes[i, j].set_yticks([])
            assert row['baseline_tasks_lost'] == 0
        fig.suptitle(f'{mode.title()} climate · 600 farm hours · baseline gated tasks retained by identity', fontsize=13)
        fig.supxlabel('Dots are qualified target-point tasks,not blocks or intervening territory. Size reflects bins;white centres indicate overlapping actors.\n'
            'The first column only checks pooled hours;the next two require every mandatory provider collection/service bin.\n'
            'Necessary delivery schedules under supplied availability,not complete annual food validation,observed staffing or authority.', fontsize=9)
        path = ROOT / f'reports/figures/network_visit_year_complete_{mode}_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); figures.append(path)
    rows = result['rows']; y = np.arange(8); labels = [f'{r["climate"].title()} · {r["hours_worker_year"]}h · crew {r["crew"]}' for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.1))
    for offset, field, label, color in [(-.23, 'original_funded_visits', 'Original pooled-hour plan', '#bab9ae'),
        (0., 'baseline_twelve_bin_visits', 'Collection-first twelve-bin gate', '#7c8780'), (.23, 'qualified_visits', 'Coherent provider-year selection', '#467f98')]:
        axes[0].barh(y + offset, [r[field] for r in rows], height=.22, label=label, color=color)
    gains = [r['added_visits'] for r in rows]; axes[1].barh(y, gains, color='#487e70')
    for i, value in enumerate(gains): axes[1].text(value + max(gains) * .02, i, f'+{value:,}', va='center', fontsize=9)
    axes[1].set_xlim(0, max(gains) * 1.22)
    for ax in axes:
        ax.set_yticks(y, labels); ax.invert_yaxis(); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    axes[0].set_title('All eight original job/resource scenarios', fontsize=11); axes[0].set_xlabel('Point visits / supplied year · thousands')
    axes[0].xaxis.set_major_formatter(FuncFormatter(lambda value, _: f'{value/1000:g}'))
    axes[1].set_title('Additional tasks with ZERO baseline identities lost', fontsize=11); axes[1].set_xlabel('Gain over the baseline twelve-bin gate')
    handles, names = axes[0].get_legend_handles_labels(); fig.legend(handles, names, frameon=False, fontsize=8, ncol=3, loc='lower center', bbox_to_anchor=(.5, .12))
    fig.suptitle('Choose one complete calendar per provider/year;never merge individual job successes', fontsize=12)
    fig.text(.5, .025, 'No extra people,food,workers,jobs or reassigned providers. Every mapped task already belongs to the original funded plan.\n'
        'The twelve-bin gate remains necessary only:daily provisioning,within-bin grain timing and actual provider functions are unqualified.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.20, right=.99, top=.88, bottom=.25, wspace=.65)
    path = ROOT / 'reports/figures/network_visit_year_complete_scenarios_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); figures.append(path)
    return figures


if __name__ == '__main__':
    for path in plot(): print(path)
