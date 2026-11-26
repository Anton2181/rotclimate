"""Saved-field trajectory proxies for diagnostics; not used by the climate model."""
import numpy as np
from scipy import ndimage as ndi

SEA,EXIT,CALM,LIMIT=1,2,3,4
STATUS={SEA:'sea_reached',EXIT:'off_domain',CALM:'calm',LIMIT:'land_through_horizon'}


def production_geometry(land,cell_km,inflow_km):
    """Reproduce e91 geometry, including explicit flags for invalid sea indices."""
    land=np.asarray(land,bool)
    distance,nearest=ndi.distance_transform_edt(land,return_indices=True)
    distance*=cell_km
    gy,gx=np.gradient(ndi.gaussian_filter(distance,1.))
    norm=np.maximum(np.hypot(gx,gy),1e-9)
    r,c=nearest;inside=(r>=0)&(r<land.shape[0])&(c>=0)&(c<land.shape[1])
    valid=inside&~land[np.clip(r,0,land.shape[0]-1),np.clip(c,0,land.shape[1]-1)]
    return dict(distance_km=distance,normal_east=gx/norm,normal_north=-gy/norm,
                reach=np.where(land,np.exp(-distance/inflow_km),0.),nearest_r=r,nearest_c=c,
                nearest_valid_sea=valid,has_sea=bool((~land).any()))


def backtrace(land,u,v,starts,*,cell_km,step_km,horizon_km):
    """Follow frozen monthly surface flow backward by fixed arc length.

    u is eastward, v northward; rows run south. Domain edges are unknown.
    A land-only path stops at its finite horizon and never asserts infinite
    upwind continentality. No synthetic sea is supplied beyond the domain.
    """
    land=np.asarray(land,bool);u=np.asarray(u,float);v=np.asarray(v,float)
    starts=np.asarray(starts,float)
    if land.ndim!=2 or min(land.shape)<2 or u.shape!=land.shape or v.shape!=land.shape:
        raise ValueError('Matching two-dimensional land and wind fields required')
    if not np.isfinite(u).all() or not np.isfinite(v).all() or starts.ndim!=2 or starts.shape[1]!=2 or not len(starts):
        raise ValueError('Finite winds and nonempty row/column start coordinates required')
    if not np.isfinite([cell_km,step_km,horizon_km]).all() or min(cell_km,step_km,horizon_km)<=0:
        raise ValueError('Positive finite distances required')
    ny,nx=land.shape;r,c=starts.T.copy()
    inside=lambda r,c:(r>-.5)&(r<ny-.5)&(c>-.5)&(c<nx-.5)
    if not np.isfinite(starts).all() or not inside(r,c).all():raise ValueError('Starts must be inside the saved domain')
    if not land[np.floor(r+.5).astype(int),np.floor(c+.5).astype(int)].all():raise ValueError('Start on scored land')
    n=len(r);status=np.zeros(n,np.uint8);distance=np.zeros(n);sea_r=np.full(n,-1,int);sea_c=sea_r.copy()
    for _ in range(int(np.ceil(horizon_km/step_km))):
        active=np.flatnonzero(status==0)
        if not len(active):break
        ue=ndi.map_coordinates(u,[r[active],c[active]],order=1,mode='nearest')
        vn=ndi.map_coordinates(v,[r[active],c[active]],order=1,mode='nearest')
        speed=np.hypot(ue,vn);calm=speed<1e-6;status[active[calm]]=CALM
        moving=~calm;ids=active[moving];speed=speed[moving]
        ds=np.minimum(step_km,horizon_km-distance[ids])
        r[ids]+=vn[moving]/speed*ds/cell_km
        c[ids]-=ue[moving]/speed*ds/cell_km
        distance[ids]+=ds
        valid=inside(r[ids],c[ids]);status[ids[~valid]]=EXIT;ids=ids[valid]
        ri=np.floor(r[ids]+.5).astype(int);ci=np.floor(c[ids]+.5).astype(int)
        hit=~land[ri,ci];status[ids[hit]]=SEA;sea_r[ids[hit]]=ri[hit];sea_c[ids[hit]]=ci[hit]
    status[status==0]=LIMIT
    return dict(status=status,distance_km=distance,sea_r=sea_r,sea_c=sea_c,final_r=r,final_c=c)
