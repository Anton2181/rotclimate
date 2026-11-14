"""Mesopotamia matched-weather fields with the Tigris added to the river pool (declared field plan).

Runs the pinned matched-weather case code unchanged; only the Mesopotamian river
source differs. Rain-only cases must reproduce the archived arrays exactly.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import daily_river_fields as D
import matched_regional_fields as M
from land_people import DAYS
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/tigris_gauge_20261114/field_plan.json'
GAUGE = ROOT / 'output/tigris_gauge_20261114'; ARCHIVE = ROOT / 'output/matched_regional_fields_20261114'
OUT = ROOT / 'output/tigris_fields_20261114'; REGION = 'mesopotamia_euphrates_only'


def pooled_source():
    z = np.load(GAUGE / 'fields.npz'); q = z['hit_plus_mosul__common_mean_flow']
    return np.maximum(q - q.mean(), 0) * DAYS * 86400


def run(spec, source):
    if M.FORCING is None: M.load_inputs()
    original = D.STATIC[REGION]; f = dict(original); f['source_m3'] = source if source is not None else original['source_m3']
    D.STATIC[REGION] = f
    try: return M.run_case(spec)
    finally: D.STATIC[REGION] = original


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    gauge = json.loads((GAUGE / 'results.json').read_text()); review = json.loads((GAUGE / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(GAUGE / 'results.json')
    archive = json.loads((ARCHIVE / 'results.json').read_text())
    for name, digest in {**archive['producers'], **archive['sources']}.items(): assert sha(ROOT / name) == digest, 'Pinned matched-weather input changed: ' + name
    for name, digest in archive['files_sha256'].items(): assert sha(ARCHIVE / name) == digest, name
    protected = {f'output/matched_regional_fields_20261114/{k}': v for k, v in archive['files_sha256'].items()}
    protected.update({f'output/tigris_gauge_20261114/{k}': v for k, v in gauge['files_sha256'].items()})
    M.load_inputs(); source = pooled_source(); old_source = D.STATIC[REGION]['source_m3'].copy()
    assert abs(source.sum() / 1e9 - gauge['comparison']['common_years']['hit_plus_mosul']['positive_excess_km3']) < 1e-9
    assert abs(old_source.sum() / 1e9 - gauge['comparison']['common_years']['hit']['positive_excess_km3']) < 1e-9
    rows = []; arrays = {}; old_rows = {r['case']: r for r in archive['rows']}
    with np.load(ARCHIVE / 'fields.npz') as z: old = {k: z[k] for k in z.files if k.startswith(REGION) and '__matched_' in k}
    for calendar in ('old', 'fractional'):
        for capture in (False, True):
            for method in ('hargreaves', 'penman_monteith'):
                spec = (REGION, calendar, capture, method, 'matched')
                row, fields, monthly, daily = run(spec, source)
                parent = row['case']; case = parent + '__tigris'; prior = old_rows[parent]
                exact = None
                if not capture:                                        # river unused: must equal the archive exactly
                    for name, value in fields.items(): np.testing.assert_array_equal(value, old[f'{parent}__{name}'], err_msg=name)
                    for name, value in monthly.items():
                        if not name.startswith('river_'): np.testing.assert_array_equal(value, old[f'{parent}__monthly_{name}'], err_msg=name)
                    for name, value in daily.items(): np.testing.assert_array_equal(value, old[f'{parent}__daily_{name}'], err_msg=name)
                    exact = True
                row.update(case=case, parent_case=parent, river='euphrates_plus_tigris', rain_only_arrays_exact=exact,
                           euphrates_only_root_coverage=prior['root_coverage'], euphrates_only_delivered_m3=prior['delivered_m3'],
                           euphrates_only_source_m3=prior['source_m3'], coverage_change_points=100 * (row['root_coverage'] - prior['root_coverage']))
                rows.append(row)
                for name, value in fields.items(): arrays[f'{case}__{name}'] = value
                for name, value in monthly.items(): arrays[f'{case}__monthly_{name}'] = value
                for name, value in daily.items(): arrays[f'{case}__daily_{name}'] = value
                print(case[-60:], 'coverage', round(100 * prior['root_coverage'], 3), '->', round(100 * row['root_coverage'], 3), 'delivered km3', round(prior['delivered_m3'] / 1e9, 3), '->', round(row['delivered_m3'] / 1e9, 3), flush=True)
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', source_m3_pooled=source, source_m3_euphrates_only=old_source, **arrays)
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, 'Protected file changed: ' + name
    write(out / 'results.json', dict(status='tigris_pool_field_development_only', adopt=False, rows=rows,
        source_km3=dict(euphrates_only=float(old_source.sum() / 1e9), euphrates_plus_tigris=float(source.sum() / 1e9)),
        source_by_month_km3=dict(euphrates_only=(old_source / 1e9).tolist(), euphrates_plus_tigris=(source / 1e9).tolist()),
        producers={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), PLAN, ROOT / 'scripts/matched_regional_fields.py', ROOT / 'scripts/daily_river_fields.py', ROOT / 'harvest/river_fields.py']},
        files_sha256={'fields.npz': sha(out / 'fields.npz')}, unchanged_sha256=protected,
        max_abs_mass_residual_m3=max(abs(r['joint_mass_residual_m3']) for r in rows)))
    print('wrote', len(rows), 'cases')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT); main(p.parse_args().out)
