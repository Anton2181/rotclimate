"""Cached local boundary humidity with unchanged flow and nominal event timing."""
from __future__ import annotations
import numpy as np
from experiments import v10_weather_panel as weather,v10_forcing_audit as atmosphere
from rotclimate_v10.core import CENTERS,interpolate_months
core=weather.core
VARIANTS=('uniform','local','local_matched')


def local_profile(case,geometry,fields):
    field=fields[case.domain.name,'shum']
    result=np.zeros((12,)+geometry.mass.shape)
    for k in range(4):
        result[:,k]=atmosphere.at_pressure(field,case.longitude,case.domain.latitude,geometry.pressure[k]/100.)[0]
    if not np.isfinite(result).all() or (result<0).any():raise ValueError('Invalid native local boundary humidity.')
    # Keep the explicit dry lid; no native data are available at 150hPa.
    return result


def build_tables(domain,geometry,original,flows,uniform_ratio,local_ratio,safe_caps,log=lambda *_:None):
    times=original['times'];mask=original['boundary_mask'];index=np.searchsorted(original['edges'][1:],times,side='right')
    shape=original['boundary_lift16_aligned'].shape
    uniform=np.empty(shape);local=np.empty(shape);caps=np.empty(shape);weights=np.empty(shape)
    for i,t in enumerate(times):
        flow=flows(float(t))[0];weights[i]=core.incoming_coefficients(flow,domain)
        caps[i]=safe_caps(float(t),float(t+core.INTERVAL))[:,mask]
        uniform[i]=np.minimum(uniform_ratio(t+.5*core.INTERVAL)[:,mask],caps[i])
        local[i]=np.minimum(local_ratio(t+.5*core.INTERVAL)[:,mask],caps[i])
        if i%500==0:log(f'Forcing queries {i+1}/{len(times)}; no climate state advanced')
    result={'uniform':np.empty(shape),'local':np.empty(shape),'local_matched':np.empty(shape),
        'target_uniform':original['monthly_import_target_mm'].copy(),'target_local':np.zeros(12),
        'target_local_matched':original['monthly_import_target_mm'].copy()}
    land=domain.land[mask];diagnostics={'monthly':[],'state_advances':0}
    for month in range(12):
        select=index==month;pattern=original['pulse_aligned'][select,None,:]
        old,old_scale=core.match_import(uniform[select]*pattern,caps[select],weights[select],core.INTERVAL,result['target_uniform'][month])
        new=np.minimum(local[select]*pattern,caps[select])
        matched,scale=core.match_import(local[select]*pattern,caps[select],weights[select],core.INTERVAL,result['target_uniform'][month])
        result['uniform'][select]=old;result['local'][select]=new;result['local_matched'][select]=matched
        result['target_local'][month]=np.sum(weights[select]*new)*core.INTERVAL
        row={'month':month+1,'local_match_scale':scale,'variants':{}}
        for name,q in (('uniform',old),('local',new),('local_matched',matched)):
            dose=float(np.sum(weights[select]*q)*core.INTERVAL)
            row['variants'][name]={'gross_import_mm':dose,
                'land_boundary_cell_import_mm':float(np.sum((weights[select]*q)[:,:,land])*core.INTERVAL),
                'marine_boundary_cell_import_mm':float(np.sum((weights[select]*q)[:,:,~land])*core.INTERVAL),
                'mean_r_by_layer':q.mean(axis=(0,2)).tolist()}
            if abs(dose-result['target_'+name][month])>1e-7:raise ValueError('Native humidity forcing dose check failed.')
        diagnostics['monthly'].append(row)
    if not np.array_equal(result['uniform'],original['boundary_lift16_aligned']):raise ValueError('Uniform humidity reconstruction changed the frozen boundary.')
    diagnostics['uniform_boundary_identical']=True
    diagnostics['note']='Native monthly local mixing ratios with original nominal event pulse. Matched variant holds actual monthly gross incoming vapor fixed. Caps and normalization can change actual humidity means/variance. Land/marine boundary-cell categories do not identify outside-domain ancestry or which edge supplies rain.'
    return result,diagnostics


def prepare_tables(case,profile,setting,geometry,air,circulation,original,monthly_local,log=lambda *_:None):
    if monthly_local.shape!=(12,)+geometry.mass.shape:raise ValueError('Wrong local boundary profile shape.')
    driver=weather.Driver(original,case,profile,setting,geometry,air,circulation,16.,'aligned',67)
    def uniform(t):return core.core.boundary_ratio(case.domain,profile,setting,geometry,air,t)
    def local(t):return interpolate_months(monthly_local,t)
    def caps(start,end):
        knots=CENTERS[(CENTERS>start)&(CENTERS<end)]
        targets=[core.coordinates.targets(case.domain,profile,setting,t,air)[0] for t in (start,*knots,end)]
        return .95*core.base.saturation(np.min(targets,axis=0),geometry.pressure)
    return build_tables(case.domain,geometry,original,driver.at,uniform,local,caps,log)


class Driver(weather.Driver):
    def __init__(self,original,tables,variant,case,profile,setting,geometry,air,circulation):
        if variant not in VARIANTS:raise ValueError('Unknown native humidity variant.')
        super().__init__(original,case,profile,setting,geometry,air,circulation,16.,'aligned',67)
        self.boundary_values=tables[variant]
        self.monthly_targets=tables['target_'+variant]
