"""Verify and publish every declared dry subsystem outcome and step-size contrast."""
from pathlib import Path
import argparse,json,shutil,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from monitor_extended_spinup import load
from local_benchmark_protocol import file_hash,write_json
from rotclimate.terrain_hydrostatics import TerrainPressureGrid
from rotclimate.terrain_apertures import horizontal_apertures
from rotclimate.column_thermodynamics import CP


def publish(source,out):
    source=source.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=True);receipt=json.loads((source/'verification.json').read_text());plan=json.loads((source/'frozen_plan.json').read_text());literal=ROOT/'calibration/terrain_dry_20261029/plan.json';assert literal.read_bytes()==(source/'frozen_plan.json').read_bytes();assert receipt['literal_plan_sha256']==file_hash(literal)
    for name,digest in plan['sources'].items():assert file_hash(ROOT/name)==digest,name
    assert len(receipt['results'])==6;assert {(r['region'],r['dt_s']) for r in receipt['results']}=={(region,dt) for region in plan['regions'] for dt in plan['timesteps_s']}
    geo=load(ROOT/'output/terrain_geometry_20261029/terrain_geometry.npz');records={};fields={};rows=[];sensitivity={};maps,axes=plt.subplots(3,3,figsize=(14,11));trace,tx=plt.subplots(3,2,figsize=(12,10))
    for index,region in enumerate(plan['regions']):
        initial_by_dt={};finals={}
        for dt in plan['timesteps_s']:
            case=next(r for r in receipt['results'] if r['region']==region and r['dt_s']==dt);folder=source/f'{region}_{dt}';initial=load(folder/'initial.npz');last=load(folder/'final_or_partial.npz');assert file_hash(folder/'initial.npz')==case['initial_sha256'];assert file_hash(folder/'final_or_partial.npz')==case['fields_sha256'];initial_by_dt[dt]=initial
            p=initial['pressure_edges'];mass=initial['layer_mass'];grid=TerrainPressureGrid(p,.5*(p[:-1]+p[1:]),mass,p[0],float(p[-1,0,0]));ports=horizontal_apertures(grid);checks=[];e0=(np.longdouble(CP)*mass.astype(np.longdouble)*initial['temperature'].astype(np.longdouble)).sum();ke0=.5*((ports.east_kg_m2*initial['east_speed']**2).sum()+(ports.south_kg_m2*initial['south_speed']**2).sum())
            def verify(a):
                stable_change=float((CP*mass*(a['temperature']-initial['temperature'])).sum());ke=float(.5*((ports.east_kg_m2*a['east_speed']**2).sum()+(ports.south_kg_m2*a['south_speed']**2).sum())-ke0);full_change=float((np.longdouble(CP)*mass.astype(np.longdouble)*a['temperature'].astype(np.longdouble)).sum()-e0)
                return dict(stable_actual_gas_change_j_m2_sum=stable_change,actual_kinetic_change_j_m2_sum=ke,stable_actual_energy_residual_j_m2_sum=stable_change+ke,extended_full_state_energy_residual_j_m2_sum=full_change+ke,full_vs_stable_enthalpy_difference_j_m2_sum=full_change-stable_change)
            for hour in range(1,7):
                path=folder/f'hour_{hour}.npz'
                if not path.exists():break
                state=load(path);saved=json.loads((folder/f'hour_{hour}.json').read_text());check=verify(state);assert abs(check['stable_actual_energy_residual_j_m2_sum']-saved['actual_energy_residual_since_initial_j_m2_sum'])<1e-7;assert abs(check['full_vs_stable_enthalpy_difference_j_m2_sum'])<2e-5;checks.append(dict(hour=hour,fields_sha256=file_hash(path),**check))
            final_check=verify(last)
            if case['status']=='completed':
                assert len(checks)==6 and case['completed_steps']==plan['duration_s']//dt
                saved=load(folder/'hour_6.npz');assert all(saved[k].tobytes()==last[k].tobytes() for k in last)
                finals[dt]=last
            records[f'{region}_{dt}']=dict(status=case['status'],completed_steps=case['completed_steps'],independent_hourly_state_energy_checks=checks,final_or_partial=final_check,maximum_runtime_step_energy_residual_j_m2_sum=max([abs(r['certificate']['actual_energy_residual_j_m2_sum']) for r in case['history']]+[0.]))
            for label,a in [('initial',initial),('final_or_partial',last)]:fields.update({f'{region}_{dt}_{label}_{k}':v for k,v in a.items()})
            color='#207da8' if dt==900 else '#cd9137';times=[r['time_s']/3600 for r in case['history']];tx[index,0].plot(times,[r['actual_energy_residual_since_initial_j_m2_sum'] for r in case['history']],color=color,label=f'{dt}s');tx[index,1].plot(times,[r['actual_kinetic_energy_j_m2_sum'] for r in case['history']],color=color,label=f'{dt}s')
            rows.append(f'<tr><td>{region.replace("_"," ")}</td><td>{dt}</td><td>{case["status"]}</td><td>{case["completed_steps"]}</td><td>{final_check["stable_actual_energy_residual_j_m2_sum"]:.2e}</td><td>{final_check["actual_kinetic_change_j_m2_sum"]:.3f}</td></tr>')
        a0,b0=initial_by_dt[900],initial_by_dt[450];assert all(a0[k].tobytes()==b0[k].tobytes() for k in a0)
        lon,lat=a0['longitude'],a0['latitude'];land=geo[region+'_land'];mass=a0['layer_mass'];ref900=a0['temperature'].copy();ref900[0,:,ref900.shape[2]//2:]-=1.
        values=[None,None,None]
        if 900 in finals:values[0]=finals[900]['temperature'][0]-ref900[0]
        if 450 in finals:values[1]=finals[450]['temperature'][0]-ref900[0]
        if len(finals)==2:
            delta=finals[900]['temperature']-finals[450]['temperature'];values[2]=delta[0];sensitivity[region]=dict(actual_temperature_mass_weighted_rms_difference_k=float(np.sqrt(np.sum(mass*delta**2)/mass.sum())),maximum_temperature_difference_k=float(abs(delta).max()))
        for col,(value,title) in enumerate(zip(values,['900s lowest-layer temperature departure','450s lowest-layer temperature departure','900s −450s lowest-layer temperature'])):
            ax=axes[index,col];ax.set_title(region.replace('_',' ')+': '+title,fontsize=9)
            if value is None:ax.text(.5,.5,'Case incomplete; retained',transform=ax.transAxes,ha='center');ax.set_axis_off();continue
            limit=max(float(max(abs(v).max() for v in values[:2] if v is not None)),.01) if col<2 else max(float(abs(value).max()),1e-6);image=ax.pcolormesh(lon,lat,value,shading='nearest',cmap='RdBu_r',vmin=-limit,vmax=limit);coast=ax.contour(lon,lat,land.astype(float),levels=[.5],colors='#203d4a',linewidths=1.);coast.set_path_effects([pe.withStroke(linewidth=2.7,foreground='white')]);maps.colorbar(image,ax=ax,shrink=.75,label='K');ax.set_xlabel('Longitude');ax.set_ylabel('Latitude')
        for ax,title,ylabel in zip(tx[index],['Gas enthalpy + kinetic energy residual','Kinetic energy developed'],['J/m² summed over cells','J/m² summed over cells']):ax.set_title(region.replace('_',' ')+': '+title,fontsize=10);ax.set_xlabel('Synthetic model hours');ax.set_ylabel(ylabel);ax.grid(alpha=.2);ax.legend(fontsize=8)
    maps.suptitle('Closed dry terrain subsystem: six-hour thermal perturbation response',fontsize=14);maps.text(.5,.01,'Synthetic reference +1K eastern bottom-layer perturbation • zero initial wind • native terrain/Coriolis • no vapor, rain or climate skill claim',ha='center',fontsize=9);maps.tight_layout(rect=(0,.035,1,.95));maps.savefig(out/'terrain_dry_maps.png',dpi=145);plt.close(maps)
    trace.suptitle('Actual state energy and pressure-driven motion: all six declared controls',fontsize=14);trace.text(.5,.01,'Closed dry pressure/Coriolis/enthalpy subsystem • independent hourly saved-state audits • residual never redistributed as heat',ha='center',fontsize=9);trace.tight_layout(rect=(0,.035,1,.95));trace.savefig(out/'terrain_dry_energy.png',dpi=145);plt.close(trace)
    np.savez_compressed(out/'terrain_dry_fields.npz',**fields);result=dict(status='all_declared_dry_controls_published',synthetic_native_geometry_integrations_started=receipt['synthetic_native_geometry_integrations_started'],synthetic_integrations_completed=receipt['synthetic_integrations_completed'],earth_climate_initialized_integrations_started=0,new_integrations_started_by_publication=0,independent_checks=records,timestep_sensitivity=sensitivity,source_receipt_sha256=file_hash(source/'verification.json'),publisher_sha256=file_hash(Path(__file__)),fields_sha256=file_hash(out/'terrain_dry_fields.npz'),figure_sha256={name:file_hash(out/name) for name in ['terrain_dry_maps.png','terrain_dry_energy.png']},physics_adoption=False,scope=receipt['scope']);write_json(out/'publication.json',result)
    dest=ROOT/'atlases/climate_accuracy/data'
    for name in ['terrain_dry_fields.npz','terrain_dry_maps.png','terrain_dry_energy.png']:shutil.copyfile(out/name,dest/name)
    write_json(dest/'terrain_dry.json',dict(protocol=plan,runs=receipt,publication=result));figures=''
    for name,caption in [('terrain_dry_energy.png','Pressure-driven motion develops while gas enthalpy plus kinetic energy remains balanced. Values sum cell-mean powers/energies over this numerical domain.'),('terrain_dry_maps.png','Lowest atmospheric layer temperature relative to the synthetic reference at six hours; this is not surface skin temperature or measured climate. Shared900/450s scales within each region, separate difference scale.')]:
        with Image.open(out/name) as im:w,h=im.size
        figures+=f'<figure><a href="data/{name}"><img src="data/{name}" width="{w}" height="{h}" loading="lazy" alt="{caption}"></a><figcaption>{caption}</figcaption></figure>'
    section=f'''<!--terrain-dry-start--><section aria-labelledby="terrain-dry-h"><h2 id="terrain-dry-h">Coupled dry terrain dynamics: six-hour controls</h2><p>All six declared closed dry trajectories are retained: {receipt['synthetic_integrations_completed']} complete. The new subsystem couples native variable-mass heat transport, hydrostatic pressure forces, continuity-derived vertical compression/expansion, a column-mass constraint and energy-skew Coriolis rotation. It starts from a synthetic common reference with a1K eastern bottom-layer anomaly and zero wind.</p>{figures}<div class="table"><table><caption>Complete or failed partial outcomes, independently checked against saved hourly states</caption><thead><tr><th>Region</th><th>Step s</th><th>Status</th><th>Accepted steps</th><th>Energy residual J/m² sum</th><th>Developed KE J/m² sum</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><p>The original state arrays match exactly between900/450s per region. Full extended-precision state enthalpy differences independently agree with the stable actual-field energy differences. Initial mass projection is absent here because wind starts at zero. A column-constant reference potential is absorbed into the constraint pressure gauge; it does zero work on admissible flow. No heat is added to repair the energy residual.</p><p class="note">These are six synthetic-state/native-geometry subsystem integrations, counted separately from Earth climate trials. No nonlinear momentum advection, vapor or rain, open regional boundaries, radiation, surface heat/water exchange, smooth terrain metric, calibration or physics adoption. Numerical qualification is not rainfall skill. The normal atlas fields and active frozen monthly rainfall trials remain unchanged.</p><p><a href="data/terrain_dry.json">All plans, outcomes, per-step certificates and independent state checks</a> · <a href="data/terrain_dry_fields.npz">Initial and final/partial native fields</a> · <a href="../../reports/TERRAIN_DRY_20261029.md">Dry subsystem derivation, checks and limitations</a></p></section><!--terrain-dry-end-->'''
    page=ROOT/'atlases/climate_accuracy/index.html';text=page.read_text();start,end='<!--terrain-dry-start-->','<!--terrain-dry-end-->'
    if start in text:before,tail=text.split(start,1);_,after=tail.split(end,1);text=before+section+after
    else:text=text.replace('<!--research-list-start-->',section+'\n<!--research-list-start-->',1)
    page.write_text(text);report='# Coupled dry terrain subsystem controls\n\n'+result['scope']+'\n\nSix declared trajectories were attempted, using the actual regional height grids and a synthetic common dry reference plus1K bottom-layer perturbation. All initial winds are zero. '+str(result['synthetic_integrations_completed'])+' completed. The independent publication starts zero additional integrations.\n\n| Region | Step s | Status | Steps | Actual final energy residual J/m² sum |\n|---|---:|---|---:|---:|\n'
    for name,row in records.items():report+=f'| {name.rsplit("_",1)[0]} | {name.rsplit("_",1)[1]} | {row["status"]} | {row["completed_steps"]} | {row["final_or_partial"]["stable_actual_energy_residual_j_m2_sum"]:.8g} |\n'
    report+='\nThe scalar state is the dry-mass-weighted layer-mean temperature. Its analytic reference mean is integrated in pressure; anomalies reconstruct the same hydrostatic profile used by pressure and compression. Momentum uses implicit midpoint pressure and energy-skew Coriolis forces with a saddle constraint for fixed column mass. Actual layer continuity generates vertical transfer; implicit upwind native enthalpy transport is conservative. Nonlinear temperature coupling is iterated under the declared tolerance; unsuccessful steps fail and retain the last accepted state.\n\nThe reference column-potential gradient is a barotropic constraint gradient. Absorbing it into the constraint gauge avoids tiny-rest-force cancellation without changing admissible motion or adding heat. A dedicated test verifies that it does zero work on constrained winds. The inherited refined saddle solver retains its8-epsilon acceptance limit.\n\nEvery available hourly state and final/partial field is hash-checked. Its actual energy change is independently reconstructed from temperatures, dry masses and native port speeds. Extended-precision full-state enthalpy differences agree with stable actual-state differences. Per-step runtime certificates and all six outcomes are downloadable. No residual is redistributed to repair heat or kinetic energy.\n\nTimestep sensitivity in final temperature (mass-weighted RMS K;900s versus450s):\n'
    for name,v in sensitivity.items():report+=f'- {name}: {v["actual_temperature_mass_weighted_rms_difference_k"]:.7g}; maximum {v["maximum_temperature_difference_k"]:.7g}.\n'
    report+='\nA small energy residual does not demonstrate spatial or time-step convergence, correct Earth winds, or accurate rain. These are six synthetic dry subsystem integrations, not six new climate-initialized Earth trials. The partial380-hPa pressure top, closed boundaries, staircase geometry, absent nonlinear momentum, vapor/phase physics and surface/radiative forcing limit interpretation. No baseline replacement or normal-atlas field changes.\n';(ROOT/'reports/TERRAIN_DRY_20261029.md').write_text(report);print(json.dumps(dict(completed=result['synthetic_integrations_completed'],sensitivity=sensitivity),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();publish(a.source,a.out)
