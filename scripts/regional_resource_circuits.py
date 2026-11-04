"""Regional circuit experiment: fixed grazing footprint, wider seasonal extent."""
from dataclasses import asdict
import numpy as np
from harvest.mobility_landscape import sample_landscape,trace_move
from harvest.seasonal_mobility import seasonal_circuit
from harvest.food_stocks import periodic_food_year


def regional_experiments(pilots,elevation,land,resolved,forage,area,water,meta,spec):
    ms=spec['mobility'];year=spec['year_days'];daily=ms['reference_feed_units']*ms['intake_kg_dm_reference_unit_day'];demand=daily*year/12
    h,w=land.shape;cell=meta['width']/w;cell_km=cell*meta['mi_per_px']*1.609344;result={}
    for scale in ms['regional_scales']:
        experiments=[]
        for pilot in pilots:
            print('Regional',scale['id'],pilot['id'],flush=True)
            world=sample_landscape(elevation,land&resolved,(pilot['row'],pilot['column']),radius=scale['radius_cells'],stride=scale['stride_cells'],
                offsets=scale['offsets'],cell_km=cell_km,level_speed_km_day=ms['reference_level_speed_km_day'],maximum_move_days=ms['maximum_move_days_per_bin'],include_radius=ms['landscape_radius_cells'])
            rows,cols=world.rows,world.columns;ground_supply=forage[:,rows,cols]*area[rows,cols]
            ground=[dict(row=int(y),column=int(x),x=float((x+.5)*cell),y=float((y+.5)*cell),land_area_km2=float(area[y,x]),
                water_distance_km=float(water[y,x]),monthly_dm_kg=ground_supply[:,i].tolist()) for i,(y,x) in enumerate(zip(rows,cols))]
            patches=[ground[i] for i in world.candidates];supply=ground_supply[:,world.candidates];cases=[]
            for wc in ms['water_scenarios']:
                threshold=wc['maximum_mapped_water_distance_km'];allowed_ground=np.ones(len(rows),bool) if threshold is None else water[rows,cols]<=threshold
                allowed=allowed_ground[world.candidates]
                kwargs=dict(daily_need=daily,reserve_days=ms['reserve_days'],reserve_quantum_days=ms['reserve_quantum_days'],year_days=year)
                mobile=seasonal_circuit(supply,world.travel,world.home,allowed=allowed,**kwargs)
                stationary=seasonal_circuit(supply[:,world.home,None],np.zeros((1,1)),0,allowed=np.array([allowed[world.home]]),**kwargs)
                fixed=periodic_food_year(ground_supply,np.full_like(ground_supply,demand),daily*ms['reserve_days'],step_days=year/12)
                fixed_met=np.where(allowed_ground,1-fixed.unmet/(daily*year),-1)
                fixed_i=int(np.argmax(fixed_met)) if allowed_ground.any() else None
                upper=None
                if allowed_ground.any():
                    envelope=ground_supply[:,allowed_ground].max(1)
                    optimistic=periodic_food_year(envelope,np.full(12,demand),daily*ms['reserve_days'],step_days=year/12)
                    upper=dict(annual_need_met=float(1-optimistic.unmet/(daily*year)),monthly_max_dm_kg=envelope.tolist(),
                        scope='One fine patch per bin, chosen anywhere on home-connected land without travel cost; continuous reserve. Optimistic resource bound, not a feasible route.')
                def encode(circuit,fixed=False):
                    if circuit is None:return None
                    value={k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in asdict(circuit).items()}
                    if fixed:value['locations']=[world.home]*12
                    previous=world.home;segments=[]
                    for destination in value['locations']:
                        segments.append(trace_move(world,previous,destination));previous=destination
                    value.update(segments=segments,annual_need_met=float(circuit.consumed.sum()/(daily*year)),
                        shortage_bins=int(np.sum(circuit.unmet>1e-8*daily)),moves=int(np.sum(circuit.travel_days>0)),total_travel_days=float(circuit.travel_days.sum()))
                    return value
                if mobile is not None:
                    if mobile.objective_unmet>stationary.objective_unmet+1e-6:raise ValueError('Regional movement lost the stationary option')
                    if mobile.consumed.sum()/(daily*year)>upper['annual_need_met']+1e-9:raise ValueError('Circuit exceeds the optimistic resource bound')
                cases.append(dict(**wc,status='conditional_circuit' if mobile is not None else 'home_excluded_by_water_scenario',
                    mobile=encode(mobile),stationary=encode(stationary,True),resource_upper_bound=upper,
                    best_fixed_base_continuous=dict(ground_node=fixed_i,row=int(rows[fixed_i]),column=int(cols[fixed_i]),annual_need_met=float(fixed_met[fixed_i]),
                        scope='Every home-connected fine cell, not just mobile candidate bases') if fixed_i is not None else None))
            experiments.append(dict(id=pilot['id'],label=pilot['label'],map_claim=pilot['map_claim'],status='scored_resource_landscape',home=world.home,
                scale=scale,patches=patches,ground_nodes=ground,patch_ground_nodes=world.candidates.tolist(),
                ground_edges=[[int(a),int(b),float(d)] for a,b,d in zip(*world.edges)],cases=cases))
        result[scale['id']]=experiments
    # Nested bases only relax the mobile state graph. All controls and the
    # grazing footprint stay fixed, so a decline is an implementation failure.
    if 'regional_sparse' in result and 'regional_dense' in result:
        for sparse,dense in zip(result['regional_sparse'],result['regional_dense']):
            for a,b in zip(sparse['cases'],dense['cases']):
                if a['mobile'] is not None and b['mobile']['annual_need_met']+1e-9<a['mobile']['annual_need_met']:raise ValueError('Additional bases reduced optimal support')
                if a['best_fixed_base_continuous']!=b['best_fixed_base_continuous']:raise ValueError('Sampling changed the stronger fixed-base control')
    return result
