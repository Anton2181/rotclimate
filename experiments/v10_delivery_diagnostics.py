"""Passive process diagnostics for exact replay of a frozen event-forcing year.

No physical tendencies are changed. Stage condensation opportunities are
instantaneous diagnostic calculations, not an alternative climate trajectory.
"""
from __future__ import annotations
import numpy as np
from experiments import v10_event_forcing as physics
from experiments.v10_time import step_length
from rotclimate_v10.core import DAY, EDGES, divergence
base = physics.base
PROCESSES = physics.PROCESSES
advance = physics.advance
W_EDGES = np.array([-np.inf,-.1,-.03,-.01,0.,.01,.03,.1,np.inf])
RH_EDGES = np.array([0.,.25,.5,.75,.9,.99,1.,1.05,2.,np.inf])
REGIONS = ('domain','scored_land','coast','interior')
STAGES = ('after_transport','after_relaxation','before_condensation')
BUDGET_TERMS = ('horizontal_import','horizontal_export','ocean_evaporation','land_recycling','rain','roundoff','storage_change')


def masked_transfers(fx,fy,mask,dx,dy):
    """Gross water across the selected region's boundary, per selected cell."""
    padded_x = np.pad(mask.astype(float),((0,0),(1,1)))
    padded_y = np.pad(mask.astype(float),((1,1),(0,0)))
    incoming_x = fx*np.diff(padded_x,axis=1)[None]/dx
    incoming_y = fy*np.diff(padded_y,axis=0)[None]/dy
    incoming = np.maximum(incoming_x,0).sum()+np.maximum(incoming_y,0).sum()
    outgoing = np.maximum(-incoming_x,0).sum()+np.maximum(-incoming_y,0).sum()
    return float(incoming/mask.sum()),float(outgoing/mask.sum())


def joint_bins(ascent,rh):
    if ascent.shape != rh.shape or not np.isfinite(ascent).all() or not np.isfinite(rh).all() or (rh < 0).any():
        raise ValueError('Invalid humidity/ascent diagnostic values.')
    iw = np.clip(np.searchsorted(W_EDGES,ascent,side='right')-1,0,len(W_EDGES)-2)
    ih = np.clip(np.searchsorted(RH_EDGES,rh,side='right')-1,0,len(RH_EDGES)-2)
    return iw*(len(RH_EDGES)-1)+ih


