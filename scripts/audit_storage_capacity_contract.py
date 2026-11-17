"""Manufactured capacity conversions and read-only labels of six model budgets."""
from dataclasses import asdict,replace
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from polity.storage_capacity import PhysicalStore,FlowReference,Quantity,convert

OUT=ROOT/'output/urban_storage_contract_20261117'
PARENT=ROOT/'output/urban_storage_methods_20261117'
BUFFERS=ROOT/'output/urban_evidence_buffers_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/storage_capacity_contract.json'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def q(value,unit,source='manufactured unit control',locator='explicit invented input'):
    return Quantity(value,unit,'unknown' if value is None else 'scenario',source,locator)


def fixture():
    return PhysicalStore('manufactured-bulk-store','commercial','invented location','invented phase','scenario access',
        'barley','husked','net edible cereal','stored_material','single_commodity_allocated_usable',
        q(100.,'m2'),q(.5,'m'),q(700.,'kg_stored/m3'),'barley','husked',
        q(.8,'kg_edible/kg_stored'),q(3500.,'kcal/kg_edible'),q(500.,'kg_stored/m2'),
        'scenario ventilation','scenario duration')


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    parent=read(PARENT/'qualification.json');assert parent['status'].startswith('passed_one_source_storage_methods')
    for folder in [PARENT,BUFFERS]:
        qual=read(folder/'qualification.json')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in qual[key].items():assert sha(prefix/name)==digest,name
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and '23 passed' in tests['stdout']
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    assert not (OUT/'results.json').exists(),'Preserve completed contract audit'
    s=fixture();flow=FlowReference(q(365000.,'kcal/year_365'),s.commodity,s.location,s.phase,s.energy_pool)
    examples=[('explicit_geometry',s,flow),('unknown_depth',replace(s,effective_depth=q(None,'m')),flow),
        ('unknown_density',replace(s,bulk_density=q(None,'kg_stored/m3')),flow),
        ('unproven_operation',replace(s,structural_mass_limit=q(None,'kg_stored/m2'),owner_access=None,preservation_condition=None),flow),
        ('zero_flow',s,replace(flow,annual_energy=q(0.,'kcal/year_365'))),
        ('incompatible_phase',s,replace(flow,phase='other invented phase')),
        ('already_net_edible',replace(s,stored_state='net_edible',density_stored_state='net_edible',material_basis='already_net_edible',net_edible_yield=q(1.,'kg_edible/kg_stored')),flow)]
    manufactured=[]
    for name,store,reference in examples:
        manufactured.append(dict(name=name,record_kind='manufactured_unit_control',store=asdict(store),flow=asdict(reference),result=convert(store,reference)))
    invalid=[('gross_area',replace(s,area_basis='gross_footprint')),
        ('mixed_unallocated',replace(s,area_basis='unallocated_mixed')),
        ('density_state_mismatch',replace(s,density_stored_state='clean')),
        ('excess_structural_load',replace(s,structural_mass_limit=q(300.,'kg_stored/m2'))),
        ('double_deduction',replace(s,material_basis='already_net_edible'))]
    rejected=[]
    for name,store in invalid:
        try:convert(store)
        except ValueError as error:rejected.append(dict(name=name,store=asdict(store),status='rejected',reason=str(error)))
        else:raise AssertionError('Invalid input accepted: '+name)
    write(OUT/'manufactured.json',manufactured);write(OUT/'rejected.json',rejected)
    rows=list(csv.DictReader((BUFFERS/'buffer_usage.csv').open()));assert len(rows)==6
    model=[]
    for row in rows:
        reading,kind=row['reading'],row['store_class'];days=90 if kind=='town' else 365
        denominator={'rural':'fixed rural meal energy','commercial_export':'original baseline annual marketed energy','town':'fixed city meal energy'}[kind]
        report='reports/URBAN_EARTH_MONTHLY_20261116.md'
        unknown=lambda unit:q(None,unit,report,'No physical-store measurement supplied')
        # This is a class-level missing-evidence record,not a claimed building.
        record=PhysicalStore('model-class:'+reading+':'+kind,kind,None,None,None,
            'model homogeneous cereal','net_edible','net edible cereal','already_net_edible','single_commodity_allocated_usable',
            unknown('m2'),unknown('m'),unknown('kg_stored/m3'),'model homogeneous cereal','net_edible',
            q(1.,'kg_edible/kg_stored',report,'Accounting pool already net edible'),unknown('kcal/kg_edible'),
            unknown('kg_stored/m2'),None,None)
        check=convert(record);assert check['geometric_net_energy_kcal'] is None and not check['empirically_qualified']
        model.append(dict(reading=reading,store_class=kind,model_capacity_grain_person_years=float(row['capacity_grain_person_years']),
            model_days=days,model_denominator=denominator,reference_kind='declared_model_scenario',
            observed_building_or_volume=False,physical_store_measurements_supplied=False,
            arithmetic_gaps=';'.join(check['arithmetic_gaps']),operational_gaps=';'.join(check['operational_gaps']),
            historical_capacity_qualified=False,physical_conversion_energy_kcal=check['geometric_net_energy_kcal']))
    with (OUT/'model_interfaces.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(model[0]));writer.writeheader();writer.writerows(model)
    paths=[Path(__file__),PLAN,PARENT/'qualification.json',BUFFERS/'qualification.json',BUFFERS/'buffer_usage.csv',
        ROOT/'polity/storage_capacity.py',ROOT/'tests/test_storage_capacity.py',OUT/'tests.json',ROOT/'reports/URBAN_EARTH_MONTHLY_20261116.md']
    result=dict(status='completed_manufactured_capacity_contract_and_existing_model_interface_audit',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=parent['protected_sha256'],
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},adapter_tests=23,manufactured_cases=len(manufactured),
        rejected_invalid_inputs=len(rejected),existing_store_class_rows=len(model),historical_capacities_qualified=0,
        new_site_measurement_rows=0,food_kernel_calls=0,new_food_scenarios=0,existing_model_capacities_changed=False,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
    for name,digest in parent['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',result);print(result['status'],flush=True)


if __name__=='__main__':main()
