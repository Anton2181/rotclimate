"""Frozen24h forced/unforced partial-column Earth-input smoke comparison."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from open_mean_pilot import prepare as prepare_wind
from local_benchmark_protocol import file_hash,write_json
from rotclimate.surface_coupling import SurfaceState,checked_surface,surface_enthalpy,receive_precipitation,advance_surface_coupled
from rotclimate.pressure_moist import PressureMoistState,gas_energy
from rotclimate.pressure_boundary import advance_boundary_with_convection
from rotclimate.column_forcing import STEFAN_BOLTZMANN
from rotclimate.column_thermodynamics import RD,CP,G
from rotclimate.astronomy import declination,distance_factor,daily_insolation


def prepare(plan,region):
    base,a,models,seeds,conversion=prepare_wind(plan,region);model=models['open_mean_ports'];p=plan['surface']
    sea=a['archived_surface_temperature_c']+273.15+plan['source_lapse_k_m']*a['elevation']
    liquid=np.where(a['land'],p['land_initial_liquid_kg_m2'],p['ocean_initial_liquid_kg_m2'])
    surface=checked_surface(SurfaceState(sea,liquid,p['substrate_capacity_j_m2_k']),model.shape)
    surface=receive_precipitation(surface,a['initial_conversion_rain'],a['initial_conversion_rain_enthalpy'])
    state=model.initial_state(a['temperature'],a['vapor'],seeds['open_mean_ports_u'],seeds['open_mean_ports_v'])
    height=CP/G*a['temperature'][0]*((model.column.edges_pa[0]/model.column.centers_pa[0])**(RD/CP)-1.)
    outside_t=np.maximum(plan['omitted_upper']['minimum_temperature_k'],sea*(plan['omitted_upper']['representative_pressure_fraction']*model.column.edges_pa[-1]/model.column.edges_pa[0])**(RD*plan['source_lapse_k_m']/G))
    kappa_lw=plan['radiation']['dry_lw_full_column_depth']*G/model.column.edges_pa[0]
    kappa_sw=plan['radiation']['dry_sw_full_column_depth']*G/model.column.edges_pa[0]
    incoming_lw=STEFAN_BOLTZMANN*outside_t**4*(-np.expm1(-kappa_lw*model.column.edges_pa[-1]/G))
    return base,a,model,state,surface,height,incoming_lw,conversion,kappa_lw,kappa_sw


def run(path,out,preflight=False):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed forcing pilot source/input: '+n)
    prepared={r:prepare(plan,r) for r in plan['regions']}
    if preflight:
        print(json.dumps(dict(status='surface_forcing_inputs_prepared_no_integrations',actual_earth_initialized_integrations_started=0,
            regions={n:dict(shape=list(a['temperature'].shape),surface_temperature_min_k=float(s.temperature_k.min()),surface_temperature_max_k=float(s.temperature_k.max())) for n,(_,a,_,_,s,*_) in prepared.items()},literal_plan_sha256=file_hash(path)),indent=2));return
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal surface forcing declaration first')
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous forcing attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);rows=[];started=0
    for region,(base,a,model,initial,initial_surface,height,incoming_lw,conversion,kappa_lw,kappa_sw) in prepared.items():
        directory=out/region;directory.mkdir();write_json(directory/'wind_conversion.json',conversion)
        np.savez_compressed(directory/'initial.npz',temperature=initial.temperature_k,vapor=initial.vapor_kg_m2,u=initial.u_east,v=initial.v_south,
            surface_temperature=initial_surface.temperature_k,surface_liquid=initial_surface.liquid_kg_m2,substrate_capacity=initial_surface.substrate_capacity_j_m2_k,
            latitude=a['latitude'],longitude=a['longitude'],land=a['land'],reference_height=height,incoming_upper_longwave=incoming_lw,
            initial_conversion_rain=a['initial_conversion_rain'],initial_conversion_rain_enthalpy=a['initial_conversion_rain_enthalpy'],pressure_edges=np.array(base['pressure_edges_pa']))
        p=plan['surface'];albedo=np.where(a['land'],p['land_albedo'],p['ocean_albedo']);z0=np.where(a['land'],p['land_roughness_m'],p['ocean_roughness_m']);z0h=np.where(a['land'],p['land_scalar_roughness_m'],p['ocean_scalar_roughness_m'])
        availability=np.where(a['land'],p['land_availability_scale_kg_m2'],p['ocean_availability_scale_kg_m2'])
        start_day=base['regions'][region]['model_day']
        for scenario in plan['scenarios']:
            folder=directory/scenario;folder.mkdir()
            for dt in plan['timesteps_s']:
                row=dict(region=region,scenario=scenario,dt_s=dt,started=False,status='not_started');history=[];state=initial;surface=initial_surface
                rain=np.zeros(model.shape);rain_h=np.zeros(model.shape);external_energy=0.;outward_water=0.;net_evap=0.
                try:
                    row['started']=True;started+=1;x0=model._velocity(state.u_east,state.v_south)
                    initial_energy=float(gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+.5*np.dot(x0,x0)+surface_enthalpy(surface).sum());initial_water=float(state.vapor_kg_m2.sum()+surface.liquid_kg_m2.sum())
                    for step in range(plan['duration_s']//dt):
                        if scenario=='forced':
                            orbital=plan['orbit'];day=start_day+step*dt/86400
                            solar=daily_insolation(a['latitude'],declination(day,orbital['tilt_deg'],orbital['winter_solstice_day'],orbital['year_days']),distance_factor(day,orbital['eccentricity'],orbital['perihelion_day'],orbital['year_days']))
                            solar*=(1-plan['radiation']['outside_solar_reflection'])*np.exp(-kappa_sw*model.column.edges_pa[-1]/G)
                            result=advance_surface_coupled(model,state,surface,dt,longwave_optical_depth=kappa_lw*model.mass+plan['radiation']['vapor_lw_opacity_m2_kg']*state.vapor_kg_m2,
                                shortwave_optical_depth=kappa_sw*model.mass,reference_height_m=height,roughness_m=z0,scalar_roughness_m=z0h,availability_scale_kg_m2=availability,
                                solar_in_w_m2=solar,longwave_in_w_m2=incoming_lw,surface_albedo=albedo,surface_emissivity=p['emissivity'],convection_relaxation_s=base['convection_relaxation_s'],
                                neutral_tolerance_k=base['neutral_tolerance_k'],maximum_convective_sweeps=base['maximum_convective_sweeps'],maximum_coupling_iterations=base['maximum_coupling_iterations'])
                            state,surface=result.atmosphere,result.surface;rain+=result.rain_kg_m2;rain_h+=result.rain_enthalpy_j_m2;c=result.certificate
                            external_energy+=c['net_external_energy_j_m2'];outward_water+=c['net_outward_water_kg_m2'];local=c['local_forcing'];net_evap+=local['mean_vapor_transfer_kg_m2'];d=c['dynamics_before_surface_return']
                            top=local['mean_net_top_incoming_w_m2']
                        else:
                            dynamic=advance_boundary_with_convection(model,state,dt,relaxation_s=base['convection_relaxation_s'],neutral_tolerance_k=base['neutral_tolerance_k'],max_sweeps=base['maximum_convective_sweeps'],max_iterations=base['maximum_coupling_iterations'])
                            surface=receive_precipitation(surface,dynamic.ground_rain_kg_m2,dynamic.ground_rain_enthalpy_j_m2);rain+=dynamic.ground_rain_kg_m2;rain_h+=dynamic.ground_rain_enthalpy_j_m2;d=dynamic.certificate
                            external_energy+=dt*(d['external_power_w_m2']+d['prescribed_boundary_rotation_work_w_m2']-d['outward_boundary_gas_enthalpy_w_m2']-d['outward_boundary_geopotential_work_w_m2']);outward_water+=dt*d['outward_boundary_vapor_kg_m2_s'];top=0.
                            state=PressureMoistState(dynamic.temperature_k,dynamic.vapor_kg_m2,dynamic.u_east,dynamic.v_south,np.zeros(model.shape),np.zeros(model.shape),d)
                        x=model._velocity(state.u_east,state.v_south);energy=float(gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+.5*np.dot(x,x)+surface_enthalpy(surface).sum());water=float(state.vapor_kg_m2.sum()+surface.liquid_kg_m2.sum())
                        history.append(dict(time_s=(step+1)*dt,mean_rain_mm=float(rain.mean()),mean_surface_temperature_k=float(surface.temperature_k.mean()),mean_atmospheric_temperature_k=float(state.temperature_k.mean()),
                            mean_net_top_radiation_w_m2=top,cumulative_net_external_energy_j_m2=external_energy,cumulative_outward_water_kg_m2=outward_water,cumulative_net_evaporation_kg_m2=net_evap,
                            actual_energy_residual_j_m2=(energy-initial_energy-external_energy*model.n)/model.n,actual_water_residual_kg_m2=(water-initial_water+outward_water*model.n)/model.n,
                            maximum_column_mass_residual_kg_m2_s=d['dynamics_before_adjustment']['maximum_column_mass_divergence_kg_m2_s']))
                    fields=folder/(str(dt)+'.npz');np.savez_compressed(fields,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,
                        surface_temperature=surface.temperature_k,surface_liquid=surface.liquid_kg_m2,substrate_capacity=surface.substrate_capacity_j_m2_k,rain=rain,rain_enthalpy=rain_h)
                    edge=np.zeros(model.shape,bool);edge[[0,-1]]=True;edge[:,[0,-1]]=True
                    row.update(status='completed',steps=len(history),history=history,relative_total_energy_error=abs(energy-initial_energy-external_energy*model.n)/abs(initial_energy),
                        relative_water_error=abs(water-initial_water+outward_water*model.n)/initial_water,mean_run_rain_mm=float(rain.mean()),outer_grid_rain_fraction=float(rain[edge].sum()/rain.sum()) if rain.sum()>0 else None,
                        mean_net_evaporation_kg_m2=net_evap,maximum_atmosphere_temperature_adjustment_k=float(abs(state.temperature_k-initial.temperature_k).max()),
                        maximum_surface_temperature_change_k=float(abs(surface.temperature_k-initial_surface.temperature_k).max()),net_external_energy_j_m2=external_energy,net_outward_water_kg_m2=outward_water,fields_sha256=file_hash(fields))
                except Exception as error:
                    fields=folder/(str(dt)+'_partial.npz');np.savez_compressed(fields,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,surface_temperature=surface.temperature_k,surface_liquid=surface.liquid_kg_m2,substrate_capacity=surface.substrate_capacity_j_m2_k,rain=rain,rain_enthalpy=rain_h)
                    row.update(status='failed',error=repr(error),traceback=traceback.format_exc(),completed_steps=len(history),history=history,partial_fields_sha256=file_hash(fields))
                write_json(folder/(str(dt)+'.json'),row);rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ['history','traceback']}),flush=True)
    write_json(out/'verification.json',dict(status='surface_forcing_24h_pilot_complete',actual_earth_initialized_integrations_started=started,integrations_completed=sum(r['status']=='completed' for r in rows),legacy_benchmark_attempts_added=0,monthly_skill=False,adoption=False,literal_plan_sha256=file_hash(path),results=rows,
        scope='24h forced/unforced Earth-input smoke, fixed declared grey/neutral flux assumptions and finite surface water/energy. Partial380hPa top has explicit exterior solar/LW, not TOA. No observed data, terrain/nonlinear momentum, monthly calibration or adoption.'))


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--preflight',action='store_true');a=ap.parse_args();run(a.plan,a.out,a.preflight)
