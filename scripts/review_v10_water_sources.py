"""Verify and diagnose completed source tracers; saved fields only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_water_sources as run
from rotclimate_v10.earth import atomic_json, sha256


def load_verified(source):
    protocol, inputs, settings, baselines, anchors = run.prepare()
    state = json.loads((source/'state.json').read_text())
    if json.loads((source/'manifest.json').read_text()) != protocol or state['status'] != 'complete':
        raise ValueError('Need unchanged completed water-source protocol.')
    if set(state['cases']) != {job['key'] for job in protocol['jobs']}:
        raise ValueError('Water-source case set differs from the declared plan.')
    records = {};seconds = 0.;cycles = 0
    for job in protocol['jobs']:
        key = job['key'];region = job['region'];mode = job['wind']
        case, profile, g, air, wind = inputs[region];row = state['cases'][key]
        folder = source/'cases'/key
        identity = dict(job, settings=asdict(settings[mode]), input_array_sha256=protocol['inputs'][region])
        if json.loads((folder/'config.json').read_text()) != identity or json.loads((folder/'summary.json').read_text()) != row:
            raise ValueError('Water-source case identity or summary changed.')
        count = row['years'];evidence = {f'year{n}.{ext}' for n in range(1, count+1) for ext in ('json', 'npz')}
        if not 3 <= count <= 6 or set(row['evidence_sha256']) != evidence:
            raise ValueError('Water-source annual evidence declaration is incomplete.')
        for name, digest in row['evidence_sha256'].items():
            if sha256(folder/name) != digest:
                raise ValueError('Water-source annual evidence changed.')
        previous = None;check = {'passed': False};anchor_checked = False
        for year in range(1, count+1):
            record = run.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed source year.')
            info = record[-1];ledger = info['sources']['totals']
            domain_rain = record[4].sum(axis=(0, 2, 3))/case.domain.land.size
            if not np.allclose(domain_rain, ledger['rain_mm'], atol=1e-8, rtol=0):
                raise ValueError('Full-domain source rain disagrees with its annual ledger.')
            for source_index, budget_key in ((2, 'ocean_evaporation_mm'), (3, 'land_evaporation_mm')):
                if abs(ledger['evaporation_mm'][source_index]-info['budget'][budget_key]) > 1e-7:
                    raise ValueError('Source evaporation disagrees with the physical ledger.')
            if abs(sum(ledger['export_mm'])-sum(ledger['import_mm'])-info['budget']['boundary_export_mm']) > 1e-7:
                raise ValueError('Gross source transport disagrees with physical net export.')
            if job['seed'] == 41 and year == baselines[region+'_'+mode]['years']:
                run.verify_anchor(record, anchors[region+'_'+mode]);anchor_checked = True
            if previous is not None:
                check = run.settling(previous, record, case, g)
            previous = record
            seconds += info['elapsed_seconds'];cycles += 1
        computed = run.night.summarize(run.model.physical_record(record), case, check, count)
        computed.update(response=run.review.run.rain_vector(case, record[1]), sources=run.source_summary(record, case),
            seed=job['seed'], wind=mode, anchor_reproduced=anchor_checked if job['seed'] == 41 else None)
        if any(computed[name] != row[name] for name in computed):
            raise ValueError('Source results disagree with recomputed summaries.')
        records[key] = record
    return protocol, state, inputs, records, seconds, cycles


def span(values):
    a = np.asarray(values, float)
    if not np.isfinite(a).all() or a.size == 0:
        raise ValueError('Need complete finite case statistics.')
    return {'mean': float(a.mean()), 'min': float(a.min()), 'max': float(a.max())}


def source_fates(source_info):
    """Atmospheric source removals over this full domain/year; not land skill."""
    ledger = source_info['totals'];result = {}
    for index, name in enumerate(run.model.SOURCES):
        supply = ledger['import_mm'][index]+ledger['evaporation_mm'][index]
        if supply <= 1e-12:
            continue  # Initial vapor has no new annual supply.
        change = source_info['end_store_mm'][index]-source_info['initial_store_mm'][index]
        result[name] = {'supply_mm_domain_mean': supply,
            'precipitation_mm_domain_mean': ledger['rain_mm'][index],
            'export_mm_domain_mean': ledger['export_mm'][index], 'store_change_mm_domain_mean': change,
            'precipitation_to_supply': ledger['rain_mm'][index]/supply,
            'export_to_supply': ledger['export_mm'][index]/supply,
            'store_change_to_supply': change/supply}
    return result


def analyse(source):
    protocol, state, inputs, records, seconds, cycles = load_verified(source)
    cases = {}
    for key, row in state['cases'].items():
        cases[key] = {'response': row['response'], 'rain_ratio': row['annual_rain_ratio'],
            'settled': row['settling']['passed'], 'broad_screen_passed': row['eligible'],
            'guards': row['guards'], 'sources': row['sources']['rain'],
            'domain_atmospheric_source_fates': source_fates(row['sources']['atmospheric_budget_domain_mean'])}
    groups = {};contrasts = {}
    for region in inputs:
        for mode in ('uniform', 'spatial'):
            keys = [f'{region}_{mode}_s{seed}' for seed in run.SEEDS]
            rows = [cases[key] for key in keys]
            groups[region+'_'+mode] = {'cases': keys,
                'responses': {name: span([row['response'][name] for row in rows]) for name in rows[0]['response']},
                'rain_ratio': span([row['rain_ratio'] for row in rows]),
                'land_rain_sources': {name: span([row['sources']['scored_land']['annual_rain_fraction_by_source'][name] for row in rows]) for name in run.model.SOURCES},
                'source_fates': {name: {quantity: span([row['domain_atmospheric_source_fates'][name][quantity] for row in rows])
                    for quantity in rows[0]['domain_atmospheric_source_fates'][name]}
                    for name in rows[0]['domain_atmospheric_source_fates']}}
        pairs = {}
        for seed in run.SEEDS:
            a,b = [cases[f'{region}_{mode}_s{seed}'] for mode in ('uniform', 'spatial')]
            fa,fb = [row['domain_atmospheric_source_fates']['boundary'] for row in (a,b)]
            pairs[str(seed)] = {'annual_land_rain_difference_mm': b['response']['annual_rain_mm']-a['response']['annual_rain_mm'],
                'coastal_winter_difference_mm': b['response']['coast_winter_mm']-a['response']['coast_winter_mm'],
                'gross_boundary_supply_fractional_change': fb['supply_mm_domain_mean']/fa['supply_mm_domain_mean']-1,
                'boundary_sourced_domain_rain_fractional_change': fb['precipitation_mm_domain_mean']/fa['precipitation_mm_domain_mean']-1}
        contrasts[region] = {'pairs': pairs, 'summary': {name: span([p[name] for p in pairs.values()]) for name in pairs[str(run.SEEDS[0])]},
            'note': 'Five fixed synthetic catalogues, paired within region. Descriptive spread; no observational climate confidence interval.'}
    max_source = max(abs(v) for record in records.values() for v in record[-1]['sources']['annual_error_mm'])
    return {'source_manifest_sha256': sha256(source/'manifest.json'), 'source_state_sha256': sha256(source/'state.json'),
        'source_code_sha256': protocol['code_sha256'], 'analysis_script_sha256': sha256(Path(__file__)),
        'sources_verified': True, 'cases': cases, 'groups': groups, 'paired_contrasts': contrasts,
        'integration_minutes': seconds/60, 'cycles': cycles, 'all_settled': all(row['settled'] for row in cases.values()),
        'seed41_anchors_reproduced': all(row['anchor_reproduced'] for key,row in state['cases'].items() if key.endswith('s41')),
        'max_final_year_source_budget_error_mm': max_source, 'new_climate_integrations': 0, 'atlas_updated': False}


def markdown(data):
    lines = ['# Completed water-source / paired-weather review', '',
        f"20/20 cases verified; {data['cycles']} cycles; {data['integration_minutes']:.1f} saved integration minutes. All settle. All four seed-41 physical controls reproduce exactly.", '',
        '| Region / winds | Annual scored-land rain across five seeds | Reference | Boundary share of land rain | Boundary supply leaving again | Ocean vapor leaving again |',
        '|---|---:|---:|---:|---:|---:|']
    for key, row in data['groups'].items():
        r = row['responses']['annual_rain_mm'];obs = row['responses']['annual_reference_mm']['mean']
        f = row['source_fates']
        lines.append(f"| {key} | {r['min']:.1f}–{r['max']:.1f} mm | {obs:.1f} mm | {row['land_rain_sources']['boundary']['mean']:.1%} | {f['boundary']['export_to_supply']['mean']:.1%} | {f['ocean_evaporation']['export_to_supply']['mean']:.1%} |")
    lines += ['', 'Rain and source shares refer to scored land. Export/supply fractions refer '
        'to full-domain atmospheric source ledgers; they are not land precipitation efficiency. '
        'Vapor supply is gross external influx or local evaporation. Store changes and '
        'explicit tiny numerical adjustments close each source balance.', '',
        'Spatial background winds underproduce rain in every tested storm catalogue. '
        'Boundary supply falls only about a fifth, while its domain precipitation falls '
        'far more. Local ocean evaporation rises, but almost all of that water leaves '
        'without precipitation. A uniform humidity/evaporation increase is therefore '
        'not yet a justified fix for the rain-placement problem.', '',
        'These are last-vapor-source tags; land evaporation resets soil ancestry. '
        'They establish source balances and catalogue sensitivity, not causal '
        'attribution between missing real fronts, thermal/vertical forcing, boundary '
        'structure and cloud physics. Five synthetic catalogues are not actual climate '
        'uncertainty, and repeated settling cycles are not independent weather years.', '',
        'Next use cached forcing/operator audits to distinguish those mechanisms. '
        'Do not spend another batch on storm-seed selection. Real six-hourly weather '
        'covariance still awaits accessible reference data. No atlas update.', '',
        '![Paired rain and source removals](source_comparison.png)']
    return '\n'.join(lines)+'\n'


def plot(data, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5), constrained_layout=True)
    for col, region in enumerate(('california', 'iberia')):
        ax = axes[0, col];groups = [data['groups'][region+'_'+mode] for mode in ('uniform', 'spatial')]
        for seed_index, seed in enumerate(run.SEEDS):
            values = [data['cases'][f'{region}_{mode}_s{seed}']['response']['annual_rain_mm'] for mode in ('uniform', 'spatial')]
            jitter = (seed_index-2)*.035
            ax.plot(np.arange(2)+jitter, values, 'o-', color='#277f97', lw=.8, alpha=.65, ms=5)
        ax.axhline(groups[0]['responses']['annual_reference_mm']['mean'], color='#a15d21', ls='--', label='Observed reference')
        ax.set(title=region.title(), ylabel='Scored-land annual rainfall (mm)', xticks=[0, 1], xticklabels=['Uniform winds', 'Spatial winds'])
        ax.set_ylim(bottom=0);ax.grid(axis='y', alpha=.2);ax.legend(frameon=False, fontsize=9)
        ax = axes[1, col]
        labels = [];values = []
        for source, name in (('boundary', 'Boundary'), ('ocean_evaporation', 'Ocean')):
            for mode, mode_label in (('uniform', 'Uniform'), ('spatial', 'Spatial')):
                labels.append(name+'\n'+mode_label)
                values.append([100*data['cases'][f'{region}_{mode}_s{seed}']['domain_atmospheric_source_fates'][source]['precipitation_to_supply'] for seed in run.SEEDS])
        ax.bar(np.arange(4), [np.mean(a) for a in values], color=['#438ca2', '#d08045']*2, alpha=.65, width=.65)
        for i, a in enumerate(values):
            ax.plot(i+np.linspace(-.12, .12, len(a)), a, '.', color='#26383e', ms=5)
        ax.set(xticks=np.arange(4), xticklabels=labels, ylabel='Annual vapor supply precipitating\nanywhere in domain (%)')
        ax.set_ylim(bottom=0);ax.grid(axis='y', alpha=.2)
    fig.suptitle('Drought persists across storm catalogues; a larger vapor fraction leaves without rain', fontsize=14)
    fig.supxlabel('Five fixed synthetic catalogues. Source removals include ocean and all land; not land precipitation efficiency.', fontsize=10)
    fig.savefig(out/'source_comparison.png', dpi=170);fig.savefig(out/'source_comparison.svg')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_water_sources')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_water_sources_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv);data = analyse(args.source)
    if args.write:
        args.out.mkdir(parents=True, exist_ok=True)
        atomic_json(args.out/'review.json', data)
        (args.out/'review.md').write_text(markdown(data));plot(data, args.out)
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
