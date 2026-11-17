import numpy as np
import pytest

from polity.task_budget import TaskBudget


def args():
    baseline=np.zeros((12,1));baseline[0]=6
    return dict(workforce_ids=['one physical crew'],annual_capacity=[10.],monthly_capacity=np.full((12,1),10.),
        baseline_annual=[6.],baseline_monthly=baseline,baseline_task_ids=['listed crop tasks'],baseline_complete=True)


def test_roles_share_remaining_budget_across_calls():
    b=TaskBudget(**args());b.reserve(['commercial'],[0],[0],['commercial'],[3.])
    c=b.reserve(['town'],[0],[0],['town'],[1.])
    assert c['annual_used'][0]==10 and c['monthly_used'][0,0]==10
    with pytest.raises(ValueError,match='annual'):b.reserve(['another town'],[0],[1],['town'],[1.])
    assert b.certificate()['additional_task_ids']==('commercial','town')


def test_individually_feasible_roles_cannot_each_spend_same_unused_time():
    b=TaskBudget(**args());b.reserve(['first'],[0],[0],['commercial'],[3.])
    with pytest.raises(ValueError,match='annual'):b.reserve(['second'],[0],[0],['town'],[3.])
    assert b.certificate()['annual_used'][0]==9


def test_monthly_limit_can_fail_while_annual_budget_fits():
    a=args();a.update(annual_capacity=[30.],monthly_capacity=np.full((12,1),8.));b=TaskBudget(**a)
    with pytest.raises(ValueError,match='monthly'):b.reserve(['task'],[0],[0],['town'],[3.])


def test_annual_limit_can_fail_while_each_month_fits():
    b=TaskBudget(**args())
    with pytest.raises(ValueError,match='annual'):b.reserve(['a','b'],[0,0],[0,1],['commercial','town'],[3.,3.])


def test_other_workforce_spare_hours_cannot_fund_overspend():
    a=args();a.update(workforce_ids=['a','b'],annual_capacity=[5.,100.],monthly_capacity=np.tile([5.,100.],(12,1)),
        baseline_annual=[4.,0.],baseline_monthly=np.vstack([[4.,0.],np.zeros((11,2))]));b=TaskBudget(**a)
    with pytest.raises(ValueError):b.reserve(['task'],[0],[0],['town'],[2.])


@pytest.mark.parametrize('complete',[False,None,1])
def test_partial_or_unknown_schedule_cannot_be_certified(complete):
    a=args();a['baseline_complete']=complete
    with pytest.raises(ValueError,match='complete'):TaskBudget(**a)


def test_reaping_only_baseline_cannot_replace_complete_listed_schedule():
    a=args();a['baseline_monthly']*=.15
    with pytest.raises(ValueError,match='inconsistent'):TaskBudget(**a)


def test_baseline_task_cannot_be_charged_again_as_handling():
    b=TaskBudget(**args())
    with pytest.raises(ValueError,match='Duplicate'):b.reserve(['listed crop tasks'],[0],[0],['town'],[1.])


@pytest.mark.parametrize('key,value',[('workforce_ids',['x','x']),('annual_capacity',[np.inf]),('baseline_annual',[-1.]),
    ('monthly_capacity',np.full((12,1),np.nan)),('baseline_task_ids',[]),('baseline_monthly',None)])
def test_invalid_or_unfunded_baseline_rejected(key,value):
    a=args();a[key]=value
    with pytest.raises(ValueError):TaskBudget(**a)


@pytest.mark.parametrize('ids,worker,month,role,hours',[
    (['a','a'],[0,0],[0,0],['town','town'],[1.,1.]),(['a'],[-1],[0],['town'],[1.]),
    (['a'],[0],[12],['town'],[1.]),(['a'],[0],[0],[''],[1.]),(['a'],[0],[0],['town'],[-1.]),
    (['a'],[0],[0],['town'],[np.inf])])
def test_invalid_task_batch_leaves_ledger_unchanged(ids,worker,month,role,hours):
    b=TaskBudget(**args())
    with pytest.raises(ValueError):b.reserve(ids,worker,month,role,hours)
    assert b.certificate()['additional_task_ids']==()


def test_caller_cannot_mutate_accepted_budget_through_input_or_certificate():
    a=args();b=TaskBudget(**a);a['monthly_capacity'][:]=999
    c=b.reserve(['a'],[0],[0],['town'],[4.]);c['annual_capacity'][0]=999
    with pytest.raises(ValueError):b.reserve(['b'],[0],[1],['town'],[1.])


def test_explicit_calendar_bins_and_zero_task_are_preserved():
    a=args();a.update(baseline_annual=[0.],baseline_monthly=np.zeros((12,1)),monthly_capacity=np.full((12,1),8.));b=TaskBudget(**a)
    c=b.reserve(['jan','dec','zero'],[0,0,0],[0,11,3],['town','commercial','town'],[6.,4.,0.])
    assert c['monthly_used'][0,0]==6 and c['monthly_used'][11,0]==4 and c['annual_used'][0]==10
