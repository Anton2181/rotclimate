"""Resume a frozen monthly trajectory at a verified daily checkpoint.

Only the driver bookkeeping is adapted. The forcing, time index, numerical
backend, integration body and literal experiment plan remain unchanged.
"""
from pathlib import Path
import argparse, inspect, json, shutil, sys, textwrap
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import rainfall_month_pilot as month
from local_benchmark_protocol import file_hash,write_json
from monitor_extended_spinup import load,energy


def checked_prefix(folder,region,dt,day):
    initial=load(folder/region/'initial.npz');mass=-np.diff(initial['pressure_edges'])/9.80665
    e0=energy(initial,mass);w0=float(initial['vapor'].sum()+initial['surface_liquid'].sum());cells=initial['land'].size
    daily=[];hashes={};previous=initial
    for number in range(1,day+1):
        stem=folder/region/'forced'/f'day_{number}_{dt}';d=json.loads(stem.with_suffix('.json').read_text());a=load(stem.with_suffix('.npz'))
        assert file_hash(stem.with_suffix('.npz'))==d['fields_sha256']
        assert abs(energy(a,mass)-e0-d['net_external_energy_j_m2']*cells)/abs(e0)<1e-10
        assert abs(a['vapor'].sum()+a['surface_liquid'].sum()-w0+d['net_outward_water_kg_m2']*cells)/w0<1e-10
        assert abs((a['day_rain']-a['surface_liquid']+previous['surface_liquid']).mean()-d['net_evaporation_kg_m2'])<1e-9
        daily.append(d);previous=a
        for path in [stem.with_suffix('.json'),stem.with_suffix('.npz')]:hashes[str(path.relative_to(folder))]=file_hash(path)
    hashes[str((folder/region/'initial.npz').relative_to(folder))]=file_hash(folder/region/'initial.npz')
    return initial,previous,daily,hashes


