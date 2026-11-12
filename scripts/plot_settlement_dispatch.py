"""Show the actual paired settlement/potential-access map update and all results."""
import gzip
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from publish_settlement_dispatch import town_image, reach_image, DATA
from build_settlement_dispatch import OUT, PARENT
from settlement_locations_earth import sha


def maps(mode):
    meta = json.loads((DATA / 'atlas.json').read_text()); parent = json.loads((DATA / 'settled_reach.json').read_text())
    original_folder = DATA / ('corrected' if mode == 'corrected' else '')
    model = json.loads(gzip.decompress((original_folder / 'settled_reach.json.gz').read_bytes()))
    x = dict(np.load(PARENT / f'{mode}_inputs.npz')); old_masks = np.load(PARENT / f'{mode}_reach.npz')['masks']
    r = json.loads((OUT / f'{mode}_reach.json').read_text()); checked = json.loads((OUT / f'{mode}_reach_review.json').read_text())
    assert checked['status'] == 'passed' and checked['results_sha256'] == sha(OUT / f'{mode}_reach.json')
    masks = np.load(OUT / f'{mode}_reach.npz')['masks']
    with gzip.open(original_folder / 'settled_reach.bin.gz', 'rb') as stream:
        prefix = stream.read(parent['packets'][mode]['offsets']['masks'])
    assignment = np.frombuffer(prefix, '<u2', count=x['land'].size, offset=parent['packets'][mode]['offsets']['catchments'])
    old = dict(np.load(PARENT / f'{mode}_h300_f0.075/fields.npz'))
    low_key = f'{mode}_h300_load120000_all_open'; high_key = f'{mode}_h600_load120000_all_open'
    low = dict(np.load(OUT / low_key / 'fields.npz')); high = dict(np.load(OUT / high_key / 'fields.npz'))
    cases = [(old, old_masks[3], 'Food only · 300 farm hours'),
             (low, masks[r['cases'].index(low_key)], 'Joint food + collection · 300 farm hours'),
             (high, masks[r['cases'].index(high_key)], 'Joint food + collection · 600 farm hours')]
    fig, axes = plt.subplots(2, 3, figsize=(15, 6.2), layout='constrained')
    pop = np.array([i.bit_count() for i in range(4096)], np.uint8); weights = x['area'].ravel()[x['land'].ravel()]
    for col, (f, mask, label) in enumerate(cases):
        axes[0, col].imshow(town_image(f, model, x, assignment, meta))
        rows, cols = np.divmod(x['nodes'], x['land'].shape[1]); pixel = meta['width'] / x['land'].shape[1]
        good = f['civilian'] >= 50
        colors = np.array([to_rgb(model['actors'][a]['color']) if a >= 0 else [.35, .4, .42] for a in x['actor']])
        axes[0, col].scatter((cols[good] + .5) * pixel, (rows[good] + .5) * pixel,
            s=np.clip(np.sqrt(f['total'][good]) * .22, 2., 12.), c=colors[good], edgecolors='white', linewidths=.15)
        axes[0, col].set_title(f'{label}\n{f["total"].sum():,.0f} town residents · {f["active"].sum():,} conditional sources', fontsize=10)
        axes[1, col].imshow(reach_image(mask, model, x, meta))
        mean = float(np.sum(weights * pop[np.bitwise_or.reduce(mask, axis=0)]) / weights.sum())
        axes[1, col].set_title(f'Potential two-way access from the SAME cohorts\n{mean:.3f} / 12 area-weighted bins', fontsize=10)
    for ax in axes.flat:
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle(f'{mode.title()} climate: grain deliveries and monthly collection work now enter the resident budget', fontsize=14)
    fig.supxlabel('Paired first two columns: same 300h inputs, 120,000 kcal per collector trip, all bins open. Third column changes farm work.\n'
        'Fixed sites and transport · 7.5% transfer ceiling · 600 supplied staff hours/year · no calibrated size or geographic patrol/authority claim.', fontsize=9)
    path = ROOT / f'reports/figures/settlement_dispatch_{mode}_maps_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig)
    print(path)


def comparison():
    rows = [json.loads(p.read_text()) for p in sorted(OUT.glob('*/results.json')) if p.parent.name != 'fresh']
    assert len(rows) == 16
    open_rows = [r for r in rows if r['availability'] == 'all_open']
    labels = [f'{r["climate"].title()} · {r["hours_worker_year"]}h · {r["load_kcal"]/1000:g}k' for r in open_rows]
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 6), layout='constrained'); y = np.arange(len(labels))
    for ax, metric, old, fixed, title in [(axes[0], 'town_people', 'original_town_people', 'fixed_plan_qualified_town_people', 'Town residents in the supplied scenario'),
                                         (axes[1], 'active_sources', 'original_active_sources', 'fixed_plan_qualified_sources', 'Conditional staffed sources')]:
        ax.barh(y - .23, [r[old] for r in open_rows], height=.23, color='#899087', label='Original food only')
        ax.barh(y, [r[fixed] for r in open_rows], height=.23, color='#ad643b', label='Fixed shipments pass work')
        ax.barh(y + .23, [r[metric] for r in open_rows], height=.23, color='#467c88', label='Joint dispatch / food / work')
        ax.set_yticks(y, labels); ax.invert_yaxis(); ax.set_title(title, fontsize=11); ax.grid(axis='x', alpha=.15); ax.set_axisbelow(True)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=8, loc='outside lower center', ncol=3)
    fig.suptitle('Reducing surplus shipments recovers feasible scenarios within the declared dispatch family', fontsize=13)
    fig.supxlabel('All eight closed-bin cases remain explicit zeros under this family and 90-day destination stores.\n'
        'Loads/work/diets/roles are supplied scenarios; fixed-plan audit totals are conditional subsets, not alternative census predictions.', fontsize=9)
    path = ROOT / 'reports/figures/settlement_dispatch_scenarios_20261112.png'; fig.savefig(path, dpi=160); plt.close(fig); print(path)


if __name__ == '__main__':
    for mode in ('raw', 'corrected'): maps(mode)
    comparison()
