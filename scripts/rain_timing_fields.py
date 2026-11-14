"""Rain-timing sensitivity on the eight mapped daily river/field illustrations.

calibration/rain_timing_20261114/plan.json. 32 cases: Nile and Euphrates-only,
both supplied calendars, capture and rain-only, four rain patterns on ONE common
clock per calendar. The pinned daily coupling, producer and reviewer are used
unchanged; only the clock and the per-step rain array differ. No adoption.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
import daily_river_fields as D
from harvest.field_clock import field_clock
from harvest.rain_timing import COUNTS, event_edges, timed_rain
from harvest.river_fields import RiverClock
from harvest.soil_drying import soil_profile
from land_people import CROPS
from settlement_locations_earth import sha, write

PLAN = ROOT / 'calibration/rain_timing_20261114/plan.json'
OUT = ROOT / 'output/rain_timing_20261114'
BASE = ROOT / 'output/daily_river_fields_20261114'
CROP, ZR, BG, POND, EFF = 'barley', 1.5, 0.15, 200.0, 1.0
PATTERNS = (None,) + COUNTS
BINS = np.linspace(0, 365, 13)
BASELINE_PREPARE = D.prepare


def label(count):
    return 'uniform' if count is None else f'events{count}'


def prepare(spec, count):
    """daily_river_fields.prepare on the common clock, with the selected rain pattern."""
    f, clock0, therm0, a0, opts = BASELINE_PREPARE(spec)                # pinned baseline, original clock
    region, crop, zr, calendar, bg, pondcap, eff, capture = spec; nf = len(f['lat'])
    begin = 365 * (10 if calendar == 'old' else 10.5) / 12; end = 365 * (3 if calendar == 'old' else 2.5) / 12; flood = 365 * 7 / 12
    clock = field_clock(BINS, event_edges_days=np.concatenate([[flood, begin, end], event_edges(BINS)]))
    globalcrop = clock.cyclic_window(begin, end); floodmask = clock.cyclic_window(flood, begin)
    ts = clock.repeat_bin_values(f['T']); c = CROPS[crop]
    therm = np.all((ts[globalcrop] >= c['window'][0]) & (ts[globalcrop] <= c['window'][1]), axis=0) & (ts[globalcrop].max(0) >= c['need_warm'])
    therm &= (np.sum(np.maximum(ts - c['base'], 0) * clock.step_days[:, None] * globalcrop[:, None], axis=0) >= c['heat'])
    if not np.array_equal(therm, therm0):
        raise ValueError('Common clock changed thermal eligibility; the plan fixes eligibility at baseline')
    cm = globalcrop[:, None] & therm[None, :]; pm = np.broadcast_to(floodmask[:, None], (len(clock.step_days), nf))
    a = dict(profile=soil_profile(.25, .1, zr, .1, 9.), area_m2=f['area_km2'] * 1e6, field_nodes=np.zeros(nf, dtype=int),
        source_m3=clock.spread_bin_totals(f['source_m3'][:, None]), clock=RiverClock(clock, [0], [-1]),
        rain_mm=timed_rain(clock, f['P'], count), eto_mm_day=clock.repeat_bin_values(f['PET'] / np.diff(clock.bin_edges_days)[:, None]),
        crop_mask=cm, capture_mask=pm if capture else np.zeros_like(pm), pond_mask=pm, crop_kcb=c['kc'])
    for key in ('profile', 'area_m2', 'field_nodes', 'crop_kcb'):       # everything not tied to the clock equals the baseline call
        same = a[key] == a0[key] if key in ('profile', 'crop_kcb') else np.array_equal(a[key], a0[key])
        if not same: raise ValueError('Baseline argument changed: ' + key)
    if not np.isclose(a['source_m3'].sum(), a0['source_m3'].sum(), rtol=1e-12) or not np.allclose(
            np.array([a['rain_mm'][clock.bin_index == b].sum(0) for b in range(12)]), f['P'], rtol=1e-11, atol=1e-9):
        raise ValueError('Bin water totals not conserved on the common clock')
    return f, clock, therm, a, opts


def main(out=OUT):
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) != PLAN.read_bytes():
        raise ValueError('Commit the exact declaration first')
    base = json.loads((BASE / 'results.json').read_text()); review = json.loads((BASE / 'review.json').read_text())
    for name, digest in base['producers'].items():
        if sha(ROOT / name) != digest: raise ValueError('Pinned daily coupling changed: ' + name)
    protected = dict(base['unchanged_sha256']); protected.update({f'output/daily_river_fields_20261114/{k}': v for k, v in base['files_sha256'].items()})
    for name, digest in protected.items():
        if sha(ROOT / name) != digest: raise ValueError('Protected file changed: ' + name)
    out.mkdir(parents=True, exist_ok=True); D.load_inputs(); archived = np.load(BASE / 'fields.npz'); old_rows = {r['case']: r for r in base['rows']}
    rows = []; fields = {}; control = []; original = D.prepare
    for region in D.REGIONS:
        for calendar in ('old', 'fractional'):
            for capture in (False, True):
                spec = (region, CROP, ZR, calendar, BG, POND, EFF, capture); results = {}
                for count in PATTERNS:
                    D.prepare = lambda s, n=count: prepare(s, n)          # only the clock and rain differ; run_case is the pinned one
                    try: row, values, monthly, daily = D.run_case(spec)
                    finally: D.prepare = original
                    parent = row['case']; case = f'{parent}__{label(count)}'
                    row.update(case=case, parent_case=parent, rain_pattern=label(count), events_per_bin=0 if count is None else count)
                    if not row['periodic']: raise ValueError('Case did not converge: ' + case)
                    rows.append(row); results[count] = (row, values)
                    for name, value in values.items(): fields[f'{case}__{name}'] = value
                    for name, value in monthly.items(): fields[f'{case}__monthly_{name}'] = value
                    for name, value in daily.items(): fields[f'{case}__daily_{name}'] = value
                    print(case, 'coverage', None if row['root_coverage'] is None else round(row['root_coverage'], 4), 'years', row['spinup_years'], flush=True)
                parent = results[None][0]['parent_case']; uni_row, uni = results[None]; old = old_rows[parent]
                diffs = {k: float(np.max(np.abs(uni[k] - archived[f'{parent}__{k}']))) for k in uni if k != 'eligible'}
                control.append(dict(parent_case=parent, original_clock_coverage=old['root_coverage'], common_clock_uniform_coverage=uni_row['root_coverage'],
                    coverage_difference=uni_row['root_coverage'] - old['root_coverage'], eligibility_identical=bool(np.array_equal(uni['eligible'], archived[f'{parent}__eligible'])),
                    max_annual_field_difference_mm=max(v for k, v in diffs.items() if k.startswith('annual_')),
                    max_field_coverage_difference=diffs['root_coverage'], original_steps=int(len(archived[f'{parent}__daily_top_mm'])),
                    common_steps=int(len(fields[f'{parent}__uniform__daily_top_mm']))))
    np.savez_compressed(out / 'fields.npz', **fields)
    for name, digest in protected.items():
        if sha(ROOT / name) != digest: raise ValueError('Protected file changed during run: ' + name)
    producers = {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT / 'harvest/rain_timing.py', PLAN]}
    write(out / 'results.json', dict(status='synthetic_rain_timing_sensitivity_development_only', adopt=False, rows=rows, clock_control=control,
        producers=producers, pinned_daily_producers=base['producers'], baseline_results_sha256=sha(BASE / 'results.json'),
        baseline_review_sha256=sha(BASE / 'review.json'), files_sha256={'fields.npz': sha(out / 'fields.npz')}, unchanged_sha256=protected,
        max_abs_mass_residual_m3=max(abs(r['joint_mass_residual_m3']) for r in rows),
        interpretation='Synthetic timing sensitivity; no event count is preferred or adopted. Events are synchronized scenarios, not observed storms.'))
    print('Wrote', len(rows), 'cases; max mass residual m3', max(abs(r['joint_mass_residual_m3']) for r in rows))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out', type=Path, default=OUT); main(p.parse_args().out)
