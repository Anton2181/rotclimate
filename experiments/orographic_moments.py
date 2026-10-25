"""Geometry-only uplift moments on a common fine terrain grid.

Not coupled to the climate solver. Average positive fine-grid ascent before
aggregation, rather than treating every cell's max-minus-mean elevation as
unresolved hills. This separates a resolved monotone slope from opposing
unresolved slopes without counting a smooth plane as extra roughness.
"""
import numpy as np


def uplift_moments(height,spacing_m,block,u=0.,v=0.):
    height=np.asarray(height,dtype=float)
    if (height.ndim!=2 or min(height.shape)<3 or not np.isfinite(height).all() or
            not np.isfinite(spacing_m) or spacing_m<=0 or
            not isinstance(block,int) or isinstance(block,bool) or block<1 or
            any(n%block for n in height.shape)):
        raise ValueError('Need finite terrain, positive spacing and an exactly divisible positive block size')
    u,v=np.broadcast_arrays(np.asarray(u,float),np.asarray(v,float),height)[:2]
    if not np.isfinite(u).all() or not np.isfinite(v).all():raise ValueError('Need finite winds')
    dy,dx=np.gradient(height,spacing_m,edge_order=2)
    ascent=u*dx-v*dy                         # rows increase southward
    shape=(height.shape[0]//block,block,height.shape[1]//block,block)
    mean=lambda x:np.asarray(x).reshape(shape).mean((1,3))
    mu=mean(ascent);positive=mean(np.maximum(ascent,0.))
    return dict(mean_ascent_ms=mu,positive_ascent_ms=positive,
                unresolved_positive_increment_ms=np.maximum(positive-np.maximum(mu,0.),0.),
                legacy_relief_m=height.reshape(shape).max((1,3))-mean(height))
