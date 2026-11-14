"""Finite, paid pond recharge and groundwater transfer around the field kernel.

Hydraulic permissions and accessible capacity are supplied inputs. This budget
does not infer a water table, root suction, local recharge or groundwater yield.
"""
from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np

from .river_fields import FieldState,field_year
from .soil_drying import SoilState,soil_state,soil_step


@dataclass(frozen=True)
class GroundwaterFieldState:
    soil: SoilState
    pond_mm: np.ndarray
    aquifer_mm: np.ndarray

    def __post_init__(self):
        for name in ['pond_mm','aquifer_mm']:
            value=np.array(getattr(self,name),float,copy=True)
            if not np.isfinite(value).all() or np.any(value<0):raise ValueError('Finite nonnegative pond/aquifer stocks required')
            value.setflags(write=False);object.__setattr__(self,name,value)


def groundwater_field_year(profile,area_m2,field_nodes,source_m3,clock,rain_mm,eto_mm_day,
                           crop_mask,capture_mask,pond_mask,*,crop_kcb,aquifer_capacity_mm,
                           capillary_permission_mm_day,recharge_mm_day,recharge_mask,
                           aquifer_loss_mm_day=0.,initial=None,**legacy):
    """Five-stock budget; recharge uses previous pond water and shared infiltration.

    Upward transfer first fills deep available, then surface below-WP, then top
    available water. Only the existing root operator may spend available water.
    No same-step fresh delivery is recharged or credited twice downstream.
    """
    area=np.asarray(area_m2,float);duration=np.asarray(clock.step_days,float)
    if area.ndim!=1 or not len(area) or not np.isfinite(area).all() or np.any(area<=0):raise ValueError('Nonempty positive finite field areas required')
    if duration.ndim!=1 or not len(duration) or not np.isfinite(duration).all() or np.any((duration<=0)|(duration>1)):raise ValueError('Actual positive steps <=1day required')
    nt,nf=len(duration),len(area);source=np.asarray(source_m3,float)
    if source.ndim!=2 or source.shape[0]!=nt or not np.isfinite(source).all() or np.any(source<0):raise ValueError('Finite nonnegative river volumes per step/node required')
    allowed={'depletion_fraction','bare_background','pond_capacity_mm','infiltration_mm_day','efficiency','pond_evap_coefficient','crop_exposed_fraction','kcmax'}
    if set(legacy)-allowed:raise TypeError('Unknown legacy field option')
    def spatial(value):
        a=np.broadcast_to(np.asarray(value,float),(nf,)).copy()
        if not np.isfinite(a).all() or np.any(a<0):raise ValueError('Finite nonnegative spatial parameter required')
        return a
    def forcing(value):
        a=np.broadcast_to(np.asarray(value,float),(nt,nf))
        if not np.isfinite(a).all() or np.any(a<0):raise ValueError('Finite nonnegative per-step rate/amount required')
        return a
    def mask(value):
        a=np.asarray(value)
        if a.dtype.kind!='b':raise ValueError('Boolean masks required')
        return np.broadcast_to(a,(nt,nf))
    rain,eto,kcb=map(forcing,[rain_mm,eto_mm_day,crop_kcb])
    permission,recharge_rate,loss_rate=map(forcing,[capillary_permission_mm_day,recharge_mm_day,aquifer_loss_mm_day])
    crop,capture,pond_allowed,can_recharge=map(mask,[crop_mask,capture_mask,pond_mask,recharge_mask])
    if np.any(crop&pond_allowed):raise ValueError('Dryland crop and pond permission may not overlap')
    capacity=spatial(aquifer_capacity_mm);infiltration=spatial(legacy.get('infiltration_mm_day',20.))
    maximum=spatial(legacy.get('kcmax',1.2))
    if initial is None:initial=GroundwaterFieldState(soil_state(profile,np.zeros(nf)),np.zeros(nf),np.zeros(nf))
    state=soil_step(profile,initial.soil,np.zeros(nf),0.,0.,maximum,.55).state
    pond=spatial(initial.pond_mm);aquifer=spatial(initial.aquifer_mm)
    if np.any(aquifer>capacity):raise ValueError('Initial aquifer exceeds accessible capacity')
    if np.any(pond>spatial(legacy.get('pond_capacity_mm',0.))):raise ValueError('Initial pond exceeds capacity')
    initial_stock={name:getattr(state,name).copy() for name in ['top_mm','deep_mm','bound_mm']}
    initial_stock.update(pond_mm=pond.copy(),aquifer_mm=aquifer.copy())
    rates={name:forcing(legacy[name]) for name in ['depletion_fraction','bare_background'] if name in legacy}
    result={name:np.zeros((nt,nf)) for name in ['aquifer_mm','aquifer_recharge_mm','capillary_rise_mm','aquifer_loss_mm']}
    soil_capacity=np.broadcast_to(profile.taw_mm+profile.bound_capacity_mm,(nf,))
    for t,days in enumerate(duration):
        old_aquifer=aquifer.copy();aquifer=np.maximum(aquifer-loss_rate[t]*days,0.)
        loss=old_aquifer-aquifer
        transfer=np.minimum(np.minimum(permission[t]*days,aquifer),np.maximum(soil_capacity-state.total_mm,0.))
        remaining=transfer.copy();stocks={name:getattr(state,name).copy() for name in ['top_mm','deep_mm','bound_mm']}
        for name,limit in [('deep_mm',profile.deep_capacity_mm),('bound_mm',profile.bound_capacity_mm),('top_mm',profile.top_capacity_mm)]:
            before=stocks[name];stocks[name]=np.minimum(limit,before+remaining)
            remaining=np.maximum(remaining-(stocks[name]-before),0.)
        added=sum(stocks[name]-getattr(state,name) for name in stocks)
        old_aquifer=aquifer.copy();aquifer=np.maximum(aquifer-added,0.);rise=old_aquifer-aquifer
        state=SoilState(stocks['top_mm'],stocks['deep_mm'],stocks['bound_mm'])
        requested=np.minimum.reduce([pond,np.maximum(capacity-aquifer,0.),recharge_rate[t]*days,infiltration*days])
        requested=np.where(can_recharge[t]&pond_allowed[t],requested,0.)
        updated=np.minimum(capacity,aquifer+requested);charge=updated-aquifer
        aquifer=updated;pond=np.maximum(pond-charge,0.)
        remaining_rate=np.maximum(infiltration-charge/days,0.)
        options=dict(legacy);options['infiltration_mm_day']=remaining_rate
        for name,value in rates.items():options[name]=value[t]
        one=SimpleNamespace(step_days=np.array([days]),river_order=clock.river_order,river_receiver=clock.river_receiver)
        step=field_year(profile,area,field_nodes,source[t:t+1],one,rain[t:t+1],eto[t:t+1],crop[t:t+1],capture[t:t+1],pond_allowed[t:t+1],crop_kcb=kcb[t:t+1],initial=FieldState(state,pond),**options)
        for name,value in step.items():
            if name in ['initial','final']:continue
            if name not in result:result[name]=np.zeros((nt,)+value.shape[1:],dtype=value.dtype)
            result[name][t]=value[0]
        state=step['final'].soil;pond=step['final'].pond_mm
        result['aquifer_mm'][t]=aquifer;result['aquifer_recharge_mm'][t]=charge;result['capillary_rise_mm'][t]=rise;result['aquifer_loss_mm'][t]=loss
    result.update(initial=initial_stock,final=GroundwaterFieldState(state,pond,aquifer))
    return result


def periodic_groundwater_fields(*args,max_years=50,tolerance_mm=1e-6,**kwargs):
    if 'initial' in kwargs:raise ValueError('Periodic groundwater replay starts empty')
    if isinstance(max_years,bool) or not isinstance(max_years,int) or max_years<1 or not np.isfinite(tolerance_mm) or tolerance_mm<=0:raise ValueError('Positive cycle count/tolerance required')
    initial=None
    for year in range(1,max_years+1):
        r=groundwater_field_year(*args,initial=initial,**kwargs);last=r['final']
        residual=max(float(np.max(np.abs((getattr(last.soil,name) if name in ['top_mm','deep_mm','bound_mm'] else getattr(last,name))-r['initial'][name]))) for name in r['initial'])
        if residual<=tolerance_mm:break
        initial=last
    r.update(years=year,periodic=residual<=tolerance_mm,periodic_residual_mm=residual)
    return r
