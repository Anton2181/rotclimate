"""User-run physical probes for Mediterranean rain; no search or atlas writes.

Default is a read-only plan. --run explicitly enables two seasonal simulations.
The existing saved world is reused as the baseline. Completed cases are reusable.
"""
from dataclasses import asdict
import argparse
import json
import os
from pathlib import Path
import sys
import time

for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(variable, '1')
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rotclimate.config import Params
from rotclimate.koppen import CODES
from scripts.audit_saved_rules import label_metrics
from rotclimate.score import best_zone


def candidates(base):
    # Separate season/latitude changes from moisture-supply changes. Neither
    # knob uses the painted target to modify the physical fields.
    return {
        'seasonal_belts': base.replace(hadley_shift=base.hadley_shift + 2.0),
        'storm_mixing': base.replace(eddy_rate=base.eddy_rate * 1.25),
        'combined': base.replace(hadley_shift=base.hadley_shift + 2.0,
                                 eddy_rate=base.eddy_rate * 1.25),
        # Narrower storm envelope with stronger exchange near its centre.
        # The product width*rate stays unchanged; the background exchange
        # floor and actual water budget do not, so this is only a hypothesis.
        'focused_storms': base.replace(storm_width=base.storm_width * 0.8,
                                       eddy_rate=base.eddy_rate * 1.25),
    }


def matching_params(saved, expected):
    return json.dumps(asdict(Params(**saved)), sort_keys=True) == json.dumps(asdict(expected), sort_keys=True)


def previous_comparisons(path, base, options):
    """Retain completed cases only when they belong to this exact experiment."""
    if not path.exists():
        return {}
    rows = json.loads(path.read_text())
    if not matching_params(rows['baseline']['params'], base):
        return {}
    return {name: row for name, row in rows.items()
            if name in options and matching_params(row['params'], options[name])}


def saved_metrics(path):
    with np.load(path, allow_pickle=False) as f:
        mem = {key[11:]: f[key] for key in f.files if key.startswith('membership_')}
        labels = best_zone(mem, koppen=f['koppen'])
        row = label_metrics(labels, f['target'], f['valid'])
        med = f['valid'] & (f['target'] == 4)
        codes = np.array(CODES + ['unclassified'])[f['koppen']]
        dry = med & np.isin(codes, [c for c in CODES if c.startswith('B')])
        desert = med & np.isin(codes, ['BWh', 'BWk'])
        row['mediterranean'] = dict(
            cells=int(med.sum()), dry_share=float(dry.sum() / med.sum()),
            desert_share=float(desert.sum() / med.sum()),
            cs_share=float(np.isin(codes[med], ['Csa', 'Csb', 'Csc']).mean()),
            dry_cells_median_annual_rain_mm=float(np.median(f['index_MAP'][dry])) if dry.any() else None,
            dry_cells_median_winter_rain_mm=float(np.median(f['index_Pwin'][dry])) if dry.any() else None,
            dry_cells_median_fixed_threshold_gap_mm=float(np.median(
                (10 * f['index_Pth'] - f['index_MAP'])[dry])) if dry.any() else None)
        row['params'] = json.loads(str(f['params_json']))
        return row


def print_row(name, row):
    med = row['mediterranean']
    print(f"{name}: Mediterranean dry {med['dry_share']:.1%}, Cs {med['cs_share']:.1%}, "
          f"own label {row['zones']['med']['recall']:.1%}; "
          f"cold-dry correct {row['zones']['cold_dry']['recall']:.1%}, "
          f"hot-dry correct {row['zones']['hot_dry']['recall']:.1%}, "
          f"overall {row['accuracy']:.1%}", flush=True)
    if 'convergence' in row:
        c = row['convergence']
        print(f"  converged: {c['usable_for_comparison']}; "
              f"temperature failures {c['temperature_unconverged_steps']}, "
              f"linear failures {c['linear_unconverged_solves']}", flush=True)
    if 'mediterranean_patch_changes' in row:
        c = row['mediterranean_patch_changes']
        print(f"  original dry patch: {c['cured_cells']} cured, {c['persistent_cells']} still dry; "
              f"{c['new_dry_cells']} newly dry Mediterranean cells", flush=True)


def dry_patch_changes(baseline_path, candidate_path):
    """Track the same locations so a moving dry patch cannot hide in a total."""
    with np.load(baseline_path, allow_pickle=False) as b, np.load(candidate_path, allow_pickle=False) as c:
        if not np.array_equal(b['target'], c['target']) or not np.array_equal(b['valid'], c['valid']):
            raise ValueError('Patch comparison requires identical target and valid grids')
        med = b['valid'] & (b['target'] == 4)
        dry_codes = [i for i, code in enumerate(CODES) if code.startswith('B')]
        before = med & np.isin(b['koppen'], dry_codes)
        after = med & np.isin(c['koppen'], dry_codes)
        return dict(original_dry_cells=int(before.sum()),
                    cured_cells=int((before & ~after).sum()),
                    persistent_cells=int((before & after).sum()),
                    new_dry_cells=int((~before & after).sum()),
                    original_dry_patch_rain_change_median_mm={
                        season: float(np.median((c[f'index_{key}'] - b[f'index_{key}'])[before]))
                        if before.any() else None
                        for season, key in [('winter', 'Pwin'), ('summer', 'Psum'), ('annual', 'MAP')]})


