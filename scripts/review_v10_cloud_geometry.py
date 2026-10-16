"""Verify and interpret completed passive cloud-path replays, without integration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import replay_v10_cloud_geometry as run
from rotclimate_v10.earth import atomic_json, sha256


def overlap_bounds(first, second):
    """Bounds on intersection of two subsets of the same weighted population."""
    if first is None or second is None:
        return None
    if not 0 <= first <= 1 or not 0 <= second <= 1:
        raise ValueError('Subset fractions must lie in [0,1].')
    return [max(0., first+second-1.), min(first, second)]


def load_verified(source, prepared=None):
    protocol, inputs, setting, initials, finals, originals, tables = run.prepare() if prepared is None else prepared
    state = json.loads((source/'state.json').read_text())
    if json.loads((source/'manifest.json').read_text()) != protocol or state['status'] != 'complete':
        raise ValueError('Need unchanged, completed cloud-geometry replays.')
    if set(state['cases']) != {job['key'] for job in protocol['jobs']}:
        raise ValueError('Cloud-geometry case set differs from protocol.')
    records = {}; collectors = {}; seconds = 0.; errors = []; path_errors = []
    for job in protocol['jobs']:
        key = job['key']; folder = source/'cases'/key; row = state['cases'][key]
        run.forcing.verify_completed(folder, row)
        if json.loads((folder/'config.json').read_text()) != {**job, 'code_sha256': protocol['code_sha256']}:
            raise ValueError('Cloud-geometry case config changed.')
        if set(row['evidence_sha256']) != {'year1.json', 'year1.npz'}:
            raise ValueError('Incomplete cloud-geometry annual evidence.')
        region = job['region']; case, p, g, air, circulation = inputs[region]
        record, collector = run.read_checkpoint(folder, case, g, setting, p, air, completed=True)
        if record is None:
            raise ValueError('Missing final cloud-geometry year.')
        run.forcing.replay.verify_physical(record, finals[key])
        run.event.validate_control_record(record, tables[region]['target_'+job['variant']])
        errors.append(run.review.verify_fields(record, initials[key], case, g, 'parcel_lower'))
        metrics = collector.arrays['metrics']
        expected = metrics[:, 2]*(g.pressure[:3]-g.pressure[1:4])[None]
        if not np.allclose(metrics[:, 5], expected, atol=1e-6, rtol=1e-11):
            raise ValueError('Rain-weighted pressure path disagrees with fixed geometry.')
        path_errors.append(float(abs(metrics[:, 5]-expected).max()))
        # Cellwise total rain was checked by the checkpoint reader. Also check
        # the full original scored-land layer ledger independently of summary.
        actual = collector.arrays['layer_rain'][:, :, case.score_mask].mean(-1)
        expected = np.array(record[-1]['diagnostics']['layer_rain_scored_land_mm'])
        if not np.allclose(actual, expected, atol=1e-9, rtol=0):
            raise ValueError('Passive layer totals disagree with physical rain ledger.')
        if run.summarize(folder, job, case, record, collector) != row:
            raise ValueError('Cloud-geometry summary differs from saved measurements.')
        records[key] = record; collectors[key] = collector; seconds += record[-1]['elapsed_seconds']
    if run.source_id() != protocol['code_sha256']:
        raise ValueError('Cloud-geometry sources changed during review.')
    return protocol, state, inputs, records, collectors, seconds, errors, path_errors


def analyse(source):
    protocol, state, inputs, records, collectors, seconds, errors, path_errors = load_verified(source)
    cases = {}
    for job in protocol['jobs']:
        key = job['key']; row = state['cases'][key]; cases[key] = {}
        case, p, g, air, circulation = inputs[job['region']]
        for area, measurements in row['regions'].items():
            result = {'cells': measurements['cells']}
            for season in ('winter', 'summer'):
                s = measurements[season]; rain = s['parcel_rain_mm']; total = s['total_rain_mm']
                result[season] = dict(s,
                    parcel_fraction_of_surface_rain=rain/total if total>0 else None,
                    parcel_fraction_by_interface=[v/rain for v in s['by_interface']['parcel_rain_mm']] if rain>0 else None,
                    late_and_dry_joint_fraction_bounds=overlap_bounds(s['parcel_rain_first_saturation_above_face_fraction'], s['parcel_rain_dry_pre_step_recipient_fraction']))
            cases[key][area] = result
    data = {'source_code_sha256': protocol['code_sha256'], 'source_manifest_sha256': sha256(source/'manifest.json'),
        'source_state_sha256': sha256(source/'state.json'), 'analysis_script_sha256': sha256(Path(__file__)),
        'sources_verified': True, 'exact_replays': len(cases), 'integration_minutes': seconds/60.,
        'maximum_recomputed_errors': {k: max(abs(e[k]) for e in errors) for k in errors[0]},
        'maximum_pressure_weighted_rain_identity_error_pa_mm': max(path_errors), 'cases': cases,
        'interpretation': 'Actual rain subsets on one unchanged synthetic trajectory. Late onset follows the frozen relaxed dry-theta path; it does not measure a different climate, entrainment or evaporation. Pre-step recipient RH/T are not in-cloud RH or virtual-temperature buoyancy. Upward vapor can recross interfaces; it is not unique input or a climate rainfall ceiling.',
        'seasons': 'Winter October–March, summer April–September. Iberia-domain masks include North Africa; location and regime groups overlap.',
        'new_climate_integrations': 0, 'new_downloads': 0, 'atlas_updated': False}
    return data


def markdown(data):
    lines = ['# Completed cloud-geometry diagnosis', '',
        f"All {data['exact_replays']} exact final-year replays verified; {data['integration_minutes']:.2f} saved integration minutes. Physical arrays/ledgers reproduce, monthly actual incoming water and annual water/energy/thermal checks pass. Diagnostic layer rain, pressure weights, subsets and summaries reconcile.", '',
        '| Case | Coastal winter parcel rain / total | Winter: first saturation above face | Arid summer parcel rain / total | Summer: first saturation above face | Summer: recipient pre-step RH <70% |',
        '|---|---:|---:|---:|---:|---:|']
    for key, areas in data['cases'].items():
        w = areas['coast']['winter']; s = areas['reference_arid']['summer']
        lines.append(f"| {key} | {w['parcel_rain_mm']:.2f} / {w['total_rain_mm']:.2f} mm | {w['parcel_rain_first_saturation_above_face_fraction']:.1%} | {s['parcel_rain_mm']:.2f} / {s['total_rain_mm']:.2f} mm | {s['parcel_rain_first_saturation_above_face_fraction']:.1%} | {s['parcel_rain_dry_pre_step_recipient_fraction']:.1%} |")
    lines += ['', '## What differs between winter coast and arid summer land', '',
        'In the input-matched Iberia-domain summer case, most surface rain comes from the unmixed parcel operator. Most of that parcel rain first saturates only after the true layer face, farther along the path to the receiving midpoint; almost all enters a dry pre-step environment. Winter coastal rain has a substantially smaller late-onset fraction. The same qualitative seasonal contrast occurs in California, whose reference-arid summer land is already too dry. This is a mechanism signature, not proof that all summer rain should be removed.', '',
        '| Local-matched case / region | Parcel fraction of total rain | Parcel fraction at third tested interface | Rain-weighted midpoint gap | Vapor-weighted donor RH |',
        '|---|---:|---:|---:|---:|']
    for region in ('california', 'iberia'):
        areas = data['cases'][region+'_local_matched']
        for area, season in (('coast', 'winter'), ('reference_arid', 'summer'), ('interior', 'summer')):
            s = areas[area][season]
            lines.append(f"| {region} / {area} {season} | {s['parcel_fraction_of_surface_rain']:.1%} | {s['parcel_fraction_by_interface'][2]:.1%} | {s['rain_weighted_midpoint_pressure_gap_hpa']:.1f} hPa | {s['vapor_weighted_donor_RH']:.1%} |")
    low, high = data['cases']['iberia_local_matched']['reference_arid']['summer']['late_and_dry_joint_fraction_bounds']
    lines += ['', f'The separate late-onset and dry-environment marginals imply that **{low:.1%}–{high:.1%}** of Iberia-domain arid summer parcel rain satisfies both conditions. This is an inclusion–exclusion bound, not a stored joint histogram. Fractions refer to parcel rain, not all surface rain or the fraction of error.', '',
        '![Rain by interface and onset](interface_rainfall.png)', '',
        '## Consequence for the next mechanism test', '',
        'First compare the vertical cloud path and conservative parcel/environment mixing under common manufactured forcing. The current data favor that controlled test over immediately adding a global RH cutoff or applying a buoyancy gate to all upward motion. A finite path may legitimately reach saturation inside the receiving layer, so deleting all above-face rain would not be a valid refinement test. A colder-than-recipient parcel is not a complete virtual-temperature/CAPE calculation, and mechanically forced rain need not require positive CAPE.', '',
        'The research comparison identifies KiD-style prescribed-flow experiments as an appropriate method, with a possible later diagnostic rain shaft or cloud/rain stores. Winter storm forcing remains a separate open problem: these gross upward-vapor amounts can recount water and must not be interpreted as a climate rainfall ceiling. No physical proposal or atlas update is selected by this replay alone.', '',
        'See [model research and proposed test sequence](../../reports/model_precipitation_research_20261016.md). Reproduce saved-only verification:', '',
        '```sh', '.venv/bin/python scripts/review_v10_cloud_geometry.py --write', '```']
    return '\n'.join(lines)+'\n'


def plot(data, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    colors = ['#6bafbb', '#3c859e', '#32536c']
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.2), constrained_layout=True)
    for i, region in enumerate(('california', 'iberia')):
        for j, (area, season, title) in enumerate((('coast', 'winter', 'Coastal winter'), ('reference_arid', 'summer', 'Reference-arid summer'))):
            ax = axes[i, j]
            for x, variant in enumerate(('uniform', 'local_matched')):
                s = data['cases'][region+'_'+variant][area][season]
                by = s['by_interface']; bottom = 0.
                for interface in range(3):
                    rain = by['parcel_rain_mm'][interface]; late = by['parcel_rain_first_saturation_above_face_mm'][interface]
                    ax.bar(x, rain, bottom=bottom, width=.55, color=colors[interface], edgecolor='white')
                    ax.bar(x, late, bottom=bottom+rain-late, width=.55, facecolor='none', edgecolor='#1c323d', hatch='////', linewidth=.4)
                    bottom += rain
                ax.bar(x, s['total_rain_mm']-s['parcel_rain_mm'], bottom=bottom, width=.55, color='#b8baba', edgecolor='white')
                ax.annotate(f"{s['total_rain_mm']:.1f} mm", (x, s['total_rain_mm']), xytext=(0, 6), textcoords='offset points', ha='center', fontsize=10)
            maximum = max(data['cases'][region+'_'+variant][area][season]['total_rain_mm'] for variant in ('uniform', 'local_matched'))
            ax.set(title=region.title()+' · '+title, ylabel='Seasonal rain (mm)', xticks=[0, 1], xticklabels=['Uniform humidity', 'Local · same monthly input'], ylim=(0, 1.22*max(1., maximum)))
            ax.grid(axis='y', alpha=.2); ax.set_axisbelow(True)
    legend = [Patch(facecolor=colors[k], label=f'Parcel rain · interface {k+1}') for k in range(3)]
    legend += [Patch(facecolor='#b8baba', label='Remaining bulk rain'), Patch(facecolor='white', edgecolor='#1c323d', hatch='////', label='First saturation above layer face')]
    fig.legend(handles=legend, loc='outside lower center', ncol=3, fontsize=9, frameon=False)
    fig.suptitle('Summer parcel rain depends strongly on the upper part of the model layer path\nExact unchanged climates · interface 1 is lowest · one synthetic catalogue', fontsize=13)
    for ext in ('png', 'svg'):
        fig.savefig(out/('interface_rainfall.'+ext), dpi=170, facecolor='#fbfcfc')
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'output/v10_cloud_geometry')
    parser.add_argument('--out', type=Path, default=ROOT/'output/v10_cloud_geometry_review')
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args(argv)
    if args.write:
        for protected in (args.source, *run.protected_paths()):
            a, b = args.out.resolve(), protected.resolve()
            if a == b or a in b.parents or b in a.parents:
                raise ValueError('Preserve original experiments and prepared evidence.')
    data = analyse(args.source)
    if args.write:
        atomic_json(args.out/'review.json', data); (args.out/'review.md').write_text(markdown(data)); plot(data, args.out)
    print(markdown(data))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
