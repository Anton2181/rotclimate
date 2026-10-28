"""Plot full-score rainfall seasons after a completed, verified tradeoff search.

No fitted coefficient, selection criterion or climate integration is changed.
Monthly regional means are distinguished from spatial monthly error metrics.
"""
from pathlib import Path
import argparse
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from local_benchmark_protocol import file_hash, identity, write_json
from publish_tradeoff_search import verified


def plot(out):
    protocol, progress, review = verified(out)
    receipt = json.loads((out / 'scientific_verification.json').read_text())
    if (receipt['status'] != 'passed' or receipt['identity'] != identity(protocol)
            or receipt['review_sha256'] != file_hash(out / 'review.json')):
        raise ValueError('Independent scientific verification must precede plots')
    valid = {n: s for n, s in review['scores'].items() if s.get('physical_admissible')}
    selected = {
        'best_objective': min(valid, key=lambda n: (valid[n]['objective'], n)),
        'best_mean_climate': min(valid, key=lambda n: (valid[n]['mean_combined_ratio'], n)),
    }
    names = list(dict.fromkeys(['reference', 'environment_control', *selected.values()]))
    labels = {'reference': 'r39', 'environment_control': 'Environmental control'}
    for role, name in selected.items():
        labels[name] = labels.get(name, '') + (' / ' if name in labels else '') + role.replace('_', ' ').title() + ' (' + name + ')'
    rows = {(r['name'], r['region']): r for r in progress['records']}
    series, hashes = {}, {}
    fig, axes = plt.subplots(2, 4, figsize=(17, 9), constrained_layout=True)
    months = np.arange(1, 13)
    for ax, region in zip(axes.flat, protocol['plan']['regions']):
        observed = np.asarray(rows['reference', region]['monthly_rain']['observed'], float)
        if observed.shape != (12,) or not np.isfinite(observed).all() or (observed < 0).any():
            raise ValueError('Invalid observed rainfall')
        ax.plot(months, observed, 'o-', color='black', lw=2, ms=3, label='Observed')
        series[region] = {'observed_mm': observed.tolist(), 'profiles': {}}
        for color, name in zip(['#777777', '#cc6677', '#0072b2', '#009e73'], names):
            row = rows[name, region]
            simulated = np.asarray(row['monthly_rain']['simulated'], float)
            if (simulated.shape != (12,) or not np.isfinite(simulated).all() or (simulated < 0).any()
                    or not np.array_equal(observed, row['monthly_rain']['observed'])
                    or not math.isclose(float(simulated.sum()), row['rain']['sim_mean_annual_mm'], rel_tol=1e-6, abs_tol=1e-3)
                    or not math.isclose(float(observed.sum()), row['rain']['obs_mean_annual_mm'], rel_tol=1e-6, abs_tol=1e-3)):
                raise ValueError('Inconsistent full-score monthly series')
            hashes[name + '/' + region] = file_hash(out / name / (region + '.json'))
            series[region]['profiles'][name] = {
                'simulated_mm': simulated.tolist(),
                'scored_land_cells': row['rain']['scored_land_cells'],
                'annual_mm': float(simulated.sum()),
                'monthly_spatial_mae_mm': row['rain']['monthly_mae_mm'],
                'rain_loss': row['rain']['loss'],
            }
            ax.plot(months, simulated, color=color, label=labels[name])
        ax.set(title=region.replace('_', ' ').title(), xticks=months,
               xticklabels=list('JFMAMJJASOND'), ylabel='Regional mean mm/month', ylim=(0, None))
        ax.grid(alpha=.15)
    axes.flat[-1].axis('off')
    axes.flat[-1].legend(*axes.flat[0].get_legend_handles_labels(), loc='upper left', bbox_to_anchor=(0, 1), frameon=False, fontsize=9)
    axes.flat[-1].text(.05, .02, 'Observed annual totals (mm/year)\n' + '\n'.join(
        r.replace('_', ' ').title() + ': ' + str(round(sum(v['observed_mm']))) for r, v in series.items()),
        transform=axes.flat[-1].transAxes, fontsize=9)
    fig.suptitle('Rainfall accuracy includes the seasonal cycle', fontsize=17)
    fig.supxlabel('Full scored land masks, including all 358 East Australia cells; equal model-month totals from the original score records.\n'
                  'Regional means can hide spatial errors: monthly spatial MAE and rain loss remain in the download. '
                  'Post-search diagnostics on reused regions; no new validation or adopted climate.', fontsize=9)
    picture = out / 'rainfall_seasons.png'
    fig.savefig(picture, dpi=145)
    plt.close(fig)
    meta = dict(status='passed', selected=selected, series=series, row_sha256=hashes,
                protocol_sha256=file_hash(out / 'protocol.json'), review_sha256=file_hash(out / 'review.json'),
                script_sha256=file_hash(Path(__file__)), image_sha256=file_hash(picture),
                scope='Declared diagnostic selections only; full-score spatial means, not pixelwise skill or independent validation',
                new_earth_integrations=0, physics_or_atlas_adoption=False)
    write_json(out / 'rainfall_seasons.json', meta)
    print(json.dumps(selected))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    plot(parser.parse_args().out.resolve())
