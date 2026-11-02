"""Plot all completed starts and descriptive region-mix sensitivity, after selection."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json
from run_calibration_portfolio import select_finalist


def region_mix_sensitivity(reference, candidate, *, draws=10000, seed=20261102):
    """Development-region resampling, not uncertainty corrected for model selection."""
    import numpy as np
    if set(reference) != set(candidate) or not reference:
        raise ValueError('Need complete paired regional errors')
    names = sorted(reference)
    a = np.asarray([reference[n] for n in names], float)
    b = np.asarray([candidate[n] for n in names], float)
    if a.shape != (len(names), 2) or b.shape != a.shape or not np.isfinite(a).all() or not np.isfinite(b).all() or (a <= 0).any() or (b < 0).any():
        raise ValueError('Need finite paired errors and positive references')
    sampled = np.random.default_rng(seed).integers(0, len(names), size=(draws, len(names)))
    ratios = b[sampled].mean(1) / a[sampled].mean(1)
    s = ratios.mean(1)
    return dict(draws=draws, seed=seed, interval_95=np.quantile(s, [.025, .975]).tolist(),
                fraction_below_one=float(np.mean(s < 1)),
                note='Sensitivity to resampling these development regions. Does not correct for candidate selection, spatial dependence or missing physics; not held-out generalization uncertainty.')


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source = ROOT / 'output/r42_multistart_20261102b'
    selected = json.loads((source / 'selection.json').read_text())
    records = []
    for chain in range(1, 4):
        rows = [json.loads(x) for x in (source / f'chain_{chain}/evals.jsonl').read_text().splitlines()]
        if [r['n'] for r in rows] != list(range(13)):
            raise ValueError('All starts must be complete')
        records.extend(dict(r, chain=chain) for r in rows)
    finalist = select_finalist(records)
    if finalist != selected['finalist']:
        raise ValueError('Finalist differs from declared selection')
    out = ROOT / 'output/r42_multistart_review_20261102'; out.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), layout='constrained')
    for chain, colour in zip(range(1, 4), ['#2868a2', '#d97726', '#36916d']):
        rows = [r for r in records if r['chain'] == chain]
        x = [r['n'] for r in rows]
        s = [r.get('S', float('nan')) for r in rows]
        axes[0].plot(x, s, '-o', color=colour, markersize=4, label=f'Start {chain}')
        eligible = [r for r in rows if r.get('T_relative', 99) <= .01 and r.get('P_relative', 99) <= .01]
        axes[1].plot([r['n'] for r in eligible], [r['S'] for r in eligible], 'o', color=colour, label=f'Start {chain}')
    for ax in axes:
        ax.axhline(1, color='#555555', lw=1); ax.axhline(.995, color='#555555', ls='--', lw=1)
        ax.set_xlabel('Evaluation within start (0 is the r42 control)'); ax.set_ylabel('Equal-region combined error / r42')
        ax.grid(alpha=.2); ax.spines[['top', 'right']].set_visible(False); ax.legend(frameon=False)
    axes[0].set_title('Every completed candidate', loc='left')
    axes[1].set_title('Candidates within both 1% T/P safeguards', loc='left')
    fig.suptitle('Three independent starts in the same nine-parameter box\nStarting-point sensitivity tested; global optimality is not established', fontsize=13)
    image = out / 'search_starts.png'; fig.savefig(image, dpi=145); plt.close(fig)
    sensitivity = None
    if finalist:
        ref = next(r for r in records if r['chain'] == 1 and r['n'] == 0)
        sensitivity = region_mix_sensitivity(ref['regions'], finalist['regions'])
    write_json(out / 'review.json', dict(evaluations=len(records), selected=finalist,
        development_region_mix=sensitivity, adoption=False, figure_sha256=file_hash(image),
        search_selection_sha256=file_hash(source / 'selection.json'), reviewer_sha256=file_hash(Path(__file__))))
    print(json.dumps(dict(selected=None if not finalist else [finalist['chain'], finalist['n'], finalist['S']],
                         development_region_mix=sensitivity), indent=2))


if __name__ == '__main__': main()