def run(path,folder,day=None,replay_dest=None):
    path=path.resolve();folder=folder.resolve();plan=json.loads(path.read_text())
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert path.read_bytes()==(folder/'frozen_plan.json').read_bytes()
    assert len(plan['regions'])==1 and plan['scenarios']==['forced'] and len(plan['timesteps_s'])==1
    region=next(iter(plan['regions']));dt=plan['timesteps_s'][0]
    numbers=[int(p.stem.split('_')[1]) for p in (folder/region/'forced').glob(f'day_*_{dt}.json')]
    latest=max(numbers);day=latest if day is None else day
    assert 1<=day<plan['duration_s']//86400
    initial,checkpoint,daily,hashes=checked_prefix(folder,region,dt,day)
    if replay_dest:
        target=replay_dest.resolve();assert not target.exists() or not any(target.iterdir());target.mkdir(parents=True,exist_ok=True)
        for name in ['frozen_plan.json',f'{region}/wind_conversion.json',*hashes]:
            destination=target/name;destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/name,destination)
        folder=target
    else:
        assert day==latest and not (folder/'verification.json').exists()
        assert not (folder/'recovery.json').exists(),'Retain and explicitly qualify each separate recovery'
    receipt=dict(checkpoint_day=day,checkpoint_hashes=hashes,literal_plan_sha256=file_hash(path),recovery_driver_sha256=file_hash(Path(__file__)),new_earth_initializations=0,new_process_segments=1,process_interruption_preserved=not bool(replay_dest),replay_only=bool(replay_dest),history_scope='Original per-step history before the checkpoint was not flushed. All original daily fields and budgets are retained; new history contains continuation steps only.',original_progress=json.loads((folder/'progress.json').read_text()) if (folder/'progress.json').exists() else None)
    write_json(folder/'recovery.json',receipt)

    def restore(model,state,surface):
        for name,value in [('temperature',state.temperature_k),('vapor',state.vapor_kg_m2),('u',state.u_east),('v',state.v_south),('surface_temperature',surface.temperature_k),('surface_liquid',surface.liquid_kg_m2),('substrate_capacity',surface.substrate_capacity_j_m2_k)]:
            np.testing.assert_array_equal(initial[name],value)
        zero=np.zeros(model.shape)
        restored=month.daily.PressureMoistState(checkpoint['temperature'].copy(),checkpoint['vapor'].copy(),checkpoint['u'].copy(),checkpoint['v'].copy(),zero.copy(),zero.copy(),{})
        ground=month.SurfaceState(checkpoint['surface_temperature'].copy(),checkpoint['surface_liquid'].copy(),checkpoint['substrate_capacity'].copy())
        return restored,ground,checkpoint['rain'].copy(),checkpoint['rain_enthalpy'].copy(),daily[-1]['net_external_energy_j_m2'],daily[-1]['net_outward_water_kg_m2'],sum(d['net_evaporation_kg_m2'] for d in daily),list(daily)

    # Exact, checked substitutions affect persistence and loop bounds only.
    # Physics calls and their complete argument lists are untouched.
    source=textwrap.dedent(inspect.getsource(month.daily.run))
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,old
        source=source.replace(old,new)
    replace("    if out.exists() and any(out.iterdir()):raise ValueError('Preserve previous forcing attempts')\n",'')
    replace('directory.mkdir();','directory.mkdir(exist_ok=True);')
    start=source.index('        np.savez_compressed(directory/\'initial.npz\'')
    end=source.index("        p=plan['surface']",start)
    source=source[:start]+source[end:]
    replace('folder.mkdir()','folder.mkdir(exist_ok=True)')
    replace("                    for step in range(plan['duration_s']//dt):", "                    state,surface,rain,rain_h,external_energy,outward_water,net_evap,daily=restore(model,state,surface)\n                    last_daily_rain=rain.copy();last_daily_evap=net_evap\n                    for step in range(resume_day*86400//dt, stop_day*86400//dt):")
    replace("row.update(status='completed',steps=len(history)","row.update(status='completed',steps=(step+1)")
    replace('completed_steps=len(history)','completed_steps=(step if not history else history[-1][\'time_s\']//dt)')
    namespace=dict(month.daily.run.__globals__,prepare=month.prepare,advance_surface_coupled=month.grid.SELECTED.surface_coupled,advance_boundary_with_convection=month.grid.SELECTED.advance_with_convection,restore=restore,resume_day=day,stop_day=day+1 if replay_dest else plan['duration_s']//86400)
    exec(compile(source,'<verified checkpoint continuation>','exec'),namespace)
    namespace['run'](path,folder)
    inherited=folder/'inherited_driver_receipt.json';(folder/'verification.json').rename(inherited);r=json.loads(inherited.read_text())
    r.update(status='checkpoint_replay_finished' if replay_dest else 'calendar_month_regional_rainfall_trial_finished',calendar=plan['calendar'],inherited_driver_receipt_sha256=file_hash(inherited),recovery_sha256=file_hash(folder/'recovery.json'),continuation_segments_added=1,new_earth_initializations_by_recovery=0,process_interruptions_retained=int(not bool(replay_dest)),history_scope=receipt['history_scope'])
    if replay_dest:
        r.update(actual_earth_initialized_integrations_started=0,integrations_completed=0)
        expected=load(Path(a.source).resolve()/region/'forced'/f'day_{day+1}_{dt}.npz');actual=load(folder/region/'forced'/f'day_{day+1}_{dt}.npz')
        differences={k:float(np.max(np.abs(actual[k]-expected[k]))) for k in actual}
        r['next_day_exact_reproduction']={k:actual[k].tobytes()==expected[k].tobytes() for k in actual};r['maximum_absolute_differences']=differences
        assert all(r['next_day_exact_reproduction'].values()),differences
    for name,digest in hashes.items():assert file_hash(folder/name)==digest,name
    write_json(folder/'verification.json',r)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--day',type=int);parser.add_argument('--replay-dest',type=Path);a=parser.parse_args();run(a.plan,a.source,a.day,a.replay_dest)
