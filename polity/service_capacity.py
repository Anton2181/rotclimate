"""Shared staff-hour limits on already allocated potential service requests.

Single-pass proportional rationing, not queues, rerouting or a maximum-flow
solution. Resource quantities belong to one caller-defined accounting period.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import csr_matrix
from polity.settlement_support import SettlementPlan


@dataclass
class StaffHourBudget:
    gross_hours: np.ndarray
    committed_hours: np.ndarray
    available_hours: np.ndarray


@dataclass
class ServiceFulfilment:
    provider_requests: np.ndarray
    origin_served: np.ndarray
    origin_unmet: np.ndarray
    origin_unreachable: np.ndarray
    origin_capacity_unmet: np.ndarray
    provider_hours_by_channel: np.ndarray
    unused_provider_hours: np.ndarray
    fulfilled_flows: list


def supported_staff_hours(plan,*,hours_per_staff,committed_hours):
    """Reserve other duties before services; food supports the same staff once.

    Both work inputs are explicit. This does not infer that institutional
    residents are all workers or that existing patrol duties consume no hours.
    The caller must supply a compatible available-work envelope and commitments.
    """
    if not isinstance(plan,SettlementPlan):raise ValueError('A food-supported SettlementPlan is required')
    staff=np.asarray(plan.institutional_people,float);civil=np.asarray(plan.civilian_people,float)
    total=np.asarray(plan.total_people,float);ceiling=np.asarray(plan.food_ceiling_people,float)
    active=np.asarray(plan.institutional_active,bool)
    if staff.ndim!=1 or any(a.shape!=staff.shape for a in [civil,total,ceiling,active]):raise ValueError('Matching resident/food arrays required')
    if any(not np.isfinite(a).all() or np.any(a<0) for a in [staff,civil,total,ceiling]):raise ValueError('Finite nonnegative supported residents required')
    if not np.allclose(total,civil+staff,rtol=1e-10,atol=1e-8) or np.any(total>ceiling+1e-7*np.maximum(1,ceiling)) or np.any((staff>0)&~active):
        raise ValueError('Staff must belong to the same feasible resident/food ledger')
    need=np.asarray(plan.food_year.needed,float);unmet=np.asarray(plan.food_year.unmet,float)
    if need.shape!=staff.shape or unmet.shape!=staff.shape or any(not np.isfinite(a).all() or np.any(a<0) for a in [need,unmet]) or np.any(unmet>1e-6*np.maximum(1,need)):
        raise ValueError('Repeating food year must support the resident cohort')
    try:
        envelope=np.broadcast_to(np.asarray(hours_per_staff,float),staff.shape)
        committed=np.broadcast_to(np.asarray(committed_hours,float),staff.shape)
    except ValueError as error:raise ValueError('One work envelope and commitment per provider required') from error
    if any(not np.isfinite(a).all() or np.any(a<0) for a in [envelope,committed]):raise ValueError('Finite nonnegative work envelope/commitments required')
    with np.errstate(over='ignore'):gross=staff*envelope
    if not np.isfinite(gross).all() or np.any(committed>gross):raise ValueError('Committed work exceeds the supported staff-hour envelope')
    return StaffHourBudget(gross,committed.copy(),gross-committed)


def fulfil_services(allocations,*,staff_hours,hours_per_request):
    """Ration all channels together at each provider, leaving deficits explicit.

    Input choices come from allocate_requests. A common per-provider fulfilment
    factor rations requested HOURS, so heterogeneous service costs share one
    budget. Unmet requests stay unmet; unused capacity elsewhere is not rerouted.
    No people, food, staffing, political actors or route probabilities change.
    """
    allocations=list(allocations)
    if not allocations:raise ValueError('At least one potential-request allocation required')
    shape=allocations[0].choice_probabilities.shape;channels=len(allocations)
    budget=np.asarray(staff_hours,float)
    if budget.shape!=(shape[0],) or not np.isfinite(budget).all() or np.any(budget<0):raise ValueError('One finite nonnegative hour budget per provider required')
    try:cost=np.broadcast_to(np.asarray(hours_per_request,float),(channels,shape[0]))
    except ValueError as error:raise ValueError('Request hours must match channel/provider dimensions') from error
    if not np.isfinite(cost).all() or np.any(cost<=0):raise ValueError('Finite positive hours per request required')
    demands=[];flows=[];unreachable=[]
    for allocation in allocations:
        p=csr_matrix(allocation.choice_probabilities,dtype=float,copy=True)
        d=np.asarray(allocation.origin_allocated,float)+np.asarray(allocation.origin_unallocated,float)
        if p.shape!=shape or d.shape!=(shape[1],) or any(not np.isfinite(a).all() or np.any(a<0) for a in [p.data,d]):raise ValueError('Matching finite request choices/demands required')
        shares=np.asarray(p.sum(axis=0)).ravel();flow=p.multiply(d[None,:]).tocsr()
        if np.any(shares>1+1e-10) or not np.allclose(d*shares,allocation.origin_allocated,rtol=1e-10,atol=1e-8) or not np.allclose(np.asarray(flow.sum(axis=1)).ravel(),allocation.allocated_requests,rtol=1e-10,atol=1e-8):
            raise ValueError('Potential-request allocation does not conserve its origin budget')
        if not np.isfinite(flow.data).all():raise ValueError('Request flow exceeds numerical range')
        demands.append(d);flows.append(flow);unreachable.append(np.maximum(0,d*(1-shares)))
    demand=np.stack(demands);unreachable=np.stack(unreachable)
    counts=np.stack([np.asarray(f.sum(axis=1)).ravel() for f in flows])
    with np.errstate(over='ignore'):requested_hours=counts*cost;work=requested_hours.sum(axis=0)
    if not np.isfinite(work).all() or np.any((counts>0)&(requested_hours==0)):raise ValueError('Requested work exceeds numerical range')
    fraction=np.divide(budget,work,out=np.ones_like(work),where=work>budget)
    fulfilled=[f.multiply(fraction[:,None]).tocsr() for f in flows]
    provider=np.stack([np.asarray(f.sum(axis=1)).ravel() for f in fulfilled])
    served=np.stack([np.asarray(f.sum(axis=0)).ravel() for f in fulfilled])
    unmet=np.maximum(0,demand-served);capacity_unmet=np.maximum(0,unmet-unreachable)
    used=provider*cost;remaining=np.maximum(0,budget-used.sum(axis=0))
    if np.any(used.sum(axis=0)>budget+1e-9*np.maximum(1,budget)) or not np.allclose(served+unreachable+capacity_unmet,demand,rtol=1e-10,atol=1e-8):
        raise RuntimeError('Service work/request budget not conserved')
    return ServiceFulfilment(provider,served,unmet,unreachable,capacity_unmet,used,remaining,fulfilled)
