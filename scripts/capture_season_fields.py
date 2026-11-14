"""Capture-season sensitivity on matched-weather fields (calibration/capture_season_20261114/plan.json).

Runs the pinned matched-weather case code; only the capture mask (and, for
Mesopotamia, the reviewed Tigris-pooled source) differ. pre_sowing must
reproduce the archived arrays exactly.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import daily_river_fields as D
import matched_regional_fields as M
from tigris_fields import pooled_source, REGION as MESO
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/capture_season_20261114/plan.json'; OUT = ROOT / 'output/capture_season_20261114'
ARCHIVE = {'nile': ROOT / 'output/matched_regional_fields_20261114', MESO: ROOT / 'output/tigris_fields_20261114'}
WINDOWS = ('pre_sowing', 'in_crop', 'both')
MATCHED_PREPARE = None


def run(spec, window, source):
    """M.run_case with the capture mask set per window; D.prepare is wrapped by M.run_case, so wrap the base it calls."""
    region = spec[0]
    if M.FORCING is None: M.load_inputs()
    original = D.STATIC[region]; f = dict(original)
    if region == MESO: f['source_m3'] = source
    D.STATIC[region] = f; base = M.BASE_PREPARE

    def prepare(s):
        fields, clock, eligible, a, opts = base(s)
        crop = a['crop_mask'].any(axis=1); pre = a['pond_mask'][:, 0] if s[-1] else np.zeros(len(clock.step_days), bool)
        if s[-1]:
            cap = {'pre_sowing': a['pond_mask'][:, 0], 'in_crop': crop, 'both': a['pond_mask'][:, 0] | crop}[window]
            if window == 'pre_sowing': assert np.array_equal(a['capture_mask'][:, 0], cap)
            a['capture_mask'] = np.broadcast_to(cap[:, None], a['pond_mask'].shape).copy()
        return fields, clock, eligible, a, opts
    M.BASE_PREPARE = prepare
    try: return M.run_case(spec)
    finally: M.BASE_PREPARE = base; D.STATIC[region] = original


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    archives = {k: json.loads((v / 'results.json').read_text()) for k, v in ARCHIVE.items()}
    tigris_review = json.loads((ARCHIVE[MESO] / 'review.json').read_text()); assert tigris_review['status'] == 'passed' and tigris_review['results_sha256'] == sha(ARCHIVE[MESO] / 'results.json')
    protected = {}
    for k, v in ARCHIVE.items():
        for name, digest in archives[k]['files_sha256'].items(): protected[str((v / name).relative_to(ROOT))] = digest
        for name, digest in archives[k]['producers'].items(): protected[name] = digest
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, name
    M.load_inputs(); source = pooled_source(); rows = []; arrays = {}
    old = {}
    for k, v in ARCHIVE.items():
        with np.load(v / 'fields.npz') as z: old.update({n: z[n] for n in z.files if '__matched_' in n and '_c1__' in n})
    for region in ('nile', MESO):
        for calendar in ('old', 'fractional'):
            for method in ('hargreaves', 'penman_monteith'):
                spec = (region, calendar, True, method, 'matched')
                for window in WINDOWS:
                    row, fields, monthly, daily = run(spec, window, source)
                    base_case = row['case'] + ('__tigris' if region == MESO else ''); case = base_case + '__' + window
                    exact = None
                    if window == 'pre_sowing':
                        for name, value in fields.items(): np.testing.assert_array_equal(value, old[f'{base_case}__{name}'], err_msg=name)
                        for name, value in monthly.items(): np.testing.assert_array_equal(value, old[f'{base_case}__monthly_{name}'], err_msg=name)
                        for name, value in daily.items(): np.testing.assert_array_equal(value, old[f'{base_case}__daily_{name}'], err_msg=name)
                        exact = True
                    row.update(case=case, parent_case=base_case, window=window, archived_arrays_exact=exact,
                               river='aswan' if region == 'nile' else 'euphrates_plus_tigris')
                    rows.append(row)
                    for name, value in fields.items(): arrays[f'{case}__{name}'] = value
                    for name, value in monthly.items(): arrays[f'{case}__monthly_{name}'] = value
                    for name, value in daily.items(): arrays[f'{case}__daily_{name}'] = value
                    print(case[-70:], round(100 * row['root_coverage'], 3), 'delivered km3', round(row['delivered_m3'] / 1e9, 3), flush=True)
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', **arrays)
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, 'Protected file changed: ' + name
    write(out / 'results.json', dict(status='capture_season_sensitivity_development_only', adopt=False, rows=rows,
        producers={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), PLAN, ROOT / 'scripts/tigris_fields.py', ROOT / 'scripts/matched_regional_fields.py', ROOT / 'scripts/daily_river_fields.py', ROOT / 'harvest/river_fields.py']},
        files_sha256={'fields.npz': sha(out / 'fields.npz')}, unchanged_sha256=protected,
        max_abs_mass_residual_m3=max(abs(r['joint_mass_residual_m3']) for r in rows)))
    print('wrote', len(rows), 'cases')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT); main(p.parse_args().out)
