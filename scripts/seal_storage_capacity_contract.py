"""Seal manufactured unit checks and unchanged model-interface classifications."""
import ast
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_storage_capacity_contract import OUT,PARENT,BUFFERS,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    r=read(OUT/'results.json');v=read(OUT/'review.json');t=read(OUT/'tests.json')
    assert r['status']=='completed_manufactured_capacity_contract_and_existing_model_interface_audit'
    assert v['status']=='passed_independent_Decimal_and_model_interface_checks'
    assert v['results_sha256']==sha(OUT/'results.json') and v['reviewer_sha256']==sha(ROOT/'scripts/review_storage_capacity_contract.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    for name,digest in t['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    assert t['status']=='passed' and '23 passed' in t['stdout']
    assert v['independent_decimal_checks']==18 and v['model_capacity_totals_exact_to_existing_table']
    assert r['historical_capacities_qualified']==r['food_kernel_calls']==r['new_food_scenarios']==r['new_site_measurement_rows']==0
    assert not r['existing_model_capacities_changed']
    # The scalar contract imports only dataclasses/math,not any model producers.
    tree=ast.parse((ROOT/'polity/storage_capacity.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):assert all(alias.name=='math' for alias in node.names)
        if isinstance(node,ast.ImportFrom):assert node.module=='dataclasses'
    for folder in [PARENT,BUFFERS]:
        parent=read(folder/'qualification.json')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    paths=[Path(__file__),ROOT/'scripts/review_storage_capacity_contract.py',ROOT/'reports/URBAN_STORAGE_CONTRACT_20261117.md',
           ROOT/'calibration/urban_diagnosis_20261117/ostia_store_source_qualification.json']
    q=dict(status='passed_explicit_storage_capacity_contract_and_manufactured_controls',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        adapter_tests=23,manufactured_cases=7,independent_decimal_checks=18,invalid_input_receipts=5,
        model_store_class_rows=6,existing_capacity_totals_unchanged=True,historical_capacities_qualified=0,
        new_site_measurement_rows=0,food_kernel_calls=0,new_food_scenarios=0,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/ostia_store_source_qualification.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
