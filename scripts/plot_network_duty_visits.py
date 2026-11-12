"""Show actual conditional visited POINTS, plus request and hour deficits."""
import gzip
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from publish_network_duty_visits import DATA, OUT, PARENT, point_image
from settlement_locations_earth import sha


def main():
    r = json.loads((OUT / 'results.json').read_text()); f = dict(np.load(OUT / 'fields.npz'))
    review = json.loads((OUT / 'review.json').read_text()); assert review['status'] == 'passed' and review['results_sha256'] == sha(OUT / 'results.json')
    manifest = json.loads((DATA / 'network_duty_visits.json').read_text()); meta = json.loads((DATA / 'atlas.json').read_text())
    for mode in ('raw', 'corrected'):
        x = dict(np.load(PARENT / f'{mode}_inputs.npz')); paths = dict(np.load(OUT / f'{mode}_paths.npz'))
        model = json.loads(gzip.decompress((DATA / manifest['packets'][mode]['payload']).read_bytes()))
        fig, axes = plt.subplots(2, 2, figsize=(14, 7.4), layout='constrained')
        for i, hours in enumerate((600, 300)):
            for j, crew in enumerate((1, 4)):
                row = next(row for row in r['rows'] if row['key'] == f'{mode}_h{hours}_crew{crew}')
                axes[i, j].imshow(point_image(x, paths, f[row['key'] + '__served'], model['actors'], meta))
                axes[i, j].set_title(f'{hours} farm hours · crew {crew}\n{row["completed_visits"]:,} / {row["requested_visits"]:,} visits ({100*row["completed_fraction"]:.1f}%)', fontsize=10)
                axes[i, j].set_xticks([]); axes[i, j].set_yticks([])
        fig.suptitle(f'{mode.title()} climate: walking point visits funded from the SAME reserved patrol slice', fontsize=13)
        fig.supxlabel('Dots are visited target points;size reflects bins completed,white centres indicate overlapping actors. No block or intervening territory is assigned.\n'
            'Fixed ~11 km target grid · one supplied task per actor/retained point/bin · walking only · conditional food/collection-supported providers.\n'
            'No observed demand,individual daily roster,political authority or mobile/unaffiliated occupancy qualification.', fontsize=9)
        path = ROOT / f'reports/figures/network_duty_visits_{mode}_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); print(path)
    labels = [f'{row["climate"].title()} · {row["hours_worker_year"]}h · crew {row["crew"]}' for row in r['rows']]
    fig, axes = plt.subplots(1, 2, figsize=(14, 6)); y = np.arange(8); left = np.zeros(8)
    for field, label, color in [('completed_visits', 'Completed whole visits', '#487e70'), ('capacity_unmet', 'Assigned provider capacity', '#c79a52'),
        ('provider_work_unavailable', 'No initially affordable crew', '#b56a52'), ('route_unreachable', 'No eligible walking round trip', '#abb0b4')]:
        value = np.array([row[field] / row['requested_visits'] * 100 for row in r['rows']]); axes[0].barh(y, value, left=left, color=color, label=label); left += value
    axes[0].set_yticks(y, labels); axes[0].invert_yaxis(); axes[0].set_xlim(0, 100); axes[0].set_xlabel('% of requested actor / point / bin tasks'); axes[0].set_title('All requests partitioned exactly once')
    axes[0].legend(loc='upper center', bbox_to_anchor=(.5, -.14), ncol=2, fontsize=8, frameon=False)
    for offset, name, color in [(-.18, 'visit_hours_used', '#487e70'), (.18, 'unused_patrol_hours', '#d4c8ac')]:
        axes[1].barh(y + offset, [row[name] / 1e6 for row in r['rows']], height=.34, color=color, label='Used for visits' if offset < 0 else 'Reserved slice left unused')
    axes[1].set_yticks(y, labels); axes[1].invert_yaxis(); axes[1].set_xlabel('Million crew-hours / year'); axes[1].set_title('Only patrol reservations are spent'); axes[1].legend(loc='upper center', bbox_to_anchor=(.5, -.14), ncol=2, fontsize=8, frameon=False)
    for ax in axes: ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    fig.suptitle('Geographic routes and provider competition reduce conditional completed visits', fontsize=13)
    fig.text(.5, .015, 'Greedy single-provider assignment can leave spare hours alongside unmet tasks. No global optimum is claimed.\n'
        'Collection and other services retain their commitments;all eight zero-patrol-budget controls complete zero visits.', ha='center', fontsize=9)
    fig.subplots_adjust(left=.19, right=.99, top=.88, bottom=.27, wspace=.75)
    path = ROOT / 'reports/figures/network_duty_visits_scenarios_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); print(path)


if __name__ == '__main__': main()
