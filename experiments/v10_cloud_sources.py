"""Passive last-vapor-entry sources for the frozen cloud-bound trajectory.

Parcel condensate inherits its ascending donor's sources before bulk mixing.
Land evaporation is relabelled land recycling, not original molecular ancestry.
No source value feeds into physical evolution.
"""
from __future__ import annotations
import numpy as np
from experiments import v10_parcel_condensation as physics
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, divergence
from experiments.v10_water_sources import SOURCES, TAG_KEYS, face_transfers
base=physics.base
core=physics.core
coordinates=physics.coordinates
PROCESSES=physics.PROCESSES
MODES=physics.MODES
advance=physics.advance


class Collector:
    def __init__(self,domain,geometry,initial_water=None,saved=None):
        self.domain=domain;self.g=geometry
        shape=geometry.mass.shape
        shapes={'tags':(4,)+shape,'tagged_rain':(12,4)+shape,'ledger':(12,5,4),'time_seconds':(12,),
            'initial_store':(4,),'maximum_errors':(4,)}
        if saved is None:
            if initial_water is None:raise ValueError('Need initial physical water for source replay.')
            self.arrays={k:np.zeros(s) for k,s in shapes.items()}
            self.arrays['tags'][0]=initial_water
            self.arrays['initial_store'][0]=initial_water.sum(0).mean()
        else:self.arrays={k:np.array(v,copy=True) for k,v in saved.items()}
        if set(self.arrays)!=set(shapes) or any(self.arrays[k].shape!=s or not np.isfinite(self.arrays[k]).all() for k,s in shapes.items()):raise ValueError('Invalid cloud-source checkpoint shapes/values.')
        if any((self.arrays[k]<0).any() for k in ('tags','tagged_rain','time_seconds','initial_store','maximum_errors')):raise ValueError('Negative cloud-source stores.')

    def add(self,before,after,rain,parcel,flow,boundary,budget,dt,time_s):
        a=self.arrays;d=self.domain;g=self.g
        if abs(a['tags'].sum(0)-before.water).max()>1e-9:raise ValueError('Source stores disagree with step start.')
        old=a['tags'];tags=np.empty_like(old);ledger=np.zeros((5,4));month=int(np.searchsorted(EDGES[1:],time_s,side='right'))
        for source in range(4):
            q=boundary if source==1 else np.zeros_like(boundary)
            fx,fy=base.flux(old[source],g.mass,flow.x,flow.y,q)
            flux=flow.vertical*np.where(flow.vertical>=0,old[source,:-1]/g.mass[:-1],old[source,1:]/g.mass[1:])
            moved=old[source]-dt*(divergence(fx,fy,d.dx,d.dy)+coordinates.vertical_divergence(flux,g.mass.shape))
            if moved.min()<-1e-11:raise FloatingPointError('Negative transported cloud-source store.')
            tags[source]=np.maximum(moved,0.)
            ledger[4,source]=(tags[source]-moved).sum(0).mean()
            ledger[0,source],ledger[1,source]=face_transfers(fx,fy,dt,d)
        available=after.water+rain
        injection=available-tags.sum(0)
        if abs(injection[1:]).max()>1e-9 or injection[0].min()<-1e-9:raise FloatingPointError('Cloud source evaporation reconstruction failed.')
        evaporation=np.maximum(injection[0],0.)
        for source,values,name in ((2,np.where(~d.land,evaporation,0.),'ocean_evaporation_mm'),(3,np.where(d.land,evaporation,0.),'land_evaporation_mm')):
            if abs(values.mean()-budget[name])>1e-9:raise FloatingPointError('Cloud source evaporation ledger differs from physics.')
            tags[source,0]+=values;ledger[2,source]=values.mean()
        def reconcile(target):
            nonlocal tags
            before_fix=tags.copy();total=tags.sum(0)
            tags*=np.divide(target,total,out=np.zeros_like(total),where=total>0)[None]
            empty=total==0;tags[0,empty]=target[empty]
            correction=tags-before_fix
            if abs(correction).max()>1e-9:raise FloatingPointError('Cloud-source roundoff reconciliation exceeded allowance.')
            ledger[4]+=correction.sum(axis=(1,2,3))/d.land.size
            return float(abs(correction).max())
        correction=reconcile(available)
        donor_fraction=np.divide(old[:,:-1],before.water[None,:-1],out=np.zeros_like(old[:,:-1]),where=before.water[None,:-1]>0)
        parcel_by_source=np.zeros_like(tags);parcel_by_source[:,1:]=donor_fraction*parcel[None,1:]
        tags-=parcel_by_source
        if tags.min()<-1e-11:raise FloatingPointError('Parcel source removal exceeds transported source water.')
        floor=np.maximum(-tags,0.);tags+=floor;ledger[4]+=floor.sum(axis=(1,2,3))/d.land.size
        correction=max(correction,float(floor.max()),reconcile(available-parcel))
        bulk=rain-parcel
        if bulk.min()<-1e-12:raise ValueError('Parcel rain exceeds physical rain.')
        fractions=np.divide(tags,(available-parcel)[None],out=np.zeros_like(tags),where=(available-parcel)[None]>0)
        tagged_rain=parcel_by_source+fractions*np.maximum(bulk,0.)[None]
        tags-=fractions*np.maximum(bulk,0.)[None]
        if tags.min()<-1e-11:raise FloatingPointError('Bulk source removal exceeds available vapor.')
        floor=np.maximum(-tags,0.);tags+=floor;ledger[4]+=floor.sum(axis=(1,2,3))/d.land.size
        correction=max(correction,float(floor.max()),reconcile(after.water))
        ledger[3]=tagged_rain.sum(axis=(1,2,3))/d.land.size
        delta=(tags-old).sum(axis=(1,2,3))/d.land.size
        error=delta-(ledger[0]-ledger[1]+ledger[2]-ledger[3]+ledger[4])
        rain_error=float(abs(tagged_rain.sum(0)-rain).max());store_error=float(abs(tags.sum(0)-after.water).max())
        if abs(error).max()>1e-9 or max(rain_error,store_error)>1e-9:raise FloatingPointError('Passive cloud-source water ledger failed.')
        a['tags']=tags;a['tagged_rain'][month]+=tagged_rain;a['ledger'][month]+=ledger;a['time_seconds'][month]+=dt
        a['maximum_errors']=np.maximum(a['maximum_errors'],[float(abs(error).max()),rain_error,store_error,correction])

    def validate_months(self,month,water,rain):
        a=self.arrays;expected=np.diff(EDGES)
        if not np.allclose(a['time_seconds'][:month],expected[:month],atol=1e-3,rtol=1e-12) or np.any(a['time_seconds'][month:]):raise ValueError('Cloud-source time weights disagree with completed months.')
        if abs(a['tags'].sum(0)-water).max()>1e-9 or abs(a['tagged_rain'].sum(axis=(1,2))-rain).max()>1e-8:raise ValueError('Cloud-source stores/rain disagree with saved physics.')
        b=a['ledger'].sum(0);end=a['tags'].sum(axis=(1,2,3))/self.domain.land.size
        error=end-a['initial_store']-(b[0]-b[1]+b[2]-b[3]+b[4])
        if abs(error).max()>1e-7:raise ValueError('Accumulated cloud-source atmospheric ledger failed.')

    def summary(self,masks,winter,summer):
        a=self.arrays;rows={}
        for name,mask in masks.items():
            if not mask.any():continue
            monthly=a['tagged_rain'][:,:,:,mask].sum(axis=2).mean(axis=2)
            rows[name]={'cells':int(mask.sum()),'monthly_rain_mm_by_source':monthly.tolist(),
                'winter_rain_mm_by_source':monthly[winter].sum(0).tolist(),'summer_rain_mm_by_source':monthly[summer].sum(0).tolist()}
        b=a['ledger'].sum(0);end=a['tags'].sum(axis=(1,2,3))/self.domain.land.size
        return {'sources':list(SOURCES),'regions':rows,'atmospheric_ledger':{key:b[i].tolist() for i,key in enumerate(TAG_KEYS)},
            'initial_store_mm':a['initial_store'].tolist(),'end_store_mm':end.tolist(),
            'annual_source_error_mm':(end-a['initial_store']-(b[0]-b[1]+b[2]-b[3]+b[4])).tolist(),
            'maximum_step_errors':dict(zip(('source_budget_mm','rain_reconstruction_mm','store_reconstruction_mm','roundoff_reconciliation_mm'),a['maximum_errors'].tolist())),
            'interpretation':'Last entry to atmospheric vapor. Land evaporation is relabelled recycling regardless of soil ancestry. Unknown initial vapor remains explicit. Parcel rain inherits upward-donor labels before bulk mixing. Fractions are not causal effects of suppressing evaporation.'}