def convergence_summary(detail):
    temperature = detail['temperature_convergence']
    linear_failures = detail['solver']['unconverged_solves']
    temperature_failures = temperature['unconverged_steps']
    moisture = detail.get('moisture_convergence', {})
    checked = moisture.get('enabled', False)
    moisture_failures = moisture.get('unconverged_steps') if checked else None
    return dict(linear_unconverged_solves=linear_failures,
                temperature_unconverged_steps=temperature_failures,
                max_temperature_update_c=max(temperature['final_update_max_c']),
                moisture_convergence_checked=checked,
                moisture_unconverged_steps=moisture_failures,
                usable_for_comparison=linear_failures == 0 and temperature_failures == 0
                    and (not checked or moisture_failures == 0))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--params', type=Path, default=ROOT / 'calibration/round20_retrograde_selected.json')
    ap.add_argument('--baseline-fields', type=Path, default=ROOT / 'output/rule_fields.npz')
    ap.add_argument('--baseline-diagnostics', type=Path,
                    help='optional convergence history accompanying the saved baseline')
    ap.add_argument('--out', type=Path, default=ROOT / 'output/mediterranean_pilot')
    ap.add_argument('--cases', default='seasonal_belts,storm_mixing')
    ap.add_argument('--run', action='store_true', help='enable long simulations; otherwise only print a plan')
    a = ap.parse_args()
    base = Params.from_json(a.params)
    options = candidates(base)
    names = a.cases.split(',')
    if len(set(names)) != len(names) or any(n not in options for n in names):
        ap.error('Choose unique cases from: ' + ','.join(options))
    baseline = saved_metrics(a.baseline_fields)
    # JSON normalises list/tuple representations of terrain tiers.
    if not matching_params(baseline['params'], base):
        ap.error('Baseline archive does not match input parameters; refusing an unfair comparison')
    if a.baseline_diagnostics is not None:
        detail = json.loads(a.baseline_diagnostics.read_text())
        if not matching_params(detail['params'], base):
            ap.error('Baseline convergence history does not match input parameters')
        baseline['convergence'] = convergence_summary(detail)
        if a.run and not baseline['convergence']['usable_for_comparison']:
            ap.error('Baseline did not converge; refusing to run physical comparisons')
    print_row('saved baseline', baseline)
    for name in names:
        changes = {k: v for k, v in asdict(options[name]).items() if v != asdict(base)[k]}
        print(f'{name}: {changes}', flush=True)
    print(f'{len(names)} simulations, one existing world; no calibration or atlas overwrite.', flush=True)
    if not a.run:
        print('Plan only. Add --run to execute. These are hypotheses, not known improvements.')
        return
    from scripts.diagnose_numerics import diagnose
    a.out.mkdir(parents=True, exist_ok=True)
    rows = previous_comparisons(a.out / 'comparison.json', base, options)
    rows['baseline'] = baseline
    for name in names:
        p = options[name]
        snapshot = a.out / f'{name}_fields.npz'
        diagnostic = a.out / f'{name}_diagnostics.json'
        reusable = snapshot.exists() and diagnostic.exists()
        if reusable:
            row = saved_metrics(snapshot)
            reusable = matching_params(row['params'], p)
        if not reusable:
            print(f'Running {name}...', flush=True)
            started = time.monotonic()
            def progress(done, total):
                if done == 1 or done % 5 == 0 or done == total:
                    print(f'  {name}: {done}/{total} seasonal steps including spin-up, '
                          f'{(time.monotonic() - started) / 60:.1f} min elapsed', flush=True)
            detail = diagnose(p, snapshot=snapshot, progress=progress)
            diagnostic.write_text(json.dumps(detail, indent=2) + '\n')
            row = saved_metrics(snapshot)
        row['convergence'] = convergence_summary(json.loads(diagnostic.read_text()))
        row['mediterranean_patch_changes'] = dry_patch_changes(a.baseline_fields, snapshot)
        rows[name] = row
        (a.out / 'comparison.json').write_text(json.dumps(rows, indent=2) + '\n')
        print_row(name, row)
        if not row['convergence']['usable_for_comparison']:
            raise SystemExit('Case did not converge. Results saved for diagnosis; stop tuning until resolved.')
    print('Compare Mediterranean dry area AND the other zones; one world is not a validation verdict.')


if __name__ == '__main__':
    main()
