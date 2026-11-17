"""Exactly three manufactured grain-to-work claims from frozen paid grain receipts."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.no_hold import NoHoldLedger
from polity.handling_claims import handling_claims
from polity.task_budget import TaskBudget
from audit_warehouse_no_hold import sha,read,write,serial

OUT=ROOT/'output/urban_warehouse_coupling_20261117'
ROLES=ROOT/'output/urban_warehouse_roles_20261117'
TASKS=ROOT/'output/urban_warehouse_tasks_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_grain_work_coupling_controls.json'


def object_hash(value):return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed grain/work coupling controls'
    sources={};protected={}
    for folder in [ROLES,TASKS]:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and '14 passed' in tests['stdout']
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    original=sha(ROLES/'scenarios.json');grain={c['name']:c for c in read(ROLES/'scenarios.json')};cases=[]
    for f in read(PLAN)['finite_cases']:
        c=grain[f['grain_receipt']];inputs=c['fixture'];result=c['result'];before=object_hash(result)
        batch=NoHoldLedger().record(inputs['ids'],inputs['origin'],inputs['destination'],inputs['sent'],inputs['delivered'],inputs['departure'],inputs['arrival'])
        claims=handling_claims([batch],inputs['consignment_store'],result,store_workforce=[0],
            inbound_hours_per_unit=[f['unloading_hours_per_delivered_kcal']],
            role_hours_per_unit=[f['commercial_hours_per_paid_kcal'],f['town_hours_per_paid_kcal']],
            grain_unit='net edible kcal',rate_unit='hours/net edible kcal',namespace=f['name'])
        assert object_hash(result)==before,'Claim conversion mutated original grain receipt'
        hours=float(np.asarray(claims['reservation']['hours']).sum());assert abs(hours-f['expected_additional_hours'])<=1e-8
        baseline=np.zeros((12,1));baseline[0]=f['baseline_hours_bin0'];certificate=None;failure=None
        try:
            budget=TaskBudget(['manufactured-physical-crew'],[f['annual_capacity_hours']],np.full((12,1),f['monthly_capacity_hours']),
                [f['baseline_hours_bin0']],baseline,baseline_task_ids=['already-charged-baseline'],baseline_complete=f['baseline_complete'])
            certificate=budget.reserve(**claims['reservation'])
        except ValueError as error:
            failure=str(error)
            if f['expected']=='annual_budget_rejection':assert 'Shared annual' in failure
            elif f['expected']=='missing_complete_schedule_rejection':assert 'complete baseline' in failure
            else:raise
        else:assert f['expected']=='accepted'
        cases.append(dict(name=f['name'],grain_receipt=f['grain_receipt'],grain_object_sha256=before,fixture=f,
            claims=serial(claims),additional_hours=hours,total_hours=f['baseline_hours_bin0']+hours,
            accepted=certificate is not None,certificate=serial(certificate),failure=failure,
            original_paid_grain=float(np.asarray(result['paid']).sum()),original_grain_unchanged=True))
        print(f['name'],'accepted' if certificate is not None else 'rejected as declared','; total hours',f['baseline_hours_bin0']+hours,flush=True)
    assert len(cases)==3 and sha(ROLES/'scenarios.json')==original
    write(OUT/'cases.json',cases)
    paths=[Path(__file__),PLAN,OUT/'tests.json',ROLES/'scenarios.json',ROOT/'polity/handling_claims.py',ROOT/'tests/test_handling_claims.py',
        ROOT/'polity/task_budget.py',ROOT/'polity/no_hold.py']
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_three_declared_original_manufactured_grain_work_couplings',sources_sha256=sources,
        protected_sha256=protected,files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},tests=14,coupling_cases=3,
        accepted_cases=1,rejected_cases=2,original_grain_outputs_unchanged=True,new_handling_converter_calls=3,
        receipt_materialization_no_hold_calls=3,converter_no_hold_revalidation_calls=sum(c['claims']['funding_revalidation_calls'] for c in cases),
        new_role_adapter_calls=0,new_shared_store_calls=0,component_work_calls=0,food_kernel_calls=0,stock_solves=0,
        graph_rebuilds=0,dijkstra_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,
        handling_rates_empirically_qualified=False,actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))


if __name__=='__main__':main()
