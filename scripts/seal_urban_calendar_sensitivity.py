"""Seal exact-energy catalogue, unchanged baseline controls and four timing cases."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_calendar_sensitivity_20261116'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())


def main():
    expected={};protected={};reviews=[]
    def expect(path,digest):
        key=str(path);assert key not in expected or expected[key]==digest,key;expected[key]=digest
    parent=read(MONTHLY/'qualification.json')
    assert parent['status']=='passed_fixed_request_Earth_monthly_food_portability_pilot'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',MONTHLY),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():expect(prefix/name,digest)
    cat=read(OUT/'catalogue/results.json');review=read(OUT/'catalogue/review.json')
    assert review['status']=='passed_independent_exact_crop_window_catalogue' and not review['energy_tolerance_used']
    expect(OUT/'catalogue/results.json',review['results_sha256']);expect(OUT/'catalogue/windows.npz',review['windows_sha256'])
    expect(ROOT/'scripts/review_urban_calendar_catalogue.py',review['reviewer_sha256'])
    for name,digest in {**cat['sources_sha256'],**cat['protected_sha256']}.items():expect(ROOT/name,digest)
    protected.update(cat['protected_sha256'])
    for reading in ['central','low']:
        control=read(OUT/'controls'/f'{reading}.json')
        assert control['status']=='passed_original_monthly_food_all_arrays_byte_exact' and control['arrays_exact']==70
        expect(MONTHLY/'cases'/reading/'fields.npz',control['baseline_fields_sha256'])
        for name,digest in control['sources_sha256'].items():expect(ROOT/name,digest)
        for timing in ['earliest','latest']:
            folder=OUT/'cases'/f'{reading}_{timing}';result=read(folder/'results.json');review=read(folder/'review.json')
            assert review['status']=='passed_exact_timing_monthly_inventories_routes_and_grain_ledger'
            assert review['maximum_fraction_of_original_inventory_tolerance']<=1
            assert result['grain_work_and_requests_unchanged'] and result['original_monthly_control_all_arrays_exact']
            expect(folder/'results.json',review['results_sha256']);expect(folder/'fields.npz',review['fields_sha256'])
            expect(ROOT/'scripts/review_urban_calendar_food.py',review['reviewer_sha256'])
            for name,digest in {**result['sources_sha256'],**result['protected_sha256']}.items():expect(ROOT/name,digest)
            reviews.append(review)
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and tests['passed']==6
    for name,digest in tests['sources_sha256'].items():expect(ROOT/name,digest)
    p=read(OUT/'presentation.json');assert p['city_rows']==4340 and p['month_rows']==72 and p['regional_rows']==30
    expect(ROOT/'scripts/render_urban_calendar_sensitivity.py',p['producer_sha256'])
    for name,digest in p['inputs_sha256'].items():expect(ROOT/name,digest)
    for name,digest in p['files_sha256'].items():expect(OUT/name,digest)
    for name,digest in expected.items():assert sha(Path(name))==digest,name
    next_plan=ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_evidence_buffer_audit.json'
    paths=[Path(__file__),ROOT/'reports/URBAN_CALENDAR_SENSITIVITY_20261116.md',next_plan,
        ROOT/'harvest/exact_crop_windows.py',ROOT/'tests/test_exact_crop_windows.py',ROOT/'scripts/urban_calendar_sensitivity.py',
        ROOT/'scripts/review_urban_calendar_catalogue.py',ROOT/'scripts/review_urban_calendar_food.py',
        ROOT/'scripts/render_urban_calendar_sensitivity.py',ROOT/'calibration/urban_diagnosis_20261116/seasonal_transfer_calendar_sensitivity.json']
    artifacts={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='qualification.json'}
    result=dict(status='passed_four_exact_energy_timing_recipes_with_fixed_grain_work_and_population',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},files_sha256=artifacts,protected_sha256=protected,
        food_cases=4,original_monthly_controls=2,food_arrays_exact_per_control=70,tie_tests=6,
        physical_source_cases=sum(r['physical_sources'] for r in reviews),inventory_groups=16,
        independent_monthly_shipments=sum(r['independent_shipments'] for r in reviews),
        max_fraction_of_original_inventory_tolerance=max(r['maximum_fraction_of_original_inventory_tolerance'] for r in reviews),
        max_grain_residual_person_years=max(abs(r['grain_residual_person_years']) for r in reviews),
        catalogue_summary=cat['summary'],next_plan=str(next_plan.relative_to(ROOT)),
        recipes_are_not_outcome_bounds=True,actual_population_changed=False,demographic_iteration=False,
        original_annual_controls_unchanged=True,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False)
    (OUT/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],len(expected),'identities verified',flush=True)


if __name__=='__main__':main()
