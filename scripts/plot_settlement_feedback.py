"""Show the actual shared resident/worker/grain/source chain and all scenarios."""
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from prepare_settlement_feedback import OUT, PLAN, DATA
from settlement_locations_earth import sha


def main():
    mode = 'corrected'; x = dict(np.load(OUT / f'{mode}_inputs.npz')); land = x['land']; h, w = land.shape
    reach = dict(np.load(OUT / f'{mode}_reach.npz')); rs = json.loads((OUT / f'{mode}_reach.json').read_text())
    import gzip
    model = json.loads(gzip.decompress((DATA / 'corrected/settled_reach.json.gz').read_bytes()))
    actors = np.array([to_rgb(a['color']) for a in model['actors']]); nodes = x['nodes']
    high = dict(np.load(OUT / 'corrected_h600_f0.075/fields.npz'))
    low = dict(np.load(OUT / 'corrected_h300_f0.075/fields.npz'))
    cases = [(high['frozen_total'], high['frozen_active'], reach['frozen_masks'][1], 'Rural budget held fixed\ninconsistent comparison'),
             (high['total'], high['active'], reach['masks'][1], 'People, workers and grain coupled\n600 field hours / worker'),
             (low['total'], low['active'], reach['masks'][3], 'People, workers and grain coupled\n300 field hours / worker')]
    fig, axes = plt.subplots(2, 3, figsize=(15, 8.7), layout='constrained')
    base = np.empty((h, w, 3)); base[:] = [.82, .89, .93]; base[land] = [.93, .91, .85]
    count = np.array([i.bit_count() for i in range(4096)], np.uint8); yy, xx = np.divmod(nodes, w)
    for col, (total, active, masks, title) in enumerate(cases):
        ax = axes[0, col]; ax.imshow(base, origin='upper')
        good = total >= 50
        color = np.array([actors[a] if a >= 0 else [.4, .4, .4] for a in x['actor']])
        ax.scatter(xx[good], yy[good], s=np.maximum(2., np.sqrt(total[good]) * .24), c=color[good], lw=.2, edgecolor='white')
        ax.scatter(xx[active], yy[active], s=1.5, c='#171f24', lw=0)
        ax.set_title(f'{title}\n{total.sum():,.0f} town residents · {active.sum():,} conditional sources', fontsize=10)
        ax = axes[1, col]; bins = count[masks]; winner = bins.argmax(0); best = bins.max(0)
        rgb = base.copy(); alpha = best / 12 * .8
        rgb.reshape(-1, 3)[reach['landnodes']] = np.array([.91, .89, .83]) * (1-alpha[:, None]) + actors[winner] * alpha[:, None]
        ax.imshow(rgb, origin='upper')
        weights = x['area'].ravel()[reach['landnodes']].astype(float)
        mean = float(np.average(count[np.bitwise_or.reduce(masks, axis=0)], weights=weights))
        ax.set_title(f'Same transport · available resident cohorts only\n{mean:.3f} / 12 area-weighted access bins', fontsize=10)
    for ax in axes.flat:ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Rural meals and farm workers now feed the SAME settlement and reach plan', fontsize=15)
    fig.supxlabel('Corrected climate · 7.5% maximum transfer from checked local origins · fixed sites/transport, all actors retained\n'
        'Research cereal scenarios, not a census or sovereignty fit. Rural deficits remain visible elsewhere; other diets and household work are incomplete.', fontsize=9)
    figures = ROOT / 'reports/figures'; figures.mkdir(exist_ok=True)
    fig.savefig(figures / 'settlement_feedback_maps_20261112.png', dpi=150); plt.close(fig)
    declaration = json.loads(PLAN.read_text()); rows = []
    for mode in declaration['climate_modes']:
        for c in declaration['scenarios']:
            key = f'{mode}_h{c["hours_worker_year"]}_f{c["transfer_fraction"]:g}'
            r = json.loads((OUT / key / 'results.json').read_text()); review = json.loads((OUT / key / 'review.json').read_text())
            if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / key / 'results.json'):
                raise ValueError('Current independent cell review required')
            rows.append(r)
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.8), layout='constrained')
    for mode, color in [('raw', '#39799a'), ('corrected', '#2b8169')]:
        selected = [r for r in rows if r['climate'] == mode and r['hours_worker_year'] == 600]
        axes[0, 0].plot([r['transfer_fraction']*100 for r in selected], [r['town_people']/1e3 for r in selected], 'o-', color=color, label=mode.capitalize()+' ·600h')
        r = next(r for r in rows if r['climate'] == mode and r['hours_worker_year'] == 300)
        axes[0, 0].scatter(7.5, r['town_people']/1e3, marker='X', s=90, c=color, label=mode.capitalize()+' ·300h')
    axes[0, 0].set(xlabel='Maximum transferable origin population · %', ylabel='Town residents · thousands', title='One people budget, recomputed food and workers'); axes[0, 0].legend(fontsize=8)
    labels = [f'{r["climate"][:3]} {r["hours_worker_year"]}h\n{100*r["transfer_fraction"]:g}%' for r in rows]; ind = np.arange(len(rows))
    axes[0, 1].bar(ind-.17, [r['frozen_reference_sources'] for r in rows], .34, color='#af8757', label='Rural budget frozen')
    axes[0, 1].bar(ind+.17, [r['active_sources'] for r in rows], .34, color='#2b8169', label='Coupled feedback')
    axes[0, 1].set_xticks(ind, labels, fontsize=8); axes[0, 1].set(ylabel='Conditional staffed sources', title='The same cohorts feed reach'); axes[0, 1].legend(fontsize=8)
    axes[1, 0].bar(ind, [100*r['local_production_retained'] for r in rows], color=['#39799a' if r['climate']=='raw' else '#2b8169' for r in rows])
    axes[1, 0].set_xticks(ind, labels, fontsize=8); axes[1, 0].set(ylabel='Retained local potential grain · %', title='Workers remaining rural constrain production', ylim=(0,100))
    axes[1, 1].bar(ind-.17, [r['local_rural_deficit_origins'] for r in rows], .34, color='#b17d4e', label='Local collection origins')
    axes[1, 1].bar(ind+.17, [r['outside_rural_deficit_origins'] for r in rows], .34, color='#87949c', label='Outside collection')
    axes[1, 1].set_xticks(ind, labels, fontsize=8); axes[1, 1].set(ylabel='Origins with unmet cereal meals', title='Deficits are retained, never relabelled empty land'); axes[1, 1].legend(fontsize=8)
    for ax in axes.flat:ax.grid(axis='y', alpha=.18)
    fig.suptitle('All eight cell-feedback scenarios · independent food/work audits and fresh replays pass', fontsize=14)
    fig.supxlabel('Scenario shares/work envelopes and partial cereal diets remain uncalibrated. Local origins differ from the earlier wide trade catchments.\n'
        'The frozen-rural comparison is internally inconsistent after relocation; it is a diagnostic control. No global optimum or main-default adoption.', fontsize=9)
    fig.savefig(figures / 'settlement_feedback_scenarios_20261112.png', dpi=150); plt.close(fig)
    print('Saved coupled settlement/reach maps and all eight scenario charts.')


if __name__ == '__main__':main()
