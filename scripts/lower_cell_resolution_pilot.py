"""Frozen 24h lower-air-cell resolution and timestep controls, not calibration."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import surface_forcing_pilot as legacy
import open_mean_pilot
from local_benchmark_protocol import file_hash,write_json
from rotclimate.phase_backend import bind_dependencies
from rotclimate.shared_transport_backend import make_shared_transport_backend
from rotclimate.surface_coupling import SurfaceState

SELECTED=make_shared_transport_backend(name='lower_cell_resolution')
wind_preparation=bind_dependencies(open_mean_pilot.prepare,OpenMeanRigidLidModel=SELECTED.model_type)
coarse_preparation=bind_dependencies(legacy.prepare,prepare_wind=wind_preparation)


def prepare(plan,region):
    base,a,old_model,old_state,surface,height,incoming_lw,conversion,kappa_lw,kappa_sw=coarse_preparation(plan,region)
    if plan['lower_cell_parts']==1:return base,a,old_model,old_state,surface,height,incoming_lw,conversion,kappa_lw,kappa_sw
    with np.load(ROOT/plan['remapped_initial_fields']) as f:fields={k:f[k] for k in f.files}
    assert np.array_equal(fields['latitude'],a['latitude']) and np.array_equal(fields['land'],a['land'])
    edges=fields['pressure_edges'];mass=(-np.diff(edges)/9.80665)[:,None,None]
    bu=np.zeros_like(fields['u']);bv=np.zeros_like(fields['v']);bu[:,:,[0,-1]]=fields['u'][:,:,[0,-1]];bv[:,[0,-1]]=fields['v'][:,[0,-1]]
    model=SELECTED.model_type(edges,a['latitude'].shape,base['cell_m'],2*base['rotation_rate_s']*np.sin(np.deg2rad(a['latitude'])),u_boundary=bu,v_boundary=bv,
        external_temperature_k=fields['temperature'],external_mixing_ratio=fields['vapor']/mass,momentum_drag_s=base['momentum_drag_s'])
    # Exact overlap refinement retains facewise column mass and KE. Do not add
    # a new projection or hide its energy in the starting temperature.
    state=model.initial_state(fields['temperature'],fields['vapor'],fields['u'],fields['v']);model._velocity(state.u_east,state.v_south)
    surface=SurfaceState(fields['surface_temperature'],fields['surface_liquid'],fields['substrate_capacity'])
    a=dict(a,temperature=fields['temperature'],vapor=fields['vapor'],initial_conversion_rain=a['initial_conversion_rain']+fields['conversion_rain'],initial_conversion_rain_enthalpy=a['initial_conversion_rain_enthalpy']+fields['conversion_rain_enthalpy'])
    base=dict(base,pressure_edges_pa=edges.tolist());conversion=dict(conversion,grid_refinement=dict(parts=plan['lower_cell_parts'],remapped_fields_sha256=file_hash(ROOT/plan['remapped_initial_fields']),additional_projection=False,static_source='output/pressure_grid_remap_20261029/verification.json'))
    return base,a,model,state,surface,fields['reference_height'],incoming_lw,conversion,kappa_lw,kappa_sw


def run(path,out,preflight=False):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    if preflight:
        rows=[]
        for spec in plan['cases']:
            p=json.loads((ROOT/spec['plan']).read_text());prepared=prepare(p,spec['region']);model=prepared[2]
            rows.append(dict(region=spec['region'],parts=p['lower_cell_parts'],timesteps_s=p['timesteps_s'],levels=model.nz,reference_height_mean_m=float(prepared[5].mean())))
        write_json(out,dict(status='resolution_inputs_prepared_no_integrations',actual_earth_initialized_integrations_started=0,cases=rows,literal_plan_sha256=file_hash(path)));return
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal dynamic resolution protocol first')
    if out.exists() and any(out.iterdir()):raise ValueError('Retain previous resolution attempts')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_protocol.json',plan);rows=[]
    runner=bind_dependencies(legacy.run,prepare=prepare,advance_surface_coupled=SELECTED.surface_coupled,advance_boundary_with_convection=SELECTED.advance_with_convection)
    for spec in plan['cases']:
        folder=out/spec['name'];write_json(out/'progress.json',dict(active=spec,finished_cases=rows))
        try:
            runner(ROOT/spec['plan'],folder);r=json.loads((folder/'verification.json').read_text())
            row=dict(name=spec['name'],region=spec['region'],started=r['actual_earth_initialized_integrations_started'],completed=r['integrations_completed'],receipt_sha256=file_hash(folder/'verification.json'))
        except Exception as error:
            folder.mkdir(parents=True,exist_ok=True);write_json(folder/'driver_failure.json',dict(error=repr(error),traceback=traceback.format_exc()))
            r=json.loads((folder/'verification.json').read_text()) if (folder/'verification.json').exists() else {}
            row=dict(name=spec['name'],region=spec['region'],started=r.get('actual_earth_initialized_integrations_started',0),completed=r.get('integrations_completed',0),error=repr(error))
        rows.append(row);print(json.dumps(row),flush=True)
    write_json(out/'verification.json',dict(status='lower_cell_resolution_attempts_finished',actual_earth_initialized_integrations_started=sum(r['started'] for r in rows),integrations_completed=sum(r['completed'] for r in rows),results=rows,literal_plan_sha256=file_hash(path),monthly_skill=False,recalibration=False,physics_adoption=False,scope='Declared lower-cell refinement, same pressure lids and Earth-like parameters. First24h transient rain and timestep sensitivity only. Static conversion rain excluded from run rainfall. Four-way grid has900/450s controls; sixteen-way grid has900s only, no local timestep convergence claim. Retain all failures/partials.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--preflight',action='store_true');a=p.parse_args();run(a.plan,a.out,a.preflight)
