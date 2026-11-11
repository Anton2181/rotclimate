"""Bounded directed walking access for potential-service hypotheses."""
import numpy as np
from scipy.sparse import coo_matrix,csr_matrix
from scipy.sparse.csgraph import dijkstra

from .control import foot_edges


def walking_graph(elevation,land,road,cell_km):
    """Dry annual walking scenario, no boats/ferries or political travel mask."""
    z,mask=np.asarray(elevation,float),np.asarray(land,bool)
    roads=np.asarray(road,bool)
    if z.ndim!=2 or z.shape!=mask.shape or roads.shape!=mask.shape or not np.isfinite(z).all():
        raise ValueError('Matching finite elevation and grid masks required')
    if not np.isfinite(cell_km) or cell_km<=0:raise ValueError('Positive cell size required')
    rows,cols,days=foot_edges(z,mask,roads,np.ones_like(z),cell_km)
    if not np.isfinite(days).all() or np.any(days<=0):raise ValueError('Finite positive walking edges required')
    h,w=z.shape;r0,c0=np.divmod(rows,w);r1,c1=np.divmod(cols,w)
    speed=np.hypot(r1-r0,c1-c0)*cell_km/days
    graph=coo_matrix((days,(rows,cols)),shape=(z.size,z.size)).tocsr()
    return graph,float(speed.max()) if len(speed) else 0.


def bounded_roundtrips(graph,centres,origins,maximum_days,batch_size=64):
    """Sparse reachable pairs: both directed shortest legs must fit the limit."""
    g=csr_matrix(graph,dtype=float);centres,origins=np.asarray(centres,int),np.asarray(origins,int)
    if g.shape[0]!=g.shape[1] or not np.isfinite(g.data).all() or np.any(g.data<0):
        raise ValueError('Square nonnegative finite travel graph required')
    if not np.isfinite(maximum_days) or maximum_days<=0 or batch_size<1:raise ValueError('Positive reach and batch size required')
    for ids in [centres,origins]:
        if ids.ndim!=1 or len(np.unique(ids))!=len(ids) or np.any(ids<0) or np.any(ids>=g.shape[0]):
            raise ValueError('Distinct valid grid nodes required')
    reverse=g.T.tocsr();rows=[];cols=[];out=[];back=[]
    for first in range(0,len(centres),batch_size):
        roots=centres[first:first+batch_size]
        a=dijkstra(g,directed=True,indices=roots,limit=maximum_days)[:,origins]
        b=dijkstra(reverse,directed=True,indices=roots,limit=maximum_days)[:,origins]
        rr,cc=np.nonzero(np.isfinite(a)&np.isfinite(b))
        rows.append(rr+first);cols.append(cc);out.append(a[rr,cc]);back.append(b[rr,cc])
    if not rows:return tuple(np.array([],dtype=int if k<2 else float) for k in range(4))
    return np.concatenate(rows),np.concatenate(cols),np.concatenate(out),np.concatenate(back)
