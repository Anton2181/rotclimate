"""Time-expanded, food-conserving provisioning with explicit scenario inputs.

Directed capacitated flows with transit times follow standard network-flow
formulations (Ford & Fulkerson 1958, doi:10.1287/opre.6.3.419). Storage/losses,
periodic food ledgers and consumption priorities are explicit adaptations.
This is feasibility/cost accounting, not prices, town sizes or gravity trade.
"""
from dataclasses import dataclass
from numbers import Integral

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix,vstack


@dataclass(frozen=True)
class FoodRoute:
    origin: int
    destination: int
    delay_steps: int
    capacity: object  # food energy departing per step; scalar or time series
    cost: float
    retention: float = 1.


@dataclass
class Provisioning:
    stocks: np.ndarray
    shipped: np.ndarray
    arrivals: np.ndarray
    consumed: np.ndarray
    unmet: np.ndarray
    spilled: np.ndarray
    storage_loss: float
    transport_loss: float
    transport_cost: float
    cell_ledger_residual: np.ndarray
    annual_ledger_residual: float
    priority_consumption: dict


def provision_food(harvest,demand,routes,*,storage_capacity,priority,
                   storage_survival=1.,holding_cost=1e-6):
    """Repeatable food provisioning over a supplied year and directed routes.

    Food energy units are shared by harvest, meals, stocks and shipments.
    Priorities are optimized in increasing integer order (e.g. rural before
    urban), then freight/holding costs are minimized at those consumption
    totals. Priorities are a policy scenario, not a historical universal.
    Costs never consume food; physical losses require explicit retentions.
    Stocks AND in-transit flows repeat over the year: no hidden initial grain.
    """
    harvest,demand=np.broadcast_arrays(np.asarray(harvest,float),np.asarray(demand,float))
    if harvest.ndim!=2 or not all(harvest.shape) or not all(np.isfinite(a).all() for a in [harvest,demand]) or np.any(harvest<0) or np.any(demand<0):
        raise ValueError('Finite nonnegative time-by-node food fields required')
    T,N=harvest.shape;routes=tuple(routes);E=len(routes)
    cap=np.broadcast_to(np.asarray(storage_capacity,float),(T,N))
    survival=np.broadcast_to(np.asarray(storage_survival,float),(T,N))
    priorities=np.asarray(priority)
    if priorities.shape!=(N,) or priorities.dtype.kind not in 'iu' or not np.isfinite(holding_cost) or holding_cost<=0:
        raise ValueError('Integer node priorities and positive holding cost required')
    if not np.isfinite(cap).all() or np.any(cap<0) or not np.isfinite(survival).all() or np.any((survival<0)|(survival>1)):
        raise ValueError('Finite capacities and storage survival in [0,1] required')
    capacities=[]
    for r in routes:
        if any(isinstance(v,bool) or not isinstance(v,Integral) for v in [r.origin,r.destination,r.delay_steps]):
            raise ValueError('Route endpoints/delay must be integers')
        if not 0<=r.origin<N or not 0<=r.destination<N or r.origin==r.destination or not 0<=r.delay_steps<T:
            raise ValueError('Invalid route endpoints or transit delay')
        if not np.isfinite(r.cost) or r.cost<0 or not np.isfinite(r.retention) or not 0<=r.retention<=1:
            raise ValueError('Finite nonnegative cost and retention in [0,1] required')
        c=np.broadcast_to(np.asarray(r.capacity,float),(T,))
        if not np.isfinite(c).all() or np.any(c<0):raise ValueError('Finite nonnegative route capacity required')
        capacities.append(c)
    # Variables: end-step stocks, served food, spills, departing shipments.
    M=T*N;F=T*E;size=3*M+F
    row=[];column=[];value=[]
    def add(r,c,v):row.append(r);column.append(c);value.append(v)
    for t in range(T):
        for n in range(N):
            k=t*N+n
            add(k,k,1.);add(k,((t-1)%T)*N+n,-survival[t,n])
            add(k,M+k,1.);add(k,2*M+k,1.)
        for e,r in enumerate(routes):
            x=3*M+t*E+e
            add(t*N+r.origin,x,1.)
            add(((t+r.delay_steps)%T)*N+r.destination,x,-r.retention)
    equality=coo_matrix((value,(row,column)),shape=(M,size)).tocsr();rhs=harvest.ravel().copy()
    flowcap=np.stack(capacities,axis=1).ravel() if E else np.zeros(0)
    bounds=list(zip(np.zeros(size),np.r_[cap.ravel(),demand.ravel(),np.full(M,np.inf),flowcap]))
    priority_totals={}
    for p in sorted(np.unique(priorities)):
        meals=np.array([M+t*N+n for t in range(T) for n in range(N) if priorities[n]==p])
        objective=np.zeros(size);objective[meals]=-1
        solution=linprog(objective,A_eq=equality,b_eq=rhs,bounds=bounds,method='highs')
        if not solution.success:raise RuntimeError('Food-priority optimization failed: '+solution.message)
        total=float(solution.x[meals].sum());priority_totals[int(p)]=total
        fix=coo_matrix((np.ones(len(meals)),(np.zeros(len(meals),int),meals)),shape=(1,size)).tocsr()
        equality=vstack([equality,fix],format='csr');rhs=np.r_[rhs,total]
    objective=np.r_[np.full(M,holding_cost),np.zeros(2*M),np.tile([r.cost for r in routes],T)]
    solution=linprog(objective,A_eq=equality,b_eq=rhs,bounds=bounds,method='highs')
    if not solution.success:raise RuntimeError('Food-cost optimization failed: '+solution.message)
    stocks=solution.x[:M].reshape(T,N);consumed=solution.x[M:2*M].reshape(T,N)
    spilled=solution.x[2*M:3*M].reshape(T,N);shipped=solution.x[3*M:].reshape(T,E)
    previous=np.roll(stocks,1,axis=0);arrivals=np.zeros_like(harvest);departures=arrivals.copy()
    transport_loss=0.
    for e,r in enumerate(routes):
        arrivals[:,r.destination]+=np.roll(shipped[:,e],r.delay_steps)*r.retention
        departures[:,r.origin]+=shipped[:,e]
        transport_loss+=float(shipped[:,e].sum()*(1-r.retention))
    loss=float(np.sum(previous*(1-survival)))
    ledger=previous*survival+harvest+arrivals-departures-consumed-spilled-stocks
    annual=float(harvest.sum()-consumed.sum()-spilled.sum()-loss-transport_loss)
    tolerance=1e-7*max(1.,float(harvest.sum()),float(demand.sum()))
    if np.max(np.abs(ledger))>tolerance or abs(annual)>tolerance or np.min(demand-consumed)<-tolerance:
        raise RuntimeError('Provisioning food ledger failed')
    return Provisioning(stocks,shipped,arrivals,consumed,np.maximum(demand-consumed,0),spilled,
        loss,transport_loss,float(np.sum(shipped*np.asarray([r.cost for r in routes]))),ledger,annual,priority_totals)
