"""Seal reviewed factorial, compact output identities and complete table accounting."""
import csv
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from urban_storage_loss import OUT, BASE, COMBOS
from urban_earth_monthly import sha, read, write, total, KCAL


def main():
    assert not (OUT/'qualification.json').exists(), 'Preserve completed qualification'
    r=read(OUT/'results.json');assert r['status']=='reviewed_six_case_fixed_infrastructure_factorial'
    protected={};sources=dict(r['sources_sha256'])
    for name,digest in sources.items():assert sha(ROOT/name)==digest,name
    test=read(OUT/'tests.json');assert test['passed']==19 and test['status']=='passed'
    for name,digest in test['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    for reading in ['central','low']:
        control=read(OUT/'controls'/f'{reading}.json');assert control['arrays_exact']==70
        for name,digest in {**control['sources_sha256'],**control['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
        protected.update(control['protected_sha256'])
        for label,loss,days in COMBOS:
            folder=OUT/'cases'/f'{reading}_{label}';case=read(folder/'results.json');review=read(folder/'review.json')
            assert review['status']=='passed_fixed_reference_storage_loss_stock_routes_and_ledger'
            for filename,key in [('results.json','results_sha256'),('fields.npz','fields_sha256')]:assert sha(folder/filename)==review[key]
            assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_storage_loss.py')
            assert review['reviewer_dependency_sha256']==sha(ROOT/'scripts/review_urban_earth_monthly.py')
            for name,digest in {**case['sources_sha256'],**case['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
            assert case['loss_fraction_year']==loss and case['commercial_days']==days
            assert not case['adopt'] and not case['actual_population_changed']
    packet=dict(np.load(OUT/'town_model.npz'))
    city=list(csv.DictReader((OUT/'towns.csv').open()));factors=list(csv.DictReader((OUT/'city_effects.csv').open()))
    assert len(city)==8680 and len(factors)==2170
    for reading in ['central','low']:
        req=packet[reading+'_request'];base=packet[reading+'_loss05_days365_consumed']/KCAL
        arrays=[]
        for label in ['loss05_days365']+[x[0] for x in COMBOS]:
            prefix=reading+'_'+label+'_';meals=packet[prefix+'consumed']/KCAL;arrays.append(meals)
            rows=[row for row in city if row['reading']==reading and row['scenario']==label]
            np.testing.assert_array_equal([float(row['requested_people']) for row in rows],req)
            np.testing.assert_array_equal([float(row['meals_person_years']) for row in rows],meals)
            np.testing.assert_array_equal([float(row['delta_meals_person_years']) for row in rows],meals-base)
            summary=next(s for s in r['summary'] if s['reading']==reading and s['scenario']==label)
            assert abs(summary['meal_fraction']-total(meals)/total(req))<1e-14
            assert abs(summary['town_meals_person_years']-total(meals))<1e-7
        a,b,c,d=arrays
        expected=dict(capacity_at_five_percent=b-a,capacity_at_zero_loss=d-c,zero_loss_at_365_days=c-a,zero_loss_at_90_days=d-b,
                      capacity_average_effect=((b-a)+(d-c))/2,zero_loss_average_effect=((c-a)+(d-b))/2,interaction=d-b-c+a)
        rows=[row for row in factors if row['reading']==reading]
        for key,value in expected.items():
            np.testing.assert_array_equal([float(row[key+'_person_years']) for row in rows],value)
            assert r['aggregate_effects_person_years'][reading][key]==total(value)
    for name,count in [('months.csv',96),('regions.csv',40),('month_effects.csv',24),('region_effects.csv',10)]:
        rows=list(csv.DictReader((OUT/name).open()));assert len(rows)==count
    assert r['maximum_fraction_of_original_inventory_tolerance']<=1
    paths=[Path(__file__),ROOT/'scripts/urban_storage_loss.py',ROOT/'scripts/review_urban_storage_loss.py',
        ROOT/'scripts/render_urban_storage_loss.py',ROOT/'polity/earth_storage_loss.py',ROOT/'tests/test_earth_storage_loss.py',
        ROOT/'reports/URBAN_STORAGE_LOSS_20261117.md',ROOT/'calibration/urban_diagnosis_20261117/storage_throughput_audit.json']
    sources.update({str(path.relative_to(ROOT)):sha(path) for path in paths})
    files={str(path.relative_to(OUT)):sha(path) for path in sorted(OUT.rglob('*')) if path.is_file() and path.name!='fields.npz'}
    q=dict(status='passed_six_fixed_infrastructure_storage_loss_cases_and_exact_original_controls',sources_sha256=sources,
        files_sha256=files,protected_sha256=protected,**r['counts'],adapter_tests=19,
        physical_source_cases=r['physical_source_cases'],inventory_groups=24,independent_shipments=r['independent_shipments'],
        maximum_fraction_of_original_inventory_tolerance=r['maximum_fraction_of_original_inventory_tolerance'],
        max_grain_residual_person_years=r['max_grain_residual_person_years'],
        preserved_canonical_zero_loss_synthetic_failure=True,smallest_zero_loss_endpoint_reviewed=True,
        fixed_commercial_references_across_loss=True,new_fit=False,new_validation_claim=False,actual_population_changed=False,adopt=False,
        main_atlas_changed=False,next_plan='calibration/urban_diagnosis_20261117/storage_throughput_audit.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
