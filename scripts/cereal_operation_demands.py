"""Normative task demand on fixed activities; no task dates or new workforce."""
import argparse
import csv
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import activity, load_packet, read, sha, write, table

BASE = ROOT / 'output/cereal_activity_packet_20261117'
OUT = ROOT / 'output/cereal_operation_demands_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/cereal_operation_demands.json'
SOURCE = ROOT / 'research_notes/farm_labour_20261103.json'
TASKS = ['plough', 'harrow', 'hoe_first', 'hoe_second', 'weed', 'reap']


def coefficients(source):
    scale = source['scenario']['hours_per_workday'] / source['scenario']['iugerum_hectares']
    return {str(code): {task: (counts[task] * scale if task in counts else None) for task in TASKS}
            for code, crop in [(1, 'wheat'), (2, 'barley')]
            for counts in [source['workdays_per_iugerum'][crop]]}


def demands(a, task, recipe):
    """Unknown crop/task/worker stays NaN; no implied zero for omitted tasks."""
    rate = np.full(len(a['origin']), np.nan)
    for code in [1, 2]:
        value = recipe[str(code)][task]
        if value is not None: rate[a['crop'] == code] = value
    hours = a['retained_area_ha'] * rate
    per_worker = np.divide(hours, a['workers'], out=np.full_like(hours, np.nan), where=a['workers'] > 0)
    return dict(normative_hours=hours, hours_per_effective_worker=per_worker,
                full_8hour_worker_days=per_worker / 8.)


def main(out):
    assert not (out / 'results.json').exists()
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    q = read(BASE / 'qualification.json')
    assert q['status'] == 'passed_fixed_cereal_origin_area_work_packet_not_seasonal_qualification'
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(BASE / n) == h, n
    source = read(SOURCE); recipe = coefficients(source)
    assert recipe['2'] == dict(plough=96., harrow=32., hoe_first=48., hoe_second=None, weed=None, reap=32.)
    task_rows = []; case_rows = []; checked = 0
    for mode in ['raw', 'corrected']:
        packet = load_packet(BASE, mode)
        for model in ['candidate', 'control']:
            for density in ['central', 'low']:
                for allowance in [600., 300.]:
                    case = f'{model}__{mode}__{density}__h{int(allowance)}'
                    a = activity(packet, model, mode, density, allowance)
                    listed = np.zeros(len(a['origin'])); defined = a['crop'] > 0
                    for task in TASKS:
                        d = demands(a, task, recipe); hours = d['normative_hours']; valid = np.isfinite(hours)
                        if not valid.any():
                            # No prescription does not mean a historically absent operation.
                            assert recipe['2'][task] is None
                            continue
                        listed[valid] += hours[valid]
                        days = d['full_8hour_worker_days']; finite = np.isfinite(days)
                        total = math.fsum(hours[valid]); max_days = float(days[finite].max())
                        task_rows.append(dict(physical_case=case, model=model, climate=mode, density=density,
                            hours_worker_year=allowance, crop='barley', operation=task,
                            prescribed_hours_per_retained_ha=recipe['2'][task],
                            total_normative_hours=total, share_of_normative_listed_hours=recipe['2'][task] / 208.,
                            origins_with_defined_demand=int(valid.sum()), origins_with_undefined_demand=int((~valid).sum()),
                            origins_with_undefined_worker_days=int((~finite).sum()),
                            max_full_8hour_worker_days=max_days,
                            equal_origin_median_full_8hour_worker_days=float(np.median(days[finite])),
                            conditional_allocation_only=True))
                        assert np.all(hours[valid] >= 0.)
                        checked += int(valid.sum())
                    norm = a['retained_area_ha'] * np.where(a['crop'] == 1, 336., np.where(a['crop'] == 2, 208., np.nan))
                    np.testing.assert_allclose(listed[defined], norm[defined], rtol=2e-15, atol=1e-7)
                    annual_residual = a['annual_hours_used'][defined] - listed[defined]
                    reap = demands(a, 'reap', recipe)['normative_hours']
                    reaping_residual = a['reaping_hours_used'][defined] - reap[defined]
                    case_rows.append(dict(physical_case=case, model=model, climate=mode, density=density,
                        hours_worker_year=allowance, normative_listed_hours=math.fsum(listed[defined]),
                        canonical_listed_hours=math.fsum(a['annual_hours_used']),
                        canonical_minus_normative_listed_hours=math.fsum(annual_residual),
                        canonical_minus_normative_reaping_hours=math.fsum(reaping_residual),
                        max_relative_listed_residual=float(np.max(abs(annual_residual) / np.where(listed[defined] > 0, listed[defined], 1.))),
                        assigned_operation_dates=0, additional_workers=0))
    assert len(task_rows) == 64 and len(case_rows) == 16
    out.mkdir(parents=True, exist_ok=True)
    table(out / 'operations.csv', task_rows); table(out / 'cases.csv', case_rows)
    write(out / 'recipe.json', dict(hours_per_cropped_hectare=recipe, assumed_hours_per_workday=8.,
        iugerum_hectares=.25, missing_prescription=None, task_order=TASKS,
        canonical_work='Unchanged base activity packet; signed rounding differences kept separate.',
        day_equivalent='Task hours / same origin effective workers /8; conditional full-workforce allocation, not observed workdays.',
        access='demands(activity(load_packet(BASE,climate),model,climate,density,hours),task,recipe)',
        physical_cases='Market-share alternatives alias the existing16 physical cases; do not add their workforce/area.',
        omissions='No complete processing, draft animal, irrigation, maintenance, household occupation or dated task windows.'))
    sources = [PLAN, SOURCE, BASE / 'qualification.json', BASE / 'activities_raw.npz', BASE / 'activities_corrected.npz',
               ROOT / 'scripts/cereal_activity_packet.py', Path(__file__),
               ROOT / 'reports/COLUMELLA_CALENDAR_20261117.md', ROOT / 'reports/COLUMELLA_CONCORDANCE_20261117.md']
    write(out / 'results.json', dict(status='prepared_normative_operation_demands_not_feasible_schedule',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        files_sha256={n: sha(out / n) for n in ['operations.csv', 'cases.csv', 'recipe.json']},
        physical_cases=16, task_rows=64, defined_origin_task_demands=checked,
        model_solver_calls=0, dates_assigned=0, workers_added=0, new_scenarios=0, new_fit=False, main_atlas_changed=False, adopt=False))
    print('Prepared64 task/case summaries on fixed activities; no dates or new workers', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
