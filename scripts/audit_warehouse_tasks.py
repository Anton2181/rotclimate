"""Eight declared physical task-budget outcomes; no crop/food/routing solvers."""
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.task_budget import TaskBudget
from audit_warehouse_no_hold import sha,read,write,serial

OUT=ROOT/'output/urban_warehouse_tasks_20261117'
PARENT=ROOT/'output/urban_warehouse_work_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_task_budget_controls.json'


def fixtures():
    baseline=np.zeros((12,1));baseline[0]=6
    base=dict(workforce_ids=['manufactured-physical-crew'],annual_capacity=[10.],monthly_capacity=np.full((12,1),10.).tolist(),
        baseline_annual=[6.],baseline_monthly=baseline.tolist(),baseline_task_ids=['already-charged-crop-tasks'],baseline_complete=True)
    tasks=dict(task_ids=['commercial','town'],workforce=[0,0],month=[0,0],role=['commercial','town'],hours=[3.,1.])
    cross_monthly=np.zeros((12,2));cross_monthly[0,0]=4
    return [
        dict(name='shared_roles_ok',budget=base,tasks=tasks,expected='accepted'),
        dict(name='duplicate_role_capacity_rejected',budget=base,tasks={**tasks,'hours':[3.,3.]},expected='Shared annual'),
        dict(name='monthly_limit_rejected',budget={**base,'annual_capacity':[30.],'monthly_capacity':np.full((12,1),8.).tolist()},
            tasks=dict(task_ids=['handling'],workforce=[0],month=[0],role=['town'],hours=[3.]),expected='Shared monthly'),
        dict(name='annual_limit_rejected',budget=base,tasks={**tasks,'month':[0,1],'hours':[3.,3.]},expected='Shared annual'),
        dict(name='calendar_bins_ok',budget={**base,'baseline_annual':[0.],'baseline_monthly':np.zeros((12,1)).tolist(),
            'monthly_capacity':np.full((12,1),8.).tolist()},tasks={**tasks,'month':[0,11],'hours':[6.,4.]},expected='accepted'),
        dict(name='zero_tasks_ok',budget={**base,'baseline_annual':[0.],'baseline_monthly':np.zeros((12,1)).tolist()},
            tasks=dict(task_ids=['explicit-zero'],workforce=[0],month=[0],role=['town'],hours=[0.]),expected='accepted'),
        dict(name='cross_workforce_borrowing_rejected',budget={**base,'workforce_ids':['crew-a','crew-b'],'annual_capacity':[5.,100.],
            'monthly_capacity':np.tile([5.,100.],(12,1)).tolist(),'baseline_annual':[4.,0.],'baseline_monthly':cross_monthly.tolist()},
            tasks=dict(task_ids=['handling'],workforce=[0],month=[0],role=['town'],hours=[2.]),expected='Shared annual'),
        dict(name='missing_full_schedule_rejected',budget={**base,'baseline_complete':False},tasks=tasks,expected='complete baseline')]


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed task-budget controls'
    q=read(PARENT/'qualification.json');assert q['status'].startswith('passed_')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and '24 passed' in tests['stdout']
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    cases=[]
    for f in fixtures():
        before=None;budget=None
        try:
            budget=TaskBudget(**f['budget']);before=serial(budget.certificate());certificate=serial(budget.reserve(**f['tasks']))
        except ValueError as error:
            assert f['expected']!='accepted' and f['expected'] in str(error),(f['name'],error)
            if budget is not None:assert serial(budget.certificate())==before,'Rejected tasks mutated budget'
            cases.append(dict(fixture=f,status='rejected_as_declared',error=str(error),budget_unchanged=budget is not None))
        else:
            assert f['expected']=='accepted',f['name'];cases.append(dict(fixture=f,status='accepted_as_declared',certificate=certificate))
        print(f['name'],cases[-1]['status'],flush=True)
    assert len(cases)==8
    write(OUT/'cases.json',cases)
    paths=[Path(__file__),PLAN,OUT/'tests.json',PARENT/'qualification.json',ROOT/'polity/task_budget.py',ROOT/'tests/test_task_budget.py']
    for name,digest in q['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_eight_declared_shared_physical_task_budget_outcomes',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=q['protected_sha256'],
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},tests=24,manufactured_cases=8,
        accepted_cases=sum(c['status']=='accepted_as_declared' for c in cases),rejected_cases=sum(c['status']=='rejected_as_declared' for c in cases),
        component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,empirical_staffing_qualified=False,handling_rate_inferred=False,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))


if __name__=='__main__':main()
