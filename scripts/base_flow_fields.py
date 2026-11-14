"""Base-flow diversion sensitivity (calibration/base_flow_20261114/plan.json).

Capture in both windows; the river source is either the archived flood excess
or a share of total monthly flow. Runs the pinned matched-weather case code.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import daily_river_fields as D
import matched_regional_fields as M
import capture_season_fields as C
from tigris_fields import REGION as MESO
from land_people import DAYS
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/base_flow_20261114/plan.json'; OUT = ROOT / 'output/base_flow_20261114'
ARCHIVE = ROOT / 'output/capture_season_20261114'; SHARES = (0.10, 0.25, 0.50)


def flows():
    phase = json.loads((ROOT / 'output/flood_basin_seasonality_20261113/results.json').read_text())
    aswan = np.array(next(v for v in phase['rows'] if v['id'] == 'aswan')['mean_monthly_flow_m3s'])
    pooled = np.load(ROOT / 'output/tigris_gauge_20261114/fields.npz')['hit_plus_mosul__common_mean_flow']
    return {'nile': aswan, MESO: pooled}


def source(q, rule):
    vol = q * DAYS * 86400
    return np.maximum(q - q.mean(), 0) * DAYS * 86400 if rule == 'flood_excess' else float(rule) * vol


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    archive = json.loads((ARCHIVE / 'results.json').read_text()); review = json.loads((ARCHIVE / 'review.json').read_text())
    assert review['status'] == 'passed' and review['results_sha256'] == sha(ARCHIVE / 'results.json')
    protected = {str((ARCHIVE / n).relative_to(ROOT)): d for n, d in archive['files_sha256'].items()}; protected.update(archive['producers'])
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, name
    with np.load(ARCHIVE / 'fields.npz') as z: old = {k: z[k] for k in z.files if '__both__' in k}
    M.load_inputs(); q = flows(); rows = []; arrays = {}; sources = {}
    for region in ('nile', MESO):
        for rule in ('flood_excess',) + tuple(f'{s:.2f}' for s in SHARES):
            src = source(q[region], rule); sources[f'{region}__{rule}'] = src
            if region == 'nile' and rule == 'flood_excess': assert np.allclose(src, D.STATIC['nile']['source_m3'], rtol=1e-12)
            for calendar in ('old', 'fractional'):
                for method in ('hargreaves', 'penman_monteith'):
                    spec = (region, calendar, True, method, 'matched')
                    original = D.STATIC[region]; f = dict(original); f['source_m3'] = src; D.STATIC[region] = f
                    try:
                        row, fields, monthly, daily = run_both(spec)
                    finally: D.STATIC[region] = original
                    stem = row['case'] + ('__tigris' if region == MESO else '') + '__both'; case = stem + '__source_' + rule
                    exact = None
                    if rule == 'flood_excess':
                        for name, value in fields.items(): np.testing.assert_array_equal(value, old[f'{stem}__{name}'], err_msg=name)
                        for name, value in monthly.items(): np.testing.assert_array_equal(value, old[f'{stem}__monthly_{name}'], err_msg=name)
                        for name, value in daily.items(): np.testing.assert_array_equal(value, old[f'{stem}__daily_{name}'], err_msg=name)
                        exact = True
                    row.update(case=case, parent_case=stem, window='both', source_rule=rule, archived_arrays_exact=exact)
                    rows.append(row)
                    for name, value in fields.items(): arrays[f'{case}__{name}'] = value
                    for name, value in monthly.items(): arrays[f'{case}__monthly_{name}'] = value
                    for name, value in daily.items(): arrays[f'{case}__daily_{name}'] = value
                    print(case[-72:], round(100 * row['root_coverage'], 2), 'adequate km2', round(row['adequate_root_area_km2'] or 0), 'delivered', round(row['delivered_m3'] / 1e9, 2), flush=True)
    out.mkdir(parents=True, exist_ok=True); np.savez_compressed(out / 'fields.npz', **{'source__' + k: v for k, v in sources.items()}, **arrays)
    for name, digest in protected.items(): assert sha(ROOT / name) == digest, 'Protected file changed: ' + name
    ratio = {}
    for rule in ('flood_excess',) + tuple(f'{s:.2f}' for s in SHARES):
        for calendar in ('old', 'fractional'):
            for method in ('hargreaves', 'penman_monteith'):
                pick = lambda region: next(r for r in rows if r['region'] == region and r['source_rule'] == rule and r['calendar'] == calendar and r['method'] == method)
                n, m = pick('nile')['adequate_root_area_km2'], pick(MESO)['adequate_root_area_km2']
                ratio[f'{rule}__{calendar}__{method}'] = dict(nile_adequate_km2=n, mesopotamia_adequate_km2=m, nile_over_mesopotamia=None if not m else n / m)
    write(out / 'results.json', dict(status='base_flow_sensitivity_development_only', adopt=False, rows=rows, adequate_area_ratio=ratio,
        annual_source_km3={k: float(v.sum() / 1e9) for k, v in sources.items()},
        producers={str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), PLAN, ROOT / 'scripts/capture_season_fields.py', ROOT / 'scripts/tigris_fields.py', ROOT / 'scripts/matched_regional_fields.py', ROOT / 'scripts/daily_river_fields.py', ROOT / 'harvest/river_fields.py']},
        files_sha256={'fields.npz': sha(out / 'fields.npz')}, unchanged_sha256=protected,
        max_abs_mass_residual_m3=max(abs(r['joint_mass_residual_m3']) for r in rows)))
    print('wrote', len(rows))


def run_both(spec):
    """capture_season_fields.run with window 'both' but WITHOUT its Mesopotamia source override (the source is set by the caller)."""
    region = spec[0]; base = M.BASE_PREPARE
    def prepare(s):
        fields, clock, eligible, a, opts = base(s)
        crop = a['crop_mask'].any(axis=1); cap = a['pond_mask'][:, 0] | crop
        a['capture_mask'] = np.broadcast_to(cap[:, None], a['pond_mask'].shape).copy()
        return fields, clock, eligible, a, opts
    M.BASE_PREPARE = prepare
    try: return M.run_case(spec)
    finally: M.BASE_PREPARE = base


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT); main(p.parse_args().out)
