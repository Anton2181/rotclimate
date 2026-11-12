"""Show common-input geography and all declared location/spacing tradeoffs."""
import json
from pathlib import Path
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from settlement_joint_locations_earth import OUT
from settlement_locations_earth import sha


def main():
    r = json.loads((OUT / 'results.json').read_text()); review = json.loads((OUT / 'review.json').read_text())
    if review['status'] != 'passed' or review['results_sha256'] != sha(OUT / 'results.json'):
        raise ValueError('A current successful independent review is required')
    if sha(OUT / 'positions.npz') != r['positions_sha256']:
        raise ValueError('Changed positions')
    positions = dict(np.load(OUT / 'positions.npz')); lead = r['development_lead']
    figures = ROOT / 'reports/figures'; figures.mkdir(exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(14, 10.4), layout='constrained')
    for row, (pool, label) in enumerate((('han', 'Han AD2'), ('rome', 'Rome AD150'))):
        x = dict(np.load(ROOT / r['inputs'][pool]['path'])); shape = x['land'].shape; cell = float(x['cell_km'])
        real = x['real'][x['allowed'].ravel()[x['real']]]
        actual = np.column_stack(np.unravel_index(real, shape))
        pp = [actual, positions[f'{pool}__production__1'], positions[f'{pool}__{lead}__1']]
        base = np.empty(shape + (3,)); base[:] = [.82, .9, .93]
        base[x['land']] = [.88, .89, .86]; base[x['allowed'] & x['land']] = [.97, .96, .90]
        titles = [f'{label} · observed centres\n{len(actual):,} distinct allowed cells']
        for variant, title in [('production', 'Current production'), (lead, 'Joint development lead · seed1')]:
            rr = next(q for q in r['rows'] if q['pool'] == pool and q['variant'] == variant and q['seed'] == 1)
            titles.append(f'{title} · {rr["n_model"]:,}\nUnique F1 {rr["unique_F1"]:.3f} · spacing KS {rr["M3"]:.3f}')
        for ax, p, title, color in zip(axes[row], pp, titles, ['#743d37', '#346d98', '#277665']):
            ax.imshow(base, extent=(0, shape[1] * cell, shape[0] * cell, 0), origin='upper')
            ax.scatter((p[:, 1] + .5) * cell, (p[:, 0] + .5) * cell, s=3.5, c=color, lw=0)
            ax.set_title(title, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle('Settlement locations after repairing population coverage and travel support', fontsize=14)
    fig.supxlabel(f'Complete current inputs and common natural counts · lead: {lead} · seed1 always shown\n'
        'All Earth pools already exposed. Location development only; resident populations, food, staff and control are unchanged.', fontsize=9)
    fig.savefig(figures / 'settlement_joint_maps_20261112.png', dpi=140); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.3), layout='constrained')
    colors = {.5: '#377cac', .7: '#aa7a39', 1.: '#37866e'}
    for power, color in colors.items():
        rows = [q for q in r['ranking'] if q['family'] == 'adaptive' and q['variant'].startswith(f'b{power:g}_')]
        axes[0].scatter([q['mean']['M3'] for q in rows], [q['mean']['unique_F1'] for q in rows],
                        s=50, c=color, alpha=.75, label=f'Density exponent {power:g}')
    for variant, label, marker, color in [(lead, 'Development lead', '*', '#164d3c'),
        ('production', 'Production control', 'X', '#444444'), ('fixed18_L800', 'Fixed18km control', 'D', '#7950a1')]:
        rr = next(q for q in r['ranking'] if q['variant'] == variant)
        axes[0].scatter(rr['mean']['M3'], rr['mean']['unique_F1'], s=210 if marker == '*' else 100,
                        marker=marker, c=color, edgecolor='white', linewidth=.7, zorder=5, label=label)
    frontier = [q for q in r['ranking'] if q['variant'] in r['pareto_frontier']]
    axes[0].set(xlabel='Nearest-neighbour spacing KS · lower is better', ylabel='Unique-site F1 within25km · higher is better',
                title='All21 variants · five-seed / equal-pool means')
    axes[0].legend(fontsize=8, loc='best'); axes[0].grid(alpha=.18)
    rows = r['ranking']; y = np.arange(len(rows))
    for pool, delta, color in [('han', -.15, '#377cac'), ('rome', .15, '#aa7a39')]:
        axes[1].scatter([q['pools'][pool]['Q'] for q in rows], y + delta, s=24, c=color, label=pool.capitalize())
    axes[1].set_yticks(y, [q['variant'] for q in rows], fontsize=8)
    axes[1].invert_yaxis(); axes[1].set(xlabel='Declared development Q · higher is better', title='Every variant, including regional tradeoffs')
    axes[1].legend(fontsize=8); axes[1].grid(axis='x', alpha=.18)
    fig.suptitle('Separate location intensity from people and historical-occupation claims', fontsize=14)
    weights = ', '.join(f'{w}: {v["variant"]}' for w, v in r['location_weight_sensitivity'].items())
    fig.supxlabel('Q uses60% unique matching and40% block/spacing diagnostics; it is not a percentage accuracy.\n'
        f'Location-weight sensitivity · {weights}\nNo prospective validation or fantasy-default adoption.', fontsize=8)
    fig.savefig(figures / 'settlement_joint_tradeoffs_20261112.png', dpi=150); plt.close(fig)
    print('Saved joint geography and complete tradeoff figures; Pareto alternatives:', len(frontier))


if __name__ == '__main__':
    main()
