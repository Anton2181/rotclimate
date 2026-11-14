"""Exact supplied event boundaries and conserved climate-bin disaggregation."""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class FieldClock:
    bin_edges_days: np.ndarray
    edges_days: np.ndarray

    def __post_init__(self):
        bins=np.asarray(self.bin_edges_days,dtype=float);edges=np.asarray(self.edges_days,dtype=float)
        if bins.shape!=(13,) or edges.ndim!=1 or len(edges)<2 or not np.isfinite(bins).all() or not np.isfinite(edges).all():
            raise ValueError('Thirteen climate edges and finite one-dimensional step edges required')
        if bins[0]!=0 or edges[0]!=0 or edges[-1]!=bins[-1] or np.any(np.diff(bins)<=0) or np.any(np.diff(edges)<=0) or np.any(np.diff(edges)>1):
            raise ValueError('Positive ordered intervals starting zero and steps <=1day required')
        if not np.isin(bins,edges).all():raise ValueError('Every climate boundary must be a step boundary')
        for name,value in [('bin_edges_days',bins),('edges_days',edges)]:
            value=value.copy();value.setflags(write=False);object.__setattr__(self,name,value)

    @property
    def step_days(self):return np.diff(self.edges_days)

    @property
    def bin_index(self):return np.searchsorted(self.bin_edges_days,self.edges_days[:-1],side='right')-1

    @property
    def fraction_of_bin(self):return self.step_days/np.diff(self.bin_edges_days)[self.bin_index]

    def repeat_bin_values(self,values):
        """Repeat state variables/rates, e.g. temperature; no duration scaling."""
        values=np.asarray(values,dtype=float)
        if values.ndim<1 or values.shape[0]!=12 or not np.isfinite(values).all():raise ValueError('Twelve finite climate-bin values required')
        return values[self.bin_index].copy()

    def spread_bin_totals(self,totals):
        """Uniform within each supplied bin; an explicit scenario, not daily data."""
        totals=np.asarray(totals,dtype=float)
        if np.any(totals<0):raise ValueError('Nonnegative water/energy totals required')
        repeated=self.repeat_bin_values(totals)
        weights=self.fraction_of_bin.reshape((-1,)+(1,)*(repeated.ndim-1))
        return repeated*weights

    def cyclic_window(self,start_day,end_day):
        """Supplied half-open interval; equal endpoints mean empty, not full year."""
        year=self.bin_edges_days[-1]
        if not np.isfinite(start_day) or not np.isfinite(end_day) or not 0<=start_day<year or not 0<=end_day<=year:
            raise ValueError('Window endpoints must lie inside the supplied year')
        if start_day not in self.edges_days or end_day not in self.edges_days:
            raise ValueError('Split the clock at event endpoints before creating a mask')
        if start_day==end_day:return np.zeros(len(self.step_days),dtype=bool)
        a,b=self.edges_days[:-1],self.edges_days[1:]
        if start_day<end_day:return (a>=start_day)&(b<=end_day)
        return (a>=start_day)|(b<=end_day)


def field_clock(bin_edges_days,*,event_edges_days=(),max_step_days=1.):
    """Split at climate/event boundaries and a regular grid of <=1day intervals."""
    bins=np.asarray(bin_edges_days,dtype=float);events=np.asarray(event_edges_days,dtype=float)
    if bins.shape!=(13,) or not np.isfinite(bins).all() or bins[0]!=0 or np.any(np.diff(bins)<=0):
        raise ValueError('Twelve positive finite climate-bin intervals starting zero required')
    if events.ndim!=1 or not np.isfinite(events).all() or np.any(events<0) or np.any(events>bins[-1]):
        raise ValueError('Finite event boundaries inside the supplied year required')
    if isinstance(max_step_days,bool) or not np.isfinite(max_step_days) or not 0<max_step_days<=1:
        raise ValueError('Maximum step must be in (0,1] days')
    edges=np.unique(np.concatenate([bins,events,np.arange(0,bins[-1],max_step_days)]))
    return FieldClock(bins,edges)
