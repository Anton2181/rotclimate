from copy import deepcopy

import numpy as np
import pytest

from polity.no_hold import NoHoldLedger
from polity.handling_claims import handling_claims
from polity.task_budget import TaskBudget


def args():
    batch=NoHoldLedger().record(['a','b'],[10,11],[20,20],[60.,60.],[60.,60.],[11,11],[0,0])
    incoming=np.zeros((12,1));incoming[0]=120;paid=np.zeros((12,2));paid[0]=[8,2];paid[1]=[5,0]
    result=dict(inventory=dict(store_ids=['store'],incoming=incoming,departures=paid.sum(1)[:,None]),
        store_nodes=np.array([20]),role_ids=['commercial','town'],role_store=np.array([0,0]),paid=paid,requested=np.tile([8.,2.],(12,1)))
    return dict(batches=[batch],consignment_store=np.array([0,0]),result=result,store_workforce=np.array([0]),
        inbound_hours_per_unit=np.array([.01]),role_hours_per_unit=np.array([.2,.5]),grain_unit='net edible kcal',
        rate_unit='hours/net edible kcal',namespace='original-grain-receipt')


def budget():
    baseline=np.zeros((12,1));baseline[0]=6
    return TaskBudget(['crew'],[11],np.full((12,1),10),[6],baseline,baseline_task_ids=['crop'],baseline_complete=True)


def test_paid_grain_generates_one_unload_per_arrival_and_one_claim_per_paid_role_bin():
    a=args();c=handling_claims(**a);tasks=c['tasks']
    assert len(tasks)==5 and sum(row['kind']=='unloading' for row in tasks)==2
    assert sum(row['grain'] for row in tasks if row['kind']=='unloading')==120
    assert sum(row['grain'] for row in tasks if row['kind']=='withdrawal')==15
    assert np.isclose(c['reservation']['hours'].sum(),4.8)
    assert np.isclose(budget().reserve(**c['reservation'])['annual_used'][0],10.8)


def test_same_total_grain_can_exceed_work_budget_under_other_role_allocation():
    a=args();a['result']['paid'][1]=[3,2];c=handling_claims(**a)
    assert a['result']['paid'].sum()==15 and np.isclose(c['reservation']['hours'].sum(),5.4)
    with pytest.raises(ValueError,match='annual'):budget().reserve(**c['reservation'])


def test_requests_are_not_claimed_as_completed_handling():
    a=args();first=handling_claims(**a);a['result']['requested']*=100;second=handling_claims(**a)
    assert first['tasks']==second['tasks']


def test_zero_rate_retains_grain_task_identity_without_imputing_work():
    a=args();a['inbound_hours_per_unit'][:]=0;c=handling_claims(**a)
    assert len([t for t in c['tasks'] if t['kind']=='unloading'])==2
    assert sum(t['hours'] for t in c['tasks'] if t['kind']=='unloading')==0


def test_claims_cannot_be_debited_twice():
    c=handling_claims(**args());b=budget();b.reserve(**c['reservation'])
    with pytest.raises(ValueError,match='Duplicate'):b.reserve(**c['reservation'])


@pytest.mark.parametrize('key,value',[('grain_unit','tonnes'),('rate_unit','hours/kg'),('inbound_hours_per_unit',np.array([np.inf])),
    ('role_hours_per_unit',np.array([.2,-.5])),('consignment_store',np.array([0,-1])),('namespace','')])
def test_invalid_or_unqualified_units_assignments_rates_rejected(key,value):
    a=args();a[key]=value
    with pytest.raises(ValueError):handling_claims(**a)


def test_missing_or_copied_grain_receipts_rejected():
    a=args();a['batches']*=2;a['consignment_store']=np.array([0,0,0,0])
    with pytest.raises(ValueError,match='Duplicate'):handling_claims(**a)
    a=args();a['result']['inventory']['incoming'][0]=121
    with pytest.raises(ValueError,match='cover'):handling_claims(**a)


def test_mismatched_paid_departures_and_endpoint_fail():
    a=args();a['result']['paid'][0,0]+=1
    with pytest.raises(ValueError):handling_claims(**a)
    a=args();a['result']['store_nodes'][0]=30
    with pytest.raises(ValueError,match='endpoint'):handling_claims(**a)


def test_converter_does_not_mutate_original_grain_results():
    a=args();before=deepcopy(a['result']);handling_claims(**a)
    for key in ['paid','requested','store_nodes']:np.testing.assert_array_equal(a['result'][key],before[key])
    np.testing.assert_array_equal(a['result']['inventory']['incoming'],before['inventory']['incoming'])
