"""Finite potential-request allocation over competing reachable destinations.

Requests are not residents, food, staff or completed services. The same primitive
can later use supported-resident demand and staffed centres from the joint ledger.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import csr_matrix


@dataclass
class RequestAllocation:
    accessible_potential: np.ndarray
    allocated_requests: np.ndarray
    requests_per_centre: np.ndarray
    origin_allocated: np.ndarray
    origin_unallocated: np.ndarray
    choice_probabilities: csr_matrix


def round_trip_weights(outward,returning,budget_days):
    """Both directed legs must fit the budget; decay uses their mean duration."""
    a,b=np.asarray(outward,float),np.asarray(returning,float)
    if a.shape!=b.shape or not np.isfinite(budget_days) or budget_days<=0:
        raise ValueError('Matching travel arrays and positive finite budget required')
    if np.isnan(a).any() or np.isnan(b).any() or np.any(a<0) or np.any(b<0):
        raise ValueError('Nonnegative travel times or unreachable infinity required')
    good=np.isfinite(a)&np.isfinite(b)&(a<=budget_days)&(b<=budget_days)
    result=np.zeros_like(a)
    result[good]=np.exp(-(a[good]+b[good])/budget_days)
    return result


def allocate_requests(kernel,demand,centre_mass):
    """Allocate each finite origin budget once using normalized destination choice.

    Kernel has destination rows/origin columns. Candidate mass may be fractional
    expected centres, or ones for actual centres. No capacity/fulfilment is implied.
    Overlapping accessible potential is separately named and is NOT additive supply.
    """
    k=csr_matrix(kernel,dtype=float,copy=True)
    d,m=np.asarray(demand,float),np.asarray(centre_mass,float)
    if d.shape!=(k.shape[1],) or m.shape!=(k.shape[0],):raise ValueError('One demand/origin and mass/destination required')
    if any(not np.isfinite(a).all() or np.any(a<0) for a in [k.data,d,m]):
        raise ValueError('Finite nonnegative demand, masses and kernel required')
    weighted=k.multiply(m[:,None]).tocsr();weighted.eliminate_zeros()
    denominator=np.asarray(weighted.sum(axis=0)).ravel()
    probability=weighted.copy()
    # Entrywise division avoids overflow from explicitly forming1/Z for tiny mass.
    probability.data/=denominator[probability.indices]
    allocated=np.asarray(probability@d).ravel()
    per=np.divide(allocated,m,out=np.zeros_like(allocated),where=m>0)
    origin_share=np.asarray(probability.sum(axis=0)).ravel()
    origin_allocated=d*origin_share
    unallocated=np.where(denominator>0,0.,d)
    if not np.isfinite(per).all():raise ValueError('Per-centre request rate exceeds numerical range')
    if np.any(origin_share>1+1e-10) or not np.allclose(origin_allocated+unallocated,d,rtol=1e-10,atol=1e-10):
        raise RuntimeError('Origin request budget not conserved')
    if not np.isclose(allocated.sum()+unallocated.sum(),d.sum(),rtol=1e-10,atol=1e-10):
        raise RuntimeError('Aggregate request budget not conserved')
    return RequestAllocation(np.asarray(k@d).ravel(),allocated,per,origin_allocated,unallocated,probability)
