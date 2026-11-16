"""Seal the read-only evidence/buffer audit without running a food model."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_evidence_buffers_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text())
    assert r['status']=='completed_read_only_existing_evidence_and_baseline_buffer_audit'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',OUT),('protected_sha256',ROOT)]:
        for name,digest in r[key].items():assert sha(prefix/name)==digest,name
    assert r['food_kernel_reruns']==0 and not r['raw_observation_records_read'] and not r['phenology_rescored']
    assert r['individual_peaks_reconstructed_bit_exact']
    assert len(r['evidence_contracts'])==6 and len(r['buffer_diagnostics'])==6
    for row in r['evidence_contracts']:
        text=' '.join((ROOT/row['source']).read_text().split());assert row['quote'] in text
    for row in r['buffer_diagnostics']:
        assert row['simultaneous_peak_grain_person_years']<=row['sum_of_individual_peaks_grain_person_years']+1e-7
        if row['store_class']=='commercial_export':
            assert row['actually_exporting_origins']==row['exporting_origin_quarter_threshold_count']
            assert row['departing_grain_share_from_flagged_origins']==1.
    next_plan=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_storage_loss_factorial.json'
    paths=[Path(__file__),ROOT/'scripts/audit_urban_evidence_buffers.py',
           ROOT/'reports/URBAN_EVIDENCE_BUFFERS_20261116.md',next_plan,
           ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_evidence_buffer_audit.json']
    qualification=dict(status='passed_read_only_evidence_contract_and_recorded_buffer_peak_checks',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        files_sha256={name:sha(OUT/name) for name in ['results.json','evidence_contracts.csv','buffer_usage.csv']},
        protected_sha256=r['protected_sha256'],evidence_contracts=6,peak_vectors_exact=6,
        simultaneous_peaks_kept_distinct=True,food_kernel_reruns=0,raw_observation_records_read=False,
        current_clock_not_rescored=True,hypothetical_capacity_flag_is_not_export_or_meal_loss=True,
        next_plan=str(next_plan.relative_to(ROOT)),new_fit=False,new_validation_claim=False,
        actual_population_changed=False,adopt=False,main_atlas_changed=False)
    (OUT/'qualification.json').write_text(json.dumps(qualification,indent=2)+'\n')
    print(qualification['status'],flush=True)


if __name__=='__main__':main()
