"""Seal a faithful primary Latin calendar witness with all edition/transfer limits."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_columella_calendar_20261117'


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified calendar packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert r['status']=='completed_one_Latin_primary_calendar_witness_with_edition_and_model_transfer_limits'
    assert review['status']=='passed_independent_calendar_witness_paragraph_and_literal_claim_checks_with_limits'
    assert review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_columella_calendar.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for key in ['files_sha256','local_source_sha256']:
        for name,digest in r[key].items():assert sha(OUT/name)==digest,name
    assert r['paragraphs']==review['paragraphs_independently_extracted']==101 and r['located_claims']==review['located_claims']==39
    assert review['literal_anchor_marker_numeric_checks']==90 and not review['exact_critical_edition_verified']
    assert r['new_numeric_model_inputs']==r['modern_dates_or_model_bins']==review['solver_calls']==0
    paths=[Path(__file__),ROOT/'scripts/review_columella_calendar.py',ROOT/'scripts/retrieve_columella_calendar.py',
        ROOT/'reports/COLUMELLA_CALENDAR_20261117.md',ROOT/'calibration/urban_diagnosis_20261117/columella_calendar_concordance.json']
    write(OUT/'qualification.json',dict(status='passed_faithful_Latin_calendar_witness_with_edition_and_calendar_transfer_limits',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},local_source_sha256=r['local_source_sha256'],protected_sha256=r['protected_sha256'],
        primary_analytical_chapters=1,paragraphs=101,located_claims=39,independent_literal_checks=90,
        exact_critical_edition_verified=False,English_source_unavailable=True,dual_solstice_markers_retained=True,
        complete_measured_monthly_occupation=False,warehouse_handling_intensity_qualified=False,
        model_date_or_bin_conversions=0,new_numeric_model_inputs=0,solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/columella_calendar_concordance.json'))
    print('Qualified faithful101paragraph/39claim Latin calendar witness;edition/transfer limits explicit',flush=True)


if __name__=='__main__':main()
