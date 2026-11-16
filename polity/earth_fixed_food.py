"""Fixed Earth city requests with multiple harvest pulses and one physical source ledger."""
import numpy as np

from harvest.field_support import FixedRuralFood
from .seasonal_settlement_network import food_year,route_sources,route_towns

KCAL=912500.


def fixed_request_food(produced,boundary,rural,request,owner,retention,between,*,marketed_share):
    produced=np.asarray(produced,float);boundary=np.asarray(boundary)
    rural=np.asarray(rural,float);request=np.asarray(request,float)
    owner=np.asarray(owner);retention=np.asarray(retention,float);between=np.asarray(between,float)
    if produced.ndim!=2 or boundary.shape!=produced.shape or rural.shape!=produced.shape[1:]:
        raise ValueError('Aligned component production/calendars and one rural population per source required')
    if request.ndim!=1 or owner.shape!=(4,len(rural)) or retention.shape!=owner.shape or between.shape!=(4,len(request),len(request)):
        raise ValueError('Original four route snapshots and fixed city requests required')
    if not all(np.isfinite(v).all() for v in [produced,rural,request,retention,between]) or any(np.any(v<0) for v in [produced,rural,request]):
        raise ValueError('Finite nonnegative physical food inputs required')
    if not 0<=marketed_share<=1 or np.any((retention<0)|(retention>1)) or np.any((between<0)|(between>1)):
        raise ValueError('Grain fractions must lie in zero to one')
    positive=produced>0
    if boundary.dtype.kind not in 'iu' or np.any(positive&((boundary<0)|(boundary>=12))):
        raise ValueError('Positive grain requires an explicit monthly harvest boundary')
    if owner.dtype.kind not in 'iu' or np.any((owner< -1)|(owner>=len(request))):
        raise ValueError('Valid physical-source route owners required')
    harvest=np.zeros((12,len(rural)))
    for component in range(len(produced)):
        valid=positive[component];source=np.flatnonzero(valid)
        np.add.at(harvest,(boundary[component,valid],source),produced[component,valid])
    need=rural*KCAL;monthly_need=np.broadcast_to(need/12,harvest.shape)
    rural_food=FixedRuralFood(harvest,food_year(harvest,monthly_need,need),monthly_need,365.,365.)
    marketed=rural_food.exportable*marketed_share
    annual_market=marketed.sum(0);dispatch=np.broadcast_to(annual_market/12,marketed.shape).copy()
    for month in range(12):dispatch[month]*=(owner[month//3]>=0)&(retention[month//3]>0)
    export_food=food_year(marketed,dispatch,annual_market)
    departures=dispatch-export_food.unmet_path
    direct=route_sources(departures,owner,retention,len(request))
    town=route_towns(direct,request,between)
    return dict(harvest=harvest,rural_food=rural_food.year,marketed=marketed,dispatch=dispatch,
                export_food=export_food,departures=departures,direct=direct,**town)
