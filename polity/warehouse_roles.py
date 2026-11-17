"""Funded endpoint arrivals and explicit roles share one physical store inventory.

Priority, capacities, material and pooling access are supplied scenario contracts.
This adapter does not certify upstream rural/work funding or historical rights.
"""
import math

import numpy as np

from .no_hold import NoHoldBatch,NoHoldLedger
from .shared_warehouse import shared_warehouse_year


def shared_role_year(batches,consignment_store,store_ids,store_nodes,capacity,
                     role_ids,role_store,requests,priority,*,consignment_pool,
                     store_pool,pooling_authorized,loss):
    if isinstance(store_ids,(str,bytes)) or isinstance(role_ids,(str,bytes)):
        raise ValueError('Explicit store/role ID sequences required')
    store_ids=tuple(store_ids);role_ids=tuple(role_ids);k=len(store_ids);r=len(role_ids)
    for ids in [store_ids,role_ids]:
        if not ids or any(not isinstance(v,str) or not v.strip() for v in ids) or len(set(ids))!=len(ids):
            raise ValueError('Unique nonempty physical store and role IDs required')
    nodes=np.asarray(store_nodes);mapping=np.asarray(consignment_store);role_store=np.asarray(role_store);priority=np.asarray(priority)
    if nodes.shape!=(k,) or nodes.dtype.kind not in 'iu' or (nodes<0).any() or (nodes>np.iinfo(np.intp).max).any() or len(set(nodes.tolist()))!=k:
        raise ValueError('One distinct nonnegative physical node per supplied store required')
    if role_store.shape!=(r,) or role_store.dtype.kind not in 'iu' or np.any((role_store<0)|(role_store>=k)):
        raise ValueError('Each role requires one explicit physical store')
    if priority.shape!=(r,) or priority.dtype.kind not in 'iu' or sorted(priority.tolist())!=list(range(r)):
        raise ValueError('Explicit role-priority permutation required')
    requests=np.asarray(requests,float)
    if requests.shape!=(12,r) or not np.isfinite(requests).all() or (requests<0).any():
        raise ValueError('Finite nonnegative twelve-bin role requests required')
    batches=tuple(batches)
    if not batches or any(not isinstance(b,NoHoldBatch) for b in batches):raise ValueError('Explicit funded no-hold receipts required')
    funded=NoHoldLedger();checked=[]
    for b in batches:
        checked.append(funded.record(b.ids,b.origin,b.destination,b.sent,b.delivered,b.departure_bin,b.arrival_bin,
            event_labels=b.charge_labels,charge_allocation=b.charges))
    n=sum(len(b.ids) for b in checked)
    if mapping.shape!=(n,) or mapping.dtype.kind not in 'iu' or np.any((mapping<0)|(mapping>=k)):
        raise ValueError('One explicit physical-store assignment per consignment required')
    mapping=mapping.astype(np.intp);role_store=role_store.astype(np.intp)
    origin=np.concatenate([b.origin for b in checked]);destination=np.concatenate([b.destination for b in checked])
    arrival=np.concatenate([b.arrival_bin for b in checked]);delivered=np.concatenate([b.delivered for b in checked])
    if np.any(destination!=nodes[mapping]):raise ValueError('Funded endpoint does not match assigned physical store')
    pools=np.asarray(consignment_pool);store_pool=np.asarray(store_pool)
    if pools.shape!=(n,) or store_pool.shape!=(k,) or any(not isinstance(v,(str,np.str_)) or not v.strip() for v in [*pools,*store_pool]):
        raise ValueError('Explicit compatible net-material pool labels required')
    if np.any(pools!=store_pool[mapping]):raise ValueError('Consignment/store material pool mismatch')
    # Coalesce repeat movements from the same physical source/store, without duplicating funding.
    keys=sorted(set(zip(origin.tolist(),mapping.tolist())))
    columns={key:i for i,key in enumerate(keys)}
    col=np.array([columns[key] for key in zip(origin.tolist(),mapping.tolist())],np.intp)
    deposits=np.zeros((12,len(keys)));np.add.at(deposits,(arrival,col),delivered)
    source_store=np.array([key[1] for key in keys],np.intp)
    aggregate=np.zeros((12,k))
    for month in range(12):aggregate[month]=np.bincount(role_store,weights=requests[month],minlength=k)
    inventory=shared_warehouse_year(deposits,source_store,store_ids,capacity,aggregate,
        origin_pool=store_pool[source_store],store_pool=store_pool,pooling_authorized=pooling_authorized,loss=loss)
    remaining=inventory['departures'].copy()
    if (remaining<0).any():raise RuntimeError('Inventory returned negative paid withdrawals')
    paid=np.zeros_like(requests)
    for role in priority:
        store=role_store[role];paid[:,role]=np.minimum(requests[:,role],remaining[:,store]);remaining[:,store]-=paid[:,role]
    paid_by_store=np.zeros((12,k))
    for month in range(12):paid_by_store[month]=np.bincount(role_store,weights=paid[month],minlength=k)
    tolerance=1e-10*np.maximum(1,np.maximum(aggregate,inventory['departures']))
    if np.any(abs(paid_by_store-inventory['departures'])>tolerance):raise RuntimeError('Role withdrawals do not conserve one store departure')
    summary=funded.summary();store_ledger=inventory['ledger']
    role_total=math.fsum(paid.ravel())
    physical_residual=summary['sent_kcal']-math.fsum([summary['whole_leg_charge_kcal'],role_total,
        store_ledger['spoiled_kcal'],store_ledger['overflow_kcal'],store_ledger['stock_change_kcal']])
    if abs(physical_residual)>1e-10*max(1,summary['sent_kcal']):raise RuntimeError('Freight/store/role physical grain does not close')
    return dict(inventory=inventory,store_nodes=nodes.copy(),role_ids=role_ids,role_store=role_store.copy(),priority=priority.copy(),
        requested=requests.copy(),paid=paid,unmet=requests-paid,paid_by_store=paid_by_store,source_store_keys=keys,
        consignment_funding=summary,whole_ledger_residual_kcal=physical_residual,
        role_departure_max_residual_kcal=float(np.max(abs(paid_by_store-inventory['departures']),initial=0)),
        upstream_rural_work_certified=False,handling_work_certified=False,empirical_capacity_qualified=False,rights_inferred=False)
