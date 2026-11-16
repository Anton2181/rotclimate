"""Seal original-tolerance fixed-request inventory and routing reviews."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_earth_monthly_20261116'
BASE=ROOT/'output/urban_component_work_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def main():
    expected={};protected={};reviews=[]
    def expect(path,digest):
        key=str(path);assert key not in expected or expected[key]==digest,key;expected[key]=digest
    parent=read(BASE/'qualification.json')
    assert parent['status']=='passed_paired_annual_component_work_primary_and_stress'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',BASE),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():expect(prefix/name,digest)
    for reading in ['central','low']:
        folder=OUT/'cases'/reading;result=read(folder/'results.json');review=read(folder/'review.json')
        assert review['status']=='passed_fixed_request_monthly_inventories_routes_and_grain_ledger'
        assert review['maximum_fraction_of_original_inventory_tolerance']<=1
        assert review['physical_sources']==56378 and review['towns']==1085
        expect(folder/'results.json',review['results_sha256']);expect(folder/'fields.npz',review['fields_sha256'])
        expect(ROOT/'scripts/review_urban_earth_monthly.py',review['reviewer_sha256'])
        for name,digest in {**result['sources_sha256'],**result['protected_sha256']}.items():expect(ROOT/name,digest)
        assert result['annual_B_work_and_fixed_share_allocations_exact']
        assert result['actual_city_population_changed'] is False and result['demographic_iteration'] is False
        protected.update(result['protected_sha256']);reviews.append(review)
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and tests['passed']==7
    for name,digest in tests['sources_sha256'].items():expect(ROOT/name,digest)
    presentation=read(OUT/'presentation.json')
    assert presentation['city_rows']==2170 and presentation['monthly_rows']==24 and presentation['regional_rows']==10
    expect(ROOT/'scripts/render_urban_earth_monthly.py',presentation['producer_sha256'])
    for name,digest in presentation['inputs_sha256'].items():expect(ROOT/name,digest)
    for name,digest in presentation['files_sha256'].items():expect(OUT/name,digest)
    for name,digest in expected.items():assert sha(Path(name))==digest,name
    next_plan=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_calendar_sensitivity.json'
    paths=[Path(__file__),ROOT/'reports/URBAN_EARTH_MONTHLY_20261116.md',next_plan,
        ROOT/'polity/earth_fixed_food.py',ROOT/'tests/test_earth_fixed_food.py',ROOT/'scripts/urban_earth_monthly.py',
        ROOT/'scripts/review_urban_earth_monthly.py',ROOT/'scripts/render_urban_earth_monthly.py',
        ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_fixed_request_pilot.json',
        ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_fixed_request_adapter.json']
    artifacts={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='qualification.json'}
    receipt=dict(status='passed_fixed_request_Earth_monthly_food_portability_pilot',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},files_sha256=artifacts,protected_sha256=protected,
        cases=2,hours=600,inventory_groups=8,physical_source_cases=112756,city_rows=2170,city_months=26040,
        independent_monthly_shipments=sum(r['independent_shipments'] for r in reviews),
        max_fraction_of_original_inventory_tolerance=max(r['maximum_fraction_of_original_inventory_tolerance'] for r in reviews),
        max_grain_residual_person_years=max(abs(r['grain_residual_person_years']) for r in reviews),
        adapter_tests=7,parent_work_tests=12,exact_original_annual_cases=6,annual_B_control_exact=True,
        requested_population_fixed=True,factorized_global_recruitment=True,demographic_iteration=False,
        actual_city_population_changed=False,next_plan=str(next_plan.relative_to(ROOT)),
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False)
    (OUT/'qualification.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(receipt['status'],len(expected),'identities verified',flush=True)


if __name__=='__main__':main()
