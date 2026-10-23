"""Plot paired regional climate-distance results; never rerun a simulation."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('folder', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--profiles', nargs='+')
    a = ap.parse_args()
    protocol = json.loads((a.folder/'protocol.json').read_text())
    regions = protocol['regions']
    profiles = a.profiles or list(protocol['profiles'])
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), gridspec_kw={'width_ratios':[3,2]})
    fig.subplots_adjust(left=.12, right=.98, top=.83, bottom=.24, wspace=.6)
    colors = plt.cm.tab10(np.arange(len(profiles)))
    for k, name in enumerate(profiles):
        rows = [json.loads((a.folder/'cases'/f'{name}_{region}.json').read_text()) for region in regions]
        if any(row['status'] != 'passed' for row in rows): raise ValueError('A case failed: '+name)
        d = [r['metrics']['climate_distance'] for r in rows]
        offset = (k-(len(profiles)-1)/2)*.15
        label = name.replace('_',' ')
        axes[0].barh(np.arange(len(regions))+offset, d, height=.14, label=label, color=colors[k])
        closure = max(r['numerics']['storm_exchange']['max_relative_closure'] for r in rows)
        axes[1].scatter(max(closure, 1e-18), k, s=65, color=colors[k], zorder=3)
        axes[1].annotate(f'{closure:.2e}', (max(closure, 1e-18), k), xytext=(0, -17),
                         textcoords='offset points', ha='center', fontsize=8)
    axes[0].set(yticks=np.arange(len(regions)), yticklabels=[r.replace('_',' ') for r in regions],
                xlabel='Climate distance · lower is better', title='Paired Earth climate fit')
    axes[0].invert_yaxis()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(.5,.105), ncol=3, fontsize=9)
    axes[1].set(yticks=range(len(profiles)), yticklabels=[p.replace('_',' ') for p in profiles],
                xscale='log', xlabel='|Net storm water| / gross exchange', title='Internal storm-exchange closure')
    axes[1].set_xlim(1e-18, 1)
    axes[1].set_ylim(-.6, len(profiles)-.4)
    axes[1].invert_yaxis()
    for ax in axes: ax.grid(axis='x', alpha=.2); ax.set_axisbelow(True)
    fig.suptitle('Paired climate skill and storm-water conservation', fontsize=15, y=.97)
    fig.text(.5, .035, '56 km · 25 seasonal steps · reused WorldClim development regions · all numerical checks pass\n'
        'Closure concerns storm exchange on the padded grid; it is not a global atmospheric water budget.',
        ha='center', fontsize=9)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out, dpi=160, bbox_inches='tight')
    plt.close(fig)


if __name__ == '__main__': main()
