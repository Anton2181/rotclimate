"""Verify and seal the reviewed calendar packet without changing its producers."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_earth_calendars_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    presentation=json.loads((OUT/'presentation.json').read_text())
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',OUT),('protected_sha256',ROOT)]:
        for name,digest in result[key].items():assert sha(prefix/name)==digest,name
    assert review['status']=='passed_original_model_calendar_and_source_partition_review'
    assert review['results_sha256']==sha(OUT/'results.json') and review['calendars_sha256']==sha(OUT/'calendars.npz')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_earth_calendars.py')
    assert presentation['producer_sha256']==sha(ROOT/'scripts/render_urban_earth_calendars.py')
    assert presentation['results_sha256']==sha(OUT/'results.json') and presentation['review_sha256']==sha(OUT/'review.json')
    assert presentation['timing_sha256']==sha(OUT/'timing.png')
    assert review['component_energy_calendar_coverage']==1 and review['basin_high_flow_overlap_sources']==0
    next_plan=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_component_work.json'
    paths=[Path(__file__),ROOT/'reports/URBAN_EARTH_CALENDARS_20261116.md',next_plan]
    artifacts=['results.json','review.json','presentation.json','calendars.npz','monthly_energy.csv','timing.png']
    receipt=dict(status='passed_original_model_calendar_recovery_component_work_gate_open',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},
        files_sha256={name:sha(OUT/name) for name in artifacts},
        annual_control_cases_exact=6,positive_sources=53265,zero_production_sources=3113,
        stored_base_crop_energy_values_exact=108648,basin_capacity_float64_exact=True,
        component_energy_calendar_coverage=1.,different_component_harvest_sources=41,
        component_work_diagnostic='On285both-positive cells median physical/annual task-area ratio1.72111. No revised work or production was simulated.',
        next_plan=str(next_plan.relative_to(ROOT)),observed_date_validation=False,
        seasonal_food_trial_performed=False,seasonal_food_trial_ready=False,new_fit=False,new_validation_claim=False,adopt=False)
    (OUT/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],flush=True)


if __name__=='__main__':main()
