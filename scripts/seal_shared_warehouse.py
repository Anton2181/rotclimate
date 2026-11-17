"""Seal exact reductions and independently reviewed shared-store bookkeeping."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_shared_warehouse import OUT,sha,read,write,gate


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    sources,protected=gate();r=read(OUT/'results.json');v=read(OUT/'review.json')
    assert r['sources_sha256']==sources and r['protected_sha256']==protected
    assert v['status']=='passed_independent_shared_store_grouping_inventory_and_physical_ledgers'
    assert v['results_sha256']==sha(OUT/'results.json') and v['reviewer_sha256']==sha(ROOT/'scripts/review_shared_warehouse.py')
    for name,digest in v['reviewer_dependencies_sha256'].items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    controls=read(OUT/'controls.json');assert len(controls)==4
    assert all(c['fields_exact']==15 and not c['new_Earth_food_scenario'] for c in controls)
    assert r['manufactured_cases']==5 and r['legacy_reduction_controls']==4 and r['physical_origin_control_rows']==225512
    assert r['manufactured_canonical_year_evaluations']==7 and r['legacy_canonical_year_evaluations']==6
    assert r['producer_canonical_annual_map_advances']==0
    assert v['independent_canonical_year_evaluations']==5 and v['independent_canonical_annual_map_advances']==102
    assert v['max_fraction_original_inventory_tolerance']<=1 and v['max_abs_whole_grain_residual_kcal']==0
    assert r['new_Earth_food_scenarios']==r['real_origin_to_port_mappings']==0
    paths=[Path(__file__),ROOT/'scripts/review_shared_warehouse.py',ROOT/'reports/SHARED_WAREHOUSE_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/shared_store_coupling_readiness.json']
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
    q=dict(status='passed_shared_warehouse_primitive_and_four_exact_legacy_reductions',sources_sha256=sources,
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=protected,
        tests=19,manufactured_cases=5,legacy_reduction_controls=4,exact_inventory_fields_per_control=15,physical_origin_control_rows=225512,
        max_fraction_original_inventory_tolerance=v['max_fraction_original_inventory_tolerance'],max_whole_grain_residual_kcal=0,
        producer_manufactured_adapter_calls=5,producer_legacy_adapter_calls=4,producer_canonical_year_evaluations=13,
        producer_canonical_annual_map_advances=0,reviewer_shared_adapter_calls=0,reviewer_canonical_year_evaluations=5,
        reviewer_canonical_annual_map_advances=102,new_Earth_food_scenarios=0,real_origin_to_port_mappings=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/shared_store_coupling_readiness.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
