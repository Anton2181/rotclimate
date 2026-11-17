"""Independent unit/operation reductions plus explicit missing-resource controls."""
import csv
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import activity, load_packet, read, sha, write, verify_parent
from cereal_operation_demands import demands

OUT = ROOT / 'output/cereal_operation_demands_20261117'
BASE = ROOT / 'output/cereal_activity_packet_20261117'


def rows(p):
    with p.open() as f: return list(csv.DictReader(f))


def close(a, b):
    np.testing.assert_allclose(a, b, rtol=2e-12, atol=1e-6, equal_nan=True)


def main():
    assert not (OUT / 'qualification.json').exists()
    verify_parent()
    r = read(OUT / 'results.json')
    for n, h in r['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in r['files_sha256'].items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *r['files_sha256']]: assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    q = read(BASE / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(BASE / n) == h, n
    source = read(ROOT / 'research_notes/farm_labour_20261103.json')
    recipe = read(OUT / 'recipe.json')['hours_per_cropped_hectare']
    for code, crop in [('1', 'wheat'), ('2', 'barley')]:
        for task, value in recipe[code].items():
            days = source['workdays_per_iugerum'][crop].get(task)
            assert value == (days * 32 if days is not None else None)
    operations = rows(OUT / 'operations.csv'); cases = rows(OUT / 'cases.csv')
    assert len(operations) == 64 and len(cases) == 16
    expected_keys = set(); values = 0; original_rows = 0
    for mode in ['raw', 'corrected']:
        packet = load_packet(BASE, mode)
        for row in [c for c in cases if c['climate'] == mode]:
            model, density, hours = row['model'], row['density'], float(row['hours_worker_year'])
            a = activity(packet, model, mode, density, hours)
            crop = a['crop']; ha = a['retained_area_ha']; workers = a['workers']
            prescribed = source['workdays_per_iugerum']['barley']; total = np.zeros(len(crop)); reaping = None
            assert set(np.unique(crop)) <= {0, 2}
            for task in recipe['2']:
                actual = demands(a, task, recipe)
                days_per_ha = prescribed.get(task)
                expected_hours = np.where(crop == 2, ha * (days_per_ha * 32 if days_per_ha is not None else np.nan), np.nan)
                expected_days = np.divide(expected_hours / 8, workers, out=np.full(len(crop), np.nan), where=workers > 0)
                close(actual['normative_hours'], expected_hours)
                close(actual['full_8hour_worker_days'], expected_days)
                close(actual['hours_per_effective_worker'], expected_days * 8)
                values += 3 * len(crop)
                if days_per_ha is None:
                    assert np.isnan(actual['normative_hours']).all()
                    continue
                key = (row['physical_case'], task); expected_keys.add(key)
                matches = [s for s in operations if (s['physical_case'], s['operation']) == key]; assert len(matches) == 1
                s = matches[0]; valid = np.isfinite(expected_hours); finite = np.isfinite(expected_days)
                check = dict(prescribed_hours_per_retained_ha=days_per_ha * 32,
                    total_normative_hours=math.fsum(expected_hours[valid]),
                    share_of_normative_listed_hours=days_per_ha / 6.5,
                    origins_with_defined_demand=int(valid.sum()), origins_with_undefined_demand=int((~valid).sum()),
                    origins_with_undefined_worker_days=int((~finite).sum()),
                    max_full_8hour_worker_days=float(expected_days[finite].max()),
                    equal_origin_median_full_8hour_worker_days=float(np.median(expected_days[finite])))
                assert s['conditional_allocation_only'] == 'True' and s['crop'] == 'barley'
                assert (s['model'], s['climate'], s['density'], float(s['hours_worker_year'])) == (model, mode, density, hours)
                for name, value in check.items(): close(float(s[name]), value)
                total[valid] += expected_hours[valid]
                if task == 'reap': reaping = expected_hours
                original_rows += int(valid.sum())
            valid = crop == 2
            canonical = a['annual_hours_used']; residual = canonical[valid] - total[valid]
            close(total[valid], ha[valid] * 208.)
            check = dict(normative_listed_hours=math.fsum(total[valid]), canonical_listed_hours=math.fsum(canonical),
                canonical_minus_normative_listed_hours=math.fsum(residual),
                canonical_minus_normative_reaping_hours=math.fsum(a['reaping_hours_used'][valid] - reaping[valid]),
                max_relative_listed_residual=float(np.max(abs(residual) / np.where(total[valid] > 0, total[valid], 1.))))
            for name, value in check.items(): close(float(row[name]), value)
            assert int(row['assigned_operation_dates']) == int(row['additional_workers']) == 0
    assert expected_keys == {(s['physical_case'], s['operation']) for s in operations}
    assert original_rows == r['defined_origin_task_demands']
    # Controls protect unknown demand/resource semantics, not only the current all-positive workforce packet.
    fixture = dict(origin=np.arange(3), crop=np.array([2, 2, 0]), retained_area_ha=np.array([1., 2., np.nan]), workers=np.array([0., 2., 1.]))
    p = demands(fixture, 'plough', recipe)
    assert p['normative_hours'][0] == 96 and np.isnan(p['full_8hour_worker_days'][0])
    assert p['normative_hours'][1] == 192 and p['full_8hour_worker_days'][1] == 12
    assert np.isnan(p['normative_hours'][2]) and np.isnan(p['full_8hour_worker_days'][2])
    assert np.isnan(demands(fixture, 'hoe_second', recipe)['normative_hours']).all()
    sources = dict(r['sources_sha256'])
    next_plan = 'calibration/roman_benchmark_20261117/plough_resource_contract.json'
    for n in ['scripts/review_cereal_operation_demands.py', 'reports/CEREAL_OPERATION_DEMANDS_20261117.md', next_plan]: sources[n] = sha(ROOT / n)
    write(OUT / 'qualification.json', dict(status='passed_fixed_normative_task_demands_not_dated_resource_schedule',
        sources_sha256=sources, files_sha256={n: sha(OUT / n) for n in ['results.json', 'operations.csv', 'cases.csv', 'recipe.json']},
        physical_cases=16, task_summary_rows=64, defined_origin_task_demands=original_rows,
        materialized_task_values_checked=values, missing_resource_and_unit_controls=4,
        fresh_exports_byte_exact=True, canonical_work_unchanged=True, dates_assigned=0, workers_added=0,
        complete_human_draft_processing_budget=False, seasonal_work_qualified=False,
        model_solver_calls=0, new_scenarios=0, new_fit=False, main_atlas_changed=False, adopt=False, next_plan=next_plan))
    print(f'Passed64 summaries and {values} per-origin task values; four missing-resource/unit controls', flush=True)


if __name__ == '__main__': main()
