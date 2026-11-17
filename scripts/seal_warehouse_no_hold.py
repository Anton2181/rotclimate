"""Seal exact no-hold accounting reductions and the next finite integration scope."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import OUT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified no-hold packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_eight_manufactured_no_hold_cases_and_two_exact_arrival_reductions'
    assert review['status']=='passed_independent_no_hold_grain_clock_and_two_scalar_arrival_reductions'
    assert review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_warehouse_no_hold.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['tests']==34 and r['manufactured_cases']==8 and r['legacy_reductions']==2
    assert review['exact_arrays']==8 and review['new_ledger_calls']==0
    for key in ['food_kernel_calls','stock_solves','dijkstra_calls','graph_rebuilds','new_Earth_food_scenarios','actual_warehouse_mappings']:
        assert r[key]==review[key]==0
    assert not (OUT/'failure.json').exists()
    paths=[Path(__file__),ROOT/'scripts/review_warehouse_no_hold.py',ROOT/'reports/WAREHOUSE_NO_HOLD_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_shared_roles_controls.json']
    write(OUT/'qualification.json',dict(status='passed_no_hold_grain_clock_and_two_exact_original_arrival_reductions',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        tests=34,manufactured_cases=8,legacy_reductions=2,exact_arrival_export_arrays=8,legacy_consignment_records=r['legacy_consignment_rows'],
        producer_ledger_calls=34,reviewer_ledger_calls=0,food_kernel_calls=0,stock_solves=0,dijkstra_calls=0,graph_rebuilds=0,
        new_Earth_food_scenarios=0,actual_warehouse_mappings=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,
        adopt=False,main_atlas_changed=False,next_plan='calibration/urban_diagnosis_20261117/warehouse_shared_roles_controls.json'))
    print('Qualified no-hold accounting and both exact original arrival reductions',flush=True)


if __name__=='__main__':main()
