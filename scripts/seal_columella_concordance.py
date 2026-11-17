"""Seal faithful six-locus source comparison without reconciling the print variant."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_columella_concordance_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified concordance'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_six_target_concordance_with_one_unreconciled_digital_print_variant'
    assert review['status']=='passed_faithful_six_locus_concordance_with_unreconciled_scan_variant'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_columella_concordance.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for key in ['files_sha256','local_source_sha256']:
        for name,digest in r[key].items():assert sha(OUT/name)==digest,name
    assert r['target_locations']==review['target_locations']==6 and r['substantive_target_variants']==review['substantive_target_scan_variants']==1
    assert review['old_packet_identities_unchanged'] and not review['printed_edition_and_digital_equivalence_established']
    paths=[Path(__file__),ROOT/'scripts/review_columella_concordance.py',ROOT/'reports/COLUMELLA_CONCORDANCE_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_work_diagnostic_map.json']
    write(OUT/'qualification.json',dict(status='passed_faithful_six_target_concordance_with_unreconciled_print_variant',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},local_source_sha256=r['local_source_sha256'],protected_sha256=r['protected_sha256'],
        selected_locations=6,selected_digital_paragraphs_exact=6,selected_scan_pages=6,titlepage_visual_inspected=True,
        substantive_target_variants=1,variant_paragraph=46,digital_has_bis=True,linked_printed_line_has_bis=False,
        variant_reconciled=False,whole_edition_equivalence_established=False,old_packet_changed=False,
        new_numeric_model_inputs=0,modern_date_conversions=0,solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_work_diagnostic_map.json'))
    print('Qualified six-target concordance;one print variant and edition limits unreconciled',flush=True)


if __name__=='__main__':main()
