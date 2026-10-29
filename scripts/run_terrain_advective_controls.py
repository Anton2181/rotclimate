"""All paired dry nonlinear-momentum trajectories from a literal declaration."""
from pathlib import Path
import argparse,json,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_work import project_column_mass
from rotclimate.terrain_advective import TerrainAdvectiveModel
from rotclimate.column_thermodynamics import CP


def run(path,out):
    path=path.resolve();out=out.resolve();plan=json.loads(path.read_text())
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Commit paired declaration first'
    assert not out.exists() or not any(out.iterdir()),'Retain earlier attempts'
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);meta=json.loads((ROOT/'output/terrain_geometry_20261029/verification.json').read_text());a=load(ROOT/'output/terrain_geometry_20261029/terrain_geometry.npz');records=[]
    for region in plan['regions']:
        record=meta['regions'][region];h=a[region+'_elevation_m'];p0=record['reference_bottom_pressure_pa'];ptop=plan['top_pressure_pa'];old_ps=a[region+'_reference_surface_pressure_pa'];old=a[region+'_hybrid_edges_pa'];sigma=(old[:,0,0]-ptop)/(old_ps[0,0]-ptop);sigma[0]=1;sigma[-1]=0;ps=surface_pressure_from_height(h,plan['reference_temperature_k'],sea_level_pressure_pa=p0,lapse_k_m=plan['reference_lapse_k_m']);grid=terrain_pressure_grid(ps,sigma,top_pressure_pa=ptop);f=2*plan['earth_rotation_rate_s']*np.sin(np.radians(a[region+'_latitude']));apertures=horizontal_apertures(grid);ny,nx=h.shape
        ue=4*np.cos(np.pi*(np.arange(ny)+.5)/ny)[:,None]*np.sin(np.pi*np.arange(1,nx)/nx)[None,:];vs=-4*np.sin(np.pi*np.arange(1,ny)/ny)[:,None]*np.cos(np.pi*(np.arange(nx)+.5)/nx)[None,:]
        raw_u=np.where(apertures.east_kg_m2>0,np.broadcast_to(ue,apertures.east_kg_m2.shape),0.);raw_v=np.where(apertures.south_kg_m2>0,np.broadcast_to(vs,apertures.south_kg_m2.shape),0.);initial_u,initial_v,projection=project_column_mass(grid,raw_u,raw_v,plan['cell_m']);write_json(out/(region+'_initial_projection.json'),projection)
        for backend,enabled in plan['backends'].items():
            folder=out/f'{region}_{backend}';folder.mkdir();model=TerrainAdvectiveModel(grid,h,f,plan['cell_m'],reference_temperature_k=plan['reference_temperature_k'],reference_pressure_pa=p0,reference_lapse_k_m=plan['reference_lapse_k_m'],advect_momentum=enabled);temperature=model.reference_mean.copy();temperature[0,:,h.shape[1]//2:]+=1.;state=model.initial_state(temperature,initial_u,initial_v);x0=model._pack(initial_u,initial_v);ke0=float(.5*(x0@x0));history=[];started=time.monotonic();row=dict(region=region,backend=backend,nonlinear_momentum_transport_enabled=enabled,status='started',synthetic_native_geometry_integrations_started=1,earth_climate_initialized_integrations_started=0)
            np.savez_compressed(folder/'initial.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms,layer_mass=grid.dry_mass_kg_m2,pressure_edges=grid.edges_pa,latitude=a[region+'_latitude'],longitude=a[region+'_longitude'],elevation=h,initial_kinetic_energy_j_m2_sum=ke0)
            write_json(out/'progress.json',dict(active=row,finished_cases=records))
            try:
                dt=plan['timestep_s']
                for step in range(plan['duration_s']//dt):
                    state=model.advance(state,dt,temperature_tolerance_k=plan['temperature_tolerance_k'],velocity_tolerance_ms=plan['velocity_tolerance_ms'],max_iterations=plan['maximum_coupling_iterations']);x=model._pack(state.east_speed_ms,state.south_speed_ms);gas_change=float((CP*model.mass*(state.temperature_k-temperature)).sum());ke=float(.5*(x@x));history.append(dict(step=step+1,time_s=(step+1)*dt,actual_gas_change_j_m2_sum=gas_change,actual_kinetic_energy_j_m2_sum=ke,actual_kinetic_change_j_m2_sum=ke-ke0,actual_energy_residual_since_initial_j_m2_sum=gas_change+ke-ke0,certificate=state.certificate))
                    if (step+1)*dt%3600==0:
                        hour=(step+1)*dt//3600;np.savez_compressed(folder/f'hour_{hour}.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms);write_json(folder/f'hour_{hour}.json',history[-1]);print(json.dumps(dict(region=region,backend=backend,completed_hours=hour,energy_residual=gas_change+ke-ke0)),flush=True)
                row.update(status='completed',completed_steps=len(history))
            except Exception as error:row.update(status='failed',completed_steps=len(history),error=repr(error),traceback=traceback.format_exc())
            np.savez_compressed(folder/'final_or_partial.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms);row.update(fields_sha256=file_hash(folder/'final_or_partial.npz'),initial_sha256=file_hash(folder/'initial.npz'),initial_projection=projection,history=history,wall_seconds=time.monotonic()-started);write_json(folder/'verification.json',row);records.append(row);write_json(out/'progress.json',dict(active=None,finished_cases=records));print(json.dumps({k:v for k,v in row.items() if k not in ['history','traceback','initial_projection']}),flush=True)
    write_json(out/'verification.json',dict(status='all_declared_nonlinear_controls_retained',literal_plan_sha256=file_hash(path),driver_sha256=file_hash(Path(__file__)),synthetic_native_geometry_integrations_started=len(records),synthetic_integrations_completed=sum(r['status']=='completed' for r in records),earth_climate_initialized_integrations_started=0,physics_adoption=False,results=records,scope='Same centered-enthalpy model body, momentum transport explicitly off/on, matched synthetic states and one shared preparation projection. Native closed dry trajectories, not rainfall or climate initialization. All failed partials retained.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan,a.out)
