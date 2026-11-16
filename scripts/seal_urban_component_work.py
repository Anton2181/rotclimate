"""Seal paired annual work controls, independent budgets/flows and presentation."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_component_work_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def main():
    expected={};protected={};reviews=[]
    def expect(path,digest):
        key=str(path)
        assert key not in expected or expected[key]==digest,key
        expected[key]=digest
    for stage,archive in [('greek','greek_walls_20261114'),('low','supply_low_reading_20261114')]:
        folder=OUT/'controls'/stage;control=read(folder/'control.json')
        assert control['status']=='passed_original_mixed_work_whole_annual_result_bytes_exact'
        assert (folder/'results.json').read_bytes()==(ROOT/'output'/archive/'results.json').read_bytes()
        expect(folder/'results.json',control['results_sha256'])
        assert control['results_sha256']==control['reference_sha256']
        for name,digest in {**control['sources_sha256'],**control['protected_sha256']}.items():expect(ROOT/name,digest)
        protected.update(control['protected_sha256'])
    for hours in [600,300]:
        folder=OUT/f'hours{hours}';result=read(folder/'results.json');review=read(folder/'review.json')
        assert review['status']=='passed_shared_component_work_and_fixed_share_supply_review' and review['hours']==hours
        expect(folder/'results.json',review['results_sha256'])
        expect(ROOT/'scripts/review_urban_component_work.py',review['reviewer_sha256'])
        expect(ROOT/'scripts/urban_component_work.py',result['producer_sha256'])
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in result[key].items():expect(prefix/name,digest)
        assert review['source_cases']==112756 and review['independent_town_allocations']==4
        assert all(case['peak_limited_cells']==0 for case in review['cases'].values())
        reviews.append(review)
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and tests['passed']==12
    for name,digest in tests['sources_sha256'].items():expect(ROOT/name,digest)
    presentation=read(OUT/'presentation.json')
    assert presentation['town_rows']==4340 and presentation['regional_rows']==40 and not presentation['new_settlement_map']
    expect(ROOT/'scripts/render_urban_component_work.py',presentation['producer_sha256'])
    for name,digest in presentation['inputs_sha256'].items():expect(ROOT/name,digest)
    for key in ['image_sha256','files_sha256']:
        for name,digest in presentation[key].items():expect(OUT/name,digest)
    for name,digest in expected.items():assert sha(Path(name))==digest,name
    next_plan=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_fixed_request_pilot.json'
    paths=[Path(__file__),ROOT/'reports/URBAN_COMPONENT_WORK_20261116.md',next_plan,
           ROOT/'polity/earth_component_work.py',ROOT/'tests/test_earth_component_work.py',
           ROOT/'scripts/urban_component_work.py',ROOT/'scripts/review_urban_component_work.py',ROOT/'scripts/render_urban_component_work.py']
    paths+=list((ROOT/'calibration/urban_diagnosis_20261116').glob('seasonal_transfer_component*.json'))
    artifacts={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='qualification.json'}
    receipt=dict(status='passed_paired_annual_component_work_primary_and_stress',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},files_sha256=artifacts,protected_sha256=protected,
        exact_original_annual_cases=6,work_hours=[600,300],densities=['central','low'],shared_budget_tests=12,
        independently_reviewed_physical_source_cases=sum(r['source_cases'] for r in reviews),
        independently_reviewed_town_allocations=8,independent_shipment_rows=sum(r['shipment_rows'] for r in reviews),
        max_grain_residual_person_years=max(r['max_source_grain_residual_person_years'] for r in reviews),
        max_town_residual_people=max(r['max_town_fed_residual_people'] for r in reviews),
        exact_policy_shares_retained=True,one_physical_workforce=True,
        next_plan=str(next_plan.relative_to(ROOT)),seasonal_food_trial_performed=False,
        new_validation_claim=False,new_fit=False,adopt=False,main_atlas_changed=False)
    (OUT/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],len(expected),'file identities verified',flush=True)


if __name__=='__main__':main()
