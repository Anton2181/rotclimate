"""Frozen boundary/initial-wind controls, with actual external-port budgets."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.pressure_boundary import BoundaryPressureMoistModel,advance_boundary_with_convection,baroclinic_lower_wind_seed
from rotclimate.pressure_moist import gas_energy
from local_benchmark_protocol import file_hash,write_json


def inputs(plan,region):
    spec=plan['regions'][region];folder=ROOT/spec['prior_pilot_folder']
    initial_record=json.loads((folder/'initial.json').read_text())
    with np.load(folder/'initial.npz') as data:initial={k:data[k] for k in data.files}
    with np.load(ROOT/spec['archive']) as source:
        index=initial_record['source_index'];stride=plan['horizontal_stride']
        if abs(source['solved_days'][index]-spec['model_day'])>1e-9:raise ValueError('Source day changed')
        lower=source['winds'][index,0,:,::stride,::stride]
    mass=-np.diff(plan['pressure_edges_pa'])/9.80665
    seed_u,seed_v=baroclinic_lower_wind_seed(lower[0],lower[1],mass)
    ub=np.zeros_like(seed_u);vb=np.zeros_like(seed_v);ub[:,:,[0,-1]]=seed_u[:,:,[0,-1]];vb[:,[0,-1]]=seed_v[:,[0,-1]]
    return initial,seed_u,seed_v,ub,vb


def run(path,out,preflight=False):
    path=path.resolve();plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed boundary trial input/source: '+n)
    prepared={n:inputs(plan,n) for n in plan['regions']}
    if preflight:
        result=dict(status='boundary_inputs_prepared_no_integrations',actual_earth_initialized_integrations_started=0,
            cases={n:dict(shape=list(a['temperature'].shape),maximum_archived_lower_seed_ms=float(max(abs(u[0]).max(),abs(v[0]).max())))
                for n,(a,u,v,ub,vb) in prepared.items()},literal_plan_sha256=file_hash(path))
        print(json.dumps(result,indent=2));return
    if subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit the literal boundary plan before integrating')
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve prior boundary trial attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);rows=[];started=0
    for region,(a,seed_u,seed_v,ub,vb) in prepared.items():
        directory=out/region;directory.mkdir();np.savez_compressed(directory/'seed.npz',seed_u=seed_u,seed_v=seed_v,u_boundary=ub,v_boundary=vb)
        f=2*plan['rotation_rate_s']*np.sin(np.deg2rad(a['latitude']))
        for name,setup in plan['setups'].items():
            folder=directory/name;folder.mkdir()
            for dt in setup['timesteps_s']:
                key=str(dt);row=dict(region=region,setup=name,dt_s=dt,status='not_started',started=False);history=[];state=None;rain=None;rain_h=None
                try:
                    b_u=ub if setup['prescribed_ports'] else np.zeros_like(ub);b_v=vb if setup['prescribed_ports'] else np.zeros_like(vb)
                    mass=np.broadcast_to((-np.diff(plan['pressure_edges_pa'])/9.80665)[:,None,None],a['temperature'].shape)
                    model=BoundaryPressureMoistModel(plan['pressure_edges_pa'],a['latitude'].shape,plan['cell_m'],f,u_boundary=b_u,v_boundary=b_v,
                        external_temperature_k=a['temperature'],external_mixing_ratio=a['vapor']/mass,momentum_drag_s=plan['momentum_drag_s'])
                    if setup['archived_lower_wind_seed']:
                        u,v=seed_u.copy(),seed_v.copy();u[:,:,[0,-1]]=b_u[:,:,[0,-1]];v[:,[0,-1]]=b_v[:,[0,-1]]
                        state=model.initial_state(a['temperature'],a['vapor'],u,v)
                    else:state=model.initial_state(a['temperature'],a['vapor'])
                    started+=1;row['started']=True;face_mass=model.mass[:,0,0,None,None]
                    kinetic=lambda s:.5*(np.sum(face_mass*s.u_east[:,:,1:-1]**2)+np.sum(face_mass*s.v_south[:,1:-1]**2))
                    initial_ke=float(kinetic(state));initial_energy=gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+initial_ke;initial_water=state.vapor_kg_m2.sum()
                    x=model._velocity(state.u_east,state.v_south);force=model.momentum@x+model._pressure_force(state.temperature_k)+model.boundary_rotation_force
                    initial_imbalance=float(max(np.max(abs(force[:model.n_u].reshape(model.nz,*state.u_east[:,:,1:-1].shape[1:])/model.sqrt_mass[:,None,None])),
                        np.max(abs(force[model.n_u:].reshape(model.nz,*state.v_south[:,1:-1].shape[1:])/model.sqrt_mass[:,None,None]))))
                    rain=np.zeros(model.shape);rain_h=np.zeros(model.shape);port_energy=0.;port_water=0.
                    for step in range(plan['duration_s']//dt):
                        state=advance_boundary_with_convection(model,state,dt,relaxation_s=plan['convection_relaxation_s'],
                            neutral_tolerance_k=plan['neutral_tolerance_k'],max_sweeps=plan['maximum_convective_sweeps'],max_iterations=plan['maximum_coupling_iterations'])
                        rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2;c=state.certificate
                        power=c['external_power_w_m2']+c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
                        port_energy+=dt*power;port_water+=dt*c['outward_boundary_vapor_kg_m2_s']
                        history.append(dict(time_s=(step+1)*dt,mean_rain_mm=float(rain.mean()),net_port_energy_j_m2=port_energy,net_outward_port_water_kg_m2=port_water,
                            boundary_gas_enthalpy_w_m2=c['outward_boundary_gas_enthalpy_w_m2'],boundary_geopotential_work_w_m2=c['outward_boundary_geopotential_work_w_m2'],
                            boundary_rotation_work_w_m2=c['prescribed_boundary_rotation_work_w_m2'],boundary_vapor_kg_m2_s=c['outward_boundary_vapor_kg_m2_s'],
                            energy_error_j_m2=c['actual_combined_energy_rain_source_residual_j_m2'],water_error_kg_m2=c['actual_combined_water_rain_source_residual_kg_m2'],
                            peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max()))))
                    fields=folder/(key+'.npz');np.savez_compressed(fields,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h)
                    final=gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+kinetic(state)+rain_h.sum()
                    water_error=state.vapor_kg_m2.sum()+rain.sum()-initial_water+port_water*model.n
                    edge=np.zeros(rain.shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True
                    row.update(status='completed',steps=len(history),history=history,initial_kinetic_energy_j_m2=initial_ke/model.n,
                        initial_maximum_momentum_imbalance_ms2=initial_imbalance,relative_total_energy_error=float(abs(final-initial_energy-port_energy*model.n)/max(abs(initial_energy),1.)),
                        relative_water_rain_error=float(abs(water_error)/max(float(initial_water),1.)),net_port_energy_j_m2=port_energy,net_outward_port_water_kg_m2=port_water,
                        mean_run_rain_mm=float(rain.mean()),outer_grid_rain_fraction=float(rain[edge].sum()/rain.sum()) if rain.sum()>0 else None,
                        peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max())),maximum_temperature_adjustment_k=float(np.max(abs(state.temperature_k-a['temperature']))),fields_sha256=file_hash(fields))
                except Exception as error:
                    row.update(status='failed',error=repr(error),traceback=traceback.format_exc(),completed_steps=len(history),history=history)
                    if state is not None and rain is not None:
                        partial=folder/(key+'_partial.npz');np.savez_compressed(partial,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h)
                        row['partial_fields_sha256']=file_hash(partial)
                write_json(folder/(key+'.json'),row);rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ['history','traceback']}),flush=True)
    r=dict(status='boundary_initialization_trial_complete',actual_earth_initialized_integrations_started=started,integrations_completed=sum(v['status']=='completed' for v in rows),
        legacy_earth_benchmark_attempts_added=0,monthly_rainfall_skill_evaluated=False,physics_or_atlas_adoption=False,results=rows,literal_plan_sha256=file_hash(path),
        scope='Prescribed model-assisted baroclinic ports and archived-lower-wind seeding, not transparent boundaries or balanced initialization. Actual gas/vapor/pressure/rotation exchange booked; no monthly climate skill, nonlinear momentum or terrain adoption.')
    write_json(out/'verification.json',r)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);ap.add_argument('--preflight',action='store_true');args=ap.parse_args();run(args.plan,args.out.resolve(),args.preflight)
