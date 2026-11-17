"""Native-grid inspection maps of the fixed recovered annual cereal activities."""
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import OUT, CATEGORIES, activity, load_packet, sha, read, write


def main():
    assert not (OUT / 'presentation.json').exists()
    r = read(OUT / 'results.json'); review = read(OUT / 'review.json')
    assert review['results_sha256'] == sha(OUT / 'results.json')
    assert review['status'] == 'passed_all_origin_scalar_retention_area_work_food_and_identity_checks'
    for n, h in r['files_sha256'].items(): assert sha(OUT / n) == h, n
    colours = ['#b9b4a8', '#1f252d', '#86b99b', '#b75e42', '#537fa7', '#8e5a9b']
    records = []; files = []
    for display in ['limits', 'retained']:
        fig, axes = plt.subplots(2, 2, figsize=(14, 8.4), facecolor='#f7f7f2')
        fig.subplots_adjust(left=.025, right=.975, top=.82, bottom=.17, hspace=.29, wspace=.055)
        for i, mode in enumerate(['raw', 'corrected']):
            packet = load_packet(OUT, mode)
            for j, density in enumerate(['central', 'low']):
                ax = axes[i, j]; a = activity(packet, 'candidate', mode, density, 600.)
                ids = a['origin']; shape = (463, 1000)
                ax.set_facecolor('#dce8ed')
                if display == 'limits':
                    rgb = np.full((shape[0] * shape[1], 3), [220/255, 232/255, 237/255])
                    from matplotlib.colors import to_rgb
                    rgb[ids] = np.asarray([to_rgb(c) for c in colours])[a['limitation_code']]
                    ax.imshow(rgb.reshape(*shape, 3), interpolation='nearest')
                    annual = int((a['limitation_code'] == 3).sum())
                    ax.set_title(f'{mode.capitalize()} · {density} density\n{annual:,} origins limited by annual work', fontsize=11)
                else:
                    grid = np.full(shape[0] * shape[1], np.nan)
                    productive = a['potential_kcal'] > 0
                    grid[ids[productive]] = a['retained_fraction'][productive]
                    cmap = plt.get_cmap('YlGnBu').copy(); cmap.set_bad('#b9b4a8')
                    # Keep sea separate from unproductive land, on the identical native grid.
                    base = np.full((shape[0] * shape[1], 3), [220/255, 232/255, 237/255]); base[ids] = [185/255, 180/255, 168/255]
                    ax.imshow(base.reshape(*shape, 3), interpolation='nearest')
                    masked = np.ma.masked_invalid(grid.reshape(shape)); cmap.set_bad((0, 0, 0, 0))
                    plotted = ax.imshow(masked, cmap=cmap, vmin=0., vmax=1., interpolation='nearest')
                    total = float(np.nansum(a['retained_area_ha']))
                    fraction = total / float(np.nansum(a['potential_area_ha']))
                    ax.set_title(f'{mode.capitalize()} · {density} density\n{total/1e6:.2f}M cropped ha retained ({fraction:.2%})', fontsize=11)
                ax.set(xlim=(-.5, 999.5), ylim=(462.5, -.5)); ax.axis('off')
                if display == 'limits':
                    records.append(dict(climate=mode, density=density, model='candidate', hours=600.,
                        origins=len(ids), category_counts=[int((a['limitation_code'] == k).sum()) for k in range(6)],
                        retained_cropped_ha=float(np.nansum(a['retained_area_ha'])),
                        retained_fraction_sha256=__import__('hashlib').sha256(a['retained_fraction'].tobytes()).hexdigest(),
                        limitation_codes_sha256=__import__('hashlib').sha256(a['limitation_code'].tobytes()).hexdigest()))
        if display == 'limits':
            fig.suptitle('Where the existing annual cereal-work allowance limits cropped area', fontsize=17, y=.97)
            fig.text(.5, .902, 'Fixed candidate cohort · 600 listed hours per worker · one resource packet per origin', ha='center', fontsize=12)
            fig.legend(handles=[Patch(color=c, label=n) for c, n in zip(colours, CATEGORIES)],
                       loc='lower center', bbox_to_anchor=(.5, .085), ncol=3, frameon=False, fontsize=10)
        else:
            fig.suptitle('Fraction of potential cereal area retained under the same work limits', fontsize=17, y=.97)
            fig.text(.5, .902, 'Identical 0–100% colour scale · area weighted summaries · gray land has no cereal output', ha='center', fontsize=12)
            cax = fig.add_axes([.27, .105, .46, .023]); bar = fig.colorbar(plotted, cax=cax, orientation='horizontal')
            bar.set_ticks([0, .25, .5, .75, 1], labels=['0%', '25%', '50%', '75%', '100%'])
        fig.text(.5, .035,
            'All productive cells choose barley under the least-listed-work objective. This is a scenario, not an observed crop mix.\n'
            'Listed operations only: full household/draft/processing work and non-reaping seasonal windows remain unqualified.',
            ha='center', fontsize=10, linespacing=1.6)
        name = 'annual_limits.png' if display == 'limits' else 'retained_cereal_area.png'
        fig.savefig(OUT / name, dpi=150, facecolor=fig.get_facecolor()); plt.close(fig); files.append(name)
    write(OUT / 'presentation.json', dict(results_sha256=sha(OUT / 'results.json'), review_sha256=sha(OUT / 'review.json'),
        renderer_sha256=sha(Path(__file__)), files_sha256={n: sha(OUT / n) for n in files}, plotted_cases=records,
        native_grid_shape=[463, 1000], shared_retained_fraction_scale=[0., 1.], adopt=False))
    print('Rendered two four-panel native-grid activity inspection figures', flush=True)


if __name__ == '__main__': main()