def year(domain, profile, settings, state, local_air, mask, geometry, driver,
         checkpoint=None, save_month=None, should_stop=lambda: False, condensation_mode="bulk", time_factor=1., collector=None):
    """Frozen physical accounting with prepared piecewise-constant boundary water."""
    if collector is None:raise ValueError('Passive cloud-source collector required.')
    if condensation_mode not in MODES or time_factor not in (1.,.5):raise ValueError('Invalid parcel mode/time factor.')
    parcel_totals = np.zeros((12,len(geometry.mass))) if checkpoint is None else np.array(checkpoint[-1]['parcel_rain_scored_land_mm'])
    if parcel_totals.shape != (12,len(geometry.mass)) or not np.isfinite(parcel_totals).all() or (parcel_totals<0).any():raise ValueError('Invalid parcel checkpoint.')
    shape = domain.land.shape;count = len(geometry.mass)
    if local_air.shape != (12, count)+shape or not np.isfinite(local_air).all() or mask.shape != shape or not mask.any():
        raise ValueError('Invalid event-forcing air input or diagnostic mask.')
    if checkpoint is None:
        rain = np.zeros((12,)+shape);temp = np.zeros((12, count)+shape);refs = np.zeros_like(temp)
        totals = {};start_month = 0;steps = 0
        initial_water = float((state.water.sum(0)+state.soil).mean());initial_energy = float(state.energy.sum(0).mean())
        maxw = maxe = continuity = ledger_error = 0.
        max_adjustment = max_raw_divergence = 0.
        layer_rain = np.zeros((12, count));thermal = np.zeros((12, len(PROCESSES), count))
        imports = np.zeros(12)
    else:
        state, rain, temp, refs, info = checkpoint
        totals = info['totals'].copy();start_month = info['month']
        initial_water,initial_energy = info['initial_water'],info['initial_energy']
        maxw,maxe,continuity,steps = (info[k] for k in ('maxw', 'maxe', 'continuity', 'steps'))
        d = info['diagnostics'];layer_rain = np.array(d['layer_rain_scored_land_mm']);thermal = np.array(d['temperature_changes_scored_land_c'])
        imports = np.array(d['monthly_boundary_import_gross_mm'], float)
        ledger_error = d['max_step_temperature_ledger_error_c'];max_adjustment = d['max_projection_adjustment_m_s']
        max_raw_divergence = d['max_raw_column_divergence_kg_m2_s']
        if imports.shape != (12,) or not np.isfinite(imports).all() or (imports < 0).any() or not np.allclose(imports[:start_month], driver.monthly_targets[:start_month], atol=1e-7, rtol=0):
            raise ValueError('Resumed monthly import control failed.')
    for month in range(start_month, 12):
        t = float(EDGES[month]);flow = None;next_forcing = t
        while t < EDGES[month+1]-1e-6:
            if steps % 32 == 0 and should_stop():
                raise base.BudgetStop()
            if flow is None or t >= next_forcing-1e-6:
                flow,boundary,next_forcing = driver.at(t)
                limit = base.stable_step(flow, geometry.mass, domain)
                max_adjustment = max(max_adjustment, driver.last_info['barotropic_velocity_adjustment_max_m_s'])
                max_raw_divergence = max(max_raw_divergence, driver.last_info['raw_column_divergence_max_kg_m2_s'])
            dt = step_length(t, limit*time_factor, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded event-forcing step count exceeded.')
            before_source_step=state
            state,p,temperature,target,b,by_layer,changes,residual,parcel_rain = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry=geometry, boundary=boundary, condensation_mode=condensation_mode)
            collector.add(before_source_step,state,by_layer,parcel_rain,flow,boundary,b,dt,t)
            parcel_totals[month] += parcel_rain[:,mask].mean(1)
            rain[month] += p;temp[month] += temperature*dt;refs[month] += target*dt
            layer_rain[month] += by_layer[:, mask].mean(1);thermal[month] += changes[:, :, mask].mean(2)
            imports[month] += b['boundary_import_gross_mm']
            for key,value in b.items():
                if key not in ('water_error_mm', 'energy_error_j_m2'):
                    totals[key] = totals.get(key, 0.)+value
            maxw = max(maxw, abs(b['water_error_mm']));maxe = max(maxe, abs(b['energy_error_j_m2']))
            continuity = max(continuity, flow.continuity);ledger_error = max(ledger_error, residual)
            t += dt;steps += 1
        if abs(imports[month]-driver.monthly_targets[month]) > 1e-7:
            raise FloatingPointError('Actual integrated monthly gross import differs from its fixed target.')
        duration = EDGES[month+1]-EDGES[month];temp[month] /= duration;refs[month] /= duration
        info = dict(month=month+1, totals=totals, initial_water=initial_water, initial_energy=initial_energy,
            maxw=maxw, maxe=maxe, continuity=continuity, steps=steps,
            diagnostics={'processes': list(PROCESSES), 'layer_rain_scored_land_mm': layer_rain.tolist(),
                'temperature_changes_scored_land_c': thermal.tolist(), 'max_step_temperature_ledger_error_c': ledger_error,
                'max_projection_adjustment_m_s': max_adjustment, 'max_raw_column_divergence_kg_m2_s': max_raw_divergence,
                'monthly_boundary_import_gross_mm': imports.tolist(), 'monthly_boundary_import_target_mm': driver.monthly_targets.tolist(),
                'note': 'Signed thermal changes are cumulative, not temperature error. Projection diagnostics refer to the original projected components; centered event anomalies remain column-balanced. Gross import is verified at every month boundary.'})
        info['parcel_rain_scored_land_mm'] = parcel_totals.tolist()
        if save_month:
            save_month(state, rain, temp, refs, info)
    wf = float((state.water.sum(0)+state.soil).mean());ef = float(state.energy.sum(0).mean())
    we = wf-initial_water-(totals['ocean_evaporation_mm']-totals['ocean_rain_mm']-totals['runoff_mm']-totals['boundary_export_mm']+totals['roundoff_correction_mm'])
    ee = ef-initial_energy-(totals['surface_latent_input_j_m2']+totals['temperature_relaxation_j_m2']-totals['energy_boundary_export_j_m2']+totals['roundoff_energy_j_m2']+totals['prescribed_flow_work_j_m2'])
    if abs(we) > 1e-6 or abs(ee) > 1:
        raise FloatingPointError('Annual event-forcing budgets failed.')
    info['budget'] = dict(totals, annual_water_error_mm=we, annual_energy_error_j_m2=ee,
        max_step_water_error_mm=maxw, max_step_energy_error_j_m2=maxe, max_air_continuity_kg_m2_s=continuity, steps=steps)
    return state, rain, temp, refs, info