class Collector:
    def __init__(self,domain,geometry,score_mask,coast_distance_km,saved=None):
        self.domain = domain;self.g = geometry
        self.masks = (np.ones(domain.land.shape,bool),score_mask,score_mask&(coast_distance_km<150),score_mask&(coast_distance_km>300))
        if geometry.mass.shape != (5,)+domain.land.shape or any(not mask.any() for mask in self.masks):
            raise ValueError('Need five layers and nonempty geographic diagnostics.')
        self.counts = np.array([mask.sum() for mask in self.masks])
        nw,nrh = len(W_EDGES)-1,len(RH_EDGES)-1
        shapes = {'time_cell_seconds':(12,4),'relative_humidity_time_sums':(12,4,3,5),
            'thermal_change_cell_sums_c':(12,4,6,5), 'joint_time_cell_seconds':(12,4,4,nw,nrh),
            'joint_layer_rain_cell_mm':(12,4,4,nw,nrh), 'stage_condensation_cell_mm':(12,4,2,5),
            'relaxation_removed_opportunity_cell_mm':(12,4,5),'relaxation_added_opportunity_cell_mm':(12,4,5),
            'actual_layer_rain_cell_mm':(12,4,5),'gross_upward_vapor_cell_mm':(12,4,4),
            'column_water_budget_mm':(12,4,7),'maximum_reconstruction_errors':(5,)}
        self.arrays = {name:np.zeros(shape) for name,shape in shapes.items()} if saved is None else {name:np.array(value,copy=True) for name,value in saved.items()}
        if set(self.arrays) != set(shapes) or any(self.arrays[name].shape != shape or not np.isfinite(self.arrays[name]).all() for name,shape in shapes.items()):
            raise ValueError('Diagnostic checkpoint shape/values changed.')
        for name,value in self.arrays.items():
            if name not in ('thermal_change_cell_sums_c','column_water_budget_mm') and (value < 0).any():
                raise ValueError('Negative accumulated diagnostic weight.')

    def add(self,before,after,rain,changes,flow,boundary,budget,dt,time_s):
        g = self.g;d = self.domain;mass = g.mass
        month = int(np.searchsorted(EDGES[1:],time_s,side='right'))
        t0 = base.temperature(before.energy,mass,before.water,g.height_m)
        fx,fy = base.flux(before.water,mass,flow.x,flow.y,boundary)
        horizontal = divergence(fx,fy,d.dx,d.dy)
        upward_water = flow.vertical*np.where(flow.vertical>=0,before.water[:-1]/mass[:-1],before.water[1:]/mass[1:])
        vertical = physics.core.coordinates.vertical_divergence(upward_water,mass.shape)
        raw = before.water-dt*(horizontal+vertical);correction = np.maximum(-raw,0);transport_water = raw+correction
        transport_t = t0+changes[:3].sum(0);relax_t = transport_t+changes[3]
        pre_water = after.water+rain
        pre_t = base.temperature(after.energy,mass,pre_water,g.height_m)
        injection = pre_water-transport_water
        injection_error = float(abs(injection[1:]).max())
        if injection[0].min() < -1e-9 or injection_error > 1e-9:
            raise ValueError('Reconstructed water-stage injection failed.')
        evap = np.maximum(injection[0],0.)
        temp_error = float(abs(pre_t-relax_t).max())
        evap_error = abs(float(evap.mean())-budget['ocean_evaporation_mm']-budget['land_evaporation_mm'])
        if temp_error > 1e-9 or evap_error > 1e-9:
            raise ValueError('Reconstructed temperature/evaporation stages failed.')
        stage_rh = np.stack([transport_water/mass/base.saturation(transport_t,g.pressure),
            transport_water/mass/base.saturation(relax_t,g.pressure),pre_water/mass/base.saturation(pre_t,g.pressure)])
        opportunities = []
        for t in (transport_t,relax_t):
            energy = mass*(base.CP*(t+273.15)+base.G*g.height_m)+base.LV*transport_water
            _,candidate,_ = base.adjust(transport_water,energy,mass,g.height_m,g.pressure)
            opportunities.append(candidate)
        opportunities = np.stack(opportunities)
        removed = np.maximum(opportunities[0]-opportunities[1],0.)
        added = np.maximum(opportunities[1]-opportunities[0],0.)
        ascent = flow.vertical*base.G
        bins = joint_bins(ascent,stage_rh[2,1:])
        cells_per_hist = (len(W_EDGES)-1)*(len(RH_EDGES)-1)
        offsets = np.arange(4)[:,None]*cells_per_hist
        maximum_local_error = 0.;gross_error = 0.
        for index,mask in enumerate(self.masks):
            selected_bins = bins[:,mask]+offsets
            hist_time = np.bincount(selected_bins.ravel(),weights=np.full(selected_bins.size,dt),minlength=4*cells_per_hist).reshape(4,len(W_EDGES)-1,len(RH_EDGES)-1)
            hist_rain = np.bincount(selected_bins.ravel(),weights=rain[1:,mask].ravel(),minlength=4*cells_per_hist).reshape(hist_time.shape)
            a = self.arrays;a['time_cell_seconds'][month,index] += dt*mask.sum()
            a['relative_humidity_time_sums'][month,index] += stage_rh[:,:,mask].sum(2)*dt
            a['thermal_change_cell_sums_c'][month,index] += changes[:,:,mask].sum(2)
            a['joint_time_cell_seconds'][month,index] += hist_time;a['joint_layer_rain_cell_mm'][month,index] += hist_rain
            a['stage_condensation_cell_mm'][month,index] += opportunities[:,:,mask].sum(2)
            a['relaxation_removed_opportunity_cell_mm'][month,index] += removed[:,mask].sum(1)
            a['relaxation_added_opportunity_cell_mm'][month,index] += added[:,mask].sum(1)
            a['actual_layer_rain_cell_mm'][month,index] += rain[:,mask].sum(1)
            a['gross_upward_vapor_cell_mm'][month,index] += np.maximum(upward_water[:,mask],0).sum(1)*dt
            incoming,outgoing = masked_transfers(fx,fy,mask,d.dx,d.dy)
            change = float((after.water-before.water).sum(0)[mask].mean())
            ocean = float(np.where(~d.land,evap,0)[mask].mean());land = float(np.where(d.land,evap,0)[mask].mean())
            p = float(rain.sum(0)[mask].mean());roundoff = float(correction.sum(0)[mask].mean())
            values = np.array([incoming*dt,outgoing*dt,ocean,land,p,roundoff,change])
            a['column_water_budget_mm'][month,index] += values
            maximum_local_error = max(maximum_local_error,abs(values[0]-values[1]+ocean+land-p+roundoff-change))
            if index == 0:
                gross_error = max(abs(values[0]-budget['boundary_import_gross_mm']),abs(values[1]-budget['boundary_export_gross_mm']))
        errors = np.array([temp_error,injection_error,evap_error,maximum_local_error,gross_error])
        if maximum_local_error > 1e-9 or gross_error > 1e-9 or not np.isfinite(errors).all():
            raise ValueError('Regional reconstructed water ledger failed.')
        self.arrays['maximum_reconstruction_errors'] = np.maximum(self.arrays['maximum_reconstruction_errors'],errors)

    def validate_months(self,month):
        a = self.arrays
        expected = np.diff(EDGES)[:,None]*self.counts[None]
        if not np.allclose(a['time_cell_seconds'][:month],expected[:month],atol=1e-3,rtol=1e-12) or np.any(a['time_cell_seconds'][month:]):
            raise ValueError('Diagnostic time weights disagree with completed months.')
        time = a['joint_time_cell_seconds'].sum(axis=(-1,-2))
        if not np.allclose(time,a['time_cell_seconds'][:,:,None],atol=1e-3,rtol=1e-12):
            raise ValueError('Joint humidity/ascent histogram loses time weight.')
        rain = a['joint_layer_rain_cell_mm'].sum(axis=(-1,-2))
        if not np.allclose(rain,a['actual_layer_rain_cell_mm'][:,:,1:],atol=1e-8,rtol=0):
            raise ValueError('Joint histogram loses layer rain.')
        b = a['column_water_budget_mm']
        if np.max(abs(b[:,:,0]-b[:,:,1]+b[:,:,2]+b[:,:,3]-b[:,:,4]+b[:,:,5]-b[:,:,6])) > 1e-7:
            raise ValueError('Accumulated regional water ledger failed.')

    def summary(self):
        self.validate_months(12);a = self.arrays;rows = {}
        w_start = int(np.flatnonzero(W_EDGES == .01)[0]);rh_start = int(np.flatnonzero(RH_EDGES == .9)[0])
        for i,name in enumerate(REGIONS):
            time = a['time_cell_seconds'][:,i].sum();joint = a['joint_time_cell_seconds'][:,i].sum(0)
            rising = joint[:,w_start:,:].sum((1,2));moist_rising = joint[:,w_start:,rh_start:].sum((1,2))
            rows[name] = {'mean_relative_humidity_by_stage_layer':(a['relative_humidity_time_sums'][:,i].sum(0)/time).tolist(),
                'recipient_moist_fraction_when_upward_exchange_ge_001_pa_s':np.divide(moist_rising,rising,out=np.zeros(4),where=rising>0).tolist(),
                'fraction_time_with_upward_exchange_ge_001_pa_s':(rising/time).tolist(),
                'annual_layer_rain_mm':(a['actual_layer_rain_cell_mm'][:,i].sum(0)/self.counts[i]).tolist(),
                'stage_condensation_opportunity_mm':(a['stage_condensation_cell_mm'][:,i].sum(0)/self.counts[i]).tolist(),
                'relaxation_removed_opportunity_mm':(a['relaxation_removed_opportunity_cell_mm'][:,i].sum(0)/self.counts[i]).tolist(),
                'relaxation_added_opportunity_mm':(a['relaxation_added_opportunity_cell_mm'][:,i].sum(0)/self.counts[i]).tolist(),
                'column_water_budget_mm':dict(zip(BUDGET_TERMS,a['column_water_budget_mm'][:,i].sum(0).tolist()))}
        return {'regions':rows,'maximum_reconstruction_errors':dict(zip(('stage_temperature_c','upper_water_mm','evaporation_mm','local_column_water_mm','gross_boundary_mm'),a['maximum_reconstruction_errors'].tolist())),
            'stages':list(STAGES),'region_weighting':'Equal selected cells and actual timestep durations. Rain/opportunities already integrate the step and are not multiplied by dt again.',
            'cautions':'Joint upward exchange/recipient RH is diagnostic, not observed omega (except interpretation on fixed-pressure surfaces), a source tag or causal attribution. Stage condensation opportunities use independent instantaneous latent saturation adjustment on the realized trajectory, not an alternative climate. Gross internal upward vapor can recirculate.'}


# Static frozen year loop; the passive collector never modifies physical states.
def year(domain, profile, settings, state, local_air, mask, geometry, driver,
         checkpoint=None, save_month=None, should_stop=lambda: False, collector=None):
    """Frozen physical accounting with prepared piecewise-constant boundary water."""
    if collector is None:
        raise ValueError('Passive collector is required before starting a replay.')
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
            dt = step_length(t, limit, next_forcing, EDGES[month+1])
            if steps >= 500000:
                raise RuntimeError('Bounded event-forcing step count exceeded.')
            diagnostic_before = state
            state,p,temperature,target,b,by_layer,changes,residual = advance(
                state, domain, profile, settings, flow, dt, t, local_air, geometry=geometry, boundary=boundary)
            collector.add(diagnostic_before,state,by_layer,changes,flow,boundary,b,dt,t)
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
