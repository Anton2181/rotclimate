"""Opportunity-mass and local null controls for finite service-choice experiments."""
import numpy as np


def normalize_opportunities(weights,eligible,total):
    w,ok=np.asarray(weights,float),np.asarray(eligible,bool)
    if w.shape!=ok.shape or not np.isfinite(w).all() or np.any(w<0):
        raise ValueError('Matching finite nonnegative opportunity weights required')
    if not np.isfinite(total) or total<0:raise ValueError('Finite nonnegative total mass required')
    result=np.zeros_like(w);active=ok&(w>0)
    if total and not active.any():raise ValueError('Positive mass requires eligible opportunity support')
    if total:
        relative=w[active]/w[active].max()
        result[active]=total*relative/relative.sum()
    return result


def local_controls(demand,mass):
    """Zero-travel D/m and inverse-mass controls, not fitted role predictions."""
    d,m=np.asarray(demand,float),np.asarray(mass,float)
    if d.shape!=m.shape or any(not np.isfinite(a).all() or np.any(a<0) for a in [d,m]):
        raise ValueError('Matching finite nonnegative demand and mass required')
    positive=m>0
    with np.errstate(over='ignore'):
        per=np.divide(d,m,out=np.zeros_like(d),where=positive)
        inverse=np.divide(1.,m,out=np.zeros_like(m),where=positive)
    if not np.isfinite(per).all() or not np.isfinite(inverse).all():
        raise ValueError('Null-control rate exceeds numerical range; no rank-changing floor applied')
    return dict(local_demand=np.where(positive,d,0.),zero_travel_per_centre=per,inverse_mass=inverse)
