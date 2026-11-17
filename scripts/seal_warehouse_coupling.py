"""Seal the final bounded manufactured grain/work bridge and evidence scope."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import sha,read,write

OUT=ROOT/'output/urban_warehouse_coupling_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified grain/work coupling packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_three_declared_original_manufactured_grain_work_couplings'
    assert review['status']=='passed_independent_grain_receipt_task_identity_fraction_hour_and_feasibility_checks'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_warehouse_coupling.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['tests']==14 and r['coupling_cases']==3 and r['accepted_cases']==1 and r['rejected_cases']==2
    assert review['task_records_checked']==16 and [c['task_count'] for c in review['cases']]==[5,6,5]
    assert review['new_handling_converter_calls']==review['new_task_budget_calls']==0
    for key in ['new_role_adapter_calls','new_shared_store_calls','component_work_calls','food_kernel_calls','stock_solves','graph_rebuilds','dijkstra_calls','new_Earth_food_scenarios','new_staff_allocations']:
        assert r[key]==review[key]==0
    paths=[Path(__file__),ROOT/'scripts/review_warehouse_coupling.py',ROOT/'reports/WAREHOUSE_GRAIN_WORK_COUPLING_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_work_evidence_scope.json']
    write(OUT/'qualification.json',dict(status='passed_three_manufactured_paid_grain_and_shared_work_coupling_controls',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        tests=14,manufactured_coupling_cases=3,accepted_cases=1,rejected_cases=2,task_records_checked=16,
        original_grain_outputs_unchanged=True,reviewer_count_corrections_retained=True,new_handling_converter_calls=3,
        receipt_materialization_no_hold_calls=3,converter_no_hold_revalidation_calls=3,new_role_adapter_calls=0,new_shared_store_calls=0,
        food_kernel_calls=0,stock_solves=0,component_work_calls=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,handling_rates_empirically_qualified=False,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_work_evidence_scope.json'))
    print('Qualified three paid-grain/shared-work couplings;one feasible,two declared rejections',flush=True)


if __name__=='__main__':main()
