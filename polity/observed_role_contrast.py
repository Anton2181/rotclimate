"""Observation-level role contrasts; uncovered space is never a negative label."""
import numpy as np
from scipy.spatial import cKDTree
from scipy.stats import rankdata


def unit_sphere(lat,lon):
    lat,lon=np.radians(lat),np.radians(lon)
    return np.column_stack([np.cos(lat)*np.cos(lon),np.cos(lat)*np.sin(lon),np.sin(lat)])


def match_full_grid(lat,lon,grid_lat,grid_lon,land,allowed,in_window):
    """Match full-grid centres before coverage flags, without a nearest-land rescue.

    Status0 usable,1 outside window,2 nonland,3 disallowed. Raw nearest indices
    are kept for diagnosis even when excluded; no point is moved to improve fit.
    """
    lat,lon=np.asarray(lat,float),np.asarray(lon,float)
    if lat.ndim!=1 or lat.shape!=lon.shape or not np.isfinite(lat).all() or not np.isfinite(lon).all():
        raise ValueError('Finite paired source coordinates required')
    glat,glon=np.asarray(grid_lat,float),np.asarray(grid_lon,float)
    land,allowed=np.asarray(land,bool),np.asarray(allowed,bool)
    inside=np.asarray(in_window,bool)
    if glat.shape!=glon.shape or land.shape!=glat.shape or allowed.shape!=land.shape or inside.shape!=lat.shape:
        raise ValueError('Grid masks and source coverage must match')
    if not np.isfinite(glat).all() or not np.isfinite(glon).all():raise ValueError('Finite grid coordinates required')
    tree=cKDTree(unit_sphere(glat.ravel(),glon.ravel()))
    _,index=tree.query(unit_sphere(lat,lon))
    status=np.where(~inside,1,np.where(~land.ravel()[index],2,np.where(~allowed.ravel()[index],3,0)))
    return np.asarray(index,int),np.asarray(status,int)


def cell_class_summary(index,classes,status):
    """Distinct cell/class support, retaining mixed cells and all source records."""
    index,classes,status=(np.asarray(v) for v in (index,classes,status))
    if index.ndim!=1 or index.shape!=classes.shape or status.shape!=index.shape or not np.isin(classes,[0,1]).all():
        raise ValueError('Paired source indices, binary context classes and statuses required')
    use=status==0
    sets={k:set(index[use&(classes==k)].tolist()) for k in [0,1]}
    return dict(included_records={str(k):int(np.sum(use&(classes==k))) for k in [0,1]},
        represented_cell_class_units={str(k):len(sets[k]) for k in [0,1]},
        mixed_cells=len(sets[0]&sets[1]),represented_cells=len(sets[0]|sets[1]),
        preparation_gate_passed=all(len(v)>=30 for v in sets.values()))


def context_auc(index,classes,status,grid_score):
    """AUC over distinct represented cell/class units; repeated records add no mass.

    Mixed cells occur once in each class. This is a conditional observation
    contrast, never specificity against unobserved/background landscape.
    """
    summary=cell_class_summary(index,classes,status)
    index,classes,status=(np.asarray(v) for v in (index,classes,status))
    score=np.asarray(grid_score,float).ravel()
    if not np.isfinite(score).all():raise ValueError('Finite predictor field required')
    samples=[]
    for cls in [0,1]:
        units=np.unique(index[(status==0)&(classes==cls)])
        if np.any(units<0) or np.any(units>=len(score)):raise ValueError('Source match outside predictor grid')
        samples.append(score[units])
    negative,positive=samples;nn,np_=len(negative),len(positive)
    auc=None
    if nn and np_:
        ranks=rankdata(np.concatenate([negative,positive]),method='average')
        auc=float((ranks[nn:].sum()-np_*(np_+1)/2)/(nn*np_))
    return dict(summary,AUC=auc)
