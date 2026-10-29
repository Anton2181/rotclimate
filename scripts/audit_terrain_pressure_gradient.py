"""Static terrain rest-state and perturbation forces under a literal declaration."""
from pathlib import Path
import argparse,json,sys,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load
from rotclimate.terrain_hydrostatics import surface_pressure_from_height,terrain_pressure_grid
from rotclimate.terrain_pressure_gradient import common_pressure_force
from rotclimate.terrain_apertures import horizontal_apertures


def audit(path,out):
    path=path.resolve();out=out.resolve();plan=json.loads(path.read_text())
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes(),'Commit static declaration first'
    assert not out.exists() or not any(out.iterdir()),'Retain previous outcomes'
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);fields=load(ROOT/'output/terrain_geometry_20261029/terrain_geometry.npz');meta=json.loads((ROOT/'output/terrain_geometry_20261029/verification.json').read_text());records={};arrays={}
    for region,record in meta['regions'].items():
        h=fields[region+'_elevation_m'];p0=record['reference_bottom_pressure_pa'];ptop=plan['top_pressure_pa'];old_ps=fields[region+'_reference_surface_pressure_pa'];old=fields[region+'_hybrid_edges_pa'];sigma=(old[:,0,0]-ptop)/(old_ps[0,0]-ptop);sigma[0]=1;sigma[-1]=0
        ps=surface_pressure_from_height(h,plan['reference_temperature_k'],sea_level_pressure_pa=p0,lapse_k_m=plan['reference_lapse_k_m']);grid=terrain_pressure_grid(ps,sigma,top_pressure_pa=ptop);ports=horizontal_apertures(grid);results={}
        for name in plan['probes']:
            anomaly=np.zeros_like(grid.dry_mass_kg_m2)
            if name=='bottom_layer_one_kelvin_eastern_half_anomaly':anomaly[0,:,h.shape[1]//2:]=1.
            else:assert name=='hydrostatic_rest_on_all_native_terrain_cells'
            force=common_pressure_force(grid,h,anomaly,plan['cell_m'],reference_temperature_k=plan['reference_temperature_k'],reference_pressure_pa=p0,reference_lapse_k_m=plan['reference_lapse_k_m']);maximum=float(max(abs(force.east_ms2).max(),abs(force.south_ms2).max()))
            if name.startswith('hydrostatic_rest'):assert maximum<plan['rest_acceleration_max_ms2']
            else:assert maximum>1e-8,'Warm pressure gradient must not be silently zeroed'
            assert not np.any(force.east_ms2[ports.east_kg_m2==0]);assert not np.any(force.south_ms2[ports.south_kg_m2==0])
            results[name]=dict(maximum_horizontal_acceleration_ms2=maximum,force_on_closed_ports_zero=True)
            arrays.update({region+'_'+name+'_east_force_ms2':force.east_ms2,region+'_'+name+'_south_force_ms2':force.south_ms2})
        records[region]=results;arrays[region+'_reference_surface_pressure_pa']=ps
    np.savez_compressed(out/'pressure_forces.npz',**arrays)
    result=dict(status='static_terrain_rest_and_thermal_response_pass',regions=records,literal_plan_sha256=file_hash(path),audit_source_sha256=file_hash(Path(__file__)),fields_sha256=file_hash(out/'pressure_forces.npz'),actual_climate_integrations_started=0,physics_adoption=False,scope='Native terrain heights and pressure interfaces with a declared common dry reference; static force diagnosis only. Rest and nonzero thermal response are necessary tests, not a proof of complete pressure-work/energy-compatible dynamics or rainfall accuracy.')
    write_json(out/'verification.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();audit(a.plan,a.out)
