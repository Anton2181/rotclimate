"""Paired native trajectories and saved static states for compression caching."""
from pathlib import Path
import argparse,json,subprocess,sys,time,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from rotclimate.terrain_hydrostatics import TerrainPressureGrid
from rotclimate.terrain_advective import TerrainAdvectiveModel
from rotclimate.terrain_pressure_work import compression_power
from rotclimate.terrain_work_cache import TerrainWorkCache,cached_work_model


def run(path,out):
    path=path.resolve();out=out.resolve();plan=json.loads(path.read_text())
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Commit cache qualification first'
    assert not out.exists() or not any(out.iterdir());out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);meta=json.loads((ROOT/'output/terrain_geometry_20261029/verification.json').read_text());rows=[];original=compression_power
    for region in plan['regions']:
        a=load(ROOT/plan['initial_fields'][region]);p=a['pressure_edges'];grid=TerrainPressureGrid(p,.5*(p[:-1]+p[1:]),a['layer_mass'],p[0],float(p[-1,0,0]));f=2*plan['earth_rotation_rate_s']*np.sin(np.radians(a['latitude']));kwargs=dict(reference_temperature_k=plan['reference_temperature_k'],reference_pressure_pa=meta['regions'][region]['reference_bottom_pressure_pa'],reference_lapse_k_m=plan['reference_lapse_k_m']);models={};states={};timing={};histories={};statuses={};errors={};build={}
        for name,cls in [('reference',TerrainAdvectiveModel),('cached',cached_work_model(TerrainAdvectiveModel))]:
            started=time.perf_counter();model=cls(grid,a['elevation'],f,plan['cell_m'],**kwargs);build[name]=time.perf_counter()-started;models[name]=model;states[name]=model.initial_state(a['temperature'],a['east_speed'],a['south_speed']);timing[name]=dict(cpu_seconds=0.,wall_seconds=0.);histories[name]=[];statuses[name]='running'
        assert models['cached'].advance.__func__.__code__ is TerrainAdvectiveModel.advance.__code__
        maxima=dict(temperature=0.,east_speed=0.,south_speed=0.);differences=[]
        write_json(out/'progress.json',dict(active_region=region,finished=rows,new_earth_climate_initializations=0))
        for step in range(plan['duration_s']//plan['timestep_s']):
            for name in (['reference','cached'] if step%2==0 else ['cached','reference']):
                if statuses[name]!='running':continue
                cpu=time.process_time();wall=time.perf_counter()
                try:
                    states[name]=models[name].advance(states[name],plan['timestep_s'],temperature_tolerance_k=plan['temperature_tolerance_k'],velocity_tolerance_ms=plan['velocity_tolerance_ms'],max_iterations=plan['maximum_coupling_iterations']);histories[name].append(dict(step=step+1,certificate=states[name].certificate))
                except Exception as error:statuses[name]='failed';errors[name]=dict(error=repr(error),traceback=traceback.format_exc(),completed_steps=len(histories[name]))
                finally:timing[name]['cpu_seconds']+=time.process_time()-cpu;timing[name]['wall_seconds']+=time.perf_counter()-wall
            if all(statuses[n]=='running' for n in models):
                delta={key:float(abs(getattr(states['cached'],attribute)-getattr(states['reference'],attribute)).max()) for key,attribute in [('temperature','temperature_k'),('east_speed','east_speed_ms'),('south_speed','south_speed_ms')]}
                for key,value in delta.items():maxima[key]=max(maxima[key],value)
                differences.append(dict(step=step+1,**delta))
            if (step+1)*plan['timestep_s']%3600==0:print(json.dumps(dict(region=region,hour=(step+1)*plan['timestep_s']//3600,maximum_differences=maxima)),flush=True)
        for name in models:
            if statuses[name]=='running':statuses[name]='completed'
            folder=out/(region+'_'+name);folder.mkdir();state=states[name];np.savez_compressed(folder/'final_or_partial.npz',temperature=state.temperature_k,east_speed=state.east_speed_ms,south_speed=state.south_speed_ms);write_json(folder/'verification.json',dict(status=statuses[name],timing=timing[name],construction_seconds=build[name],history=histories[name],error=errors.get(name),fields_sha256=file_hash(folder/'final_or_partial.npz')))
        qualified=all(statuses[n]=='completed' for n in statuses) and all(v<=plan['maximum_state_difference'] for v in maxima.values());row=dict(region=region,statuses=statuses,qualified_numerical_equivalence=qualified,maximum_state_differences=maxima,step_differences=differences,timing=timing,construction_seconds=build,cpu_speedup=timing['reference']['cpu_seconds']/timing['cached']['cpu_seconds']);rows.append(row);write_json(out/'progress.json',dict(active_region=None,finished=rows,new_earth_climate_initializations=0));print(json.dumps({k:v for k,v in row.items() if k!='step_differences'}),flush=True)
    assert TerrainAdvectiveModel.advance.__globals__['compression_power'] is original
    write_json(out/'verification.json',dict(status='all_paired_cache_controls_retained',literal_plan_sha256=file_hash(path),driver_sha256=file_hash(Path(__file__)),results=rows,synthetic_native_geometry_integrations_started=6,synthetic_integrations_completed=sum(v=='completed' for r in rows for v in r['statuses'].values()),new_earth_climate_initializations=0,unchanged_advance_code_body=True,original_globals_unchanged=True,physics_adoption=False,scope='Numerical quadrature cache only. Matched paired trajectories, alternate execution order and both CPU/wall timing; setup cost separate. Every failure and partial retained. No rainfall or climate skill claim.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan,a.out)
