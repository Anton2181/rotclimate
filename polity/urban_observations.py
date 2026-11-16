"""Observation-aware diagnostics; no urban population or model-area imputation."""
import numpy as np


def interval_ks_lower_bound(sample,lower,upper):
    """Necessary CDF gap to interval-censored observations, including open tails.

    Every possible observed CDF lies between counts of intervals wholly below
    x and intervals whose lower endpoint is below x. The returned maximum gap
    is a lower bound on KS, not a p-value or an imputed-area KS statistic.
    """
    a,lo,hi=map(lambda x:np.asarray(x,float),[sample,lower,upper])
    if any(x.ndim!=1 or not len(x) for x in [a,lo,hi]) or lo.shape!=hi.shape:
        raise ValueError('Nonempty one-dimensional sample and matched intervals required')
    if not np.isfinite(a).all() or not np.isfinite(lo).all() or np.isnan(hi).any() or np.isneginf(hi).any():
        raise ValueError('Finite sample/lower bounds and finite or positive-infinite upper bounds required')
    if np.any(a<0) or np.any(lo<0) or np.any(hi<lo):raise ValueError('Nonnegative area and ordered bounds required')
    edges=np.unique(np.r_[a,lo,hi[np.isfinite(hi)]])
    x=np.r_[edges,np.nextafter(edges,-np.inf)]
    model=np.searchsorted(np.sort(a),x,side='right')/len(a)
    lowest=np.searchsorted(np.sort(hi),x,side='right')/len(lo)
    highest=np.searchsorted(np.sort(lo),x,side='right')/len(lo)
    return float(max(0.,np.max(lowest-model),np.max(model-highest)))
