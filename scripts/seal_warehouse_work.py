"""Seal read-only original work budgets with explicit peak-count limitations."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_work import OUT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified work-readiness packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_read_only_original_work_budget_and_handling_readiness_audit'
    assert review['status']=='passed_independent_original_work_budget_and_limit_interpretation_checks'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_warehouse_work.py')
    assert review['diagnostics_sha256']==sha(OUT/'limit_diagnostics.json')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['contracts']==10 and r['archive_schemas']==4 and review['source_rows_checked']==112756
    for key in ['component_work_calls','food_kernel_calls','stock_solves','graph_rebuilds','dijkstra_calls','new_Earth_food_scenarios','new_staff_allocations']:assert r[key]==review[key]==0
    paths=[Path(__file__),ROOT/'scripts/review_warehouse_work.py',ROOT/'reports/WAREHOUSE_WORK_READINESS_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_task_budget_controls.json']
    write(OUT/'qualification.json',dict(status='passed_read_only_original_work_budgets_with_monthly_timing_and_staffing_limits',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        original_cases=2,source_rows_checked=112756,exact_source_population_alignment=True,
        complete_monthly_work_schedule_present=False,handling_rate_qualified=False,handler_affiliation_qualified=False,
        unused_listed_allowance_is_staff=False,absolute_floor_peak_count_caveat_retained=True,
        component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,
        adopt=False,main_atlas_changed=False,next_plan='calibration/urban_diagnosis_20261117/warehouse_task_budget_controls.json'))
    print('Qualified read-only original work budgets and missing monthly/staffing contracts',flush=True)


if __name__=='__main__':main()
