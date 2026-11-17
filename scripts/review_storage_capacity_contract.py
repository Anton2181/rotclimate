"""Independent Decimal arithmetic and six model-interface label checks."""
import csv
from decimal import Decimal
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_storage_capacity_contract import OUT,BUFFERS,sha,read,write


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed review'
    r=read(OUT/'results.json')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    examples=read(OUT/'manufactured.json');assert len(examples)==7
    decimal_checks=0
    for example in examples:
        s=example['store'];flow=example['flow'];result=example['result']
        assert example['record_kind']=='manufactured_unit_control'
        for key in ['usable_area','effective_depth','bulk_density','net_edible_yield','edible_energy_density','structural_mass_limit']:
            assert s[key]['kind'] in ['scenario','unknown']
        assert not result['empirically_qualified'] and result['operational_capacity_kcal'] is None
        missing=[key for key in ['usable_area','effective_depth','bulk_density','net_edible_yield','edible_energy_density'] if s[key]['value'] is None]
        if missing:
            assert result['geometric_net_energy_kcal'] is None and set(missing)<=set(result['arithmetic_gaps'])
            continue
        d=lambda field:Decimal(str(s[field]['value']))
        volume=d('usable_area')*d('effective_depth');mass=volume*d('bulk_density')
        energy=mass*d('net_edible_yield')*d('edible_energy_density')
        for field,expected in [('geometric_volume_m3',volume),('stored_mass_kg',mass),('geometric_net_energy_kcal',energy)]:
            assert result[field]==float(expected);decimal_checks+=1
        matching=all(flow[key]==s[key] for key in ['commodity','location','phase','energy_pool'])
        annual=flow['annual_energy']['value']
        if matching and annual is not None and annual>0:
            days=energy/Decimal(str(annual))*365
            assert math.isclose(result['geometric_flow_days'],float(days),rel_tol=1e-14,abs_tol=1e-12);decimal_checks+=1
        else:assert result['geometric_flow_days'] is None
        if s['structural_mass_limit']['value'] is None:assert result['structural_fill_supported'] is None
        else:assert mass<=d('usable_area')*d('structural_mass_limit')
    invalid=read(OUT/'rejected.json');assert len(invalid)==5
    assert all(row['status']=='rejected' and row['reason'] for row in invalid)
    original=list(csv.DictReader((BUFFERS/'buffer_usage.csv').open()))
    model=list(csv.DictReader((OUT/'model_interfaces.csv').open()));assert len(model)==6
    for source,row in zip(original,model):
        assert (row['reading'],row['store_class'])==(source['reading'],source['store_class'])
        assert float(row['model_capacity_grain_person_years'])==float(source['capacity_grain_person_years'])
        assert row['reference_kind']=='declared_model_scenario' and row['historical_capacity_qualified']=='False'
        assert row['physical_conversion_energy_kcal']=='' and row['observed_building_or_volume']=='False'
        assert int(row['model_days'])==(90 if row['store_class']=='town' else 365)
    receipt=dict(status='passed_independent_Decimal_and_model_interface_checks',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),independent_decimal_checks=decimal_checks,manufactured_cases=7,
        invalid_input_receipts=5,existing_model_store_classes=6,model_capacity_totals_exact_to_existing_table=True,
        arithmetic_does_not_qualify_evidence=True,food_kernel_calls=0,new_site_measurement_rows=0,new_food_scenarios=0,
        new_fit=False,new_validation_claim=False,adopt=False)
    write(OUT/'review.json',receipt);print(receipt,flush=True)


if __name__=='__main__':main()
