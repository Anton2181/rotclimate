"""Independent task derivation and grain/work feasibility from frozen source values."""
from fractions import Fraction
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import sha,read,write

OUT=ROOT/'output/urban_warehouse_coupling_20261117'
ROLES=ROOT/'output/urban_warehouse_roles_20261117'


def main():
    assert not (OUT/'review.json').exists(),'Preserve independent coupling review'
    r=read(OUT/'results.json');assert r['status']=='completed_three_declared_original_manufactured_grain_work_couplings'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    grain={c['name']:c for c in read(ROLES/'scenarios.json')};cases=read(OUT/'cases.json');assert len(cases)==3;checked=[]
    for case in cases:
        fixture=case['fixture'];original=grain[case['grain_receipt']];f=original['fixture'];c=original['result'];paid=np.asarray(c['paid'])
        expected=[]
        for i,g in enumerate(f['delivered']):
            if g>0:expected.append((f'unload:{f["ids"][i]}','unloading',f['arrival'][i],float(g),fixture['unloading_hours_per_delivered_kcal'],f['ids'][i]))
        for month in range(12):
            for role,label in enumerate(c['role_ids']):
                if paid[month,role]>0:
                    rate=fixture['commercial_hours_per_paid_kcal'] if label=='commercial' else fixture['town_hours_per_paid_kcal']
                    expected.append((f'withdraw:{month}:{label}',label,month,float(paid[month,role]),rate,f'paid:{month}:{label}'))
        tasks=case['claims']['tasks'];assert len(expected)==len(tasks)
        assert len({t['id'] for t in tasks})==len(tasks)
        by_month=[Fraction(0) for _ in range(12)];by_role={}
        for wanted,actual in zip(expected,tasks):
            suffix,label,month,grain_amount,rate,reference=wanted
            assert actual['id']==case['name']+':'+suffix and actual['month']==month and actual['role']==label and actual['workforce']==0
            assert actual['grain_reference']==reference and actual['grain']==grain_amount and actual['rate']==rate
            assert actual['store_id']==c['inventory']['store_ids'][0]
            exact=Fraction(str(grain_amount))*Fraction(str(rate));assert math.isclose(actual['hours'],float(exact),rel_tol=0,abs_tol=1e-12)
            by_month[month]+=exact;by_role[label]=by_role.get(label,Fraction(0))+exact
        total=Fraction(fixture['baseline_hours_bin0'])+sum(by_month)
        assert math.isclose(case['total_hours'],float(total),rel_tol=0,abs_tol=1e-12)
        assert float(total)==fixture['expected_total_hours']
        within_monthly=all(v+(fixture['baseline_hours_bin0'] if m==0 else 0)<=fixture['monthly_capacity_hours'] for m,v in enumerate(by_month))
        accepted=fixture['baseline_complete'] and total<=fixture['annual_capacity_hours'] and within_monthly
        assert bool(accepted)==case['accepted'] and case['original_paid_grain']==paid.sum()==15
        if accepted:
            cert=case['certificate'];assert math.isclose(cert['annual_used'][0],float(total),rel_tol=0,abs_tol=1e-12)
            assert cert['annual_capacity']==[11.] and not cert['empirical_staffing_qualified']
        checked.append(dict(name=case['name'],original_paid_grain=15,task_count=len(tasks),exact_additional_hours=str(sum(by_month)),
            exact_total_hours=str(total),by_role_hours={k:str(v) for k,v in by_role.items()},accepted=bool(accepted)))
    assert [row['task_count'] for row in checked]==[5,6,5]
    write(OUT/'review.json',dict(status='passed_independent_grain_receipt_task_identity_fraction_hour_and_feasibility_checks',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),cases=checked,task_records_checked=sum(row['task_count'] for row in checked),
        new_handling_converter_calls=0,new_task_budget_calls=0,new_role_adapter_calls=0,new_shared_store_calls=0,
        food_kernel_calls=0,stock_solves=0,component_work_calls=0,graph_rebuilds=0,dijkstra_calls=0,new_Earth_food_scenarios=0,
        new_staff_allocations=0,handling_rates_empirically_qualified=False,new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent coupling review passed:16 exact task identities/fraction-hour checks;one feasible,two rejected',flush=True)


if __name__=='__main__':main()
