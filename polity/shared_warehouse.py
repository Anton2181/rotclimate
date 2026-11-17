"""One funded inventory and capacity per explicitly identified physical store.

Deposits are net edible kcal already released by an upstream source ledger.
Pool labels and pooling permission are supplied scenario contracts,not inferred
ownership or archaeological qualification. Routing,people and work stay outside.
"""
import math

import numpy as np

from .earth_storage_loss import inventory


def shared_warehouse_year(deposits,origin_store,store_ids,capacity,withdrawals,*,
                          origin_pool,store_pool,pooling_authorized,loss):
    deposits=np.asarray(deposits,float);mapping=np.asarray(origin_store)
    capacity=np.asarray(capacity,float);withdrawals=np.asarray(withdrawals,float)
    if isinstance(store_ids,(str,bytes)):raise ValueError('An explicit sequence of physical store IDs required')
    ids=tuple(store_ids);k=len(ids)
    if not k or any(not isinstance(i,str) or not i.strip() for i in ids) or len(set(ids))!=k:
        raise ValueError('Unique nonempty physical store IDs required')
    if deposits.ndim!=2 or deposits.shape[0]!=12 or mapping.shape!=deposits.shape[1:]:
        raise ValueError('Twelve-bin deposits and one physical-store assignment per origin required')
    if mapping.dtype.kind not in 'iu' or np.any((mapping< -1)|(mapping>=k)):
        raise ValueError('Integer store assignment must be valid or explicitly unassigned')
    mapping=mapping.astype(np.intp,copy=False)
    if capacity.shape!=(k,) or withdrawals.shape!=(12,k):raise ValueError('One capacity and explicit twelve-bin withdrawals per store required')
    if any(not np.isfinite(v).all() or (v<0).any() for v in [deposits,capacity,withdrawals]):
        raise ValueError('Finite nonnegative energy/capacity required;unknown is not zero or unlimited')
    if loss not in (0.,.05):raise ValueError('Only declared zero/five-percent stored loss supported')
    source_pools=np.asarray(origin_pool);pools=np.asarray(store_pool);permission=np.asarray(pooling_authorized)
    if source_pools.shape!=mapping.shape or pools.shape!=(k,) or permission.shape!=(k,) or permission.dtype.kind!='b':
        raise ValueError('Explicit pool labels and boolean pooling permission per store required')
    if any(not isinstance(v,(str,np.str_)) or not v.strip() for v in [*source_pools,*pools]):
        raise ValueError('Named homogeneous net-edible pools required')
    assigned=mapping>=0
    if np.any(deposits[:,~assigned]>0):raise ValueError('Positive deposits require one explicit store assignment')
    if np.any(source_pools[assigned]!=pools[mapping[assigned]]):raise ValueError('Stored material/pool mismatch')
    contributors=np.bincount(mapping[assigned],minlength=k)
    if np.any((contributors>1)&~permission):raise ValueError('Sharing a physical store requires explicit scenario pooling permission')
    incoming=np.zeros((12,k))
    for month in range(12):
        incoming[month]=np.bincount(mapping[assigned],weights=deposits[month,assigned],minlength=k)
    year=inventory(incoming,withdrawals,capacity,loss)
    paid=withdrawals-year.unmet_path
    total=lambda v:math.fsum(np.asarray(v).ravel())
    supplied=total(deposits);funded=total(paid);spoiled=total(year.spoiled);overflow=total(year.overflow)
    stock_change=total(year.final_stock-year.initial_stock)
    residual=supplied-math.fsum([funded,spoiled,overflow,stock_change])
    tolerance=1e-10*max(1,supplied,total(withdrawals))
    if abs(residual)>tolerance:raise RuntimeError('Shared-store physical grain ledger does not close')
    return dict(store_ids=ids,store_pool=pools.copy(),origin_store=mapping.copy(),contributors=contributors,
        pooling_authorized=permission.copy(),capacity=capacity.copy(),incoming=incoming,requested=withdrawals.copy(),
        departures=paid,food_year=year,ledger=dict(deposited_kcal=supplied,paid_departures_kcal=funded,
        spoiled_kcal=spoiled,overflow_kcal=overflow,stock_change_kcal=stock_change,residual_kcal=residual),
        ownership_inferred=False,empirical_capacity_qualified=False)
