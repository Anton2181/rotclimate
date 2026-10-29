"""Frozen Earth-input smoke tests; not climate calibration or skill scoring."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate.pressure_initialization import initialize_archived_column,select_recorded_day
from rotclimate.pressure_moist import PressureMoistModel,gas_energy
from rotclimate.convective_adjustment import advance_with_convection
from local_benchmark_protocol import file_hash,write_json


def prepare(plan,region):
    declaration=plan['regions'][region];path=ROOT/declaration['archive'];stride=plan['horizontal_stride']
    with np.load(path) as archive:
        index=select_recorded_day(archive['days'],archive['scored_indices'],archive['solved_days'],declaration['model_day'])
        # Deliberately read only simulated states, declared calendar and map
        # geometry. No observed rain/temperature, reference wind or humidity.
        t=archive['closure_T'][index,::stride,::stride];water=archive['water'][index,:,::stride,::stride]
        elevation=archive['elevation'][::stride,::stride];latitude=archive['latitude'][::stride,::stride]
        longitude=archive['longitude'][::stride,::stride];land=archive['land'][::stride,::stride]
    state=initialize_archived_column(t,water[0],water[1],elevation,plan['pressure_edges_pa'],lapse_k_m=plan['lapse_k_m'],cap_temperature_k=plan['isothermal_cap_k'])
    geometry=dict(latitude=latitude,longitude=longitude,land=land,elevation=elevation,archived_surface_temperature_c=t,
        archived_lower_water=water[0],archived_upper_water=water[1])
    return state,geometry,index


def run(plan_path,out,preflight=False):
    plan_path=plan_path.resolve();plan=json.loads(plan_path.read_text())
    for n,h in plan['sources'].items():
        if file_hash(ROOT/n)!=h:raise ValueError('Changed frozen source/input: '+n)
    prepared={}
    for region in plan['regions']:
        state,geometry,index=prepare(plan,region);prepared[region]=(state,geometry,index)
    if preflight:
        result=dict(status='prepared_no_integrations',actual_earth_initialized_integrations_started=0,
            cases={n:dict(source_index=i,shape=list(s.temperature_k.shape),minimum_temperature_k=float(s.temperature_k.min()),
                maximum_temperature_k=float(s.temperature_k.max()),initial_conversion_mean_rain_mm=float(s.initial_rain_kg_m2.mean()),
                certificate=s.certificate) for n,(s,g,i) in prepared.items()},plan_sha256=file_hash(plan_path))
        print(json.dumps(result,indent=2));return result
    relative=str(plan_path.relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)!=plan_path.read_bytes():raise ValueError('Commit the exact literal pilot plan first')
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous pilot attempts; choose a new output folder')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan)
    results=[];started=0
    for region,(initial,geo,index) in prepared.items():
        directory=out/region;directory.mkdir()
        np.savez_compressed(directory/'initial.npz',**geo,raw_temperature=initial.raw_temperature_k,raw_vapor=initial.raw_vapor_kg_m2,
            temperature=initial.temperature_k,vapor=initial.vapor_kg_m2,initial_conversion_rain=initial.initial_rain_kg_m2,
            initial_conversion_rain_enthalpy=initial.initial_rain_enthalpy_j_m2)
        write_json(directory/'initial.json',dict(source_archive=plan['regions'][region]['archive'],source_archive_sha256=plan['sources'][plan['regions'][region]['archive']],
            model_day=plan['regions'][region]['model_day'],source_index=index,certificate=initial.certificate,fields_sha256=file_hash(directory/'initial.npz')))
        for dt in plan['timesteps_s']:
            key=str(dt);row=dict(region=region,dt_s=dt,model_day=plan['regions'][region]['model_day'],status='not_started',started=False)
            state=None;rain=None;rain_h=None;history=[]
            try:
                f=2*plan['rotation_rate_s']*np.sin(np.deg2rad(geo['latitude']))
                model=PressureMoistModel(plan['pressure_edges_pa'],geo['latitude'].shape,plan['cell_m'],f,momentum_drag_s=plan['momentum_drag_s'])
                state=model.initial_state(initial.temperature_k,initial.vapor_kg_m2);started+=1;row['started']=True
                rain=np.zeros(model.shape);rain_h=np.zeros(model.shape);history=[]
                for step in range(int(plan['duration_s']/dt)):
                    state=advance_with_convection(model,state,dt,relaxation_s=plan['convection_relaxation_s'],
                        neutral_tolerance_k=plan['neutral_tolerance_k'],max_sweeps=plan['maximum_convective_sweeps'],
                        max_iterations=plan['maximum_coupling_iterations'])
                    rain+=state.ground_rain_kg_m2;rain_h+=state.ground_rain_enthalpy_j_m2;c=state.certificate
                    history.append(dict(time_s=(step+1)*dt,mean_run_rain_mm=float(rain.mean()),
                        mean_temperature_k=float(state.temperature_k.mean()),minimum_temperature_k=float(state.temperature_k.min()),maximum_temperature_k=float(state.temperature_k.max()),
                        peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max())),
                        energy_error_j_m2=c['actual_combined_energy_rain_source_residual_j_m2'],water_error_kg_m2=c['actual_combined_water_rain_source_residual_kg_m2'],
                        convective_pairs=c['convective_adjustment']['adjusted_pairs'],coupling_iterations=c['dynamics_before_adjustment']['iterations']))
                fields=directory/(key+'.npz');np.savez_compressed(fields,temperature=state.temperature_k,vapor=state.vapor_kg_m2,
                    u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h)
                face_mass=model.mass[:,0,0,None,None];kinetic=.5*(np.sum(face_mass*state.u_east[:,:,1:-1]**2)+np.sum(face_mass*state.v_south[:,1:-1]**2))
                before=gas_energy(initial.temperature_k,initial.vapor_kg_m2,model.mass).sum()
                after=gas_energy(state.temperature_k,state.vapor_kg_m2,model.mass).sum()+kinetic+rain_h.sum()
                water_error=state.vapor_kg_m2.sum()+rain.sum()-initial.vapor_kg_m2.sum()
                row.update(status='completed',steps=len(history),history=history,fields_sha256=file_hash(fields),
                    relative_total_energy_error=float(abs(after-before)/max(abs(before),1.)),
                    relative_water_rain_error=float(abs(water_error)/max(float(initial.vapor_kg_m2.sum()),1.)),
                    mean_run_rain_mm=float(rain.mean()),mean_initial_conversion_rain_mm=float(initial.initial_rain_kg_m2.mean()),
                    peak_level_velocity_ms=float(max(abs(state.u_east).max(),abs(state.v_south).max())))
            except Exception as error:
                row.update(status='failed',error=repr(error),traceback=traceback.format_exc(),completed_steps=len(history),history=history)
                if state is not None and rain is not None:
                    partial=directory/(key+'_partial.npz')
                    np.savez_compressed(partial,temperature=state.temperature_k,vapor=state.vapor_kg_m2,u=state.u_east,v=state.v_south,rain=rain,rain_enthalpy=rain_h)
                    row['partial_fields_sha256']=file_hash(partial)
            write_json(directory/(key+'.json'),row);results.append(row)
            print(json.dumps({k:v for k,v in row.items() if k not in ['history','traceback']}),flush=True)
    receipt=dict(status='earth_input_smoke_test_complete',actual_earth_initialized_integrations_started=started,
        integrations_completed=sum(r['status']=='completed' for r in results),legacy_earth_benchmark_attempts_added=0,
        monthly_rainfall_skill_evaluated=False,recalibration=False,physics_or_atlas_adoption=False,
        frozen_plan_sha256=file_hash(out/'frozen_plan.json'),literal_committed_plan_sha256=file_hash(plan_path),
        initial_conversion_rain_in_run_totals=False,results=results,
        scope='Archived-model Earth input, terrain flattened by fixed lapse, initially unbalanced/resting, closed six-hour sensitivity. No solar/surface/lateral forcing, observations, wind nudging, climate scoring or adoption. Earth-initialized runs counted separately from legacy benchmark attempts.')
    write_json(out/'verification.json',receipt)
    return receipt


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--preflight',action='store_true');args=ap.parse_args();run(args.plan,args.out.resolve(),args.preflight)
