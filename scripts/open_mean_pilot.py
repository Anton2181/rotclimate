"""Paired fixed regional mean-boundary throughflow controls, with actual pressure work."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from pressure_boundary_pilot import inputs
from local_benchmark_protocol import file_hash,write_json
from rotclimate.rigid_lid_moist import stagger_two_reservoir_wind
from rotclimate.open_mean_boundary import OpenMeanRigidLidModel,balance_normal_ports
from rotclimate.pressure_boundary import advance_boundary_with_convection
from rotclimate.pressure_moist import gas_energy


def prepare(plan,region):
    base=json.loads((ROOT/plan['boundary_plan']).read_text());a,_,_,_,_=inputs(base,region)
    spec=base['regions'][region];record=json.loads((ROOT/spec['prior_pilot_folder']/'initial.json').read_text());index=record['source_index'];stride=base['horizontal_stride']
    with np.load(ROOT/spec['archive']) as source:
        if abs(source['solved_days'][index]-spec['model_day'])>1e-9:raise ValueError('Changed source model day')
        wind=source['winds'][index,:,:,::stride,::stride]
    raw_u,raw_v=stagger_two_reservoir_wind(wind[0,0],wind[0,1],wind[1,0],wind[1,1],len(base['pressure_edges_pa'])-1)
    mass=-np.diff(base['pressure_edges_pa'])/9.80665;ub=np.zeros_like(raw_u);vb=np.zeros_like(raw_v)
    ub[:,:,[0,-1]]=raw_u[:,:,[0,-1]];vb[:,[0,-1]]=raw_v[:,[0,-1]]
    open_u,open_v,port_conversion=balance_normal_ports(ub,vb,mass,base['cell_m'])
    closed_u=open_u-np.sum(mass[:,None,None]*open_u,axis=0,keepdims=True)/mass.sum()
    closed_v=open_v-np.sum(mass[:,None,None]*open_v,axis=0,keepdims=True)/mass.sum()
    models={};seeds=dict(raw_u=raw_u,raw_v=raw_v);conversion=dict(global_port_preparation=port_conversion,initial_wind_projection={})
    for name,bu,bv in [('closed_mean_ports',closed_u,closed_v),('open_mean_ports',open_u,open_v)]:
        model=OpenMeanRigidLidModel(base['pressure_edges_pa'],a['latitude'].shape,base['cell_m'],2*base['rotation_rate_s']*np.sin(np.deg2rad(a['latitude'])),
            u_boundary=bu,v_boundary=bv,external_temperature_k=a['temperature'],external_mixing_ratio=a['vapor']/mass[:,None,None],momentum_drag_s=base['momentum_drag_s'])
        u,v=raw_u.copy(),raw_v.copy();u[:,:,[0,-1]]=bu[:,:,[0,-1]];v[:,[0,-1]]=bv[:,[0,-1]]
        pu,pv,c=model.project_initial_wind(u,v)
        models[name]=model;conversion['initial_wind_projection'][name]=c
        seeds.update({name+'_raw_u':u,name+'_raw_v':v,name+'_u':pu,name+'_v':pv,name+'_boundary_u':bu,name+'_boundary_v':bv})
    for component in ['u','v']:
        left=seeds['closed_mean_ports_'+component];right=seeds['open_mean_ports_'+component]
        anomalies=lambda q:q-np.sum(mass[:,None,None]*q,axis=0,keepdims=True)/mass.sum()
        np.testing.assert_allclose(anomalies(left),anomalies(right),atol=1e-10,rtol=1e-10)
    return base,a,models,seeds,conversion

def run(path,out,preflight=False):
    plan=json.loads(path.read_text())
    for name,h in plan['sources'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Changed rigid-lid pilot source/input: '+name)
    prepared={region:prepare(plan,region) for region in plan['regions']}
    if preflight:
        print(json.dumps(dict(status='open_mean_inputs_prepared_no_integrations',actual_earth_initialized_integrations_started=0,
            regions={n:dict(shape=list(a['temperature'].shape),baroclinic_shear_match=True) for n,(_,a,_,_,_) in prepared.items()},plan_sha256=file_hash(path)),indent=2));return
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal rigid-lid plan before integration')
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous rigid-lid attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);rows=[];started=0
    for region,(base,a,models,seeds,conversion) in prepared.items():
        directory=out/region;directory.mkdir();np.savez_compressed(directory/'initial_winds.npz',**seeds);write_json(directory/'conversion.json',conversion)
        for scenario in plan['scenarios']:
            model=models[scenario]
            folder=directory/scenario;folder.mkdir()
            for dt in plan['timesteps_s']:
                row=dict(region=region,scenario=scenario,dt_s=dt,started=False,status='not_started');history=[];state=None;rain=None
                try:
                    state=model.initial_state(a['temperature'],a['vapor'],seeds[scenario+'_u'],seeds[scenario+'_v']);row['started']=True;started+=1
                    x0=model._velocity(state.u_east,state.v_south);initial_ke=float(.5*np.dot(x0,x0));initial_energy=float(gas_energy(a['temperature'],a['vapor'],model.mass).sum()+initial_ke);initial_water=float(a['vapor'].sum())
                    rain=np.zeros(model.shape);rain_h=np.zeros(model.shape);port_energy=0.;outward_water=0.
                    for step in range(plan['duration_s']//dt):
                        state=advance_boundary_with_convection(model,state,dt,relaxation_s=base['convection_relaxation_s'],neutral_tolerance_k=base['neutral_tolerance_k'],max_sweeps=base['maximum_convective_sweeps'],max_iterations=base['maximum_coupling_iterations'])
                        c=state.certificate;d=c['dynamics_before_adjustment'];rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2
                        power=c['external_power_w_m2']+c['prescribed_boundary_rotation_work_w_m2']-c['outward_boundary_gas_enthalpy_w_m2']-c['outward_boundary_geopotential_work_w_m2']
                        port_energy+=dt*power;outward_water+=dt*c['outward_boundary_vapor_kg_m2_s']
                        history.append(dict(time_s=(step+1)*dt,mean_rain_mm=float(rain.mean()),port_power_w_m2=power,outward_boundary_vapor_kg_m2_s=c['outward_boundary_vapor_kg_m2_s'],
                            maximum_column_mass_divergence_kg_m2_s=d['maximum_column_mass_divergence_kg_m2_s'],constraint_pressure_work_w_m2=d['rigid_lid_constraint_pressure_work_w_m2'],outward_constraint_geopotential_work_w_m2=d['outward_boundary_constraint_geopotential_work_w_m2'],outward_thermal_geopotential_work_w_m2=d['outward_boundary_thermal_geopotential_work_w_m2'],saddle_refinement=d['saddle_refinement'],
                            energy_error_j_m2=c['actual_combined_energy_rain_source_residual_j_m2'],water_error_kg_m2=c['actual_combined_water_rain_source_residual_kg_m2']))
                    fields=folder/(str(dt)+'.npz');np.savez_compressed(fields,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h)
                    x=model._velocity(state.u_east,state.v_south);final=float(gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+.5*np.dot(x,x)+rain_h.sum())
                    edge=np.zeros(rain.shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True
                    mass=model.column.cell_mass_kg_m2[:,None,None]
                    means=[np.sum(mass*flow,axis=0)/mass.sum() for flow in [state.u_east,state.v_south]]
                    row.update(status='completed',steps=len(history),history=history,initial_kinetic_energy_j_m2=initial_ke/model.n,
                        relative_total_energy_error=abs(final-initial_energy-port_energy*model.n)/abs(initial_energy),
                        relative_water_rain_error=abs(state.vapor_kg_m2.sum()+rain.sum()-initial_water+outward_water*model.n)/initial_water,
                        net_port_energy_j_m2=port_energy,net_outward_port_water_kg_m2=outward_water,mean_run_rain_mm=float(rain.mean()),
                        outer_grid_rain_fraction=float(rain[edge].sum()/rain.sum()) if rain.sum()>0 else None,
                        maximum_temperature_adjustment_k=float(abs(state.temperature_k-a['temperature']).max()),peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max())),
                        peak_depth_mean_velocity_ms=float(max(abs(q).max() for q in means)),fields_sha256=file_hash(fields))
                except Exception as error:
                    row.update(status='failed',error=repr(error),traceback=traceback.format_exc(),history=history,completed_steps=len(history))
                    if state is not None and rain is not None:
                        fields=folder/(str(dt)+'_partial.npz');np.savez_compressed(fields,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h);row['partial_fields_sha256']=file_hash(fields)
                write_json(folder/(str(dt)+'.json'),row);rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ['history','traceback']}),flush=True)
    write_json(out/'verification.json',dict(status='open_mean_boundary_pilot_complete',actual_earth_initialized_integrations_started=started,integrations_completed=sum(r['status']=='completed' for r in rows),
        legacy_benchmark_attempts_added=0,monthly_rainfall_skill_evaluated=False,adoption=False,literal_plan_sha256=file_hash(path),results=rows,
        scope='Paired identical source shear with closed or globally balanced open mean boundary flow. Affine initial projection signed KE change separate. Actual thermal and constraint pressure boundary work booked. Three extended-residual LU corrections with mixed-unit block scales; native mass/energy checks unchanged. No nonlinear momentum, surface-pressure evolution, thermal balance or monthly skill claim.'))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--preflight',action='store_true');a=ap.parse_args();run(a.plan,a.out,a.preflight)
