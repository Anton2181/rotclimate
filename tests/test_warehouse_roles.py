from dataclasses import asdict

import numpy as np
import pytest

from polity.no_hold import NoHoldLedger
from polity.shared_warehouse import shared_warehouse_year
from polity.warehouse_roles import shared_role_year


def args():
    b=NoHoldLedger().record(['a','b'],[10,11],[20,20],[60,60],[60,60],[11,11],[0,0])
    return dict(batches=[b],consignment_store=np.array([0,0]),store_ids=['one store'],store_nodes=np.array([20]),capacity=np.array([20.]),
        role_ids=['commercial','town'],role_store=np.array([0,0]),requests=np.tile([8.,2.],(12,1)),priority=np.array([0,1]),
        consignment_pool=['cereal','cereal'],store_pool=['cereal'],pooling_authorized=np.array([True]),loss=0.)


def test_two_roles_draw_from_one_capacity_and_one_grain_balance():
    result=shared_role_year(**args());stock=result['inventory']
    assert stock['capacity'].sum()==stock['food_year'].peak_stock[0]==20
    assert result['paid'].sum()==30 and stock['food_year'].overflow[0]==90
    np.testing.assert_array_equal(result['paid'].sum(0),[24,6])
    assert result['whole_ledger_residual_kcal']==0


def test_priority_changes_role_access_without_changing_stock_or_total_food():
    a=args();a['capacity']=np.array([5.]);first=shared_role_year(**a)
    a['priority']=np.array([1,0]);second=shared_role_year(**a)
    np.testing.assert_array_equal(first['paid'].sum(0),[13,2]);np.testing.assert_array_equal(second['paid'].sum(0),[11,4])
    for key,value in asdict(first['inventory']['food_year']).items():np.testing.assert_array_equal(value,asdict(second['inventory']['food_year'])[key])


def test_dry_store_cannot_borrow_another_stores_grain():
    a=args();a.update(store_ids=['funded','dry'],store_nodes=np.array([20,30]),capacity=np.array([20.,20.]),role_store=np.array([0,1]),
        store_pool=['cereal','cereal'],pooling_authorized=np.array([True,False]))
    result=shared_role_year(**a);assert result['paid'][:,1].sum()==0


def test_duplicate_receipts_cannot_fund_two_roles_or_stores():
    a=args();a['batches']*=2;a['consignment_store']=np.array([0,0,0,0]);a['consignment_pool']*=2
    with pytest.raises(ValueError,match='Duplicate'):shared_role_year(**a)


def test_multiple_arrivals_from_one_origin_do_not_require_false_multi_origin_permission():
    a=args();a['batches']=[NoHoldLedger().record(['a','b'],[10,10],[20,20],[60,60],[60,60],[11,0],[0,1])];a['pooling_authorized']=np.array([False])
    result=shared_role_year(**a);assert result['inventory']['contributors'][0]==1


def test_zero_delivery_funds_no_inherited_roles():
    a=args();a['batches']=[NoHoldLedger().record(['a','b'],[10,11],[20,20],[60,60],[0,0],[11,11],[0,0])]
    result=shared_role_year(**a);assert result['paid'].sum()==result['inventory']['food_year'].initial_stock.sum()==0


def test_zero_capacity_pays_only_funded_immediate_requests():
    a=args();a['capacity']=np.array([0.]);result=shared_role_year(**a)
    assert result['paid'].sum()==10 and result['inventory']['food_year'].stock_path.sum()==0


@pytest.mark.parametrize('key,value',[('role_ids',['same','same']),('priority',np.array([0,0])),('priority',np.array([1.,0.])),
    ('role_store',np.array([0,1])),('consignment_store',np.array([0,-1])),('store_nodes',np.array([30])),
    ('consignment_pool',['cereal','other']),('pooling_authorized',np.array([False])),('requests',np.full((12,2),np.nan)),
    ('requests',np.full((12,2),-1)),('capacity',np.array([np.inf]))])
def test_unfunded_or_ambiguous_role_store_contracts_fail(key,value):
    a=args();a[key]=value
    with pytest.raises(ValueError):shared_role_year(**a)


def test_differently_named_stores_cannot_duplicate_same_physical_node():
    a=args();a.update(store_ids=['one','two'],store_nodes=np.array([20,20]))
    with pytest.raises(ValueError,match='distinct'):shared_role_year(**a)


@pytest.mark.parametrize('loss',[0.,.05])
def test_all_fifteen_fields_reduce_to_one_aggregate_inventory(loss):
    a=args();a['loss']=loss;result=shared_role_year(**a);deposit=np.zeros((12,2));deposit[0]=[60.,60.]
    expected=shared_warehouse_year(deposit,np.array([0,0]),a['store_ids'],a['capacity'],a['requests'].sum(1)[:,None],
        origin_pool=a['consignment_pool'],store_pool=a['store_pool'],pooling_authorized=a['pooling_authorized'],loss=loss)
    for key,value in asdict(expected['food_year']).items():np.testing.assert_array_equal(asdict(result['inventory']['food_year'])[key],value)
