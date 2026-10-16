"""Read-only review of complete or stopped transport experiments; never integrates."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from scripts import check_v10_regional_transport as run
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def completed_prefix(state, jobs):
    keys = [job['key'] for job in jobs]
    done = list(state['cases'])
    if done != keys[:len(done)] or (state['status'] == 'complete' and len(done) != len(keys)):
        raise ValueError('Saved cases are not the declared completed prefix.')
    if state['status'] not in ('complete', 'needs_diagnosis', 'budget_reached', 'interrupted'):
        raise ValueError('Review requires a stopped or completed experiment.')
    return keys[len(done):]


def check_review_path(out, source):
    run.check_output_path(out)
    a = out.resolve()
    for protected in (source, ROOT/'atlas'):
        b = protected.resolve()
        if a == b or a in b.parents or b in a.parents:
            raise ValueError('Review must not overwrite experiment evidence or the atlas.')


def fingerprints(source):
    roots = set(run.protected_paths()) | {source, ROOT/'atlas/data'}
    return {str(p.relative_to(ROOT)): sha256(p) for root in roots
            for p in root.rglob('*') if p.is_file()}


def endpoint_diagnostics(previous, current, case, geometry):
    temperature = run.model.base.temperature
    a, b = previous[0], current[0]
    old = temperature(a.energy, geometry.mass, a.water, geometry.height_m)
    new = temperature(b.energy, geometry.mass, b.water, geometry.height_m)
    delta = new-old
    index = np.unravel_index(np.argmax(abs(delta)), delta.shape)
    layers = []
    for k in range(len(delta)):
        layers.append({'layer': k, 'all_cells_p95_c': float(np.percentile(abs(delta[k]), 95)),
            'scored_land_p95_c': float(np.percentile(abs(delta[k][case.score_mask]), 95)),
            'max_c': float(abs(delta[k]).max()), 'mean_signed_c': float(delta[k].mean()),
            'fraction_exceeding_0_05c': float((abs(delta[k]) > .05).mean())})
    result = {'all_cells_p95_c': float(np.percentile(abs(delta), 95)),
        'scored_land_p95_c': float(np.percentile(abs(delta[:, case.score_mask]), 95)),
        'layers': layers, 'max_location_layer_y_x': [int(i) for i in index],
        'max_location_is_land': bool(case.domain.land[index[1:]]),
        'max_location_is_scored': bool(case.score_mask[index[1:]]),
        'max_location_pressure_hpa': float(geometry.pressure[index]/100),
        'max_location_dry_mass_kg_m2': float(geometry.mass[index]),
        'max_location_old_c': float(old[index]), 'max_location_new_c': float(new[index]),
        'max_location_old_water_mm': float(a.water[index]),
        'max_location_new_water_mm': float(b.water[index])}
    return result, delta


def analyse(source):
    before = fingerprints(source)
    protocol, inputs, setting, anchors, tables, originals = run.prepare()
    if json.loads((source/'manifest.json').read_text()) != protocol:
        raise ValueError('Frozen protocol differs from the saved experiment.')
    ready = json.loads((run.PREFLIGHT/'manifest.json').read_text())
    if ready['protocol'] != protocol or sha256(run.PREFLIGHT/'manufactured_waves.npz') != ready['manufactured_arrays_sha256']:
        raise ValueError('Prepared transport evidence changed.')
    state = json.loads((source/'state.json').read_text())
    missing = completed_prefix(state, protocol['jobs'])
    cases = {}; errors = []; dose = []; arrays = {}; cycles = 0; seconds = 0.
    for job in protocol['jobs']:
        key = job['key']; folder = source/'cases'/key
        identity = {**job, 'code_sha256': protocol['code_sha256'], 'settings': asdict(setting)}
        if (folder/'config.json').exists() and json.loads((folder/'config.json').read_text()) != identity:
            raise ValueError('Case configuration changed: '+key)
        if key not in state['cases']:
            cases[key] = {'status': 'incomplete', 'saved_files': sorted(p.name for p in folder.glob('*'))}
            continue
        row = state['cases'][key]; n = row['years']
        run.verify_completed(folder, row)
        names = {f'year{year}.{ext}' for year in range(1, n+1) for ext in ('json', 'npz')}
        if set(row['evidence_sha256']) != names or (n != 1 if job['phase'] == 'control' else not 3 <= n <= 6):
            raise ValueError('Incomplete annual evidence declaration: '+key)
        case, p, g, air, circulation = inputs[job['region']]
        anchor = anchors[job['source_case']]
        initial = anchor['initial'] if job['phase'] == 'control' else anchor['record'][0]
        target = run.driver_for(job['region'], inputs, setting, tables, originals).monthly_targets
        last = None; check = {'passed': False}; elapsed = 0.; history = []; last_delta = None
        for year in range(1, n+1):
            record = run.checkpoints.read_checkpoint(folder, year, case.domain.land.shape, completed=True)
            if record is None:
                raise ValueError('Missing completed annual record: '+key)
            run.source.run.run.validate_control_record(record, target)
            errors.append(run.review.verify_fields(record, initial, case, g, job['mode']))
            dose.append(float(abs(np.array(record[-1]['diagnostics']['monthly_boundary_import_gross_mm'])-target).max()))
            endpoint = None
            if last is not None:
                check = run.checkpoints.settling(last, record, case, g)
                endpoint, delta = endpoint_diagnostics(last, record, case, g)
                if last_delta is not None:
                    both = (abs(delta) > .05) & (abs(last_delta) > .05)
                    endpoint['successive_change_opposite_sign_fraction'] = float((delta[both]*last_delta[both] < 0).mean()) if both.any() else None
                    endpoint['successive_change_common_cells'] = int(both.sum())
                last_delta = delta
            if year >= 3 and year < n and check['passed']:
                raise ValueError('Case continued beyond the first eligible settling point.')
            response = run.review.rain_vector(case, record[1])
            history.append({'year': year, 'settling': check, 'endpoint': endpoint,
                'coast_winter_mm': response['coast_winter_mm'],
                'monthly_mae_mm': response['monthly_mae_mm'],
                'elapsed_seconds': record[-1]['elapsed_seconds'], 'steps': record[-1]['steps']})
            initial = record[0]; last = record; elapsed += record[-1]['elapsed_seconds']; cycles += 1
        if job['phase'] == 'control':
            run.replay.verify_physical(record, anchor['record']); check = {'passed': True}
        computed = run.summarize(record, case, check, n, anchor, job)
        computed.update(case_config_sha256=sha256(folder/'config.json'), elapsed_seconds=elapsed,
            evidence_sha256={name: sha256(folder/name) for name in sorted(names)})
        if computed != row:
            raise ValueError('Reconstructed summary differs from saved case: '+key)
        cases[key] = {'status': 'verified', 'summary': computed, 'cycles': history}
        seconds += elapsed
        arrays[key+'_rain'] = record[1]
        if last_delta is not None:
            arrays[key+'_end_temperature_delta_c'] = last_delta
        arrays[job['region']+'_reference_rain'] = case.observed_rain_mm
        arrays[job['region']+'_score_mask'] = case.score_mask
    if run.source_id() != protocol['code_sha256'] or fingerprints(source) != before:
        raise ValueError('Source, atlas or protected experiment evidence changed during review.')
    maxima = {name: max(abs(e[name]) for e in errors) for name in errors[0]} if errors else {}
    return {'schema': 1, 'review_code_sha256': sha256(Path(__file__)),
        'experiment_status': state['status'], 'error': state.get('error'),
        'code_sha256': protocol['code_sha256'], 'completed_cases': len(state['cases']),
        'planned_cases': len(protocol['jobs']), 'incomplete_cases': missing,
        'verified_annual_records': cycles, 'saved_integration_minutes': seconds/60,
        'invocation_minutes': sum(r['elapsed_seconds'] for r in state['invocations'])/60,
        'max_reconstructed_residuals': maxima, 'max_monthly_input_error_mm': max(dose, default=0.),
        'protected_files_checked_unchanged': len(before), 'protected_file_sha256': before,
        'real_simulations_started': 0, 'downloads': 0, 'atlas_updated': False, 'cases': cases}, arrays


def write_report(out, data):
    lines = ['# Saved regional transport review', '',
        f"Experiment **{data['experiment_status']}**, {data['completed_cases']}/{data['planned_cases']} cases; "
        f"{data['verified_annual_records']} annual records independently checked. Atlas unchanged.", '',
        'Stopped error: '+str(data['error']), '',
        '| Case | Winter coast mm | Reference mm | Monthly MAE mm | Target Med now arid | Settled |',
        '|---|---:|---:|---:|---:|---|']
    for key, result in data['cases'].items():
        if result['status'] != 'verified':
            lines.append(f'| {key} | incomplete | | | | |'); continue
        r = result['summary']; response = r['response']
        lines.append(f"| {key} | {response['coast_winter_mm']:.2f} | {response['coast_winter_reference_mm']:.2f} | {response['monthly_mae_mm']:.3f} | {r['koppen_fixed_surface_temperature']['target_mediterranean_to_arid']:.2%} | {r['settling']['passed']} |")
    lines += ['', 'Candidate rows describe the last **unsettled** cycle, not accepted climates.', '',
        'All four controls reproduce the parent physical fields and ledgers exactly. Each saved annual budget, '
        'signed thermal change, incoming monthly vapor target, evidence hash and reconstructed case summary was checked. '
        'The JSON contains cycle histories, layerwise endpoint changes and protected-file fingerprints.', '',
        'The California parcel candidate has only its configuration file; the failing state/time was not saved. '
        'The Iberia parcel candidate did not start. The original parcel dose uses donor-cell vapor, whereas '
        'the new corrected transport can leave a different amount in the recipient. This is a compatibility '
        'failure, not evidence that adding water or clipping rain is an acceptable fix.', '',
        '![Saved convergence and rainfall](convergence.png)', '',
        'No integration, forcing download or atlas publication is performed by this reviewer.']
    (out/'review.md').write_text('\n'.join(lines)+'\n')


def plot(out, data):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 2, figsize=(10, 10), layout='constrained')
    for col, region in enumerate(('california', 'iberia')):
        keys = ['control_'+region+'_bulk', 'candidate_'+region+'_bulk']
        if not all(data['cases'].get(key, {}).get('status') == 'verified' for key in keys):
            for ax in axes[:, col]:
                ax.text(.5, .5, region.title()+': paired results unavailable', ha='center', transform=ax.transAxes)
                ax.set_axis_off()
            continue
        old = data['cases']['control_'+region+'_bulk']['summary']['response']
        result = data['cases']['candidate_'+region+'_bulk']; new = result['summary']['response']
        ax = axes[0, col]
        label = f"FCT cycle {result['summary']['years']}\n"+('SETTLED' if result['summary']['settling']['passed'] else 'UNSETTLED')
        ax.bar(['Upwind', label, 'Reference'],
               [old['coast_winter_mm'], new['coast_winter_mm'], old['coast_winter_reference_mm']],
               color=['#777777', '#237f94', '#b07c25'])
        ax.set(title=region.title()+' — coastal winter', ylabel='Rain (mm)')
        for row, metric, limit, label in ((1, 'end_temperature_p95_c', .05, 'Endpoint temperature p95 (°C)'),
                                          (2, 'monthly_rain_p95_mm', 1., 'Monthly rain change p95 (mm)')):
            ax = axes[row, col]; history = result['cycles'][1:]
            ax.plot([h['year'] for h in history], [h['settling']['changes'][metric] for h in history], 'o-', color='#237f94')
            ax.axhline(limit, color='#b54b35', ls='--', label='Settling limit')
            ax.set(xlabel='Repeated forcing cycle', ylabel=label, yscale='log'); ax.legend()
    fig.suptitle('Fixed transport comparison — '+data['experiment_status'], fontsize=14)
    fig.savefig(out/'convergence.png', dpi=160); plt.close(fig)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=run.DEFAULT_OUT)
    p.add_argument('--out', type=Path, default=ROOT/'output/v10_regional_transport_review')
    args = p.parse_args(argv)
    check_review_path(args.out, args.source)
    data, arrays = analyse(args.source)
    args.out.mkdir(parents=True, exist_ok=True)
    atomic_json(args.out/'review.json', data); atomic_npz(args.out/'fields.npz', **arrays)
    plot(args.out, data); write_report(args.out, data)
    print(f"Verified {data['completed_cases']}/{data['planned_cases']} cases, {data['verified_annual_records']} annual records; {args.out/'review.md'}")


if __name__ == '__main__':
    main()
