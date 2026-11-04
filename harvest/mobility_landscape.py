"""Sample seasonal bases without enlarging a herd's daily resource footprint.

Fine-grid connected land provides travel paths and the stronger fixed-base
control. Sparse candidate bases only restrict the mobile optimizer; they never
pool resources from skipped cells or infer camps, institutions or ethnicity.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components,dijkstra


@dataclass
class Landscape:
    rows: np.ndarray
    columns: np.ndarray
    edges: tuple
    candidates: np.ndarray
    home: int
    travel: np.ndarray
    predecessors: np.ndarray


def sample_landscape(elevation,land,home,*,radius,stride,offsets=((0,0),),cell_km,
                     level_speed_km_day=10.,maximum_move_days=2.,include_radius=0):
    """Keep home-connected fine land, then sample a declared nested lattice.

    Radius is in fine cells; offsets are lattice residues relative to home.
    Shortest paths may use noncandidate land, never its food. Water and
    diagonal corner cutting are prohibited. Positive graph costs are days.
    """
    z=np.asarray(elevation,float);land=np.asarray(land,bool)
    if z.ndim!=2 or z.shape!=land.shape or not np.isfinite(z).all():raise ValueError('Finite matching terrain and land required')
    if any(isinstance(v,bool) or not isinstance(v,(int,np.integer)) for v in [radius,stride,*home]) or radius<1 or stride<1:raise ValueError('Positive integer radius/stride and integer home required')
    if isinstance(include_radius,bool) or not isinstance(include_radius,(int,np.integer)) or not 0<=include_radius<=radius:raise ValueError('Included local radius must be an integer within the landscape')
    if not np.isfinite([cell_km,level_speed_km_day,maximum_move_days]).all() or min(cell_km,level_speed_km_day,maximum_move_days)<=0:raise ValueError('Positive distance and travel scales required')
    cy,cx=home;h,w=land.shape
    if not 0<=cy<h or not 0<=cx<w or not land[cy,cx]:raise ValueError('Home must be traversable')
    offsets=tuple(offsets)
    if not offsets or any(len(o)!=2 or any(isinstance(v,bool) or not isinstance(v,(int,np.integer)) or not 0<=v<stride for v in o) for o in offsets):raise ValueError('Integer lattice residues within the stride required')
    ys,xs=np.mgrid[max(0,cy-radius):min(h,cy+radius+1),max(0,cx-radius):min(w,cx+radius+1)]
    valid=land[ys,xs]&((ys-cy)**2+(xs-cx)**2<=radius**2)
    rows,cols=ys[valid],xs[valid];nodes=rows*w+cols;local={int(p):i for i,p in enumerate(nodes)}
    rr=[];cc=[];dd=[]
    for i,(y,x) in enumerate(zip(rows,cols)):
        for dy,dx in [(a,b) for a in [-1,0,1] for b in [-1,0,1] if a or b]:
            target=(int(y)+dy)*w+int(x)+dx
            if not 0<=int(y)+dy<h or not 0<=int(x)+dx<w or target not in local:continue
            if dy and dx and ((int(y)+dy)*w+int(x) not in local or int(y)*w+int(x)+dx not in local):continue
            j=local[target];distance=cell_km*np.hypot(dy,dx);slope=(z[rows[j],cols[j]]-z[y,x])/(1000*distance)
            speed=level_speed_km_day*np.exp(-3.5*(abs(slope+.05)-.05))
            rr.append(i);cc.append(j);dd.append(distance/speed)
    graph=csr_matrix((dd,(rr,cc)),shape=(len(nodes),len(nodes)))
    _,component=connected_components(graph,directed=False);origin=local[cy*w+cx]
    connected=np.flatnonzero(component==component[origin]);rows,cols=rows[connected],cols[connected]
    graph=graph[connected][:,connected].tocsr();coo=graph.tocoo()
    mask=np.zeros(len(rows),bool)
    for dy,dx in offsets:mask|=((rows-cy)%stride==dy)&((cols-cx)%stride==dx)
    mask|=(rows-cy)**2+(cols-cx)**2<=include_radius**2
    mask|=(rows==cy)&(cols==cx)
    candidates=np.flatnonzero(mask);home_index=int(np.flatnonzero((rows[candidates]==cy)&(cols[candidates]==cx))[0])
    days,parents=dijkstra(graph,directed=True,indices=candidates,return_predecessors=True)
    travel=days[:,candidates];travel[travel>maximum_move_days]=np.inf;np.fill_diagonal(travel,0)
    return Landscape(rows,cols,(coo.row,coo.col,coo.data),candidates,home_index,travel,parents)


def trace_move(landscape,origin,destination):
    """A candidate-to-candidate move as fine-ground node indices."""
    if not np.isfinite(landscape.travel[origin,destination]):raise ValueError('Move is outside the declared budget')
    start=int(landscape.candidates[origin]);end=int(landscape.candidates[destination]);path=[end]
    while path[-1]!=start:
        previous=int(landscape.predecessors[origin,path[-1]])
        if previous<0 or len(path)>len(landscape.rows):raise ValueError('Unreachable or cyclic movement path')
        path.append(previous)
    return path[::-1]
