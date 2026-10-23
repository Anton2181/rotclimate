"""Mass-conserving census allocation and directed Tobler walking access."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra


def allocate(capacity, attraction, requested):
    """p_i=min(C_i, lambda*C_i*a_i); return people and any unmet budget."""
    c, w = np.broadcast_arrays(np.asarray(capacity, float), np.asarray(attraction, float))
    if not np.isfinite(requested) or requested < 0 or not np.isfinite(c).all() or not np.isfinite(w).all():
        raise ValueError('Population, capacities and weights must be finite and nonnegative')
    if (c < 0).any() or (w < 0).any():
        raise ValueError('Negative capacity or attraction')
    eligible = (c > 0) & (w > 0)
    ceiling = float(c[eligible].sum()); target = min(float(requested), ceiling)
    people = np.zeros(c.shape)
    if target >= ceiling:
        people[eligible] = c[eligible]
    elif target > 0:
        lo, hi = 0., 1 / float(w[eligible].min())
        for _ in range(50):
            mid = (lo + hi) / 2
            if np.minimum(c, mid*c*w).sum() < target: lo = mid
            else: hi = mid
        people = np.minimum(c, ((lo+hi)/2)*c*w)
    return people, max(0., float(requested)-float(people.sum()))


def walking_speed(slope, off_path=.6):
    return 6 * off_path * np.exp(-3.5*np.abs(np.asarray(slope)+.05))


def market_access(elevation, land, cell_km, places, off_path=.6):
    """Walking hours TO a market, not FROM it; no sea or diagonal corner cuts.

    places contains (row, column) indices. Unreachable land has time -1 and
    market ID 0. IDs otherwise refer to the first named place at that cell + 1.
    """
    z=np.asarray(elevation,float);land=np.asarray(land,bool)
    if z.shape!=land.shape or z.ndim!=2 or cell_km<=0 or not np.isfinite(z).all():
        raise ValueError('Invalid walking terrain')
    h,w=z.shape;nodes=np.arange(z.size).reshape(z.shape)
    rows=[];cols=[];cost=[]
    for dy,dx in [(a,b) for a in [-1,0,1] for b in [-1,0,1] if a or b]:
        y0,y1=max(0,-dy),min(h,h-dy);x0,x1=max(0,-dx),min(w,w-dx)
        src=np.s_[y0:y1,x0:x1];dst=np.s_[y0+dy:y1+dy,x0+dx:x1+dx]
        valid=land[src]&land[dst]
        if dy and dx:
            valid &= land[y0:y1,x0+dx:x1+dx]&land[y0+dy:y1+dy,x0:x1]
        distance=cell_km*np.hypot(dx,dy)
        slope=(z[dst]-z[src])/(distance*1000)
        rows.append(nodes[src][valid]);cols.append(nodes[dst][valid])
        cost.append(distance/np.maximum(walking_speed(slope,off_path),1e-12)[valid])
    graph=coo_matrix((np.concatenate(cost),(np.concatenate(rows),np.concatenate(cols))),shape=(z.size,z.size)).tocsr()
    source_ids={}
    for i,(y,x) in enumerate(places):
        if 0<=y<h and 0<=x<w and land[y,x]: source_ids.setdefault(int(nodes[y,x]),i+1)
    hours=np.full(z.size,-1.);market=np.zeros(z.size,np.uint16)
    if source_ids:
        # Reverse the directed edges: shortest market->cell on G.T is cell->market on G.
        distance,_,sources=dijkstra(graph.T.tocsr(),directed=True,indices=list(source_ids),
                                   min_only=True,return_predecessors=True)
        reached=np.isfinite(distance)&land.ravel()
        hours[reached]=distance[reached]
        lookup=np.zeros(z.size,np.uint16)
        for node,number in source_ids.items():lookup[node]=number
        market[reached]=lookup[sources[reached]]
    return hours.reshape(z.shape),market.reshape(z.shape)


def attraction_fields(elevation, land, water_distance, hours, cell_km, spec):
    """Positive weights allow remote land; suitability does not create people."""
    z=np.asarray(elevation,float);land=np.asarray(land,bool)
    padded=np.pad(z,1,mode='edge');mask=np.pad(land,1,constant_values=False)
    slopes=[]
    for a,b in [(padded[1:-1,2:],mask[1:-1,2:]),(padded[1:-1,:-2],mask[1:-1,:-2]),
                (padded[2:,1:-1],mask[2:,1:-1]),(padded[:-2,1:-1],mask[:-2,1:-1])]:
        slopes.append(np.where(b,np.abs(a-z)/(cell_km*1000),0))
    slope=np.maximum.reduce(slopes)
    water=spec['water_weight_floor']+(1-spec['water_weight_floor'])*np.exp(-water_distance/spec['water_distance_scale_km'])
    rural=np.maximum(spec['minimum_attraction'],water*np.exp(-slope/spec['slope_scale']))
    access=np.where(hours>=0,np.exp(-np.maximum(hours,0)/spec['market_time_scale_hours']),0)
    market=rural*(spec['market_weight_floor']+(1-spec['market_weight_floor'])*access)
    return np.where(land,rural,0),np.where(land,market,0)
