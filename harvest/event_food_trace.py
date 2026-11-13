"""Display-bin ledgers for an already supplied continuous event inventory.

The initial stock is explicit. No delivery retention or additional food is
applied here. Bin boundaries split accounting intervals without moving cargo.
"""
from math import fsum,isfinite

import numpy as np

from harvest.event_food_stocks import _prepare,_flow


def trace_event_food_year(times,supplies,*,demand_rate,capacity,initial_stock,year_days=365.,loss_fraction_year=.05,bins=12):
    events,hazard=_prepare(times,supplies,demand_rate,capacity,year_days,loss_fraction_year)
    if isinstance(bins,bool) or not isinstance(bins,int) or bins<1:raise ValueError('Positive integer display-bin count required')
    if not isfinite(initial_stock) or not 0<=initial_stock<=capacity:raise ValueError('Initial stock must lie within capacity')
    names=['arrivals','needed','consumed','unmet','spoiled','overflow','shortfall_days','peak_stock'];result={name:np.zeros(bins) for name in names}
    stock=float(initial_stock);clock=0.;index=0;stocks=[stock]
    for month in range(bins):
        left=month*year_days/bins;right=(month+1)*year_days/bins;result['needed'][month]=demand_rate*(right-left);peak=stock
        arrivals=[];eaten=[];unmet=[];spoiled=[];overflow=[];short=[]
        while index<len(events) and events[index][0]<right:
            time,cargo=events[index];stock,meal,missing,loss,duration=_flow(stock,time-clock,demand_rate,hazard)
            eaten.append(meal);unmet.append(missing);spoiled.append(loss);short.append(duration)
            arrivals.append(cargo);overflow.append(max(0.,stock+cargo-capacity));stock=min(capacity,stock+cargo);peak=max(peak,stock);clock=time;index+=1
        stock,meal,missing,loss,duration=_flow(stock,right-clock,demand_rate,hazard);clock=right
        eaten.append(meal);unmet.append(missing);spoiled.append(loss);short.append(duration)
        for name,values in [('arrivals',arrivals),('consumed',eaten),('unmet',unmet),('spoiled',spoiled),('overflow',overflow),('shortfall_days',short)]:result[name][month]=fsum(values)
        result['peak_stock'][month]=peak;stocks.append(stock)
    assert index==len(events)
    result['stock_path']=np.asarray(stocks)
    return result
