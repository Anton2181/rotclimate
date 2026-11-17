from dataclasses import asdict

import numpy as np
import pytest

from polity.earth_storage_loss import inventory
from polity.shared_warehouse import shared_warehouse_year


def args():
    deposits=np.zeros((12,2));deposits[0]=[60.,60.]
    return dict(deposits=deposits,origin_store=np.array([0,0]),store_ids=['one physical store'],capacity=np.array([20.]),
        withdrawals=np.full((12,1),10.),origin_pool=['net cereal','net cereal'],store_pool=['net cereal'],
        pooling_authorized=np.array([True]),loss=0.)


def test_two_origins_fund_one_capacity_without_copying_stock():
    result=shared_warehouse_year(**args())
    assert result['incoming'].sum()==120 and result['capacity'].sum()==20
    assert result['food_year'].peak_stock[0]==20
    assert result['departures'].sum()==30 and result['food_year'].overflow[0]==90
    assert result['ledger']['residual_kcal']==0


@pytest.mark.parametrize('loss',[0.,.05])
def test_one_origin_per_store_reduces_exactly_to_qualified_inventory(loss):
    a=args();a.update(origin_store=np.array([1,0]),store_ids=['b','a'],capacity=np.array([10.,20.]),
        withdrawals=np.full((12,2),4.),store_pool=['net cereal','net cereal'],pooling_authorized=np.array([False,False]),loss=loss)
    result=shared_warehouse_year(**a);expected=inventory(a['deposits'][:,::-1],a['withdrawals'],a['capacity'],loss)
    for key,value in asdict(expected).items():np.testing.assert_array_equal(asdict(result['food_year'])[key],value)


def test_zero_deposits_cannot_fund_inherited_food():
    a=args();a['deposits'][:]=0;result=shared_warehouse_year(**a)
    assert result['departures'].sum()==result['food_year'].initial_stock.sum()==0
    assert result['food_year'].unmet.sum()==120


def test_zero_capacity_can_pay_immediately_but_carries_no_grain():
    a=args();a['capacity'][:]=0;result=shared_warehouse_year(**a)
    assert result['departures'].sum()==10 and result['food_year'].stock_path.sum()==0


def test_zero_withdrawals_do_not_create_shipments_or_resize_capacity():
    a=args();a['withdrawals'][:]=0;result=shared_warehouse_year(**a)
    assert result['departures'].sum()==0 and result['capacity'][0]==20
    np.testing.assert_array_equal(result['requested'],a['withdrawals'])


def test_sharing_requires_explicit_permission():
    a=args();a['pooling_authorized'][:]=False
    with pytest.raises(ValueError,match='permission'):shared_warehouse_year(**a)


def test_duplicate_physical_ids_cannot_multiply_capacity():
    a=args();a.update(store_ids=['same','same'],capacity=np.array([20.,20.]),withdrawals=np.zeros((12,2)),
        store_pool=['net cereal','net cereal'],pooling_authorized=np.array([True,True]))
    with pytest.raises(ValueError,match='Unique'):shared_warehouse_year(**a)


def test_unassigned_positive_grain_is_rejected_but_explicit_zero_is_allowed():
    a=args();a['origin_store'][1]=-1
    with pytest.raises(ValueError,match='Positive deposits'):shared_warehouse_year(**a)
    a['deposits'][:,1]=0;result=shared_warehouse_year(**a)
    assert result['incoming'].sum()==60


def test_incompatible_material_pools_cannot_be_merged():
    a=args();a['origin_pool'][1]='other material'
    with pytest.raises(ValueError,match='pool mismatch'):shared_warehouse_year(**a)


@pytest.mark.parametrize('invalid',[None,np.array([np.inf]),np.array([-1.])])
def test_unknown_unlimited_or_negative_capacity_is_rejected(invalid):
    a=args();a['capacity']=invalid
    with pytest.raises(ValueError):shared_warehouse_year(**a)


@pytest.mark.parametrize('mapping',[np.array([0.,0.]),np.array([0,1]),np.array([0,-2])])
def test_invalid_partition_is_rejected(mapping):
    a=args();a['origin_store']=mapping
    with pytest.raises(ValueError):shared_warehouse_year(**a)


def test_withdrawals_are_explicit_and_unchanged_when_deposits_change():
    a=args();first=shared_warehouse_year(**a);a['deposits']*=2;second=shared_warehouse_year(**a)
    np.testing.assert_array_equal(first['requested'],second['requested'])
    np.testing.assert_array_equal(first['capacity'],second['capacity'])


def test_unsigned_integer_partition_is_supported():
    a=args();a['origin_store']=a['origin_store'].astype(np.uint64)
    assert shared_warehouse_year(**a)['incoming'].sum()==120


def test_unknown_permission_or_nonfinite_deposit_is_rejected():
    a=args();a['pooling_authorized']=np.array([1])
    with pytest.raises(ValueError):shared_warehouse_year(**a)
    a=args();a['deposits'][0,0]=np.nan
    with pytest.raises(ValueError):shared_warehouse_year(**a)
