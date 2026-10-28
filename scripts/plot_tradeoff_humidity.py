"""Expose native seasonal water amount and vertical shape without new runs."""
from pathlib import Path
import argparse
import json
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
        raise ValueError('Need matching independent verification')
    p = protocol['plan']
    valid = {n: s for n, s in review['scores'].items() if s.get('physical_admissible')}
    selected = {'best_objective': min(valid, key=lambda n: (valid[n]['objective'], n)),
                'best_native': min(valid, key=lambda n: (valid[n]['native_squared_regret'], n))}
    names = list(dict.fromkeys(['native_control', 'environment_control', *selected.values()]))
    labels = {'native_control': 'Native control (regional baseline)', 'environment_control': 'Environmental control'}
    for name in set(selected.values()):
        labels[name] = 'Best ' + ' / '.join(k.replace('best_', '') for k, v in selected.items() if v == name) + ' (' + name + ')'
    groups = [(r, 'circulation', p['circulation_groups'][r]) for r in p['circulation_regions']]
    groups += [(r, 'extra_circulation', p['extra_circulation_groups'][r]) for r in p['extra_circulation_regions']]
    rows = {(r['name'], r['region']): r for r in progress['records']}
    fig, axes = plt.subplots(len(groups), 2, figsize=(13, 3 * len(groups)), squeeze=False, constrained_layout=True)
    series, hashes = {}, {}
    fields = [('water_mm', 'Partial water 925–300 hPa (mm)'), ('q_ratio', 'Upper/lower mean specific humidity')]
    for pair, (region, key, group) in zip(axes, groups):
        baseline = 'transport_control' if key == 'circulation' else 'column_control'
        reference = rows[baseline, region][key]
        order = np.argsort(reference['original_month'])
        ref = reference['humidity']['scores'][group]
        if ref is None:
            raise ValueError('Missing declared native humidity footprint')
        series[region] = dict(group=group, native_control=baseline, native_cells=ref['native_cells'], area_km2=ref['area_km2'],
                              calendar_month_for_model_month=reference['original_month'], profiles={})
        for ax, (suffix, unit) in zip(pair, fields):
            observed = np.asarray(ref['monthly_reference_' + suffix], float)[order]
            ax.plot(range(1, 13), observed, 'o-', color='black', lw=2, ms=3, label='Observed')
            for color, name in zip(['#777777', '#cc6677', '#0072b2', '#009e73'], names):
                actual_name = baseline if name == 'native_control' else name
                row = rows[actual_name, region]
                report = row[key]
                metric = report['humidity']['scores'][group]
                if (report['original_month'] != reference['original_month'] or metric is None
                        or metric['native_cells'] != ref['native_cells'] or metric['area_km2'] != ref['area_km2']
                        or metric['monthly_reference_' + suffix] != ref['monthly_reference_' + suffix]):
                    raise ValueError('Unpaired native monthly series')
                value = np.asarray(metric['monthly_model_' + suffix], float)[order]
                if value.shape != (12,) or not np.isfinite(value).all() or (value < 0).any():
                    raise ValueError('Invalid native humidity')
                hashes[actual_name + '/' + region] = file_hash(out / actual_name / (region + '.json'))
                series[region]['profiles'][actual_name] = metric
                ax.plot(range(1, 13), value, color=color, label=labels[name])
            ax.set(title=region.replace('_', ' ').title() + f' · {group}, {ref["native_cells"]} native cells',
                   ylabel=unit, xticks=range(1, 13), xticklabels=list('JFMAMJJASOND'), ylim=(0, None))
            ax.grid(alpha=.15)
    handles, legend = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend, loc='outside upper center', ncols=2, frameon=False, fontsize=9)
    fig.supxlabel('Calendar months (recorded southern shift undone); same pressure intervals, native footprints and areas as the scores.\n'
                  'Native controls: transport_control for North India/Iberia/East Australia; column_control for PNW. r39 has no saved humidity certificate.\n'
                  'Area-mean curves can conceal local error: original area/day-weighted native MAEs remain in the download. '
                  'Post-search diagnostics on reused small samples; no independent validation or adopted climate.', fontsize=9)
    picture = out / 'humidity_seasons.png'
    fig.savefig(picture, dpi=145)
    plt.close(fig)
    write_json(out / 'humidity_seasons.json', dict(
        status='passed', selected=selected, series=series, row_sha256=hashes,
        protocol_sha256=file_hash(out / 'protocol.json'), review_sha256=file_hash(out / 'review.json'),
        script_sha256=file_hash(Path(__file__)), image_sha256=file_hash(picture),
        scope='Native source metrics preserved; curves reordered to calendar months for display only',
        new_earth_integrations=0, physics_or_atlas_adoption=False))
    print(json.dumps(selected))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    plot(parser.parse_args().out.resolve())
