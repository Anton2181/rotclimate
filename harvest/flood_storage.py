"""Finite field storage coupled to a conserved river-volume ledger.

This is an explicit fixed-calendar scenario. Crop suitability, flood access,
soil capacity and river supply are inputs, not inferred irrigation geography.
"""
import numpy as np
from .flood_water import route_water_budget


def storage_year(rain_mm,crop_et_mm,bare_et_mm,area_m2,field_nodes,source_m3,order,receiver,
                 *,capacity_mm,capture_mask,initial_mm=0.,efficiency=1.):
    rain=np.asarray(rain_mm,dtype=float);crop=np.asarray(crop_et_mm,dtype=float);bare=np.asarray(bare_et_mm,dtype=float)
    if rain.ndim!=2 or rain.shape[0]!=12 or crop.shape!=rain.shape or bare.shape!=rain.shape:
        raise ValueError('Rain and both ET demands require matching (12,fields) arrays')
    if not all(np.isfinite(a).all() and np.all(a>=0) for a in (rain,crop,bare)) or np.any((crop>0)&(bare>0)):
        raise ValueError('Finite nonnegative water inputs and disjoint crop/bare demand required')
    nf=rain.shape[1];area=np.asarray(area_m2,dtype=float);nodes=np.asarray(field_nodes)
    if area.shape!=(nf,) or not np.isfinite(area).all() or np.any(area<=0):raise ValueError('Positive finite field areas required')
    source=np.asarray(source_m3,dtype=float)
    if source.ndim!=2 or source.shape[0]!=12:raise ValueError('Twelve monthly river source volumes required')
    nn=source.shape[1]
    if nodes.shape!=(nf,) or nodes.dtype.kind not in 'iu' or np.any(nodes<0) or np.any(nodes>=nn):
        raise ValueError('One valid integer river node per field required')
    # The river routine validates the drainage graph even with no capture.
    route_water_budget(source,np.zeros_like(source),order,receiver,efficiency=efficiency)
    if not np.isin(nodes,np.asarray(order)).all():raise ValueError('Fields must attach to active river nodes')
    cap=np.broadcast_to(np.asarray(capacity_mm,dtype=float),(nf,)).copy()
    stock=np.broadcast_to(np.asarray(initial_mm,dtype=float),(nf,)).copy()
    if not np.isfinite(cap).all() or np.any(cap<0) or not np.isfinite(stock).all() or np.any(stock<0) or np.any(stock>cap):
        raise ValueError('Capacity and initial stock must be finite, nonnegative and bounded')
    capture=np.asarray(capture_mask)
    if capture.dtype.kind!='b':raise ValueError('Capture eligibility must be boolean')
    capture=np.broadcast_to(capture,rain.shape)
    keys=('start_mm','end_mm','request_mm','delivered_mm','crop_et_actual_mm','bare_et_actual_mm','rain_spill_mm','rain_excluded_mm')
    result={name:np.zeros_like(rain) for name in keys}
    river_names=('requested','withdrawal','delivered','loss','outlet')
    river={name:np.zeros_like(source) for name in river_names};initial=stock.copy()
    for m in range(12):
        result['start_mm'][m]=stock
        wet=stock+.8*rain[m];spill=np.maximum(wet-cap,0.);stock=wet-spill
        request=np.where(capture[m],np.maximum(cap-stock,0.),0.)
        demand=np.zeros_like(source);demand[m]=np.bincount(nodes,weights=request*area/1000.,minlength=nn)
        current=np.zeros_like(source);current[m]=source[m]
        routed=route_water_budget(current,demand,order,receiver,efficiency=efficiency)
        ratio=np.divide(routed['delivered_m3'][m],demand[m],out=np.zeros(nn),where=demand[m]>0)
        delivered=request*ratio[nodes];stock=stock+delivered
        actual=np.minimum(stock,crop[m]+bare[m]);stock=stock-actual
        result['end_mm'][m]=stock;result['request_mm'][m]=request;result['delivered_mm'][m]=delivered
        result['crop_et_actual_mm'][m]=np.where(crop[m]>0,actual,0.)
        result['bare_et_actual_mm'][m]=np.where(bare[m]>0,actual,0.)
        result['rain_spill_mm'][m]=spill;result['rain_excluded_mm'][m]=.2*rain[m]
        river['requested'][m]=demand[m];river['delivered'][m]=routed['delivered_m3'][m]
        river['loss'][m]=routed['delivery_loss_m3'][m];river['outlet'][m]=routed['outlet_m3'][m]
        river['withdrawal'][m]=routed['delivered_m3'][m]+routed['delivery_loss_m3'][m]
    result.update({'river_'+name+'_m3':value for name,value in river.items()})
    result.update(initial_mm=initial,final_mm=stock.copy())
    return result


def periodic_storage(*args,max_years=50,tolerance_mm=1e-6,**kwargs):
    if isinstance(max_years,bool) or not isinstance(max_years,int) or max_years<1 or not np.isfinite(tolerance_mm) or tolerance_mm<=0:
        raise ValueError('Positive integer years and finite positive tolerance required')
    if 'initial_mm' in kwargs:raise ValueError('Periodic simulation must start with zero stock')
    stock=0.;converged=False
    for year in range(1,max_years+1):
        result=storage_year(*args,initial_mm=stock,**kwargs)
        residual=float(np.max(np.abs(result['final_mm']-result['initial_mm']),initial=0.))
        if residual<=tolerance_mm:converged=True;break
        stock=result['final_mm']
    result.update(years=year,periodic=converged,periodic_residual_mm=residual)
    return result
