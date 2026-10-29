"""Static native-terrain pressure/compression tests under a frozen declaration."""
from pathlib import Path
import argparse,json,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.terrain_pressure_gradient import common_pressure_force
from rotclimate.terrain_pressure_work import project_column_mass,compression_power


def audit(path,out):
    path=path.resolve();out=out.resolve();plan=json.loads(path.read_text())
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Commit static declaration first'
    assert not out.exists() or not any(out.iterdir());out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan)
    fields=load(ROOT/'output/terrain_geometry_20261029/terrain_geometry.npz');meta=json.loads((ROOT/'output/terrain_geometry_20261029/verification.json').read_text());records={};arrays={}
    for region,record in meta['regions'].items():
        h=fields[region+'_elevation_m'];p0=record['reference_bottom_pressure_pa'];ptop=plan['top_pressure_pa'];old_ps=fields[region+'_reference_surface_pressure_pa'];old=fields[region+'_hybrid_edges_pa'];sigma=(old[:,0,0]-ptop)/(old_ps[0,0]-ptop);sigma[0]=1;sigma[-1]=0;ps=surface_pressure_from_height(h,plan['reference_temperature_k'],sea_level_pressure_pa=p0,lapse_k_m=plan['reference_lapse_k_m']);grid=terrain_pressure_grid(ps,sigma,top_pressure_pa=ptop);ports=horizontal_apertures(grid);rows=[]
        for seed in plan['seeds']:
            rng=np.random.default_rng(seed);u=rng.normal(0,plan['raw_velocity_standard_deviation_ms'],ports.east_kg_m2.shape);v=rng.normal(0,plan['raw_velocity_standard_deviation_ms'],ports.south_kg_m2.shape);u,v,projection=project_column_mass(grid,u,v,plan['cell_m']);delta=rng.uniform(*plan['temperature_anomaly_uniform_range_k'],grid.dry_mass_kg_m2.shape)
            force=common_pressure_force(grid,h,delta,plan['cell_m'],reference_temperature_k=plan['reference_temperature_k'],reference_pressure_pa=p0,reference_lapse_k_m=plan['reference_lapse_k_m']);compression=compression_power(grid,u,v,plan['cell_m'],delta,reference_temperature_k=plan['reference_temperature_k'],reference_pressure_pa=p0,reference_lapse_k_m=plan['reference_lapse_k_m']);pressure=float((ports.east_kg_m2*u*force.east_ms2).sum()+(ports.south_kg_m2*v*force.south_ms2).sum());thermal=float(compression.layer_power_w_m2.sum());residual=pressure+thermal;scale=max(abs(pressure),abs(thermal),1.);error=abs(residual)/scale
            assert error<plan['maximum_normalized_pressure_compression_work_error']
            rows.append(dict(seed=seed,pressure_mechanical_power_w_m2_sum=pressure,compression_power_w_m2_sum=thermal,actual_signed_work_residual_w_m2_sum=residual,normalized_absolute_work_error=error,normalization_scale_w_m2=scale,maximum_ground_omega_pa_s=compression.maximum_lower_boundary_omega_pa_s,projection=projection))
            for key,value in dict(east_speed_ms=u,south_speed_ms=v,temperature_anomaly_k=delta,compression_power_w_m2=compression.layer_power_w_m2,interface_omega_pa_s=compression.interface_omega_pa_s).items():arrays[f'{region}_{seed}_{key}']=value
        records[region]=rows
    np.savez_compressed(out/'pressure_work.npz',**arrays)
    result=dict(status='nine_static_terrain_work_checks_pass',regions=records,literal_plan_sha256=file_hash(path),audit_source_sha256=file_hash(Path(__file__)),fields_sha256=file_hash(out/'pressure_work.npz'),actual_climate_integrations_started=0,physics_adoption=False,scope='Three declared synthetic velocity/anomaly seeds per actual terrain grid. Initial dry-mass projection and independent pressure/continuity/compression diagnostics only. No energy residual redistributed as heat; no time integration, open boundaries, tracer transport, climate score or physics adoption.')
    write_json(out/'verification.json',result);print(json.dumps({k:v for k,v in result.items() if k!='regions'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();audit(a.plan,a.out)
