"""Seal manufactured single-physical-workforce task-budget outcomes."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import sha,read,write

OUT=ROOT/'output/urban_warehouse_tasks_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified task-budget packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_eight_declared_shared_physical_task_budget_outcomes'
    assert review['status']=='passed_independent_scalar_shared_task_budget_acceptance_and_rejection_checks'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_warehouse_tasks.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['tests']==24 and r['manufactured_cases']==8 and r['accepted_cases']==review['accepted_cases']==3
    assert r['rejected_cases']==review['rejected_cases']==5 and review['new_task_budget_calls']==0
    for key in ['component_work_calls','food_kernel_calls','stock_solves','graph_rebuilds','dijkstra_calls','new_Earth_food_scenarios','new_staff_allocations']:assert r[key]==review[key]==0
    paths=[Path(__file__),ROOT/'scripts/review_warehouse_tasks.py',ROOT/'reports/WAREHOUSE_TASK_BUDGET_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_grain_work_coupling_controls.json']
    write(OUT/'qualification.json',dict(status='passed_eight_manufactured_shared_physical_task_budget_outcomes',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        tests=24,manufactured_cases=8,accepted_cases=3,rejected_cases=5,reviewer_task_budget_calls=0,
        component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,new_Earth_food_scenarios=0,
        new_staff_allocations=0,empirical_staffing_qualified=False,handling_rate_inferred=False,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_grain_work_coupling_controls.json'))
    print('Qualified shared physical task-budget checks:3 accepted,5 rejected',flush=True)


if __name__=='__main__':main()
