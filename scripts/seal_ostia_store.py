"""Seal source transcription while preserving unresolved capacity inconsistencies."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_ostia_store import OUT,PARENT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    r=read(OUT/'results.json');v=read(OUT/'review.json')
    assert v['status']=='passed_Ostia_source_transcription_with_unresolved_numeric_consistency'
    assert v['results_sha256']==sha(OUT/'results.json') and v['reviewer_sha256']==sha(ROOT/'scripts/review_ostia_store.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    for name,digest in r['local_source_sha256'].items():assert sha(OUT/name)==digest,name
    assert v['numeric_source_claims']==61 and v['numeric_token_checks']==81
    assert v['independent_source_column_checks']==10 and not v['source_capacities_reconciled']
    assert v['printed_dimensional_issue_retained']
    assert v['historical_operational_capacities_qualified']==v['network_attachments']==v['food_kernel_calls']==v['new_food_scenarios']==0
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    paths=[Path(__file__),ROOT/'scripts/review_ostia_store.py',ROOT/'reports/URBAN_OSTIA_STORAGE_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/shared_warehouse_primitive.json']
    q=dict(status='passed_Ostia_source_identity_and_transcription_with_numeric_limits_retained',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},local_source_sha256=r['local_source_sha256'],
        protected_sha256=r['protected_sha256'],publisher_paragraphs=81,printed_chapter_pages=50,
        numeric_source_claims=61,context_rows=18,capacity_estimate_rows=7,numeric_token_checks=81,
        independent_source_column_checks=10,source_numeric_inconsistencies_unresolved=True,
        source_formula_not_adopted=True,historical_operational_capacities_qualified=0,
        geometric_net_energy_computed=False,network_attachments=0,food_kernel_calls=0,new_food_scenarios=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/shared_warehouse_primitive.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
