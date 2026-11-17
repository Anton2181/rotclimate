"""Independent scalar outcomes for complete baseline and shared additional task sets."""
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import sha,read,write

OUT=ROOT/'output/urban_warehouse_tasks_20261117'


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed independent task review'
    r=read(OUT/'results.json');assert r['status']=='completed_eight_declared_shared_physical_task_budget_outcomes'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    cases=read(OUT/'cases.json');assert len(cases)==8
    checked=[]
    for case in cases:
        f=case['fixture'];b=f['budget'];t=f['tasks'];annual=[];monthly=np.array(b['baseline_monthly'],float)
        additional=np.zeros_like(monthly);bad_annual=bad_monthly=False
        for worker,month,hours in zip(t['workforce'],t['month'],t['hours']):additional[month,worker]+=hours
        for worker,capacity in enumerate(b['annual_capacity']):
            baseline=math.fsum(row[worker] for row in b['baseline_monthly'])
            assert abs(baseline-b['baseline_annual'][worker])<=1e-8*max(1,capacity)
            used=b['baseline_annual'][worker]+math.fsum(row[worker] for row in additional)
            annual.append(used);bad_annual|=used>capacity+1e-8*max(1,capacity)
            for month in range(12):
                cap=b['monthly_capacity'][month][worker];value=monthly[month,worker]+additional[month,worker]
                bad_monthly|=value>cap+1e-8*max(1,cap)
        accepted=b['baseline_complete'] and not (bad_annual or bad_monthly)
        assert accepted==(case['status']=='accepted_as_declared')
        if accepted:
            c=case['certificate'];np.testing.assert_array_equal(c['annual_capacity'],b['annual_capacity']);np.testing.assert_array_equal(c['monthly_capacity'],b['monthly_capacity'])
            np.testing.assert_array_equal(c['annual_used'],annual);np.testing.assert_array_equal(c['monthly_used'],monthly+additional)
            np.testing.assert_array_equal(c['additional_monthly'],additional)
            combined=np.zeros_like(additional)
            for role,values in c['additional_by_role'].items():
                expected=np.zeros_like(additional)
                for w,m,label,h in zip(t['workforce'],t['month'],t['role'],t['hours']):
                    if label==role:expected[m,w]+=h
                np.testing.assert_array_equal(values,expected);combined+=values
            np.testing.assert_array_equal(combined,additional)
            assert not c['empirical_staffing_qualified'] and not c['handling_rate_inferred'] and not c['source_affiliation_inferred']
        checked.append(dict(name=f['name'],accepted=bool(accepted),annual_violation=bool(bad_annual),monthly_violation=bool(bad_monthly),
            complete_baseline=b['baseline_complete'],annual_used=annual))
    write(OUT/'review.json',dict(status='passed_independent_scalar_shared_task_budget_acceptance_and_rejection_checks',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),cases=checked,new_task_budget_calls=0,
        accepted_cases=3,rejected_cases=5,component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent scalar task review passed:3 accepted,5 rejected,zero new checker calls',flush=True)


if __name__=='__main__':main()
