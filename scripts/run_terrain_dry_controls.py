"""All declared dry subsystem trajectories, preserving every failure and state."""
from pathlib import Path
import argparse,json,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_dry import TerrainDryModel
from rotclimate.column_thermodynamics import CP


def run(path,out):
    path=path.resolve();out=out.resolve();plan=json.loads(path.read_text())
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Commit dry control declaration first'
    assert not out.exists() or not any(out.iterdir()),'Retain all previous attempts'
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);meta=json.loads((ROOT/'output/terrain_geometry_20261029/verification.json').read_text());a=load(ROOT/'output/terrain_geometry_20261029/terrain_geometry.npz');records=[]
    for region in plan['regions']:
        record=meta['regions'][region];h=a[region+'_elevation_m'];p0=record['reference_bottom_pressure_pa'];ptop=plan['top_pressure_pa'];old_ps=a[region+'_reference_surface_pressure_pa'];old=a[region+'_hybrid_edges_pa'];sigma=(old[:,0,0]-ptop)/(old_ps[0,0]-ptop);sigma[0]=1;sigma[-1]=0;ps=surface_pressure_from_height(h,plan['reference_temperature_k'],sea_level_pressure_pa=p0,lapse_k_m=plan['reference_lapse_k_m']);grid=terrain_pressure_grid(ps,sigma,top_pressure_pa=ptop);f=2*plan['earth_rotation_rate_s']*np.sin(np.radians(a[region+'_latitude']))
        for dt in plan['timesteps_s']:
            folder=out/f'{region}_{dt}';folder.mkdir();model=TerrainDryModel(grid,h,f,plan['cell_m'],reference_temperature_k=plan['reference_temperature_k'],reference_pressure_pa=p0,reference_lapse_k_m=plan['reference_lapse_k_m']);temperature=model.reference_mean.copy();temperature[0,:,h.shape[1]//2:]+=1.;state=model.initial_state(temperature,np.zeros_like(model.apertures.east_kg_m2),np.zeros_like(model.apertures.south_kg_m2));history=[];started=time.monotonic();row=dict(region=region,dt_s=dt,status='started',synthetic_native_geometry_integrations_started=1,earth_climate_initialized_integrations_started=0)
            np.savez_compressed(folder/'initial.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms,layer_mass=grid.dry_mass_kg_m2,pressure_edges=grid.edges_pa,latitude=a[region+'_latitude'],longitude=a[region+'_longitude'],elevation=h)
            write_json(out/'progress.json',dict(active=row,finished_cases=records))
            try:
                for step in range(plan['duration_s']//dt):
                    state=model.advance(state,dt,temperature_tolerance_k=plan['temperature_tolerance_k'],max_iterations=plan['maximum_coupling_iterations']);x=model._pack(state.east_speed_ms,state.south_speed_ms);actual_gas_change=float((CP*model.mass*(state.temperature_k-temperature)).sum());actual_ke=float(.5*(x@x));history.append(dict(step=step+1,time_s=(step+1)*dt,actual_gas_change_j_m2_sum=actual_gas_change,actual_kinetic_energy_j_m2_sum=actual_ke,actual_energy_residual_since_initial_j_m2_sum=actual_gas_change+actual_ke,certificate=state.certificate))
                    if (step+1)*dt%3600==0:
                        np.savez_compressed(folder/f'hour_{(step+1)*dt//3600}.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms);write_json(folder/f'hour_{(step+1)*dt//3600}.json',history[-1]);print(json.dumps(dict(region=region,dt_s=dt,completed_hours=(step+1)*dt//3600,energy_residual=actual_gas_change+actual_ke)),flush=True)
                row.update(status='completed',completed_steps=len(history))
            except Exception as error:row.update(status='failed',completed_steps=len(history),error=repr(error),traceback=traceback.format_exc())
            np.savez_compressed(folder/'final_or_partial.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms)
            row.update(fields_sha256=file_hash(folder/'final_or_partial.npz'),initial_sha256=file_hash(folder/'initial.npz'),history=history,wall_seconds=time.monotonic()-started);write_json(folder/'verification.json',row);records.append(row);write_json(out/'progress.json',dict(active=None,finished_cases=records));print(json.dumps({k:v for k,v in row.items() if k not in ['history','traceback']}),flush=True)
    write_json(out/'verification.json',dict(status='all_declared_dry_subsystem_attempts_retained',literal_plan_sha256=file_hash(path),driver_sha256=file_hash(Path(__file__)),synthetic_native_geometry_integrations_started=len(records),synthetic_integrations_completed=sum(r['status']=='completed' for r in records),earth_climate_initialized_integrations_started=0,physics_adoption=False,results=records,scope='Actual six-hour closed dry integrations on native regional terrain, using synthetic reference/anomaly/zero wind rather than climate initialization. No vapor/rain, open boundaries, nonlinear momentum, surface forcing, calibration or atlas climate adoption. Every declared failed partial retained.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan,a.out)
