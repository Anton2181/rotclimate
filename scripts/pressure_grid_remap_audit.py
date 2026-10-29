"""Frozen static pressure-grid transfer audit; starts no climate integrations."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,write_json
from rotclimate.pressure_remap import pressure_overlap,remap_moist_column
from rotclimate.pressure_coordinate import pressure_coordinate
from rotclimate.fast_liquid_phase import enthalpy_phase_fast
from rotclimate.surface_coupling import SurfaceState,receive_precipitation,surface_enthalpy
from rotclimate.pressure_moist import gas_energy
from rotclimate.column_thermodynamics import CP,RD,G


def run(path,out):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal static audit protocol first')
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve every prior static audit')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);rows=[]
    for region,input_path in plan['inputs'].items():
        with np.load(ROOT/input_path) as f:a={k:f[k] for k in f.files}
        for parts in plan['lowest_cell_parts']:
            old=a['pressure_edges'];edges=np.r_[np.linspace(old[0],old[1],parts+1),old[2:]]
            op=pressure_overlap(old,edges);coord=pressure_coordinate(edges)
            thermal=remap_moist_column(a['temperature'],a['vapor'],old,edges,phase_solver=enthalpy_phase_fast)
            u,lu=op.velocity(a['u']);v,lv=op.velocity(a['v'])
            initial_surface=SurfaceState(a['surface_temperature'],a['surface_liquid'],a['substrate_capacity'])
            surface=receive_precipitation(initial_surface,thermal.rain_kg_m2,thermal.rain_enthalpy_j_m2)
            m0=op.source_mass_kg_m2[:,None,None];m1=op.target_mass_kg_m2[:,None,None]
            kinetic=lambda velu,velv,m:.5*((m*velu[:,:,1:-1]**2).sum()+(m*velv[:,1:-1]**2).sum())
            e0=float(gas_energy(a['temperature'],a['vapor'],m0).sum()+surface_enthalpy(initial_surface).sum()+kinetic(a['u'],a['v'],m0))
            e1=float(gas_energy(thermal.temperature_k,thermal.vapor_kg_m2,m1).sum()+surface_enthalpy(surface).sum()+kinetic(u,v,m1))
            w0=float(a['vapor'].sum()+a['surface_liquid'].sum());w1=float(thermal.vapor_kg_m2.sum()+surface.liquid_kg_m2.sum())
            port_u_error=float(abs((m0*a['u']).sum(0)-(m1*u).sum(0)).max());port_v_error=float(abs((m0*a['v']).sum(0)-(m1*v).sum(0)).max())
            height=CP/G*thermal.temperature_k[0]*((edges[0]/coord.centers_pa[0])**(RD/CP)-1.)
            values=dict(energy_relative_error=abs(e1-e0)/abs(e0),water_relative_error=abs(w1-w0)/w0,maximum_u_momentum_integral_error_kg_m_s=port_u_error,maximum_v_momentum_integral_error_kg_m_s=port_v_error,maximum_absolute_face_kinetic_loss_j_m2=float(max(abs(lu).max(),abs(lv).max())))
            assert values['energy_relative_error']<plan['energy_water_relative_tolerance'] and values['water_relative_error']<plan['energy_water_relative_tolerance']
            assert max(port_u_error,port_v_error)<plan['momentum_absolute_tolerance_kg_m_s']
            assert values['maximum_absolute_face_kinetic_loss_j_m2']<plan['refinement_kinetic_tolerance_j_m2']
            filename=out/(region+f'_split{parts}.npz')
            np.savez_compressed(filename,pressure_edges=edges,temperature=thermal.temperature_k,vapor=thermal.vapor_kg_m2,u=u,v=v,surface_temperature=surface.temperature_k,surface_liquid=surface.liquid_kg_m2,substrate_capacity=surface.substrate_capacity_j_m2_k,conversion_rain=thermal.rain_kg_m2,conversion_rain_enthalpy=thermal.rain_enthalpy_j_m2,reference_height=height,land=a['land'],latitude=a['latitude'],longitude=a['longitude'])
            row=dict(region=region,lowest_cell_parts=parts,source_cells=len(old)-1,target_cells=len(edges)-1,source_reference_height_mean_m=float(a['reference_height'].mean()),target_reference_height_mean_m=float(height.mean()),target_reference_height_min_m=float(height.min()),target_reference_height_max_m=float(height.max()),mean_conversion_rain_mm=float(thermal.rain_kg_m2.mean()),maximum_surface_temperature_change_k=float(abs(surface.temperature_k-initial_surface.temperature_k).max()),actual_checks=values,thermal_certificate=thermal.certificate,fields_sha256=file_hash(filename));rows.append(row);print(json.dumps(row),flush=True)
    write_json(out/'verification.json',dict(status='static_pressure_remap_complete',actual_earth_initialized_integrations_started=0,static_transfer_cases=len(rows),results=rows,literal_plan_sha256=file_hash(path),physics_adoption=False,recalibration=False,monthly_skill=False,scope='Initial arrays only, no model.advance or climate integration. Same column pressure lids, total water/enthalpy, momentum and resolved KE under piecewise-constant refinement. Target phase rain and liquid enthalpy returned to same surface. Hydrostatic balance, forcing response and rainfall accuracy not tested.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    try:run(a.plan,a.out)
    except Exception as error:
        a.out.mkdir(parents=True,exist_ok=True)
        failure=a.out/'audit_failure.json'
        if not failure.exists():write_json(failure,dict(error=repr(error),traceback=traceback.format_exc(),actual_earth_initialized_integrations_started=0))
        raise
