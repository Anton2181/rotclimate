"""Observation-period aggregation for an audit of Earth monthly skill only.

The model/atlas default remains twelve equal months. WorldClim monthly totals
are compared here to a declared 365-day non-leap Gregorian reference. Southern
cases retain the existing six-month observation reorder, with half a model
year of phase applied to the actual month boundaries, including wraparound.
"""
import numpy as np
from rotclimate.numerics import matrix_product

MONTH_DAYS=np.array([31,28,31,30,31,30,31,31,30,31,30,31],dtype=float)


def observation_weights(days,*,mirrored=False):
    """Return monthly averaging weights, actual durations, original month IDs.

    Assumes uniform five-day-style model intervals represented by their
    centers. Values are piecewise constant within each interval, as in the
    legacy monthly aggregator. No interpolation of old monthly means occurs.
    """
    days=np.asarray(days,float)
    if days.ndim!=1 or not len(days) or not np.isfinite(days).all():
        raise ValueError('Need finite one-dimensional model step centers')
    expected=(np.arange(len(days))+.5)*365/len(days)
    if not np.allclose(days,expected,atol=1e-10,rtol=0):
        raise ValueError('Earth calendar audit requires uniform intervals over a 365-day model year')
    step=365/len(days)
    left=np.arange(len(days))*step;right=left+step
    edges=np.r_[0,np.cumsum(MONTH_DAYS)]
    order=(np.arange(12)+(6 if mirrored else 0))%12
    phase=182.5 if mirrored else 0
    overlap=np.zeros((12,len(days)))
    for row,month in enumerate(order):
        a,b=edges[month]-phase,edges[month+1]-phase
        for turn in [-1,0,1]:
            overlap[row]+=np.maximum(np.minimum(right,b+turn*365)-np.maximum(left,a+turn*365),0)
    duration=MONTH_DAYS[order]
    if not np.allclose(overlap.sum(1),duration,atol=1e-10,rtol=0) or not np.allclose(overlap.sum(0),step,atol=1e-10,rtol=0):
        raise ValueError('Observation months do not partition the model year')
    return overlap/duration[:,None],duration,order


def monthly_stats(T,P,days,*,mirrored=False):
    T,P=np.asarray(T),np.asarray(P)
    if T.shape!=P.shape or T.shape[0]!=len(days):
        raise ValueError('Expected paired temperature and daily rain at every model step')
    weights,duration,order=observation_weights(days,mirrored=mirrored)
    shape=(12,)+T.shape[1:]
    tm=matrix_product(weights,T.reshape(len(days),-1)).reshape(shape)
    pm=matrix_product(weights,P.reshape(len(days),-1)).reshape(shape)
    pm=pm*duration.reshape((12,)+(1,)*(P.ndim-1))
    return dict(Tm=tm,Pm=pm,month_days=duration,original_month=order,
                method='gregorian-noleap-365, uniform-interval overlap, half-year mirrored phase')
