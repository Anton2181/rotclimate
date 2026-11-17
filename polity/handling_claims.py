"""Explicit handling-hour claims from already-funded arrivals and paid withdrawals.

Rates are supplied hours per net edible kcal, not measured or inferred here.
This converter does not solve food stocks, change priorities or recruit staff.
"""
import numpy as np

from .no_hold import NoHoldBatch,NoHoldLedger


def handling_claims(batches,consignment_store,result,*,store_workforce,inbound_hours_per_unit,
                    role_hours_per_unit,grain_unit,rate_unit,namespace):
    if grain_unit!='net edible kcal' or rate_unit!='hours/net edible kcal':
        raise ValueError('Explicit compatible net-edible kcal and hours/net edible kcal units required')
    if not isinstance(namespace,str) or not namespace.strip():raise ValueError('Named grain receipt/task namespace required')
    inventory=result['inventory'];store_ids=tuple(inventory['store_ids']);role_ids=tuple(result['role_ids']);k=len(store_ids);r=len(role_ids)
    for ids in [store_ids,role_ids]:
        if not ids or any(not isinstance(v,str) or not v.strip() for v in ids) or len(set(ids))!=len(ids):raise ValueError('Unique nonempty store/role IDs required')
    nodes=np.asarray(result['store_nodes']);role_store=np.asarray(result['role_store']);crew=np.asarray(store_workforce)
    for value,size in [(nodes,k),(role_store,r),(crew,k)]:
        if value.shape!=(size,) or value.dtype.kind not in 'iu' or np.any(value<0) or np.any(value>np.iinfo(np.intp).max):
            raise ValueError('Explicit integer physical nodes,role stores and workforce assignments required')
    if len(set(nodes.tolist()))!=k or np.any(role_store>=k):raise ValueError('Unambiguous physical store/role assignment required')
    inbound=np.asarray(inbound_hours_per_unit,float);outbound=np.asarray(role_hours_per_unit,float)
    if inbound.shape!=(k,) or outbound.shape!=(r,) or any(not np.isfinite(v).all() or (v<0).any() for v in [inbound,outbound]):
        raise ValueError('Finite nonnegative supplied handling intensities required')
    paid=np.asarray(result['paid'],float);requests=np.asarray(result['requested'],float)
    incoming=np.asarray(inventory['incoming'],float);departures=np.asarray(inventory['departures'],float)
    for value,shape in [(paid,(12,r)),(requests,(12,r)),(incoming,(12,k)),(departures,(12,k))]:
        if value.shape!=shape or not np.isfinite(value).all() or (value<0).any():raise ValueError('Aligned finite nonnegative funded grain required')
    if np.any(paid>requests):raise ValueError('Paid withdrawal exceeds original request')
    per_store=np.zeros_like(departures)
    for role,store in enumerate(role_store):per_store[:,store]+=paid[:,role]
    if np.any(abs(per_store-departures)>1e-10*np.maximum(1,departures)):
        raise ValueError('Role paid grain differs from one physical store departure')
    batches=tuple(batches);funding=NoHoldLedger();checked=[]
    for b in batches:
        if not isinstance(b,NoHoldBatch):raise ValueError('Original funded no-hold receipts required')
        checked.append(funding.record(b.ids,b.origin,b.destination,b.sent,b.delivered,b.departure_bin,b.arrival_bin,
            event_labels=b.charge_labels,charge_allocation=b.charges))
    n=sum(len(b.ids) for b in checked);mapping=np.asarray(consignment_store)
    if mapping.shape!=(n,) or mapping.dtype.kind not in 'iu' or np.any((mapping<0)|(mapping>=k)):
        raise ValueError('Explicit original consignment-to-store assignments required')
    records=[];aggregate=np.zeros_like(incoming);offset=0
    for b in checked:
        for i,consignment in enumerate(b.ids):
            store=int(mapping[offset+i]);month=int(b.arrival_bin[i]);grain=float(b.delivered[i])
            if int(b.destination[i])!=int(nodes[store]):raise ValueError('Consignment endpoint/store mismatch')
            aggregate[month,store]+=grain
            if grain>0:
                records.append(dict(id=f'{namespace}:unload:{consignment}',workforce=int(crew[store]),month=month,role='unloading',
                    hours=grain*float(inbound[store]),grain=grain,rate=float(inbound[store]),store_id=store_ids[store],
                    grain_reference=consignment,kind='unloading',grain_unit=grain_unit,rate_unit=rate_unit))
        offset+=len(b.ids)
    if np.any(abs(aggregate-incoming)>1e-10*np.maximum(1,incoming)):
        raise ValueError('Consignment arrivals do not cover original physical store deposits')
    for month in range(12):
        for role,store in enumerate(role_store):
            grain=float(paid[month,role])
            if grain>0:
                records.append(dict(id=f'{namespace}:withdraw:{month}:{role_ids[role]}',workforce=int(crew[store]),month=month,
                    role=role_ids[role],hours=grain*float(outbound[role]),grain=grain,rate=float(outbound[role]),store_id=store_ids[store],
                    grain_reference=f'paid:{month}:{role_ids[role]}',kind='withdrawal',grain_unit=grain_unit,rate_unit=rate_unit))
    if not all(np.isfinite(row['hours']) for row in records):raise ValueError('Handling-hour products must remain finite')
    ids=[row['id'] for row in records]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate grain-to-task identity')
    return dict(tasks=records,reservation=dict(task_ids=ids,workforce=np.array([row['workforce'] for row in records],int),
        month=np.array([row['month'] for row in records],int),role=[row['role'] for row in records],hours=np.array([row['hours'] for row in records])),
        funding_revalidation_calls=funding.record_calls,grain_unit=grain_unit,rate_unit=rate_unit,
        handling_rate_qualified=False,physical_staffing_qualified=False,grain_dispatch_changed=False)
