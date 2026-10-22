"""Export a scientific comparison figure from two or three completed atlases."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('free', type=Path)
    ap.add_argument('earth', type=Path)
    ap.add_argument('whittaker', type=Path, nargs='?')
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    roots=[args.free,args.earth]
    labels=['Free fit','Earth fit · r29 physics']
    if args.whittaker:
        roots.append(args.whittaker);labels.append('Whittaker fit · proposed strict crosswalk')
    fig, axes = plt.subplots(len(roots), 1, figsize=(13, 6*len(roots)+2))
    for ax, root, label in zip(axes, roots, labels):
        meta = json.loads((root / 'data/atlas.json').read_text())
        summary = json.loads((root / 'summary.json').read_text())
        with Image.open(root / 'data/whittaker.webp') as im:
            ax.imshow(im)
        ax.axis('off')
        score=f'Seasonal zone objective {summary["zonefit"]:.4f}'
        if 'whittaker' in summary:
            score+=f' · Biome objective {summary["whittaker"]["strict"]["score"]:.4f}'
        ax.set_title(label+'\n'+score, loc='left', fontsize=13)
    handles = [Patch(facecolor=b['color'], label=b['label']) for b in meta['biomes']]
    fig.legend(handles=handles, loc='lower center', ncol=3, fontsize=10, frameon=False,
               bbox_to_anchor=(.5, .027))
    fig.suptitle('Whittaker potential biomes', fontsize=22, y=.98)
    fig.text(.5, .953, 'Annual temperature and precipitation · digitized Ricklefs (2008) envelopes via plotbiomes',
             ha='center', fontsize=10)
    if args.whittaker:
        fig.text(.5,.936,'Same three-layout mean climate · different calibration objectives',ha='center',fontsize=10)
    fig.text(.5, .015, 'Grey = outside the published diagram. Climate potential excludes soils, fire, land use and wetland hydrology.',
             ha='center', fontsize=9)
    fig.subplots_adjust(top=.91, bottom=.14, hspace=.12, left=.02, right=.98)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160, facecolor='white')
    plt.close(fig)


if __name__ == '__main__':
    main()
