"""One unsplit herd on a closed seasonal circuit, with a finite feed pack.

This is a conditional dry-matter accounting experiment, not household diet,
livestock nutrition, actual camps, tenure, ethnicity or political control.
Only current-bin growth at the occupied destination can be collected. Unused
growth expires; there is no free standing-forage bank at abandoned patches.
"""
from dataclasses import dataclass
import numpy as np


@dataclass
class Circuit:
    locations: np.ndarray
    reserves: np.ndarray
    travel_days: np.ndarray
    collected: np.ndarray
    consumed: np.ndarray
    unmet: np.ndarray
    discarded: np.ndarray
    objective_unmet: float
    feed_ledger_residual: float


def seasonal_circuit(supply, travel_days, home, *, daily_need, reserve_days=7,
                     reserve_quantum_days=1., allowed=None, year_days=365.):
    """Globally optimal closed path ON THE DECLARED finite state graph.

    State = one location and a discrete carried-feed reserve. Each edge moves
    at the start of the bin. Feed already carried pays transit meals first;
    destination growth cannot feed the past. Deficits are recorded, not death.
    Then destination food supplies meals and next reserve. No hoarding while
    destination meals are unmet. Start/end location AND stock are identical.
    Lexicographic objective: least unmet DM, then least travel, then smallest
    initial reserve. Water/permission exclusions are supplied scenarios.
    """
    supply=np.asarray(supply,float);travel=np.asarray(travel_days,float)
    if supply.ndim!=2 or supply.shape[0]!=12 or not supply.shape[1]:raise ValueError('Twelve bins and nonempty patches required')
    T,N=supply.shape
    if travel.shape!=(N,N) or np.isnan(travel).any() or np.any(travel<0) or not np.all(np.diag(travel)==0):raise ValueError('Nonnegative travel matrix with zero self moves required')
    if not np.isfinite(supply).all() or np.any(supply<0):raise ValueError('Finite nonnegative forage required')
    if isinstance(home,bool) or not isinstance(home,(int,np.integer)) or not 0<=home<N:raise ValueError('Integer home patch required')
    if not np.isfinite([daily_need,reserve_days,reserve_quantum_days,year_days]).all() or daily_need<=0 or reserve_days<0 or reserve_quantum_days<=0 or year_days<=0:raise ValueError('Valid intake, year and reserve required')
    ratio=reserve_days/reserve_quantum_days
    if not np.isclose(ratio,round(ratio)):raise ValueError('Reserve capacity must be a multiple of its quantum')
    levels=np.arange(int(round(ratio))+1)*reserve_quantum_days*daily_need;R=len(levels);length=year_days/T;demand=daily_need*length
    if reserve_days>=length:raise ValueError('This finite pack experiment requires a reserve shorter than one bin')
    allowed=np.ones((T,N),bool) if allowed is None else np.broadcast_to(np.asarray(allowed,bool),(T,N))
    if not allowed[-1,home]:return None
    origins,destinations=np.where(np.isfinite(travel)&(travel<length))
    duration=travel[origins,destinations];trip=duration*daily_need
    # Enumerate transitions once per monthly supply. The endpoint pack is
    # quantized DOWN by requiring actual food for the selected reserve level.
    starts=np.repeat(origins,R*R);ends=np.repeat(destinations,R*R)
    a=np.tile(np.repeat(np.arange(R),R),len(origins));b=np.tile(np.arange(R),len(origins)*R)
    days=np.repeat(duration,R*R);tripmeal=days*daily_need
    remaining=np.maximum(levels[a]-tripmeal,0);fed_trip=np.minimum(levels[a],tripmeal)
    src=starts*R+a;dst=ends*R+b;size=N*R;transitions=[]
    for t in range(T):
        available=remaining+supply[t,ends]
        target=levels[b];fed_here=np.minimum(demand-tripmeal,np.maximum(available-target,0))
        shortage_here=demand-tripmeal-fed_here
        valid=(available+1e-10>=target)&((shortage_here<1e-9)|(b==0))&allowed[t,ends]
        missing=np.maximum(demand-fed_trip-fed_here,0)
        transitions.append((valid,missing,fed_here))
    best=None
    for startlevel in range(R):
        cost=np.full(size,np.inf);distance=cost.copy();cost[home*R+startlevel]=0;distance[home*R+startlevel]=0;history=[]
        for t,(valid,missing,_) in enumerate(transitions):
            score=cost[src]+missing;length_score=distance[src]+days
            good=np.flatnonzero(valid&np.isfinite(score))
            # Exact cost first, travel second, deterministic transition last.
            order=good[np.lexsort((good,length_score[good],score[good],dst[good]))]
            first=np.r_[True,dst[order][1:]!=dst[order][:-1]] if len(order) else np.zeros(0,bool)
            pick=order[first];pre=np.full(size,-1,np.int32)
            nxt=np.full(size,np.inf);nd=nxt.copy();nxt[dst[pick]]=score[pick];nd[dst[pick]]=length_score[pick];pre[dst[pick]]=pick
            history.append(pre);cost,distance=nxt,nd
        final=home*R+startlevel;key=(cost[final],distance[final],startlevel)
        if not np.isfinite(key[0]) or (best is not None and key>=best[0]):continue
        state=final;path=[]
        for t in range(T-1,-1,-1):
            edge=int(history[t][state]);path.append(edge);state=int(src[edge])
        path=path[::-1];best=(key,path,startlevel)
    if best is None:return None
    key,path,initial=best;path=np.asarray(path)
    places=ends[path];reserve=np.r_[levels[initial],levels[b[path]]];tripdays=days[path]
    here=np.array([transitions[t][2][edge] for t,edge in enumerate(path)])
    eaten=fed_trip[path]+here;unmet=np.maximum(demand-eaten,0)
    collected=here+reserve[1:]-remaining[path]
    if np.any(collected< -1e-8) or np.any(collected>supply[np.arange(T),places]+1e-8):raise RuntimeError('Forage used twice or borrowed from the future')
    collected=np.maximum(collected,0)
    discarded=supply[np.arange(T),places]-collected
    residual=float(reserve[0]+collected.sum()-eaten.sum()-reserve[-1])
    tolerance=1e-8*max(1.,demand*T)
    if abs(residual)>tolerance or not np.isclose(unmet.sum(),key[0],atol=tolerance):raise RuntimeError('Closed herd/feed ledger failed')
    return Circuit(places,reserve,tripdays,collected,eaten,unmet,discarded,float(key[0]),residual)
