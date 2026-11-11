"""Core travel on explicitly known geography; missing support is not cheap sea."""
from dataclasses import dataclass
from numbers import Integral
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from rotclimate import biomes

FOREST_SHARE={1:.5,3:1.,4:1.,7:1.,9:1.}


@dataclass(frozen=True)
class CoreTravel:
    distance_km: np.ndarray
    covered: np.ndarray
    connected: np.ndarray
    coarse_nodes: int
    coarse_edges: int
    source_nodes: tuple[int,...]


def travel_distance_supported(z,cores,*,covered=None,forest_cost=2.,sea_cost=1.,relief_cost=1.,coarsen=3):
    """Retain the old cost/8-neighbour geometry, excluding unsupported nodes.

    A coarse node requires all constituent source cells. Distances are shortest
    paths within known support, not an assertion of a globally complete optimum.
    Unsupported and disconnected cells retain infinity and separate flags.
    """
    lat,lon=np.asarray(z['lat'],float),np.asarray(z['lon'],float)
    land=np.asarray(z['land'],bool)
    if lat.ndim!=1 or lon.ndim!=1 or land.shape!=(len(lat),len(lon)):
        raise ValueError('Expected regular latitude/longitude source axes and matching land')
    if not np.isfinite(lat).all() or not np.isfinite(lon).all() or len(lat)<2 or len(lon)<2:
        raise ValueError('Finite source axes with at least two cells required')
    if not np.all(np.diff(lat)<0) or not np.all(np.diff(lon)>0) or not np.allclose(np.diff(lat),lat[1]-lat[0]) or not np.allclose(np.diff(lon),lon[1]-lon[0]):
        raise ValueError('Regular descending latitude/ascending longitude required')
    if isinstance(coarsen,bool) or not isinstance(coarsen,Integral) or coarsen<1:
        raise ValueError('Positive integer coarsening required')
    if not all(np.isfinite(v) for v in [forest_cost,sea_cost,relief_cost]) or forest_cost<=0 or sea_cost<=0 or relief_cost<0:
        raise ValueError('Positive travel costs and nonnegative relief cost required')
    covered=np.ones(land.shape,bool) if covered is None else np.asarray(covered,bool)
    if covered.shape!=land.shape:raise ValueError('Source support must match the land grid')
    # Preserve source precision: the frozen kernel averages float32 relief in
    # float32 before combining it with the float64 land fractions.
    fields={k:np.asarray(z[k]) for k in ['T_ann','P_ann','relief']}
    if any(v.shape!=land.shape or not np.isfinite(v[land&covered]).all() for v in fields.values()):
        raise ValueError('Known land needs finite climate/relief fields')
    kind=biomes.classify(np.nan_to_num(fields['T_ann']),np.nan_to_num(fields['P_ann']),land)
    forest=np.zeros(land.shape)
    for code,share in FOREST_SHARE.items():forest[kind==code]=share
    relief=np.clip(np.nan_to_num(fields['relief']),0,3000)/1000.
    c=int(coarsen);ny,nx=land.shape[0]//c,land.shape[1]//c
    if min(ny,nx)<2:raise ValueError('At least two coarse cells on each axis required')
    def co(a):return a[:ny*c,:nx*c].reshape(ny,c,nx,c).mean((1,3))
    valid=co(covered.astype(float))==1.;lf=co(land.astype(float))
    cost=np.where(lf>=.5,1.+(forest_cost-1.)*co(forest*land)/np.maximum(lf,1e-9)
        +relief_cost*co(relief*land)/np.maximum(lf,1e-9),sea_cost)
    clat=lat[:ny*c].reshape(ny,c).mean(1);clon=lon[:nx*c].reshape(nx,c).mean(1)
    dy_km=abs(clat[1]-clat[0])*111.32;idx=np.arange(ny*nx).reshape(ny,nx)
    rows=[];cols=[];weights=[]
    for di,dj in [(0,1),(1,0),(1,1),(1,-1)]:
        a=idx[max(0,-di):ny-max(0,di),max(0,-dj):nx-max(0,dj)]
        b=idx[max(0,di):ny-max(0,-di) or None,max(0,dj):nx-max(0,-dj) or None]
        ia=a//nx
        dx_km=abs(clon[1]-clon[0])*111.32*np.cos(np.radians(.5*(clat[ia]+clat[b//nx])))
        distance=np.hypot(di*dy_km,dj*dx_km)
        wt=.5*(cost.ravel()[a]+cost.ravel()[b])*distance
        known=valid.ravel()[a]&valid.ravel()[b]
        rows.extend([a[known],b[known]]);cols.extend([b[known],a[known]]);weights.extend([wt[known],wt[known]])
    graph=coo_matrix((np.concatenate(weights),(np.concatenate(rows),np.concatenate(cols))),shape=(ny*nx,ny*nx)).tocsr()
    sources=[]
    for name,(la,lo) in cores.items():
        if not (lat[-1]-.5*abs(lat[1]-lat[0])<=la<=lat[0]+.5*abs(lat[1]-lat[0]) and
                lon[0]-.5*abs(lon[1]-lon[0])<=lo<=lon[-1]+.5*abs(lon[1]-lon[0])):
            raise ValueError('Core lies outside known source axes: '+str(name))
        row,col=int(np.argmin(np.abs(clat-la))),int(np.argmin(np.abs(clon-lo)))
        if not valid[row,col]:raise ValueError('Core snaps to unsupported geography: '+str(name))
        sources.append(row*nx+col)
    if not sources:raise ValueError('At least one supported core required')
    coarse=dijkstra(graph,indices=sources,min_only=True).reshape(ny,nx)
    full=np.repeat(np.repeat(coarse,c,0),c,1)
    support=np.repeat(np.repeat(valid,c,0),c,1)
    # Preserve the old edge repetition for complete source remainders.
    out=np.full(land.shape,np.inf);available=np.zeros(land.shape,bool)
    out[:ny*c,:nx*c]=full;available[:ny*c,:nx*c]=support
    out[ny*c:,:]=out[ny*c-1:ny*c,:];out[:,nx*c:]=out[:,nx*c-1:nx*c]
    available[ny*c:,:]=available[ny*c-1:ny*c,:];available[:,nx*c:]=available[:,nx*c-1:nx*c]
    available&=covered;out[~available]=np.inf
    return CoreTravel(out,available,np.isfinite(out),int(valid.sum()),graph.nnz,tuple(sources))
