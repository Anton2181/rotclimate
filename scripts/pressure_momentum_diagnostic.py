"""Frozen momentum-only initialization tradeoff; no Earth time integrations."""
from pathlib import Path
import argparse,json,subprocess,sys
import numpy as np
from scipy.sparse.linalg import spsolve
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from pressure_boundary_pilot import inputs
from local_benchmark_protocol import file_hash,write_json
from rotclimate.pressure_boundary import BoundaryPressureMoistModel
from rotclimate.momentum_initialization import least_acceleration_wind,initial_transport_tendency


def run(path,out):
    plan=json.loads(path.read_text())
    for name,h in plan['sources'].items():
        if file_hash(ROOT/name)!=h:raise ValueError('Changed frozen momentum input/source: '+name)
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit exact diagnostic declaration first')
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous diagnostic outcomes')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan)
    source_plan=json.loads((ROOT/plan['boundary_plan']).read_text());rows=[]
    for region in source_plan['regions']:
        a,seed_u,seed_v,ub,vb=inputs(source_plan,region);f=2*source_plan['rotation_rate_s']*np.sin(np.deg2rad(a['latitude']))
        for scenario in plan['scenarios']:
            ports=scenario=='prescribed_ports';bu=ub if ports else np.zeros_like(ub);bv=vb if ports else np.zeros_like(vb)
            model=BoundaryPressureMoistModel(source_plan['pressure_edges_pa'],a['latitude'].shape,source_plan['cell_m'],f,
                u_boundary=bu,v_boundary=bv,external_temperature_k=a['temperature'],external_mixing_ratio=a['vapor']/(-np.diff(source_plan['pressure_edges_pa'])/9.80665)[:,None,None],momentum_drag_s=source_plan['momentum_drag_s'])
            ref_u,ref_v=seed_u.copy(),seed_v.copy();ref_u[:,:,[0,-1]]=bu[:,:,[0,-1]];ref_v[:,[0,-1]]=bv[:,[0,-1]]
            candidates=[('archived_seed',ref_u,ref_v,{})]
            for tau in plan['correction_times_s']:
                r=least_acceleration_wind(model,a['temperature'],ref_u,ref_v,correction_time_s=tau)
                candidates.append(('regularized_'+str(tau),r.u_east,r.v_south,r.certificate))
            force=model._pressure_force(a['temperature'])+model.boundary_rotation_force
            steady_x=spsolve(model.momentum,-force);steady_u,steady_v=model._unpack(steady_x)
            candidates.append(('formal_steady_drag',steady_u,steady_v,dict(scope='Formal frozen-temperature steady momentum solution only; no thermal/moist balance or speed clipping.')))
            directory=out/region/scenario;directory.mkdir(parents=True)
            for name,u,v,certificate in candidates:
                x=model._velocity(u,v);res=model.momentum@x+force
                acceleration=np.r_[(res[:model.n_u].reshape(model.nz,*u[:,:,1:-1].shape[1:])/model.sqrt_mass[:,None,None]).ravel(),
                    (res[model.n_u:].reshape(model.nz,*v[:,1:-1].shape[1:])/model.sqrt_mass[:,None,None]).ravel()]
                tendency=initial_transport_tendency(model,a['temperature'],a['vapor'],u,v)
                div=(np.diff(u,axis=2)+np.diff(v,axis=1))/model.dx
                pressure_velocity=model.column.pressure_velocity(div)
                fields=directory/(name+'.npz');np.savez_compressed(fields,u=u,v=v,temperature_tendency_k_s=tendency['temperature_k_s'],vapor_tendency_kg_m2_s=tendency['vapor_kg_m2_s'],pressure_velocity_pa_s=pressure_velocity)
                row=dict(region=region,scenario=scenario,candidate=name,certificate=certificate,fields_sha256=file_hash(fields),
                    mass_weighted_acceleration_norm=float(np.linalg.norm(res)),maximum_acceleration_ms2=float(abs(acceleration).max()),
                    peak_level_velocity_ms=float(max(abs(u).max(),abs(v).max())),
                    maximum_temperature_tendency_k_day=float(abs(tendency['temperature_k_s']).max()*86400),
                    temperature_tendency_rms_k_day=float(np.sqrt(np.mean(tendency['temperature_k_s']**2))*86400),
                    maximum_pressure_velocity_pa_s=float(abs(pressure_velocity).max()),
                    kinetic_energy_j_m2=float(.5*np.dot(x,x)/model.n),
                    velocity_correction_rms_ms=float(np.sqrt((np.sum((u[:,:,1:-1]-ref_u[:,:,1:-1])**2)+np.sum((v[:,1:-1]-ref_v[:,1:-1])**2))/(model.n_u+model.n_v))))
                write_json(directory/(name+'.json'),row);rows.append(row)
                print(json.dumps({k:v for k,v in row.items() if k!='certificate'}),flush=True)
    result=dict(status='momentum_initialization_diagnostic_complete',static_initial_states_evaluated=len(rows),actual_earth_initialized_integrations_started=0,
        legacy_benchmark_attempts_added=0,monthly_rainfall_skill_evaluated=False,adoption=False,literal_plan_sha256=file_hash(path),results=rows,
        scope='Fixed thermal/water fields; convex initial-wind tradeoff and formal steady momentum solve. No timestep, phase/convection step, coupled equilibrium, full normal-mode initialization or rainfall optimization.')
    write_json(out/'verification.json',result)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();run(args.plan,args.out)
