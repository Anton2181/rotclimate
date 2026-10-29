"""Explicit common-footprint rainfall diagnostics, never atmospheric forcing."""
import numpy as np


def _overlap(n,stride):
    fine=np.arange(n,dtype=float);coarse=np.arange(0,n,stride,dtype=float)
    return np.maximum(np.minimum(coarse[:,None]+stride/2,fine[None,:]+.5)-np.maximum(coarse[:,None]-stride/2,fine[None,:]-.5),0.)


def aggregate_footprints(field,valid_fine,area_km2,*,stride):
    """Area-weight fine cells into centered stride-spaced model footprints.

    A coarse center at fine index4 with stride4 spans [2,6]; the end fine
    pixels contribute half widths. No shifted 4x4 block or nearest-point
    observation is substituted. Valid area/total available footprint area is
    returned explicitly; the caller declares its coverage and scoring masks.
    Field leading dimensions are retained. NaNs outside valid_fine are ignored;
    NaNs inside it are rejected, not silently filtered from a score.
    """
    a=np.asarray(field,float);valid=np.asarray(valid_fine);area=np.asarray(area_km2,float)
    if (a.ndim<2 or valid.shape!=a.shape[-2:] or area.shape!=valid.shape or valid.dtype.kind!='b'
            or not isinstance(stride,int) or isinstance(stride,bool) or stride<1
            or not np.isfinite(area).all() or np.any(area<=0) or not np.isfinite(a[...,valid]).all()):
        raise ValueError('Need matching fields, explicit boolean validity, positive finite areas and integer stride')
    wy=_overlap(valid.shape[0],stride);wx=_overlap(valid.shape[1],stride)
    total=wy@area@wx.T;accepted=wy@(area*valid)@wx.T
    numerator=np.einsum('ai,...ij,bj->...ab',wy,np.where(valid,a,0)*area,wx)
    mean=np.divide(numerator,accepted,out=np.full_like(numerator,np.nan),where=accepted>0)
    return dict(mean=mean,valid_area_km2=accepted,available_area_km2=total,coverage=accepted/total)


def rainfall_metrics(predicted_mm_day,observed_mm_day,area_km2,mask):
    """Score exactly the declared sites/area; no implicit missing-data mask."""
    sim,obs,area=np.asarray(predicted_mm_day,float),np.asarray(observed_mm_day,float),np.asarray(area_km2,float);m=np.asarray(mask)
    if (sim.shape!=obs.shape or area.shape!=sim.shape or m.shape!=sim.shape or m.dtype.kind!='b' or not m.any()
            or not np.isfinite(sim[m]).all() or not np.isfinite(obs[m]).all() or not np.isfinite(area[m]).all()
            or np.any(sim[m]<0) or np.any(obs[m]<0) or np.any(area[m]<=0)):
        raise ValueError('Need nonempty declared mask, finite nonnegative rainfall and positive scored area')
    w=area[m]/area[m].sum();error=sim[m]-obs[m]
    return dict(cells=int(m.sum()),area_km2=float(area[m].sum()),observed_mean_mm_day=float(w@obs[m]),predicted_mean_mm_day=float(w@sim[m]),mae_mm_day=float(w@abs(error)),rmse_mm_day=float(np.sqrt(w@(error**2))),bias_mm_day=float(w@error))
