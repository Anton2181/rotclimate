"""Seal single-physical-capacity shared-role manufactured integration."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import sha,read,write

OUT=ROOT/'output/urban_warehouse_roles_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified shared-role packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_seven_shared_role_scenarios_and_seven_exact_aggregate_reductions'
    assert review['status']=='passed_independent_shared_role_grain_priority_and_canonical_inventory_checks'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_warehouse_roles.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['tests']==21 and r['manufactured_scenarios']==r['aggregate_reductions']==7 and r['exact_fields_per_case']==15
    assert review['reviewer_role_adapter_calls']==review['reviewer_shared_store_adapter_calls']==0
    assert review['reviewer_canonical_year_evaluations']==7 and review['reviewer_canonical_annual_map_advances']==0
    assert review['max_fraction_original_inventory_tolerance']<=1 and not (OUT/'failure.json').exists()
    for key in ['new_Earth_food_scenarios','actual_warehouse_mappings']:assert r[key]==review[key]==0
    paths=[Path(__file__),ROOT/'scripts/review_warehouse_roles.py',ROOT/'reports/WAREHOUSE_SHARED_ROLES_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_work_readiness.json']
    write(OUT/'qualification.json',dict(status='passed_seven_single_physical_store_shared_role_scenarios_and_exact_aggregate_reductions',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        tests=21,manufactured_scenarios=7,aggregate_reductions=7,exact_inventory_fields_per_case=15,
        adapter_canonical_year_evaluations=r['adapter_canonical_year_evaluations'],reference_canonical_year_evaluations=r['reference_canonical_year_evaluations'],
        reviewer_canonical_year_evaluations=7,canonical_annual_map_advances=0,new_Earth_food_scenarios=0,actual_warehouse_mappings=0,
        upstream_rural_work_certified=False,handling_work_certified=False,empirical_capacity_qualified=False,rights_inferred=False,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_work_readiness.json'))
    print('Qualified seven shared-role scenarios and seven exact aggregate reductions',flush=True)


if __name__=='__main__':main()
