"""Review every declared transport profile; incomplete profiles stay unscored."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from local_benchmark_protocol import file_hash, write_json


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    source = ROOT / 'output/r42_conservative_replay_20261102'
    out = ROOT / 'output/r42_transport_review_20261102'; out.mkdir(exist_ok=True)
    plan = json.loads((source / 'protocol.json').read_text())
    names = list(plan['regions']); profiles = {}; packets = {}; curves = {}
    for profile in plan['profiles']:
        folder = source / profile; summary = folder / 'summary.json'
        if not summary.exists():
            profiles[profile] = dict(status='pending', aggregate=None); continue
        d = json.loads(summary.read_text())
        if not d.get('complete'):
            profiles[profile] = dict(status='failed', aggregate=None, failures=d.get('failures')); continue
        if set(d['regions']) != set(names):
            raise ValueError('Incomplete declared footprint: ' + profile)
        curves[profile] = {}
        for name in names:
            row = d['regions'][name]; path = folder / 'cells' / (name + '.npz')
            if row['status'] != 'passed' or row['numerics'].get('all_checks_passed') is not True or file_hash(path) != row['cells_sha256']:
                raise ValueError('Unverified regional packet: ' + profile + ':' + name)
            ref = json.loads((source / 'reference_damped/summary.json').read_text())['regions'][name]
            if row['case_identity'] != ref['case_identity'] or row['cells'] != ref['cells']:
                raise ValueError('Different case: ' + name)
            packets[str(path.relative_to(ROOT))] = file_hash(path)
            with np.load(path) as z, np.load(source / 'reference_damped/cells' / (name + '.npz')) as r:
                for key in ('i', 'j', 'To', 'Po', 'lat', 'lon', 'elev', 'elev_max', 'coast_km'):
                    if not np.array_equal(z[key], r[key]):
                        raise ValueError('Different forcing or observed footprint: ' + name)
                curves[profile][name] = dict(prediction=z['Ps'].mean(1), observed=z['Po'].mean(1))
        t = np.mean([d['regions'][n]['temperature']['monthly_mae_C'] for n in names])
        p = np.mean([d['regions'][n]['rain']['loss'] for n in names])
        profiles[profile] = dict(status='complete', T=float(t), P=float(p), summary_sha256=file_hash(summary))
    baseline = profiles['reference_damped']
    if baseline['status'] != 'complete':
        raise ValueError('No complete numerical control')
    for profile, row in profiles.items():
        if row['status'] == 'complete':
            row.update(temperature_ratio=row['T'] / baseline['T'], rain_ratio=row['P'] / baseline['P'])
            row['aggregate'] = .5 * (row['temperature_ratio'] + row['rain_ratio'])
    labels = dict(reference_damped='r42 numerical control', flux_conservative='Conservative flux + storms',
                  mass_counterflow='With mass-balanced counterflow', independent_reservoirs='Independent reservoirs',
                  reservoirs_resolved_drying='Reservoirs, resolved drying')
    colours = ['#2868a2', '#d97726', '#36916d', '#9164a3', '#af4356']
    fig, axes = plt.subplots(2, 4, figsize=(16, 7.5), layout='constrained')
    for ax, name in zip(axes.flat, names):
        reference = curves['reference_damped'][name]
        ax.plot(range(1, 13), reference['observed'], '--', color='#222222', lw=2, label='Observed')
        for colour, profile in zip(colours, plan['profiles']):
            if profile in curves:
                ax.plot(range(1, 13), curves[profile][name]['prediction'], color=colour, lw=1.8, label=labels[profile])
        ax.set_title(name.replace('_', ' ').title(), loc='left', fontsize=11)
        ax.set_xticks([1, 4, 7, 10], ['Jan', 'Apr', 'Jul', 'Oct']); ax.set_ylim(bottom=0)
        ax.set_ylabel('mm/month'); ax.grid(alpha=.2); ax.spines[['top', 'right']].set_visible(False)
    complete = sum(p['status'] == 'complete' for p in profiles.values())
    fig.suptitle(f'Moisture transport on r42: {complete}/5 profiles complete\nEight matched development regions · strict checks unchanged · other profiles remain unscored', fontsize=14)
    handles, legends = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legends, loc='outside lower center', ncol=3, frameon=False)
    image = out / 'monthly_transport_rain.png'; fig.savefig(image, dpi=135); plt.close(fig)
    write_json(out / 'review.json', dict(adoption=False, profiles=profiles, declared_profiles=len(plan['profiles']),
        completed_profiles=complete, packets_sha256=packets, figure_sha256=file_hash(image),
        plan_sha256=file_hash(source / 'protocol.json'), reviewer_sha256=file_hash(Path(__file__))))
    print(json.dumps(profiles, indent=2))


if __name__ == '__main__':
    main()
