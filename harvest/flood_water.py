"""Conserved water delivery on a drainage forest; no irrigation-area inference.

Inputs are volumes per month, not discharges or above-mean-flow shares.
Upstream demands are served before downstream demands. Crop selection,
floodplain access, storage and travel times are supplied by later field models.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _route(source, demand, order, receiver, efficiency):
    available=source.copy();delivered=np.zeros_like(source);loss=np.zeros_like(source)
    downstream=np.zeros_like(source);outlet=np.zeros_like(source)
    for k in range(order.size-1,-1,-1):
        c=order[k];r=receiver[c]
        for month in range(12):
            # Gross withdrawal can never exceed water arriving at this node.
            gross=min(available[month,c],demand[month,c]/efficiency[c])
            delivered[month,c]=gross*efficiency[c]
            loss[month,c]=gross-delivered[month,c]
            remaining=available[month,c]-gross
            downstream[month,c]=remaining
            if r>=0:available[month,r]+=remaining
            else:outlet[month,c]=remaining
    return available,delivered,loss,downstream,outlet


def route_water_budget(source_m3, demand_m3, order, receiver, *, efficiency=1.):
    """Route twelve monthly volumes through an outlet-first drainage order.

    source_m3/demand_m3: finite nonnegative (12, nodes) arrays. Demands mean
    useful delivered water. efficiency: scalar or (nodes,), in (0,1]; no fitted
    conveyance efficiency is implied by the loss-free accounting default.

    receiver: integer (nodes,), -1 for outlets; order: distinct active nodes,
    with each downstream receiver BEFORE its upstream node. Inactive nodes
    must have zero source/demand and receiver=-1. Cycles/partial trees are refused.

    Results preserve monthly source = useful delivery + loss + outlet volume.
    'available' and 'downstream' are internal node fluxes and must NOT be summed
    across nodes as water supplies. There is no carry between months, river
    travel delay or return flow. This primitive is not a field irrigation rule.
    """
    source=np.asarray(source_m3,dtype=float);demand=np.asarray(demand_m3,dtype=float)
    if source.ndim!=2 or source.shape[0]!=12 or demand.shape!=source.shape:
        raise ValueError('Source and useful demand require matching (12,nodes) volumes')
    if not np.isfinite(source).all() or not np.isfinite(demand).all() or np.any(source<0) or np.any(demand<0):
        raise ValueError('Water volumes must be finite and nonnegative')
    n=source.shape[1];order=np.asarray(order);receiver=np.asarray(receiver)
    if order.ndim!=1 or receiver.shape!=(n,) or order.dtype.kind not in 'iu' or receiver.dtype.kind not in 'iu':
        raise ValueError('Order and receivers require one-dimensional integer arrays')
    if np.any(order>=n) or np.any(order<0) or len(np.unique(order))!=len(order):
        raise ValueError('Order must contain distinct valid node indices')
    if np.any(receiver>=n) or np.any(receiver< -1):raise ValueError('Invalid receiver index')
    rank=np.full(n,-1,dtype=np.int64);rank[order]=np.arange(len(order))
    if np.any(source[:,rank<0]!=0) or np.any(demand[:,rank<0]!=0) or np.any(receiver[rank<0]!=-1):
        raise ValueError('Inactive nodes cannot supply, request or route water')
    linked=receiver>=0
    if np.any(rank[receiver[linked]]<0) or np.any(rank[receiver[linked]]>=rank[linked]):
        raise ValueError('Receiver must precede its source in outlet-first order')
    efficiency=np.broadcast_to(np.asarray(efficiency,dtype=float),(n,)).copy()
    if not np.isfinite(efficiency).all() or np.any(efficiency<=0) or np.any(efficiency>1):
        raise ValueError('Delivery efficiency must be finite and in (0,1]')
    with np.errstate(over='ignore'):
        total=source.sum(axis=1)
    if not np.isfinite(total).all():raise ValueError('Monthly source total overflows')
    available,delivered,loss,downstream,outlet=_route(source,demand,order.astype(np.int64),receiver.astype(np.int64),efficiency)
    if not all(np.isfinite(v).all() for v in (available,delivered,loss,downstream,outlet)):
        raise ValueError('Routed volume overflow')
    return dict(available_m3=available,delivered_m3=delivered,delivery_loss_m3=loss,
                downstream_m3=downstream,outlet_m3=outlet,unmet_m3=np.maximum(demand-delivered,0.))
